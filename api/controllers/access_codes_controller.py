from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
import mysql.connector
from sshtunnel import SSHTunnelForwarder
from api import db
import time
import os
import pika
import paramiko
import hashlib
import datetime
from smtplib import SMTPException
import smtplib
from flask_csv import send_csv
from cryptography.fernet import Fernet
import re
from api.helpers import verify_jwt
access_codes_controller = Blueprint('access_codes_controller', __name__)
CORS(access_codes_controller)

def handle_token():
    # Get the token from the Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response(json.dumps({"message": "Missing token"}), 401)
    token = auth_header.split(" ")[1]
    decoded_token, error = verify_jwt.verify_token(token)
    if error:
        return Response(json.dumps({"message": error}), 401)
    return decoded_token


@access_codes_controller.route("/v1/expire/access_code", methods=['PATCH'])
def mark_expired_access_codes_as_expired():
    # f = None
    try:             
        # f= open("mark_expired_access_codes_as_expired.log","a")
        # f.write(str("Beginning with mark_expired_access_codes_as_expired ") + str(datetime.datetime.utcnow()))
        # f.write(str(os.popen("uptime").read()))
        active_access_codes=api.models.AccessCodes.query.filter(api.models.AccessCodes.status != -1).all()       
        for access_code in active_access_codes:
            if datetime.datetime.utcnow() > (datetime.datetime.strptime(str(access_code.created_at), '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=int(access_code.life_cycle))):
            #     log = SCLogs({
            # "log": 'mark_expired_access_codes_as_expired: ' + '  ' + str(access_code) + '   ' + str(access_code.life_cycle)})
            #     db.session.add(log)
            #     db.session.commit() 
                access_code.status = -1
                db.session.commit() 
        # f.write(str(os.popen("uptime").read()))  
        # f.write(str("Ended with mark_expired_access_codes_as_expired ") + str(datetime.datetime.utcnow())) 
        # f.close()     
        return 'OK'                    
    except Exception as e:
        log = api.models.SCLogs({
                    "log": ' error in mark_expired_access_codes_as_expired  ' + str(e)
                    })
        db.session.add(log)
        db.session.commit()    
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()         
    finally:
        db.session.close()  # optional, depends on use case 
        # f.write(str("Ended with mark_expired_access_codes_as_expired ") + str(datetime.datetime.utcnow()))
        # f.close()
        return 'OK'

@access_codes_controller.route("/v1/generate/access_code", methods=['POST'])
def register():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        data = json.loads(request.data)
        for key in ['vendor_name', 'course_name', 'course_duration', 'course_created', 'total_codes', 'life_cycle','user_id']:
            if key == 'vendor_name' and vendor_id:
                continue
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        vendor_name = decoded_token.get('vendor_name') if vendor_id else data['vendor_name']
        course_name = data['course_name']
        duration = data['course_duration']
        course_created = data['course_created']
        total_codes = data['total_codes']
        life_cycle = data['life_cycle']
        user_id = data['user_id']

        for i in range(int(total_codes)):
            now = datetime.datetime.now()
            data = str(now)+str(course_name)+str(duration)+str(course_created)
            code = int(hashlib.sha1(data.encode("utf-8")
                                    ).hexdigest(), 16) % (10 ** 8)
            new_acccess_codes = api.models.AccessCodes({
                'course_name': course_name,
                'vendor_name': vendor_name,
                'access_code': code,
                'status': 0,
                'first_name': 'null',
                'last_name': 'null',
                'email': 'null',
                'key': Fernet.generate_key().decode('utf-8').encode('utf-8'),
                'password': 'null',
                'user_course_id':0,
                'life_cycle':life_cycle,
                'percent':0,
                'phone_no':0,
                'motp':0,                
                'access_codes_user_id':user_id,
                'progress':None,
                'user_type':None,
                'token':None
            })
            db.session.add(new_acccess_codes)
            db.session.commit()
            db.session.refresh(new_acccess_codes)

        all_codes = api.models.AccessCodes.query.filter_by(
            course_name=str(course_name)).first()
        if all_codes:
            return Response(json.dumps({
                'Message': "Access code creation successful"
            }), status=200)
        else:
            return Response(json.dumps({
                'Error': "Access code creation failed"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/register/access_code", methods=['POST'])
def instructor_accesscode():
    try:
        data = json.loads(request.data)
        for key in ['email','access_code','course_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        email = data['email']
        course = data['course_name']
        all_codes = api.models.AccessCodes.query.filter_by(
            email=str(email),course_name = str(course)).order_by('-id').first()
        if all_codes:
            all_codes.access_code = data['access_code']
            db.session.commit()
            db.session.refresh(all_codes)
            return Response(json.dumps({'Message': "Access code registration successful"}), status=200)                   
        else:
            return Response(json.dumps({
                   'Error': "Access Code already assigned to different user"
                }), status=400) 
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/list/access_codes", methods=['GET'])
def get_codes():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        codes = api.models.AccessCodes.query.all()
        result = []
        log = api.models.SCLogs({
        "log": 'v1/list/access_codes:: 182'})
        db.session.add(log)
        db.session.commit() 
        if codes:
            for data in codes:
                if vendor_id and vendor_name != data.vendor_name:
                    continue
                log = api.models.SCLogs({
                "log": 'v1/list/access_codes:: 200 looping'})
                db.session.add(log)
                db.session.commit() 
                if data.key == "null":
                    print( data.key)
                    result.append({
                        'id':data.id,
                        'course_name': str(data.course_name),
                        'vendor_name': data.vendor_name,
                        'access_code': data.access_code,
                        'status': data.status,
                        'life_cycle':data.life_cycle,
                        'user_course_id':data.user_course_id,
                        'user_type':data.user_type,
                                    
                    })
                else:
                    log = api.models.SCLogs({
                    "log": 'v1/list/access_codes:: 222 else' + str(data.access_code)})
                    db.session.add(log)
                    db.session.commit() 
                    first_name = ''
                    last_name = ''
                    f=Fernet(data.key)
                    if data.first_name is not None and data.first_name != 'null':
                        encoded_first_name = bytes(data.first_name, 'utf-8')
                        decrypted_first_name = f.decrypt(encoded_first_name)
                        first_name = (decrypted_first_name.decode())
                    if data.last_name is not None and data.last_name != 'null':
                        encoded_last_name = bytes(data.last_name, 'utf-8')
                        decrypted_last_name = f.decrypt(encoded_last_name)
                        last_name = (decrypted_last_name.decode())
                    result.append({
                        'id':data.id,
                        'course_name': str(data.course_name),
                        'vendor_name': data.vendor_name,
                        'access_code': data.access_code,
                        'status': data.status,
                        'life_cycle':data.life_cycle,
                        'user_course_id':data.user_course_id,
                        'user_type':data.user_type,
                        'first_name':first_name,
                        'last_name':last_name,
                        'email':data.email,
                    })
        log = api.models.SCLogs({
        "log": 'v1/list/access_codes:: 250 ' + str(result)})
        db.session.add(log)
        db.session.commit() 
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
        "log": 'v1/list/access_codes:: 258 error ' + str(e)})
        db.session.add(log)
        db.session.commit()    
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/validate/access_code", methods=['POST'])
def validate():
    try:
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        access_code = data['access_code']
        
        all_codes = api.models.AccessCodes.query.filter_by(
            access_code=str(access_code)).first()
        if all_codes:
            if all_codes.first_name == 'null' and all_codes.last_name == 'null' and all_codes.email == 'null':
                user_with_access_code = api.models.AccessCodes.query.filter_by(
                email=str(data['email'])).first()
                if user_with_access_code is not None:
                    return Response(json.dumps({
                                'Error': "User with this email address already exists"
                            }), status=400) 
                
                key = Fernet.generate_key()
                first_name = str(data['first_name']).encode()
                last_name = str(data['last_name']).encode()
                email = str(data['email'])
                password = str(data['password']).encode()
                f = Fernet(key)
                encrypted_first_name = f.encrypt(first_name)
                encrypted_last_name = f.encrypt(last_name)
                user_type = data['user_type']
                
                
                if(data['student_portal']==True):

                    encrypted_password = f.encrypt(password)
                    all_codes.status = 0
                    all_codes.first_name = encrypted_first_name
                    all_codes.last_name = encrypted_last_name
                    all_codes.email = email
                    all_codes.user_type = user_type
                    all_codes.api_key = 'null'
                    all_codes.phone_no = data['phone']
                    all_codes.motp = data['motp']
                    all_codes.password = encrypted_password
                    all_codes.key = key
                    db.session.commit()
                    db.session.refresh(all_codes)
                else:
                    encrypted_password = f.encrypt(password)
                    all_codes.status = 1
                    all_codes.first_name = encrypted_first_name
                    all_codes.last_name = encrypted_last_name
                    all_codes.email = email
                    all_codes.user_type = user_type
                    all_codes.api_key = 'null'
                    all_codes.phone_no = data['phone']
                    all_codes.motp = data['motp']
                    all_codes.password = encrypted_password
                    all_codes.key = key
                    db.session.commit()
                    db.session.refresh(all_codes)               
                sender = 'accesscode@securitycentric.net'
                receivers =str(data['email'])
              
                SUBJECT = "User Details"
                TEXT = "Details of user with First Name: "+data['first_name'] + " Last Name: "+data['last_name'] + \
                "\n https://idp.securitycentric.net/login" + \
                            "\n email:"+data['email'] + "\n password:" + \
                            data['password'] + "\n Access code:"+data['access_code']
                message = 'From:accesscode@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)

                try:
                    smtpObj = smtplib.SMTP('172.20.9.21')
                    smtpObj.sendmail(sender, receivers, message)

                except SMTPException:
                            print("Error: unable to send email")
                return Response(json.dumps({
                            'Message': "Access code validation successful"
                        }), status=200) 
                
   
                    
            else:
                return Response(json.dumps({
                   'Error': "Access Code already assigned to different user"
                }), status=400)
                    
        else:
            return Response(json.dumps({
                    'Error': "Invalid access code"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@access_codes_controller.route("/v1/redeem/access_code", methods=['POST'])
def redeem_access_code():
    try:
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        access_code = data['access_code']
        
        all_codes = api.models.AccessCodes.query.filter_by(
            access_code=str(access_code)).first()
        if all_codes:
            if all_codes.first_name == 'null' and all_codes.last_name == 'null' and all_codes.email == 'null':                
                key = Fernet.generate_key()
                first_name = str(data['first_name']).encode()
                last_name = str(data['last_name']).encode()
                email = str(data['email'])
                password = str(data['password']).encode()
                f = Fernet(key)
                encrypted_first_name = f.encrypt(first_name)
                encrypted_last_name = f.encrypt(last_name)
                user_type = data['user_type']
                
                
                if(data['student_portal']==True):

                    encrypted_password = f.encrypt(password)
                    all_codes.status = 0
                    all_codes.first_name = encrypted_first_name
                    all_codes.last_name = encrypted_last_name
                    all_codes.email = email
                    all_codes.user_type = user_type
                    all_codes.api_key = 'null'
                    all_codes.phone_no = data['phone']
                    all_codes.motp = data['motp']
                    all_codes.password = encrypted_password
                    all_codes.key = key
                    db.session.commit()
                    db.session.refresh(all_codes)
                else:
                    encrypted_password = f.encrypt(password)
                    all_codes.status = 1
                    all_codes.first_name = encrypted_first_name
                    all_codes.last_name = encrypted_last_name
                    all_codes.email = email
                    all_codes.user_type = user_type
                    all_codes.api_key = 'null'
                    all_codes.phone_no = data['phone']
                    all_codes.motp = data['motp']
                    all_codes.password = encrypted_password
                    all_codes.key = key
                    db.session.commit()
                    db.session.refresh(all_codes)               
                sender = 'accesscode@securitycentric.net'
                receivers =str(data['email'])
              
                SUBJECT = "User Details"
                TEXT = "Details of user with First Name: "+data['first_name'] + " Last Name: "+data['last_name'] + \
                "\n https://idp.securitycentric.net/login" + \
                            "\n email:"+data['email'] + "\n password:" + \
                            data['password'] + "\n Access code:"+data['access_code']
                message = 'From:accesscode@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)

                try:
                    smtpObj = smtplib.SMTP('172.20.9.21')
                    smtpObj.sendmail(sender, receivers, message)

                except SMTPException:
                            print("Error: unable to send email")
                return Response(json.dumps({
                            'Message': "Access code validation successful"
                        }), status=200) 
                
   
                    
            else:
                return Response(json.dumps({
                   'Error': "Access Code already assigned to different user"
                }), status=400)
                    
        else:
            return Response(json.dumps({
                    'Error': "Invalid access code"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/register/instructor", methods=['POST'])
def register_instructor():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        
        for key in ['first_name', 'last_name', 'password','phone_no','motp' ,'email', 'user_type','course_name','vendor_name','user_id']:
            if vendor_id and key == 'vendor_name':
                continue
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        key = Fernet.generate_key()
        first_name = str(data['first_name']).encode()
        
        last_name = str(data['last_name']).encode()
        email = str(data['email'])
        
        
        password = str(data['password']).encode()
        
        f = Fernet(key)
        encrypted_first_name = f.encrypt(first_name)
        encrypted_last_name = f.encrypt(last_name)
        user_type = data['user_type']               
        encrypted_password = f.encrypt(password)        
        course = data['course_name']       
        user_courses=[] 
        for c in range(len(course)):
            my_course = api.models.Courses.query.filter_by(course_name=str(course[c])).first()
            duration = my_course.course_duration            
            course_created = my_course.created_at            
            now = datetime.datetime.now()
            my_data = str(now)+str(course[c])+str(duration)+str(course_created)
            my_code = int(hashlib.sha1(my_data.encode("utf-8")
                                    ).hexdigest(), 16) % (10 ** 8)
            user=api.models.AccessCodes.query.filter_by(email=str(email)).all()
            for u in user:
                if(u.email==str(data['email'])):
                    print("something is happening")
                    print(u.course_name)
                    user_courses.append(u.course_name)
                else:
                    print("nothing is happing")  

            print(user_courses)
            if(course[c] in user_courses ):
                print("exiata")
                return Response(json.dumps({
                    'Error': " This mail id is alreday registerd with course '" + course[c] + "'"
                }), status=402)
                
            else:
                new_acccess_codes = api.models.AccessCodes({
                'course_name': course[c],
                'vendor_name':vendor_name if vendor_id else data['vendor_name'],
                'access_code': my_code,
                'status': 0,
                'first_name': encrypted_first_name,
                'last_name': encrypted_last_name,
                'email': email,
                'phone_no':data['phone_no'],   
                'motp':data['motp'],             
                'key': key,
                'password': encrypted_password,
                'user_course_id':0,
                'life_cycle':364,
                'percent':0,
                'progress':None,
                'user_type':data['user_type'],
                'access_codes_user_id':data['user_id'],
                'token':None
            })
                db.session.add(new_acccess_codes)
                db.session.commit()
                db.session.refresh(new_acccess_codes)
                sender = 'accesscode@securitycentric.net'
                receivers = data['email']
              
                SUBJECT = "User Details"
                TEXT = "Details of user with First Name: "+data['first_name'] + " Last Name: "+data['last_name'] + \
                "\n https://idp.securitycentric.net/login" + \
                            "\n email:"+data['email'] + "\n password:" + \
                            data['password'] + "\n Access code:"+str(my_code)
                message = 'From:accesscode@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)
                # print("exists====>",course[c])
                print("does not exists===?",course[c])

            

            try:
                smtpObj = smtplib.SMTP('172.20.9.21')
                smtpObj.sendmail(sender, receivers, message)

            except SMTPException:
                        print("Error: unable to send email")
                        
        return Response(json.dumps({
                    'Success': "Instructor registered"
                }), status=200)
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/rest_password/instructor", methods=['POST'])
def reset_password():
    try:
        data = json.loads(request.data)
        for key in ['email','password','token',"userType"]:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        check=api.models.Resets.query.filter_by(token=data['token']).first()
        user_type = ''
        if check:
            user = api.models.AccessCodes.query.filter_by(email=data['email'],user_type=data['userType']).all()    
            print(user)
            if len(user) > 0:
                user_type = user
                print('inside if instructor',user_type)
            else:
                user = api.models.AccessCodes.query.filter_by(email=data['email'],user_type=-1).all()
                user_type = user   
                print('inside if instructor des',user_type)
            if user_type:
                for u in user_type:   
                    key = u.key
                    encoded_message = str(data['password']).encode()
                    f = Fernet(key)        
                    encrypted_message = f.encrypt(encoded_message)
                    if 'password' in data.keys():
                        u.password=encrypted_message                   
                        
                    db.session.commit()
                    db.session.refresh(u)
                return Response(json.dumps({
                    'Message': "Password Changed Sucessfully"
                    }), status=200) 
            else:
                return Response(json.dumps({
                        'Message': "No user Found!"
                    }), status=400) 
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/forgot_password/instructor", methods=['POST'])
def forgot_password():  
    try:
        
        data = json.loads(request.data)
        for key in ['email','token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
            temp_token = data['token']
            if data['otp'] == True:
                temp_token = str(data['token'])[:6]
                 
            new_token = api.models.Resets({
                'token': temp_token,            
                })
            usertoken=temp_token
            
            db.session.add(new_token)
            db.session.commit()
            db.session.refresh(new_token) 
            db.session.commit()
            db.session.refresh(new_token)     
            sender = 'support@securitycentric.net'
            receivers = data['email']
            if data['otp'] == False:
                SUBJECT = "Forgot Password"
                TEXT = "Reset your password with following link (NOTE: This link will be valid for 15 minutes) link to access: link to access: https://idp.securitycentric.net/resetpassword?&token="+str(usertoken)
                message = 'From:support@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)
            else:
                SUBJECT = "Login Otp"
                TEXT = "OTP for Login (NOTE: This link will be valid for 15 minutes):"+str(usertoken)
                message = 'From:support@securitycentric.net\nSubject: {}\n\n{}'.format(SUBJECT, TEXT)
            try:
                smtpObj = smtplib.SMTP('172.20.9.21')
                smtpObj.sendmail(sender, receivers, message)

            except SMTPException:
                print("Error: unable to send email")
            return Response(json.dumps({
                    'Message': "Reset link sent"
                    }), status=200)          
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/otp/verification", methods=['POST'])
def otp_verification():
    try:
        data = json.loads(request.data)
        for key in ['otp']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        check=api.models.Resets.query.filter_by(token=data['otp']).first()
        if check:            
            return Response(json.dumps({
                    'Message': "Valid OTP"
                    }), status=200) 
        else:
            return Response(json.dumps({
                        'Message': "Invalid OTP"
                    }), status=400) 
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/delete/instructor", methods=['POST'])
def delete_instructor():
    try:
        decoded_token = handle_token()
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['user_id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        code = None
        if vendor_id:
            code = api.models.AccessCodes.query.filter_by(id=data['user_id'],vendor_name=vendor_name).first()
        else:
            code = api.models.AccessCodes.query.filter_by(id=data['user_id']).first()    
        if code:
            db.session.delete(code)
            db.session.commit()
            if vendor_id:
                code = api.models.AccessCodes.query.filter_by(id=data['user_id'],vendor_name=vendor_name).first()
            else:
                code = api.models.AccessCodes.query.filter_by(id=data['user_id']).first()  
            if code:
                return Response(json.dumps({"Error": 'Instructor deletion failed'}), status=400)
            else:
                return Response(json.dumps({"Message": 'Instructor deleted successfully'}), status=200)

        else:
            return Response(json.dumps({"Error": 'Id not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/update/instructor", methods=['POST'])
def update_instructor():
    try:
        decoded_token = handle_token()
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['user_id','first_name','last_name','phone_no','user_type','email_id','motp']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user_type = data['user_type']
        code= api.models.AccessCodes.query.filter_by(
                email=data['email_id']).all()
        first_name = str(data['first_name']).encode()
        last_name = str(data['last_name']).encode()
        print("working here")
        if code:
            for c in code:
                if vendor_id and vendor_name != c.vendor_name:
                    continue
                key = c.key
                f = Fernet(key)
                encrypted_first_name = f.encrypt(first_name )
                encrypted_last_name = f.encrypt(last_name)
                if c.user_type==0:
                    print("do nothing")
                else:
                    if 'first_name' in data.keys():
                        c.first_name=encrypted_first_name
                    if 'last_name' in data.keys():
                        c.last_name=encrypted_last_name
                    if 'motp' in data.keys():
                        c.motp=data['motp']
                    if 'user_type' in data.keys():
                        c.user_type=data['user_type']
                    if 'phone_no' in data.keys():
                        c.phone_no=data['phone_no']
            db.session.commit()
            db.session.refresh(c)
            code = api.models.AccessCodes.query.filter_by(email=data['email_id'], user_type=data['user_type']).all()
            if code:
                return Response(json.dumps({
                    'Message': "Successfully updated"
                }), status=200)
        else:
            return Response(json.dumps({"Error":'code not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e) 
    finally:
        db.session.close()

@access_codes_controller.route("/v1/view/instructors", methods=['POST'])
def viewInstructors():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['user_type']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user_type = data['user_type']
        all_codes = api.models.AccessCodes.query.filter(api.models.AccessCodes.user_type.in_(user_type)).all()
        result=[]      
        if all_codes:
            for c in all_codes:
                if vendor_id and vendor_name != c.vendor_name:
                    continue
                encoded_first_name = bytes(c.first_name, 'utf-8')
                encoded_last_name = bytes(c.last_name, 'utf-8')
                key = c.key
                f = Fernet(key)
                decrypted_first_name = f.decrypt(encoded_first_name)
                first_name = (decrypted_first_name.decode())
                decrypted_last_name = f.decrypt(encoded_last_name)
                
                last_name = (decrypted_last_name.decode())                
                email = c.email
                phone_no = c.phone_no
                vendor_name = c.vendor_name
                course_name = c.course_name
                user_id = c.id
                motp = c.motp
                user_type = c.user_type    
                result.append({'id':user_id,'first_name': str(first_name),'last_name': last_name,'phone_no':phone_no,'email': email,'vendor_name':vendor_name,'course_name':course_name,'motp':motp,'user_type':user_type})
            return Response(json.dumps({
                'data': result,              
            }), status=200)
        else:
            return Response(json.dumps({
                'Error': "Invalid access code"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/view/instructors/<email>/labs", methods=['GET'])
def viewInstructorLabs(email):
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        email_match = re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)
        if email is None or not bool(email_match):
            return Response(json.dumps({
                'Error': "Please provide a valid email address"
            }), status=400)    
        all_codes = api.models.AccessCodes.query.filter(api.models.AccessCodes.user_type.in_([1,-1]),api.models.AccessCodes.email == email).all()
        result=[]
        if all_codes:
            for c in all_codes:
                if vendor_id and vendor_name != c.vendor_name:
                    continue
                course_name = c.course_name
                vendor_name = c.vendor_name
                result.append({'vendor_name':vendor_name,'course_name':course_name})
            return Response(json.dumps({
                'data': result,              
            }), status=200)
        else:
            return Response(json.dumps({
                'Error': "Invalid access code"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/view/lms-user", methods=['POST'])
def viewLMSUser():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        access_code = data['access_code']
        if vendor_id:
            access_code = api.models.AccessCodes.query.filter_by(access_code=str(access_code),vendor_name=vendor_name).all()
            if not access_code:
                return Response(json.dumps({
                    'Error': "You are not allowed to modify details of this access code"
                }), status=400)    
        all_codes = api.models.AccessCodes.query.filter_by(
            access_code=str(access_code)).first()

        if all_codes:

            key = all_codes.key
            encoded_first_name = bytes(all_codes.first_name, 'utf-8')
            encoded_last_name = bytes(all_codes.last_name, 'utf-8')
            
            f = Fernet(key)
            decrypted_first_name = f.decrypt(encoded_first_name)
            first_name = (decrypted_first_name.decode())
            decrypted_last_name = f.decrypt(encoded_last_name)
            last_name = (decrypted_last_name.decode())
            
            email = all_codes.email

            return Response(json.dumps({
                'first_name': str(first_name),
                'last_name': last_name,
                'access_code': data['access_code'],
                'email': email
            }), status=200)
        else:
            return Response(json.dumps({
                'Error': "Invalid access code"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/get/access_codes_report", methods=['POST'])
def get_report():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        data = json.loads(request.data)
        if 'report_type' not in data.keys():
            return Response(json.dumps({
                'Error': "Missing parameter 'report_type'"
            }), status=402)
        report_data = []
        vendor_name = decoded_token.get('vendor_name') if vendor_id else data['vendor']
        if data['report_type'] == 'access_codes':
            access_codes = api.models.AccessCodes.query.filter_by(
                vendor_name=vendor_name, course_name=data['course']).all()

            if access_codes:
                for ac in access_codes:
                    status = ''
                    if ac.status == 0:
                        status = 'False'
                    else:
                        status = 'True'

                    d = {
                        "Course name": ac.course_name,
                        "Vendor": ac.vendor_name,
                        "Access code": ac.access_code,
                        "Used access code": status
                    }
                    report_data.append(d)

        if report_data != []:
            return send_csv(report_data, "report.csv", report_data[0].keys())
        else:
            return Response(json.dumps({
                'Error': "No data to download"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/authenticateUser/access_code", methods=['POST'])
def authenticate():
    try:
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
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
        access_code = data['access_code']
        password = data['password']
        user_key = api.models.AccessCodes.query.filter_by(
            access_code=str(access_code)).first()
        if user_key:
            key = user_key.key

            encoded_password = bytes(user_key.password, 'utf-8')
            print("email from database",user_key.email)
            f = Fernet(key)
            decrypted_password = f.decrypt(encoded_password)
            decrypted_password = decrypted_password.decode()
            print(decrypted_password)
            email = data['email']
            if password == str(decrypted_password) and email == str(user_key.email):
                valid_user = api.models.AccessCodes.query.filter_by(
                    access_code=str(access_code)).first()
                result = []
                if valid_user:
                    encoded_first_name = bytes(user_key.first_name, 'utf-8')
                    decrypted_first_name = f.decrypt(encoded_first_name)
                    decrypted_first_name = decrypted_first_name.decode()
                    encoded_last_name = bytes(user_key.last_name, 'utf-8')
                    decrypted_last_name = f.decrypt(encoded_last_name)
                    decrypted_last_name = decrypted_last_name.decode()
                    return Response(json.dumps({
                        'first_name': decrypted_first_name,
                        'last_name': decrypted_last_name,
                        'access_code': data['access_code'],
                        'email': user_key.email
                    }), status=200)
                else:
                    return Response(json.dumps({
                        'Error': "Invalid access code"
                    }), status=400)
            else:
                return Response(json.dumps({
                    'Error': "Invalid username/password."
                }), status=400)
        else:
            return Response(json.dumps({
                'Error': "Invalid access code"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/delete/access_code", methods=['POST'])
def delete_access_code():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        if vendor_id:
            access_code = api.models.AccessCodes.query.filter_by(access_code=str(access_code),vendor_name=vendor_name).all()
            if not access_code:
                return Response(json.dumps({
                    'Error': "You are not allowed to delete this access code"
                }), status=400)    
        code = api.models.AccessCodes.query.filter_by(
            access_code=data['access_code']).first()
        if code:
            if code.email:
                code.access_code=None;
                code.status=1;
                # code.course_name=None;
                db.session.commit()
                return Response(json.dumps({"Error": 'Access code deletion failed'}), status=200)
            else:
                print("email does not exits")
                db.session.delete(code)
                db.session.commit()
                code = api.models.AccessCodes.query.filter_by(
                 access_code=data['access_code']).first()
                if code:
                    return Response(json.dumps({"Error": 'Access code deletion failed'}), status=400)
                else:
                    return Response(json.dumps({"Message": 'Access code deleted successfully'}), status=200)
        else:
            return Response(json.dumps({"Error": 'Access code not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/delete/access_db", methods=['POST'])
def delete_access_db():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        table = data['table']
        if table == 'AccessCodes':
            code = api.models.AccessCodes.query.filter_by(
                id=data['id']).first()       
            if code:
                db.session.delete(code)
                db.session.commit()
        elif table == 'VirtualMachines':
            code = api.models.VirtualMachines.query.filter_by(
                id=data['id']).first()       
            if code:
                db.session.delete(code)
                db.session.commit()
        elif table == 'UserCourse':
            code = api.models.UserCourse.query.filter_by(
                id=data['id']).first()       
            if code:
                db.session.delete(code)
                db.session.commit()
        else:
            code = db.session.query(api.models.VendorUsers).filter_by(
                id=data['id']).filter_by(status=True).first()      
            if code:
                code.status = False
                db.session.commit()
            
        return Response(json.dumps({"Message": 'DB row deleted successfully'}), status=200)

        

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/guide/progression", methods=['POST'])
def get_progression_api():
    try:
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=400)
        user_key = api.models.AccessCodes.query.filter_by(
            access_code=str(data['access_code'])).first()        
        if user_key:  
             return Response(json.dumps({"data":{"percentage":user_key.percent,"progress":user_key.progress}}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/update/progression", methods=['POST'])
def update_user_progression():
    try:
        
        data = json.loads(request.data)
        for key in ['access_code']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=400)
        user_key = api.models.AccessCodes.query.filter_by(
            access_code=str(data['access_code'])).first()   
           
        if user_key:             
            temp = user_key.progress
            final=[]
            if temp == None:
                
                user_key.progress = str(data['progress'])
                
            else:
                temp = temp + ',' + data['progress']
                user_key.progress = str(temp) 
             
            user_key.percent = int(data['percent'])+user_key.percent
            db.session.commit()  
            return Response(json.dumps({"data":"Updated successfully"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/register_event/instructor", methods=['POST'])
def register_event():
    try:
        data = json.loads(request.data)
        
        for key in ['event']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)      
            
        new_event = api.models.Reminders({'event': data['event']})
        db.session.add(new_event)
        db.session.commit()
        db.session.refresh(new_event)                                    
        return Response(json.dumps({
                    'Success': "Event Added"
                }), status=200)
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/list_event/instructor", methods=['GET'])
def list_event():
    try:
        events = api.models.Reminders.query.all()
        result=[]
        if events:
            for data in events:
                result.append(data.event)
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/delete/event", methods=['POST'])
def delete_event():
    try:        
        data = json.loads(request.data)       
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        code = api.models.Reminders.query.all()
      
        myevent = ''
        if code:
           
            for c in code:                              
                if c.event['id'] == data['id']:
                    myevent = c.id             
            
            code = api.models.Reminders.query.filter_by(id=int(myevent)).first()            
            db.session.delete(code)
            db.session.commit()
            code = api.models.Reminders.query.filter_by(id=int(myevent)).first()
            if code:
                return Response(json.dumps({"Error": 'Event deletion failed'}), status=400)
            else:
                return Response(json.dumps({"Message": 'Event deleted successfully'}), status=200)

        else:
            return Response(json.dumps({"Error": 'Event not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/update/event", methods=['POST'])
def update_event():
    try:
        data = json.loads(request.data)
        
        myevent = api.models.Reminders.query.filter_by(id=int(data['id'])).first()        
        if myevent: 
             
            myevent.event = data['event']
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@access_codes_controller.route("/v1/multidelete/access_code", methods=['POST'])
def multidelete():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        for key in ['ids']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        print("ids",data["ids"])
        for id in data['ids']:
            print("id-->",  id)
            if vendor_id:
                access_code = api.models.AccessCodes.query.filter_by(access_code=id,vendor_name=vendor_name).all()
                if not access_code:
                    continue                      
            access_code = api.models.AccessCodes.query.filter_by(access_code=id).first()
            if(access_code):
                db.session.delete(access_code)
                db.session.commit()
        return Response(json.dumps({"Message":' deleted successfully'}),status=200)           
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        print(e)    
        return Response(json.dumps({"Message":' Error while deleting access_codes'}),status=500)
    finally:
        db.session.close()    
        
