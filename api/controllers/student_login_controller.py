from api.models.user_course import UserCourse
from api.models.vendor_users import VendorUsers
from api.models.group_instances import GroupInstances
from sqlalchemy import desc
from api import app
import paramiko
import jwt
from pylti1p3.tool_config import ToolConfJsonFile
from lti import ToolProvider
from pylti1p3.session import SessionService
from pylti1p3.cookie import CookieService
from pylti1p3.message_launch import MessageLaunch
from flask_caching import Cache
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest, FlaskCacheDataStorage
import secrets
import requests
from abc import ABCMeta, abstractmethod
import typing as t
from cryptography.hazmat.primitives import serialization
from flask import Blueprint, request, Response, redirect, make_response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
import random
import datetime
import string
from api import db
from api.helpers import crypto
import mysql.connector
from sshtunnel import SSHTunnelForwarder
import os
from api.controllers.configuration_controller import *
from cryptography.fernet import Fernet
from netaddr import *
from smtplib import SMTPException
import smtplib
import time
# Generate a random secret key
secret_key = secrets.token_hex(16)


class Request(metaclass=ABCMeta):
    @abstractmethod
    def _get_request_param(self, key: str) -> str:
        raise NotImplementedError

class RequestsAdapter(Request):
    def __init__(self, url: t.Optional[str] = None, params: t.Optional[t.Dict[str, str]] = None):
        self.url = url
        self.params = params or {}
        self.response = None
        if url:
            # Make the request only if a URL is provided
            self.response = requests.get(self.url, params=self.params)

    def _get_request_param(self, key: str) -> str:
        # If a URL was provided, extract parameters from the response if applicable
        if self.url:
            if self.response is not None:
                # Assuming the parameters are in the query string of the URL
                # or in the response JSON if the response was a JSON response
                return self.params.get(key, '')
        # Handle cases where no URL is provided
        return self.params.get(key, '')

student_login_controller = Blueprint('student_login_controller', __name__)
CORS(student_login_controller)


# def generate_nonce(length=16):
#     return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
current_directory = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(current_directory, '../../files/tool_config.json')
print(str(config_file_path))
if not os.path.isfile(config_file_path):
    raise FileNotFoundError(f"LTI tool config file not found: {config_file_path}")

tool_conf = ToolConfJsonFile(config_file_path)

# Brightspace LTI configuration
ISSUER = 'https://apustest.brightspace.com'
KEYSET_URL = 'https://apustest.brightspace.com/d2l/.well-known/jwks'
AUTH_TOKEN_URL = 'https://auth.brightspace.com/core/connect/token'
AUDIENCE = 'https://api.brightspace.com/auth/token'

CLIENT_ID = 'db0ad402-e9f1-4f7e-96b8-6ec9a3f44d49'
DEPLOYMENT_ID = 'cc1f7c67-6209-477d-bef8-0e32cfb98cd1'
# # CLIENT_SECRET = 'your-client-secret'
# REDIRECT_URI = 'https://idp.securitycentric.net/oauth2/callback'
# AUTH_URL = 'https://auth.brightspace.com/core/connect/authorize'
# TOKEN_URL = 'https://auth.brightspace.com/core/connect/token'
# JWKS_URL = 'https://auth.brightspace.com/core/connect/jwks'
# # In-memory storage for state and nonce
# state_nonce_store = {}
# @student_login_controller.route('/callback')
# def callback():
#     state = request.args.get('state')
#     code = request.args.get('code')
#     nonce = state_nonce_store.get(state)

#     if not nonce:
#         return 'Invalid state or nonce', 400

#     token_response = requests.post(TOKEN_URL, data={
#         'grant_type': 'authorization_code',
#         'code': code,
#         'redirect_uri': REDIRECT_URI,
#         'client_id': CLIENT_ID,
#         # 'client_secret': CLIENT_SECRET,
#     })
#     token_response_data = token_response.json()
#     id_token = token_response_data.get('id_token')

#     if not id_token:
#         return 'Error fetching id_token', 400

#     # Fetch JWKS and decode the token
#     jwks_response = requests.get(JWKS_URL)
#     jwks = jwks_response.json()
#     public_key = RSAAlgorithm.from_jwk(jwks['keys'][0])
#     try:
#         decoded_token = jwt.decode(id_token, public_key, algorithms=['RS256'], audience=CLIENT_ID)
#     except jwt.ExpiredSignatureError:
#         return 'Token has expired', 400
#     except jwt.InvalidTokenError:
#         return 'Invalid token', 400

#     if decoded_token.get('nonce') != nonce:
#         return 'Nonce mismatch error', 400

#     # Cleanup state and nonce
#     del state_nonce_store[state]

#     # Establish session or return user information
#     return jsonify(decoded_token)


def apus_lab_url_creation(access_code,portal,first_name,last_name,email,os_env_key,os_env_guac_user,os_env_guac_pass,os_env_guac_host,os_env_guac_host2,token):
    try:
        link = ""
        course_name = ""
        ucid = -1
        log = api.models.SCLogs({
            "log": 'Starting the apus_lab_url_creation' + str(access_code) + '  ' + str(portal) + '  ' + str(first_name) + '  ' + str(last_name) + '  ' + str(email) +
            '  ' + str(os_env_key) + '  ' + str(os_env_guac_user) + '  ' + str(os_env_guac_pass) + '  ' + str(os_env_guac_host) + '  ' + str(os_env_guac_host2) 
        })
        db.session.add(log)
        db.session.commit()
        designated_host=''
        connection_broker=''
        data = {}
        profile_user_id = None 
        data['access_code'] = access_code 
        data['portal'] = portal  
        data['uid'] = str(first_name)+"_"+str(last_name)
        if not data['uid']:
            return Response(json.dumps({
                    'Error': "Invalid uid"
                }), status=400)                
        code = api.models.AccessCodes.query.filter_by(email=email,course_name='course-v1:APUS-ISSC242').first()
        if code.status == -1:
            return Response(json.dumps({
                    'Error': "Access code has expired"
                }), status=400)
        if not code.course_name or (type(code.course_name) is str and code.course_name.strip() == ''):
            return Response(json.dumps({
                    'Error': "Invalid Course"
                }), status=400)        
        if(code.status==0):
            code.status=1
            db.session.commit()
            db.session.refresh(code)
        email=''
        if code:
            email=code.email

            
                      
        data['user_name'] = code.vendor_name
        if not data['user_name']:
            return Response(json.dumps({
                    'Error': "Invalid Username"
                }), status=400)
        log = api.models.SCLogs({"log": 'line======>1285'})
        db.session.add(log)
        db.session.commit()    
        data['course_name'] = str(code.course_name)+'+001'
        data['course_name'] = data['course_name'].replace(" ", "+")    
        course_name = str(data['course_name']).replace(" ","_") 
        course_check_name = course_name.split('+')[0]
        course_check_series = course_name.split('+')[1]
        course_check_series_filter = course_check_series[:5] #40001/40002
        log = api.models.SCLogs({"log":'course_check_name ' + str(course_check_name)+ '  ' + str(course_check_series) + '    ' + str(course_check_series_filter)})
        db.session.add(log)
        db.session.commit()        
        
        temp_course=''
        course_start_series = ''
        all_course = api.models.Courses.query.all()
        for a in all_course:
            if(a.course_series_start != '' and a.course_series_end != '' ):
                if int(a.course_series_start) <= int(course_check_series_filter) and int(a.course_series_end) >= int(course_check_series_filter):
                    temp_course = a.course_name
                    course_start_series = a.course_series_start
            
        print('temp course ==>',temp_course)
        if temp_course == '':
            temp_course = data['course_name']
            if temp_course.endswith('+001'):
                temp_course = data['course_name'].split('+001')[0]
            course_check_series = 0
            
        registered_course_check = course_check_name+"+"+course_start_series
        if course_start_series != '':
            registered_course_check = course_check_name+"+"+course_start_series
        else:
            registered_course_check = course_check_name
        print(registered_course_check,course_check_series)  
        odv=""
        odv_opt=""
        
        course = api.models.Courses.query.filter_by(vendor_name=data['user_name'] ,course_name=temp_course).first()   
        if course:            
            active = course.course_activation
            static = course.static_file
            series_start = course.course_series_start
            series_end = course.course_series_end
            user =  api.models.Users.query.filter_by(name=data['user_name']).first()
            if not user:
                return Response(json.dumps({
                    'Error': "Invalid Vendor"
                }), status=400)
            log = api.models.SCLogs({"log": 'line======>1343'})
            db.session.add(log)
            db.session.commit()
            user_cou = api.models.UserCourse.query.filter_by(user_name=data['user_name']+"_"+str(data["uid"])+"_"+temp_course,email=code.email).first()
            inst_name=''
            ins_name=''
            if user_cou:
                inst_name = user_cou.instance_name.split("_")[1]
                ins_name = user_cou.instance_name
                
            print(">>>>>>",data['user_name']+"_"+str(inst_name)+"_"+str(data["uid"])+"_"+temp_course)    
            vend_user = db.session.query(api.models.VendorUsers).filter_by(username=data['user_name']+"_"+str(inst_name)+"_"+str(data["uid"])+"_"+temp_course).filter_by(status=True).first()
            #log
            log = api.models.SCLogs({"log": 'VendorUserFilter ' + str(data['user_name']+"_"+str(inst_name)+"_"+str(data["uid"])+"_"+temp_course) + 
            'GroupInstance filter ' + str(ins_name) + 'UseCourse Filter ' + str(data['user_name']+"_"+str(data["uid"])+"_"+temp_course)})
            db.session.add(log)
            db.session.commit()    
            five_mins_before_now = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
            log = api.models.SCLogs({"log": str(five_mins_before_now)+ '  ' + '   ' + str(datetime.datetime.utcnow()) + '   ' + str(datetime.datetime.now())})
            db.session.add(log)
            db.session.commit()   
            GroupInstances = api.models.GroupInstances 
            instance = None       
            group = api.models.VmGroups.query.filter_by(group_name=temp_course).first() 
            if not group:
                return Response(json.dumps({
                    'Error': 'EVM1: Failed to launch course, please contact admin!'
                }), status=400) 
            access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
            print("ACCESS TOKEN",access_token)                               
            if vend_user:
                instance = db.session.query(api.models.GroupInstances)\
                .filter(GroupInstances.name==ins_name).filter(GroupInstances.status==1)\
                .filter(GroupInstances.is_assigned.is_(True)).first()     
            if not instance:
                instance = db.session.query(api.models.GroupInstances)\
                .filter(GroupInstances.name==ins_name).filter(GroupInstances.status==1)\
                .filter(GroupInstances.is_assigned.is_(False))\
                .filter((GroupInstances.lab_end_session<five_mins_before_now) | (GroupInstances.lab_end_session==None)).first()
                log = api.models.SCLogs({"log":'GroupInstance 281 apus_lab_url_creation ---->>> ' + str(instance) +  '   '  + str(group.id) +  '   '  + str(ins_name) })
                db.session.add(log)
                db.session.commit()
                if not instance:
                    instance = db.session.query(api.models.GroupInstances)\
                    .filter(GroupInstances.group_id==group.id).filter(GroupInstances.status==1)\
                    .filter(GroupInstances.is_assigned.is_(False))\
                    .filter((GroupInstances.lab_end_session<five_mins_before_now) | (GroupInstances.lab_end_session==None)).first()
                    if not instance:
                        return Response(json.dumps({
                            'Error': "EVM2: Failed to launch course, out of resources! ( Error code:- 1949 )"
                        }), status=400)
                log = api.models.SCLogs({"log": str(instance) + str(instance.name)})
                db.session.add(log)
                db.session.commit()        
                instance.status = 0
                instance.is_assigned = True
                db.session.add(instance)
                db.session.commit()
                log = api.models.SCLogs({"log": '1587========>' + str(instance.status) + str(instance.name)})
                db.session.add(log)
                db.session.commit()      
            grp_inst=instance             
            odv = instance.odv
            odv_opt = instance.odv_options
            conn_name = instance.name    
            log = api.models.SCLogs({"log":'course_check_name 1598=============>' + str(vend_user)})
            db.session.add(log)
            db.session.commit()           
            log = api.models.SCLogs({"log":'course_check_name 1600=============>' + str(course_check_series) + str(series_start) + str(series_end)})
            db.session.add(log)
            db.session.commit()                    
            if vend_user and int(course_check_series) != 0 and int(course_check_series) >= int(series_start) and int(course_check_series) <= int(series_end): 
                profile_user_id = vend_user.vendor_users_user_id
                print("inside vendor user")
                
                session_actve= api.models.UserSessions.query.filter_by(user_id=vend_user.id).all()
               
                if session_actve:
                    for sess in session_actve:
                        if sess.status==1:
                            session = api.models.UserSessions.query.filter_by(id=sess.id).first()
                            session.status=0
                            db.session.commit()
                session=api.models.UserSessions({
                    'access_token': access_token,
                    'user_id': vend_user.id,
                    'user_login':1,
                    'user_sessions_user_id':profile_user_id
                })
                session.expiry=1440
                db.session.add(session)
                db.session.commit()
                log = api.models.SCLogs({"log": 'line======>1389'})
                db.session.add(log)
                db.session.commit()
                vend_lab = api.models.UserCourse.query.filter_by(instance_name=vend_user.lab).first()
                print("Vend lab",vend_lab)              
                if vend_lab and vend_lab.status == 0:
                    instance.status = 1
                    db.session.add(instance)
                    db.session.commit()                      
                    return Response(json.dumps({
                        'Error': "Lab access expired!"
                    }), status=400)

                if vend_lab:
                    headers = {
			            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }
                    key = os_env_key
                    plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    password=plain_text.decode('utf-8')
                    ccu = vend_lab.instance_name.split("_")[1]
                    user_data = {
                        'username': user.username+"_"+ccu+"_"+str(data['uid']),
                        'password': password
                    }
                    load_balancer = ''     
                    lb=''               
                    guac_user=os_env_guac_user 
                    guac_password=os_env_guac_pass
                    guac_host1=os_env_guac_host
                    guac_host2=os_env_guac_host2
                    with SSHTunnelForwarder(
                        (guac_host1, 22),
                        ssh_username=guac_user,
                        ssh_password=guac_password,
                        remote_bind_address=("127.0.0.1", 3306)
                    ) as server:
                        time.sleep(1)
                        conn = mysql.connector.connect(host="127.0.0.1",
                        port=server.local_bind_port,
                        user="root",
                        passwd="sqltoor",
                        db="guacamole")
                        cursor =conn.cursor(buffered=True)
                        cursor.execute('SELECT connection_id FROM guacamole_connection where connection_name="'+conn_name+'";')
                        check_for_connection = cursor.fetchone()
                        print("CHK FOR CONN",check_for_connection)
                        if check_for_connection is None:
                            designated_host = guac_host2
                            load_balancer = 'https://scig-v2-lb2.securitycentric.net/labview/'
                            lb = 'v2-lb2'
                            connection_broker = 'LB-2'
                        else:
                            designated_host = guac_host1
                            load_balancer ='https://scig-v2.securitycentric.net/labview/'
                            lb = 'v2'
                            connection_broker = 'LB-1'
                        cursor.close()
                        conn.close()
                                
                    authToken = requests.post(str(load_balancer)+'api/tokens', headers=headers, data=user_data,verify=False).json()
                    log = api.models.SCLogs({"log": 'line======>1448'})
                    db.session.add(log)
                    db.session.commit()
                    if not "authToken" in authToken:
                        raiseException(authToken)
                    user_cou.access_token = authToken["authToken"]
                    user_cou.lab_access_url = 'https://sca-v2.securitycentric.net/labview/#/client?token=' + authToken["authToken"]
                    db.session.commit()
                    db.session.refresh(user_cou) 
                    u_c_i = api.models.UserCourse.query.filter_by(user_name=data['user_name']+"_"+str(data["uid"])+"_"+temp_course,email=code.email).first()

                    lab_access_url = str(load_balancer)+'#/client?token='+authToken["authToken"]      
                    time.sleep(10)          
                    # return redirect()     
                    if data['portal'] == 'false':
                        link = "https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&static="+str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])
                        course_name = str(registered_course_check)
                    else:
                        link = "https://idp.securitycentric.net/session?&user_id="+str(vend_user.id)+"&static="+str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])
                        course_name = str(registered_course_check)
                        #return redirect("https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
                    if u_c_i:
                        ucid = u_c_i.id
                        u_c_i.lab_user_access_url = link
                        # u_c_i.is_user_active_lab = True
                        code.user_course_id = u_c_i.id
                        db.session.commit()
                        db.session.refresh(u_c_i)
                        log = api.models.SCLogs({"log": 'line======>1735 ' + link})
                        db.session.add(log)   
                        db.session.commit()                     
                    instance.status = 1
                    db.session.add(instance)
                    db.session.commit()
                    response = make_response(redirect(link +  '&course_name=' + str(course_name)+  '&uid=' + str(ucid)))    
                    # Set the cookie
                    response.set_cookie(
                        'apus_token',                   # Cookie name
                        value=token,               # Cookie value
                        secure=True,               # Ensure the cookie is only sent over HTTPS
                        samesite='None',           # Allow the cookie to be sent across different domains
                        domain='.securitycentric.net',  # Allows subdomains like idp.securitycentric.net
                        max_age=60*60*60*60*24           # Cookie expiration time (optional)
                    )
                    return response
            log = api.models.SCLogs({"log":'course_check_name 1712=============>' + str(int(course_check_series))})
            db.session.add(log)
            db.session.commit()       
            if vend_user and int(course_check_series) == 0:
                log = api.models.SCLogs({"log":'course_check_name 1713=============>'})
                db.session.add(log)
                db.session.commit()       
                profile_user_id = vend_user.vendor_users_user_id
                print("inside vendor user")
                if not group:
                    return Response(json.dumps({
                        'Error': 'EVM1: Failed to launch course, please contact admin!'
                    }), status=400)
                
                session_actve= api.models.UserSessions.query.filter_by(user_id=vend_user.id).all()
               
                if session_actve:
                    for sess in session_actve:
                        if sess.status==1:
                            session = api.models.UserSessions.query.filter_by(id=sess.id).first()
                            session.status=0
                            db.session.commit()
                session=api.models.UserSessions({
                    'access_token': access_token,
                    'user_id': vend_user.id,
                    'user_login':1,
                    'user_sessions_user_id':profile_user_id
                })
                session.expiry=1440
                db.session.add(session)
                db.session.commit()
                log = api.models.SCLogs({"log": 'line======>1495'})
                db.session.add(log)
                db.session.commit()
                vend_lab = api.models.UserCourse.query.filter_by(instance_name=vend_user.lab).first()
                print("Vend lab",vend_lab)
                if vend_lab and vend_lab.status == 0:
                    instance.status = 1
                    db.session.add(instance)
                    db.session.commit()
                    return Response(json.dumps({
                        'Error': "Lab access expired!"
                    }), status=400)

                if vend_lab:
                    headers = {
			            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }
                    key = os_env_key
                    plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    password=plain_text.decode('utf-8')
                    ccu = vend_lab.instance_name.split("_")[1]
                    user_data = {
                        'username': user.username+"_"+ccu+"_"+str(data['uid']),
                        'password': password
                    }
                    load_balancer = ''     
                    lb='' 
                    log = api.models.SCLogs({"log": 'line======>1520'+ user_data['username'] + '_' + user_data['password']})
                    db.session.add(log)
                    db.session.commit()              
                    guac_user=os_env_guac_user
                    guac_password=os_env_guac_pass
                    guac_host1=os_env_guac_host
                    guac_host2=os_env_guac_host2
                    with SSHTunnelForwarder(
                        (guac_host1, 22),
                        ssh_username=guac_user,
                        ssh_password=guac_password,
                        remote_bind_address=("127.0.0.1", 3306)
                    ) as server:
                        time.sleep(1)
                        conn = mysql.connector.connect(host="127.0.0.1",
                        port=server.local_bind_port,
                        user="root",
                        passwd="sqltoor",
                        db="guacamole")
                        cursor =conn.cursor(buffered=True)
                        cursor.execute('SELECT connection_id FROM guacamole_connection where connection_name="'+conn_name+'";')
                        check_for_connection = cursor.fetchone()
                        print("CHK FOR CONN",check_for_connection)
                        if check_for_connection is None:
                            designated_host = guac_host2
                            load_balancer = 'https://scig-v2-lb2.securitycentric.net/labview/'
                            lb = 'v2-lb2'
                            connection_broker = 'LB-2'
                        else:
                            designated_host = guac_host1
                            load_balancer ='https://scig-v2.securitycentric.net/labview/'
                            lb = 'v2'
                            connection_broker = 'LB-1'
                        cursor.close()
                        conn.close()
                    log = api.models.SCLogs({"log": 'line======>1555'})
                    db.session.add(log)
                    db.session.commit()            
                    authToken = requests.post(str(load_balancer)+'api/tokens', headers=headers, data=user_data,verify=False).json()
                    log = api.models.SCLogs({"log": 'line======>1559'+ authToken['authToken']})
                    db.session.add(log)
                    db.session.commit()
                    if not "authToken" in authToken:
                        raiseException(authToken)
                    user_cou.access_token = authToken["authToken"]
                    user_cou.lab_access_url = 'https://sca-v2.securitycentric.net/#/client?token=' + authToken["authToken"]
                    db.session.commit()
                    db.session.refresh(user_cou) 
                    u_c_j = api.models.UserCourse.query.filter_by(user_name=data['user_name']+"_"+str(data["uid"])+"_"+temp_course,email=code.email).first()
                    lab_access_url = str(load_balancer)+'#/client?token='+authToken["authToken"]      
                    time.sleep(10)       
                    log = api.models.SCLogs({"log": 'line======>1575'})
                    db.session.add(log)
                    db.session.commit()   
                    if data['portal'] == 'false':
                        link = "https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&static="+str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])
                        course_name = str(registered_course_check)
                    else:
                        link = "https://idp.securitycentric.net/session?&user_id="+str(vend_user.id)+"&static="\
                        +str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)\
                        +"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="\
                        +str(data['user_name'])+"&token="+str(authToken["authToken"])
                        course_name = str(registered_course_check)
                    instance.status = 1
                    db.session.add(instance)
                    db.session.commit()        
                    if u_c_j:
                        u_c_j.lab_user_access_url = link
                        # u_c_j.is_user_active_lab = True
                        ucid = u_c_j.id
                        code.user_course_id = u_c_j.id
                        db.session.commit()
                        db.session.refresh(u_c_j)
                        log = api.models.SCLogs({"log": 'line======>1871 ' + link})
                        db.session.add(log) 
                        db.session.commit()     
                    else:
                        headers = {
                                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                                'Content-Type': 'application/x-www-form-urlencoded',
                            }
                        print(user.username+"_"+str(instance.ccu_landing))
                        user_data = {
                            'username': user.username+"_"+str(instance.ccu_landing)+"_"+str(data['uid']),
                            'password': password
                        }
                        # gauc_cred = api.models.GaucCred({'username': user_data['username'], 'access_code': data['access_code'], 'load_balancer_url': load_balancer})
                        # db.session.add(gauc_cred)
                        # db.session.commit()
                        authToken = requests.post(str(load_balancer)+'api/tokens', headers=headers, data=user_data,timeout=5,verify=False).json()
                        if not "authToken" in authToken:
                            instance.status = 1
                            db.session.add(instance)
                            db.session.commit()                                  
                            raiseException(authToken)
                        
                        log = api.models.SCLogs({"log": 'line======>2006'})
                        db.session.add(log)
                        db.session.commit()
                        user_course = api.models.UserCourse({
                            'user_name': data['user_name']+"_"+str(data['uid'])+"_"+temp_course,
                            'course_name': temp_course, 
                            'status': 1, 
                            'access_token':str(authToken["authToken"]),
                            'instance_name':grp_inst.name,
                            'course_duration': 30,
                            'lab_access_url': str(load_balancer)+'#/client?token=' + authToken["authToken"],
                            'access_code_status':1,
                            'connection_broker':connection_broker,
                            'user_course_user_id':profile_user_id,
                            'lab_user_access_url': link,
                            'email': code.email
                            
                        })
                        db.session.add(user_course)
                        db.session.commit()
                        db.session.refresh(user_course)    
                        code.user_course_id = user_course.id
                        db.session.commit()
                    response = make_response(redirect(link +  '&course_name=' + str(course_name)+  '&uid=' + str(ucid)))    
                    # Set the cookie
                    response.set_cookie(
                        'apus_token',                   # Cookie name
                        value=token,               # Cookie value
                        secure=True,               # Ensure the cookie is only sent over HTTPS
                        samesite='None',           # Allow the cookie to be sent across different domains
                        domain='.securitycentric.net',  # Allows subdomains like idp.securitycentric.net
                        max_age=60*60*60*60*24           # Cookie expiration time (optional)
                    )    
                    return response                                   
                        #return redirect("https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
            # if group:
            #     odv=""
            #     odv_opt=""
            #     instances =  api.models.GroupInstances.query.filter_by(group_id=group.id).all()  
            #     check_connection_name = ''          
            #     grp_inst=None            
            #     if instances:
            #         for instance in instances:
            #             print(instance.name)                 
            #             profile_user_id = instance.group_instances_user_id   
            #             conn_name = instance.name 
            #             odv = instance.odv     
            #             odv_opt = instance.odv_options           
            #             reg_vm =api.models.UserCourse.query.filter_by(instance_name=instance.name).first()
            #             log = api.models.SCLogs({"log": 'line======>1834 ' + str(reg_vm)})
            #             db.session.add(log)
            #             db.session.commit()                          
            #             print("registered VM",reg_vm)
            #             if not reg_vm:
            #                 grp_inst=instance
            #                 log = api.models.SCLogs({"log": 'line======>1845 ' + str(instance.name)})
            #                 db.session.add(log)
            #                 db.session.commit()                               
            #                 print("group instance",grp_inst)
            #                 break
            if not group:
        #                         print("No instance")
        #                         code = api.models.AccessCodes.query.filter_by(access_code=data['access_code']).first()
        #                         if code:        
        #                             code.status = 0
        #                             code.first_name = 'null'
        #                             code.last_name = 'null'
        #                             code.email = 'null'
        #                             code.key = 'null'
        #                             code.password='null'
        #                             db.session.commit()
        #                         return Response(json.dumps({
        #                                 'Error': "EVM1: Failed to launch course, please contact admin!"
        #                             }), status=400)
                print("No instance")
                code = api.models.AccessCodes.query.filter_by(email=email,course_name='course-v1:APUS-ISSC242').first()
                if code:        
                    code.status = 0
                    # code.first_name = 'null'
                    # code.last_name = 'null'
                    # code.email = 'null'
                    # code.key = 'null'
                    # code.password='null'
                    # code.status=0
                    # code.phone_no=0
                    
                    db.session.commit()
                    print("email=======",email)
                    pending_user=api.models.PendingUsers({"user_email":email, "course_name":data['course_name']})
                    db.session.add(pending_user)
                    db.session.commit()
                    db.session.refresh(pending_user)
                    log = api.models.SCLogs({"log": 'line======>1635'})
                    db.session.add(log)
                    db.session.commit()
                    sender = 'support@securitycentricinc.com'
                    receivers = email
                    SUBJECT = "No Vm available"
                    TEXT = "All available sessions are in use, the system has created a queue and will email you when a session comes available"
                    message = 'From:support@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)
                    instance.status = 1
                    db.session.add(instance)
                    db.session.commit()
                    try:
                        smtpObj = smtplib.SMTP('172.20.9.21')
                        smtpObj.sendmail(sender, receivers, message)
                        return Response(json.dumps({
                        'Error': "EVM1: Failed to launch course, please contact admin! and check your mail"
                        }), status=400)
                    
                    except SMTPException:
                        print("Error: unable to send email")
                        return Response(json.dumps({
                            'Error': "EVM1: Failed to launch course, please contact admin!"
                            }), status=400)
            if not grp_inst:
                print("Reached here")
                code = api.models.AccessCodes.query.filter_by(email=email,course_name='course-v1:APUS-ISSC242').first()
                if code:        
                    code.status = 0
                    # code.first_name = 'null'
                    # code.last_name = 'null'
                    # code.email = 'null'
                    # code.key = 'null'
                    # code.password='null'
                    db.session.commit()
                instance.status = 1
                db.session.add(instance)
                db.session.commit()                        
                return Response(json.dumps({
                        'Error': "EVM2: Failed to launch course, please contact admin! ( Error code: 2364 )"
                    }), status=400)
            elif user and grp_inst:
                    # key = os_env_key
                    # plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    # password=plain_text.decode('utf-8')
                    load_balancer = ''
                    access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
                    guac_user=os_env_guac_user
                    guac_password=os_env_guac_pass
                    guac_host1=os_env_guac_host
                    guac_host2=os_env_guac_host2
                    with SSHTunnelForwarder(
                        (guac_host1, 22),
                        ssh_username=guac_user,
                        ssh_password=guac_password,
                        remote_bind_address=("127.0.0.1", 3306)
                    ) as server:
                        time.sleep(1)
                        conn = mysql.connector.connect(host="127.0.0.1",
                        port=server.local_bind_port,
                        user="root",
                        passwd="sqltoor",
                        db="guacamole")
                        
                        cursor =conn.cursor(buffered = True)
                        cursor.execute('SELECT connection_id FROM guacamole_connection where connection_name="'+conn_name+'";')
                        check_for_connection = cursor.fetchone()
                        
                        lb = ''
                        if check_for_connection is None:
                            designated_host = guac_host2
                            load_balancer = 'https://scig-v2-lb2.securitycentric.net/labview/'
                            lb = 'v2-lb2'
                            connection_broker = 'LB-2'
                        else:
                            designated_host = guac_host1
                            load_balancer ='https://scig-v2.securitycentric.net/labview/'
                            lb = 'v2'
                            connection_broker = 'LB-1'
                        cursor.close()
                        conn.close()
                    log = api.models.SCLogs({"log": 'line======>1721'})
                    db.session.add(log)
                    db.session.commit()        
                    with SSHTunnelForwarder(
                        (designated_host, 22),
                        ssh_username=guac_user,
                        ssh_password=guac_password,
                        remote_bind_address=("127.0.0.1", 3306)
                    ) as server:
                        time.sleep(1)
                        conn = mysql.connector.connect(host="127.0.0.1",
                        port=server.local_bind_port,
                        user="root",
                        passwd="sqltoor",
                        db="guacamole")

                        cursor =conn.cursor(buffered=True)
                        cursor.execute("SET @salt = UNHEX(SHA2(UUID(), 256));")
                        conn.commit()
                        
                        key = os_env_key
                        plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                        password=plain_text.decode('utf-8')
                        log = api.models.SCLogs({"log": 'line======>1744'+ "SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';"})
                        db.session.add(log)
                        db.session.commit()  
                        cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';") 
                        check_for_user = cursor.fetchone()
                        if check_for_user is None:
                            cursor.execute("INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"','USER');")
                            conn.commit()
                            log = api.models.SCLogs({"log": 'line======>1768'+ "INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"','USER');"})
                            db.session.add(log)
                            db.session.commit()    
                            cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';")
                            log = api.models.SCLogs({"log": 'line======>1772'+ "SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';"})
                            db.session.add(log)
                            db.session.commit()  
                            entity_id=cursor.fetchone()[0]   
                            cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(entity_id)+"','"+data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                            conn.commit()                 
                            cursor.execute("SELECT entity_id FROM guacamole_user where username='"+data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course+"';")
                            vend_id=cursor.fetchone()[0]
                            log = api.models.SCLogs({"log": 'line======>1780'+ "SELECT user_id FROM guacamole_user where username='"+data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course+"';"})
                            db.session.add(log)
                            db.session.commit()                                                          
                            log = api.models.SCLogs({"log": 'line======>1791'+ "SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';"})
                            db.session.add(log)
                            db.session.commit()   
                            cursor.execute("SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';")
                            connection_id=cursor.fetchone()[0]
                            log = api.models.SCLogs({"log": 'line======>1793'+ "SELECT sharing_profile_id FROM guacamole_sharing_profile WHERE primary_connection_id='"+str(connection_id)+"';"})
                            db.session.add(log)
                            db.session.commit() 
                            cursor.execute("SELECT sharing_profile_id FROM guacamole_sharing_profile WHERE primary_connection_id='"+str(connection_id)+"';")
                            sharing_profile_id=cursor.fetchone()
                            log = api.models.SCLogs({"log": 'line======>1797'+ "SELECT sharing_profile_id FROM guacamole_sharing_profile WHERE primary_connection_id='"+str(connection_id)+"';"})
                            db.session.add(log)
                            db.session.commit()  
                            print("SHARING++",sharing_profile_id)
                            if sharing_profile_id is not None:
                                print("INSIDE",sharing_profile_id[0])
                                sharing_profile_id=sharing_profile_id[0]
                                cursor.execute("INSERT INTO guacamole_sharing_profile_permission(entity_id,sharing_profile_id,permission) VALUES ("+str(entity_id)+","+str(sharing_profile_id)+", 'READ');")
                                conn.commit()
                                cursor.execute("INSERT INTO guacamole_sharing_profile_permission(entity_id,sharing_profile_id,permission) VALUES ("+str(entity_id)+","+str(sharing_profile_id)+", 'UPDATE');")
                                conn.commit()
                                cursor.execute("INSERT INTO guacamole_sharing_profile_permission(entity_id,sharing_profile_id,permission) VALUES ("+str(entity_id)+","+str(sharing_profile_id)+", 'DELETE');")
                                conn.commit()
                                cursor.execute("INSERT INTO guacamole_sharing_profile_permission(entity_id,sharing_profile_id,permission) VALUES ("+str(entity_id)+","+str(sharing_profile_id)+", 'ADMINISTER');")
                                conn.commit()
                                        
                            cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ');")
                            conn.commit()
                            cursor.execute("SELECT entity_id FROM guacamole_connection_permission where entity_id='"+str(vend_id)+"';")
                            temp = cursor.fetchone()                    
                            log = api.models.SCLogs({"log": 'line======>1816'+ "SELECT entity_id FROM guacamole_connection_permission where entity_id='"+str(vend_id)+"';"})
                            db.session.add(log)
                            db.session.commit()
                            log = api.models.SCLogs({"log": 'line======>1817'+ str(temp)+ "INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(vend_id)+","+str(connection_id)+", 'READ');"})
                            db.session.add(log)
                            db.session.commit()                                
                            if temp is None:                                
                                cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(vend_id)+","+str(connection_id)+", 'READ');")                               
                                conn.commit()
                            cursor.close()
                            conn.close()  
                            log = api.models.SCLogs({"log": 'line======>1955'})
                            db.session.add(log)
                            db.session.commit()
                            now = datetime.datetime.utcnow()
                            now_plus_60 = now + datetime.timedelta(minutes = 60)    
                            vendor_user=db.session.query(api.models.VendorUsers).filter_by(
                                username=data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course).filter_by(
                                status=True).filter_by(
                                lab=grp_inst.name).first()
                            log = api.models.SCLogs({"log": 'line======>1955' + str(vendor_user)})
                            db.session.add(log)
                            db.session.commit()
                            if  vendor_user:    
                                instance.status = 1
                                db.session.add(instance)
                                db.session.commit()                            
                                return Response(json.dumps({'Error': "Lab for " + str(data["course_name"]) + " is active and will end on " + str(vendor_user.lab_end_session)}), status=400)
                            log = api.models.SCLogs({"log": 'line======>1969' + str(vendor_user)+ str(type(now_plus_60))})
                            db.session.add(log)
                            db.session.commit()                                 
                            course = api.models.Courses.query.filter_by(course_name=temp_course).first()  
                            log = api.models.SCLogs({"log": 'line======>1973' + str(course)+ str(type(course))})
                            db.session.add(log)
                            db.session.commit()                                            
                            vendor_user=api.models.VendorUsers({
                                "username":data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course,
                                "vendor_id":user.id,
                                "status":True,
                                "lab":grp_inst.name,
                                "lab_update_session":0,
                                "lab_end_session":now_plus_60,
                                "vendor_users_user_id":profile_user_id,
                                "course_id":course.id,
                                "email":email
                            })
                            db.session.add(vendor_user)
                            db.session.commit()

                            headers = {
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                                'Content-Type': 'application/x-www-form-urlencoded',
                            }
                            print(user.username+"_"+str(instance.ccu_landing))
                            user_data = {
                                'username': user.username+"_"+str(instance.ccu_landing)+"_"+str(data['uid']),
                                'password': password
                            }
                            # gauc_cred = api.models.GaucCred({'username': user_data['username'], 'access_code': data['access_code'], 'load_balancer_url': load_balancer})
                            # db.session.add(gauc_cred)
                            # db.session.commit()
                            authToken = requests.post(str(load_balancer)+'api/tokens', headers=headers, data=user_data,timeout=5,verify=False).json()
                            if not "authToken" in authToken:
                                instance.status = 1
                                db.session.add(instance)
                                db.session.commit()                                  
                                raiseException(authToken)
                            
                            log = api.models.SCLogs({"log": 'line======>2006'})
                            db.session.add(log)
                            db.session.commit()
                            user_course = api.models.UserCourse({
                                'user_name': data['user_name']+"_"+str(data['uid'])+"_"+temp_course,
                                'course_name': temp_course, 
                                'status': 1, 
                                'access_token':str(authToken["authToken"]),
                                'instance_name':grp_inst.name,
                                'course_duration': 30,
                                'lab_access_url': str(load_balancer)+'#/client?token=' + authToken["authToken"],
                                'access_code_status':1,
                                'connection_broker':connection_broker,
                                'user_course_user_id':profile_user_id,
                                'email': code.email
                                
                            })
                            log = api.models.SCLogs({"log": 'line======>2022'})
                            db.session.add(log)
                            db.session.commit()
                            db.session.add(user_course)
                            db.session.commit()
                            db.session.refresh(user_course)
                            log = api.models.SCLogs({"log": 'line======>2028'})
                            db.session.add(log)
                            db.session.commit()
                            u_c = api.models.UserCourse.query.filter_by(user_name=data['user_name']+"_"+str(data["uid"])+"_"+temp_course,email=code.email).first()
                            vend_user=db.session.query(api.models.VendorUsers).filter_by(username=data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course).filter_by(
                                status=True).first()
                            log = api.models.SCLogs({"log": 'line======>2038'})
                            db.session.add(log)
                            db.session.commit()                             
                            session=api.models.UserSessions({
                                'access_token':access_token,
                                'user_id':vend_user.id,
                                'user_login':1,
                                'user_sessions_user_id':profile_user_id
                            })
                            session.expiry=1440
                            db.session.add(session)
                            db.session.commit()
                            log = api.models.SCLogs({"log": 'line======>2050'})
                            db.session.add(log)
                            db.session.commit()
                            if data['portal'] == 'false':
                               link = "https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&static="+str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])
                               course_name = str(registered_course_check)
                            else:
                                link = "https://idp.securitycentric.net/session?&user_id="+str(vend_user.id)+"&static="+str(static)+"&accesscode="+str(data['access_code'])+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])
                                course_name = str(registered_course_check)
                            if u_c:
                                u_c.lab_user_access_url = link
                                # u_c.is_user_active_lab = True
                                code.user_course_id = u_c.id
                                ucid = u_c.id
                                db.session.commit()
                                db.session.refresh(u_c)
                                log = api.models.SCLogs({"log": 'line======>2222 ' + link})
                                db.session.add(log) 
                                db.session.commit() 
                            instance.status = 1
                            db.session.add(instance)
                            db.session.commit()   
                            response = make_response(redirect(link +  '&course_name=' + str(course_name)+  '&uid=' + str(ucid)))    
                            # Set the cookie
                            response.set_cookie(
                                'apus_token',                   # Cookie name
                                value=token,               # Cookie value
                                secure=True,               # Ensure the cookie is only sent over HTTPS
                                samesite='None',           # Allow the cookie to be sent across different domains
                                domain='.securitycentric.net',  # Allows subdomains like idp.securitycentric.net
                                max_age=60*60*60*60*24           # Cookie expiration time (optional)
                            )
                            return response   
                                #return redirect("https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
                            # return redirect("http://localhost:3000/connection-broker?&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
                        else:
                            instance.status = 1
                            db.session.add(instance)
                            db.session.commit()                            
                            return Response(json.dumps({
                                'Error': "User Already Exist"
                            }), status=400)
                            
            # else:
            #     instance.status = 1
            #     db.session.add(instance)
            #     db.session.commit()                
            #     return Response(json.dumps({
            #                     'Error': "Course not found"
            #                 }), status=400) 
        else:
            return Response(json.dumps({
                                'Error': "Course not Registered"
                            }), status=400) 
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        print(e)
        return raiseException(e)
    finally:
        db.session.close()

def generate_jwt(user_id, client_id, private_key_path, audience, kid):
    with open(private_key_path, "r") as key_file:
        private_key = key_file.read()
    now = datetime.datetime.now(datetime.timezone.utc)
    future = now + datetime.timedelta(minutes=5)
    now_ms = int(now.timestamp() * 1000)
    future_ms = int(future.timestamp() * 1000)

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": audience,
        "iat": now_ms,
        "exp": future_ms,
        "jti": user_id
    }

    headers = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": "b42a2dd8-ee11-4e6b-8d8a-389694f1ff05"  # Add the Key ID here
    }

    token = jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
    log = api.models.SCLogs({
            "log": "returning generate_jwt" + str( {
        "iss": client_id,
        "sub": client_id,
        "aud": audience,
        "iat": now_ms,
        "exp": future_ms,
        "jti": user_id
    })  })
    db.session.add(log)
    db.session.commit()     
    return token

def submit_grade(line_item_url, user_id, client_id, private_key_path, score_data, kid, jwt):
    try:
        audience = "https://api.brightspace.com/auth/token"
        auth_token = generate_jwt(user_id, client_id, private_key_path, audience, kid)
        log = api.models.SCLogs({
            "log": "in submit_grade auth_token:" + str(auth_token) + ' '  })
        db.session.add(log)
        db.session.commit()   

        headers = {
            "Authorization": f"Bearer {auth_token}", #auth_token
            "Content-Type": "application/vnd.ims.lis.v1.score+json"
        }

        response = requests.post(f"{line_item_url}/scores", headers=headers, json=score_data)
        log = api.models.SCLogs({
                "log": "response received submit_grade 1" + str(response.text)  })
        db.session.add(log)
        db.session.commit()     
        log = api.models.SCLogs({
                "log": "response received submit_grade 2" + str(response.json())  })
        db.session.add(log)
        db.session.commit()  
        log = api.models.SCLogs({
                "log": "response received submit_grade 3" + str(response)  })
        db.session.add(log)
        db.session.commit()   
        if response.status_code == 200:
            print("Grade submitted successfully:", response.json())
            log = api.models.SCLogs({
                    "log": "Grade submitted successfully:" + str(response) + ' '  })
            db.session.add(log)
            db.session.commit()        
        else:
            print("Error submitting grade:", response.text)
            log = api.models.SCLogs({
                    "log": "Error submitting grade:" + str(response) + ' '  })
            db.session.add(log)
            db.session.commit()        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
                "log": "Error from submit_grade" + str(e)})
        db.session.add(log)
        db.session.commit()         
        return raiseException(e)

@student_login_controller.route("/apus/oauth2/redirect", methods=['GET','POST'])
def apus_redirect():
    try:
        content_type = request.headers.get('Content-Type')

        # Extract form data based on the Content-Type
        if content_type == 'application/x-www-form-urlencoded':
            data = request.form.to_dict()
        elif content_type == 'application/json':
            data = request.get_json()
        else:
            args = request.args
            data = args.to_dict()
            log = api.models.SCLogs({
                    "log": "line 156 apus_redirect ==> " + str(data) + ' '  })
            db.session.add(log)
            db.session.commit()
        try:
            current_directory = os.path.dirname(os.path.abspath(__file__))
            config_file_path = os.path.join(current_directory, '../../files/tool_config.json')
            with open(config_file_path, 'r') as file:
                tool_config_data = file.read()
                tool_config_data = json.loads(tool_config_data)
            with open(tool_config_data['https://apustest.brightspace.com']['public_key_file'], 'rb') as file:
                public_key = file.read()
                public_key = serialization.load_pem_public_key(public_key)
                log = api.models.SCLogs({
                         "log": "public key bs==> " + str(content_type) + '     '+  str(public_key) + ' ' + str(data.get('id_token'))})
                db.session.add(log)
                db.session.commit()

            decoded_token = jwt.decode(data.get('id_token'),  options={"verify_signature": False})
            unique_id = decoded_token['email'] or decoded_token['sub']
            new_access_code = api.models.AccessCodes.query.filter_by(
                email=str(unique_id),course_name='course-v1:APUS-ISSC242').first()
            email = str(unique_id)
            if new_access_code is None:
                key = Fernet.generate_key()
                password = str('Password@1').encode()
                f = Fernet(key)
                first_name = str(decoded_token['given_name']).encode()
                last_name = str(decoded_token['family_name']).encode()
                encrypted_first_name = f.encrypt(first_name)
                encrypted_last_name = f.encrypt(last_name)
                encrypted_password = f.encrypt(password)
                new_access_code = api.models.AccessCodes({
                    'course_name': 'course-v1:APUS-ISSC242',
                    'access_code': 0,
                    'vendor_name': 'APUS',
                    'status': 1,
                    'first_name': encrypted_first_name,
                    'last_name': encrypted_last_name,
                    'email': email,
                    'key': key,
                    'password': encrypted_password,
                    'user_course_id':0,
                    'life_cycle':364,
                    'percent':0,
                    'phone_no':0,
                    'motp':0,                
                    'access_codes_user_id':45,
                    'progress':None,
                    'user_type':0,
                    'token':data.get('id_token')
                })
                db.session.add(new_access_code)
                db.session.commit()
                db.session.refresh(new_access_code)                       

            log = api.models.SCLogs({
                        "log": "new_access_code " + str(new_access_code)})
            db.session.add(log)
            db.session.commit()

            jwt_token = data.get('id_token')
            client_id = tool_config_data['https://apustest.brightspace.com']['client_id']
            private_key_path = tool_config_data['https://apustest.brightspace.com']['private_key_file']

            decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
            line_item_url = decoded_token["https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"]["lineitem"]

            score_data = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "scoreGiven": 85,
                "scoreMaximum": 100,
                "comment": "Great work!",
                "activityProgress": "Completed",
                "gradingProgress": "FullyGraded",
                "userId": decoded_token["sub"]
            }

            unverified_header = jwt.get_unverified_header(jwt_token)
            kid = unverified_header.get("kid")

            submit_grade(line_item_url, decoded_token["sub"], client_id, private_key_path, score_data, kid, jwt_token)

            os_env_key=os.environ.get('XE_PASSWORD_KEY')
            os_env_guac_user=os.environ.get('APP_GUAC_USER')
            os_env_guac_pass=os.environ.get('APP_GUAC_PASSWORD')
            os_env_guac_host=os.environ.get('APP_GUAC_HOST')
            os_env_guac_host2=os.environ.get('APP_GUAC_HOST2')
            return apus_lab_url_creation(0,None,str(decoded_token['given_name']),str(decoded_token['family_name']),email,os_env_key,os_env_guac_user,os_env_guac_pass,os_env_guac_host,os_env_guac_host2,data.get('id_token'))
        except jwt.ExpiredSignatureError:
            return 'Token has expired', 400
        except jwt.InvalidTokenError:
            return 'Invalid token', 400
        except Exception as e:
            if e.__class__.__name__ == "IntegrityError":
                db.session.rollback()
            return raiseException(e)
    finally:
        db.session.close()
 
def generate_token(email, vendor, is_vendor=False, is_instructor=False):
    # Payload containing the email and vendorId
    payload = {
        'email': email,
        'vendor_id': None if vendor is None else vendor.id,
        'vendor_name': None if vendor is None else vendor.name,
        'is_vendor': is_vendor,
        'is_instructor':is_instructor,
        # Expiration time set to 7 days from now
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    }

    # Secret key (store this securely)
    secret_key = os.environ.get('APP_SECRET')

    # Generate token using the HS256 algorithm
    token = jwt.encode(payload, secret_key, algorithm='HS256')

    return token

@student_login_controller.route("/v1/student_login", methods=['POST'])
def login():
    try:
        data = json.loads(request.data)        
        for key in ['email']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        for key in ['password']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        
        password = data['password']
        user_key = api.models.AccessCodes.query.filter_by(
            email=str(data['email']),user_type = data['role'] if isinstance(data['role'],int) else data['role'][0]).all()
        
        if len(user_key) == 0:            
            user_key = api.models.AccessCodes.query.filter_by(
            email=str(data['email']),user_type = data['role'] if isinstance(data['role'],int) else data['role'][1]).all()
            
        if user_key:
            
            result=[]
            fname = ''
            lname = ''
            my_email = ''
            my_password = ''
            api_key =''
            for u in user_key:
                key = u.key
                # log = api.models.SCLogs({
                #         "log": "line 66==> " + str(u) + ' ' })
                # db.session.add(log)
                # db.session.commit()
                encoded_password = bytes(u.password, 'utf-8')
                
                f = Fernet(key)
                decrypted_password = f.decrypt(encoded_password)
                decrypted_password = decrypted_password.decode()  
                my_password = decrypted_password          
                email = data['email']
                vendor_user = None
                if password == str(decrypted_password) and email == str(u.email):                
                    encoded_first_name = bytes(u.first_name, 'utf-8')
                    decrypted_first_name = f.decrypt(encoded_first_name)
                    decrypted_first_name = decrypted_first_name.decode()
                    fname = decrypted_first_name
                    encoded_last_name = bytes(u.last_name, 'utf-8')
                    decrypted_last_name = f.decrypt(encoded_last_name)
                    decrypted_last_name = decrypted_last_name.decode()   
                    lname = decrypted_last_name     
                    my_email= str(u.email)        
                    print(1)                   
                    course = api.models.Courses.query.filter_by(course_name=str(u.course_name)).first() 
                    # log = api.models.SCLogs({
                    #     "log": "/v1/student_login line 86==> " + str(course) + ' ' + str(hasattr(course, 'id'))})
                    # db.session.add(log)
                    # db.session.commit()
                    if course:                    
                        vendor_user = api.models.VendorUsers.query\
                            .filter_by(course_id=course.id, email=data['email']).order_by(desc(VendorUsers.lab_end_session)).first() 
                    lab_end_session = None
                    status = False
                    usercourse = None
                    uid = 0
                    lab_user_access_url = None
                    if vendor_user:
                        lab_end_session = vendor_user.lab_end_session
                        status = vendor_user.status
                        # log = api.models.SCLogs({
                        #     "log": "/v1/student_login line 104==> " + str(status) + ' ' + str(vendor_user.id)+ ' ' + str(vendor_user.lab)})
                        # db.session.add(log)
                        # db.session.commit()   
                        if status == True:
                            usercourse = UserCourse.query.filter_by(instance_name=vendor_user.lab)\
                                    .filter_by(status=1).first()
                            if usercourse:
                                instance =  GroupInstances.query.filter(GroupInstances.name==vendor_user.lab)\
                                    .filter((GroupInstances.odv_options=='controls')|(GroupInstances.odv_options=='')|(GroupInstances.odv_options=='timer'))\
                                    .filter(GroupInstances.status==1)\
                                    .order_by(desc(GroupInstances.created_at)).first()
                                lab_user_access_url = usercourse.lab_user_access_url  
                                uid = usercourse.id  
                                # log = api.models.SCLogs({
                                #     "log": "line 114 Vendor student_login==> " + str(vendor_user.lab) + '           ' + str(instance) })
                                # db.session.add(log)
                                # db.session.commit()        
                                # log = api.models.SCLogs({
                                #     "log": str(instance) + '   || dir =====>' + str(vendor_user.lab)})
                                # db.session.add(log)
                                # db.session.commit()
                                if not instance:     
                                    # log = api.models.SCLogs({
                                    #     "log": "line 119 Vendor student_login==> " + str(instance) })
                                    # db.session.add(log)
                                    # db.session.commit()        
                                    status = False
                    if u.access_code and course:
                        print("access code is present")
                        # log = api.models.SCLogs({
                        #     "log": "/v1/student_login line 113==> " + str(u) + ' ' + str(hasattr(u, 'id'))})
                        # db.session.add(log)
                        # db.session.commit()      
                        # log = api.models.SCLogs({
                        #     "log": "/v1/student_login line 126 Vendor student_login==> " + str(status) + '       ' + str(u.course_name) })
                        # db.session.add(log)
                        # db.session.commit()        
                        result.append({                           
                            'access_code':u.access_code,                  
                            'course_name':u.course_name,
                            'course_detail':course.course_description,
                            'percent':u.percent,
                            'progress':u.progress,
                            'user_type':u.user_type,
                            "motp":u.motp,
                            "id":u.id,
            			    "chat_room":course.chat_room,
                            "lab_end_session":str(lab_end_session),
                            "is_lab_active":status,
                            "lab_user_access_url": lab_user_access_url,
                            "user_course": uid
                        })
                    else:
                        # log = api.models.SCLogs({
                        # "log": "line 131==> " + str(u) + ' ' + str(hasattr(u, 'id'))})
                        # db.session.add(log)
                        # db.session.commit()  
                        print("access code is not present")
                        result.append({                           
                            # 'access_code':u.access_code,                  
                            # 'course_name':u.course_name,
                            # 'course_detail':course.course_description,
                            # 'percent':u.percent,
                            # 'progress':u.progress,
                            'user_type':u.user_type,
                            "motp":u.motp,
                            "id":u.id
                        })

                    
            
            if len(result) > 0:
                # log = api.models.SCLogs({
                #         "log": "line 150==> " + str(u) + ' ' + str(hasattr(u, 'id'))})
                # db.session.add(log)
                # db.session.commit()  
                vendor = None
                is_instructor = False
                if data['role'] == [1,-1]:
                    is_instructor = True
                vendor = api.models.Users.query.filter_by(name=u.vendor_name).first()
                token = generate_token(u.email,vendor,True,is_instructor)     
                response = Response(json.dumps({
                            'first_name': fname,
                            'last_name': lname,
                            'email': my_email,
                            'password':my_password,
                            'data': result, 
                            "id":u.id,    
                            "phone":u.phone_no,                                                  
                            'Message':'Login sucess'
                        }), status=200)
                response.headers['Authorization'] = f'Bearer {token}'
                return response
                
            else:
                return Response(json.dumps({
                            'Error': "Invalid user"
                        }), status=400)
            
        else:
            return Response(json.dumps({
                'Error': "Invalid username/password."
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        # log = api.models.SCLogs({
        #         "log": "Exception " + str(e)})
        # db.session.add(log)
        # db.session.commit()     
        return raiseException(e) 
    finally:
        db.session.close()

@student_login_controller.route("/v1/apus/login", methods=['GET','POST'])
def apus_login():
    try:
        # Get the Content-Type from the request headers
        content_type = request.headers.get('Content-Type')
        
        # Extract form data based on the Content-Type
        if content_type == 'application/x-www-form-urlencoded':
            data = request.form.to_dict()
        elif content_type == 'application/json':
            data = request.get_json()
        else:
            args = request.args
            data = args.to_dict()
        log = api.models.SCLogs({
                "log": "apus_login Passed content_type:" + str(data) + '   ' + str(content_type)})
        db.session.add(log)
        db.session.commit()     
        # Extract necessary fields from the data
        iss = data.get('iss')
        login_hint = data.get('login_hint')
        client_id = data.get('client_id')
        lti_message_hint = data.get('lti_message_hint')
        target_link_uri = data.get('target_link_uri')
        cache = Cache(app)
        launch_data_storage = FlaskCacheDataStorage(cache)

        flask_request = FlaskRequest()
        # target_link_uri = target_link_uri
        if not target_link_uri:
            raise Exception('Missing "target_link_uri" param')

        oidc_login = FlaskOIDCLogin(flask_request, tool_conf, launch_data_storage=launch_data_storage)
        return oidc_login\
            .enable_check_cookies()\
            .redirect(target_link_uri)
        # Validate the LTI request
        if iss != ISSUER or client_id != CLIENT_ID:
            return "Invalid LTI request", 400

        # Optionally use `login_hint` and `lti_message_hint`
        # For example, you might use `login_hint` to manage user sessions or authentication
        if login_hint:
            # Example usage: validate or store the login hint
            # Here, you might look up the user based on `login_hint` or perform other actions
            print(f"Login hint: {login_hint}")

        if lti_message_hint:
            # Example usage: handle specific LTI message hints
            # Here, you might use `lti_message_hint` to customize the launch experience
            print(f"LTI message hint: {lti_message_hint}")

        log = api.models.SCLogs({
                "log": "apus login login and lti message hint"})
        db.session.add(log)
        db.session.commit()     
        # Create the tool provider instance
        tool_provider = ToolProvider(
            # request=request,
            # tool_conf=tool_conf,
            # launch_data_storage=None,
            # service_connector=ServiceConnector(tool_conf)
        )

        # Assuming you have Flask app context
        session_service = SessionService(request)
        cookie_service = CookieService()
        # Create an instance of RequestsAdapter
        adapter = RequestsAdapter()
        # Create a MessageLaunch instance with the tool provider and necessary parameters
        message_launch = MessageLaunch(
            request=adapter,
            tool_config=tool_conf,
            session_service=session_service,
            cookie_service=cookie_service            
            # iss=iss,
            # client_id=client_id,
            # deployment_id=DEPLOYMENT_ID,
            # target_link_uri=target_link_uri,
            # tool_provider=tool_provider
        )

        log = api.models.SCLogs({
                "log": "apus login tool_provider and message_launch"})
        db.session.add(log)
        db.session.commit()  
        # Validate the LTI launch request
        if not message_launch.validate():
            return "LTI launch validation failed", 400

        log = api.models.SCLogs({
                "log": "apus message_launch.validate passed"})
        db.session.add(log)
        db.session.commit()  

        log = api.models.SCLogs({
                "log": "data from lti:: " + str(data)})
        db.session.add(log)
        db.session.commit()     
        # Generate the redirect URL for LTI launch
        return message_launch.get_redirect(data)
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
                "log": "Error from lti" + str(e)})
        db.session.add(log)
        db.session.commit()         
        return raiseException(e)
    finally:
        db.session.close()  



@student_login_controller.route("/v1/logger", methods=['POST'])
def logger():
    try:
        data = json.loads(request.data)      
        log = api.models.SCLogs({
                "log": "Frontend error::: " + str(data['log'])})
        db.session.add(log)
        db.session.commit()       
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()      

@student_login_controller.route("/v1/student_recording", methods=['POST'])
def record():
    try:
        file = request.files['file']
        fn = file.filename
        
        print(fn)
        print("this file==>",fn)
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()
       
        stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/test")
        result = stdout.readline()
        
        print("Error......................", stderr.read()) 
        sftp_client.putfo(file,"/Guides/vendors/test")         
            
        
        
        print("Error......................", stderr.read())        
        sftp_client.close()   
        ssh.close() 
       
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    
