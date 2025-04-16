from flask import Blueprint, request, Response, redirect
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
import requests
# from pprint import pprint
from api.controllers.configuration_controller import *
# import uuid
# from lti import ToolConfig
# import urllib
# from bs4 import BeautifulSoup
# from pylti.flask import lti
# import pyslet.http.client as http
# import pyslet.http.auth as auth
# import urllib.request as urllib2
import re
# import schedule
# from threading import Timer
from apscheduler.schedulers.background import BackgroundScheduler
# import sys
# import pandas
# import argparse
# import urllib.parse
import paramiko
from cryptography.fernet import Fernet
from netaddr import *
# import ssl
import pika
import re
from smtplib import SMTPException
import smtplib
import time
users_course_controller = Blueprint('users_course_controller', __name__)
CORS(users_course_controller)    
token=''
count=1

def job():
    user_course = api.models.UserCourse.query.all()        
    # if user_course:
    #     for data in user_course:           
    #         date_1 = datetime.datetime.strptime(str(data.created_at),'%Y-%m-%d %H:%M:%S')
    #         start_date = str(date_1).split(" ")[0]            
    #         end_date = (datetime.datetime.strptime(start_date, '%Y-%m-%d') + datetime.timedelta(days=int(data.course_duration))).strftime('%Y-%m-%d')
    #         current_date = datetime.datetime.today().strftime('%Y-%m-%d')            
    #         print(current_date,end_date)
    #         if(str(current_date) == str(end_date)):
    #             data= {'id':data.id}
    #             requests.post('https://sc-api-us-v2.securitycentric.net/v11816/user_course', json=data)
    #         else:
    #             print("No user to delete")
    codes = api.models.AccessCodes.query.all()        
    if codes:
        for data in codes:           
            date_1 = datetime.datetime.strptime(str(data.created_at),'%Y-%m-%d %H:%M:%S')
            start_date = str(date_1).split(" ")[0]            
            end_date = (datetime.datetime.strptime(start_date, '%Y-%m-%d') + datetime.timedelta(days=int(data.life_cycle))).strftime('%Y-%m-%d')
            current_date = datetime.datetime.today().strftime('%Y-%m-%d')            
            print(current_date,end_date)
            if(str(current_date) == str(end_date)):
                print(data.access_code)
                a_c= {'access_code':str(data.access_code)}                              
                requests.post('https://sc-api-us-v2.securitycentric.net/v1/delete/access_code', json=a_c)
            else:
                print("No codes to delete")
    sessions = api.models.UserSessions.query.all()    
    if sessions:
        for data in sessions:           
            date_1 = datetime.datetime.strptime(str(data.created_at),'%Y-%m-%d %H:%M:%S')
            start_date = str(date_1).split(" ")[0]            
            end_date = (datetime.datetime.strptime(start_date, '%Y-%m-%d') + datetime.timedelta(days=int(1))).strftime('%Y-%m-%d')
            current_date = datetime.datetime.today().strftime('%Y-%m-%d')            
            
            if(str(current_date) == str(end_date)):                
                data= {'id':data.id}
                requests.post('https://sc-api-us-v2.securitycentric.net/v1/delete/user_session', json=data)
            else:
                print("No user session to delete")       
    return

def job3():
    tokens = api.models.Resets.query.all()    
    if tokens:
        for data in tokens:           
            start_date = datetime.datetime.strptime(str(data.created_at),'%Y-%m-%d %H:%M:%S')            
            end_date = start_date + \
                        datetime.timedelta(minutes = 15)
            current_date = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            formated_current_date = datetime.datetime.strptime(str(current_date), "%Y-%m-%d %H:%M:%S")
            formated_end_date = datetime.datetime.strptime(str(end_date),"%Y-%m-%d %H:%M:%S")           
            if(formated_current_date >= formated_end_date):                
                token = api.models.Resets.query.filter_by(id=data.id).first()
                if token:
                    db.session.delete(token)
                    db.session.commit()                
            else:
                print("No user session to delete")       
    return

def job2():
    server_performance() 
    # time.sleep(5)  
      
    #requests.get('https://sc-api-us-v2.securitycentric.net/v1/list/vms')


job_defaults = {    
    'max_instances': 4
}    
scheduler = BackgroundScheduler(job_defaults=job_defaults)
job = scheduler.add_job(job, 'interval', minutes=60)
# job2 = scheduler.add_job(job2, 'interval', seconds=5)
#job3=scheduler.add_job(job3, 'interval', minutes=15)

scheduler.start()
network_result = ''
network_result2 = ''
network_result3 = ''
network_result4 = ''
memory_result = []
cpu_result = []
# new_data = []
cpu_performance_result = []

def chunks(lst, n):   
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

        
def reset_enqueue_credentials(data):
    #    try:
    # log = api.models.SCLogs({
    #     "log": 'basic_publish '})
    # db.session.add(log)
    # db.session.commit()       
    user = os.environ.get('APP_RABBITMQ_USER')
    password = os.environ.get('APP_RABBITMQ_PASSWORD')
    host = os.environ.get('APP_RABBITMQ3_HOST')
    #host = '172.20.4.49'
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(credentials=credentials, host=host))
    try:
        channel = connection.channel()
        channel.queue_declare(queue='scia_queue')
        channel.basic_publish(
            exchange='', routing_key='scia_queue', body=str(data))
        connection.close()
    except Exception as e:
        connection.close()
        print(e)

def ssh_remotely(user, password, host):
    # Create a network
    ##########################################################################

    paramiko.util.log_to_file('ssh.log')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(host, username=user, password=password)
    return client


def run_command_ssh(client, command,per_type):
    stdin, stdout, stderr = client.exec_command(command[0])
    if per_type == 'cpu':
        
        result = stdout.read()  
    
        result=str(result).replace('\\n','')
        result = result.split(' ')
        uuid =[]
        for r in result:        
            if len(r) == 36:
                uuid.append(r)                      
        return uuid
    else:
        result = stdout.read() 
        return (1, result.strip())
    if stderr.readline():
        return (0, stderr.read())

def delete_course_session_guacamole(guac_host,guac_user,guac_password,usernames,user_course_details,instance_names):
    log = api.models.SCLogs({
    "log": ' error while deleting user courses: 195 '
    })
    db.session.add(log)
    db.session.commit()      
    with SSHTunnelForwarder(
    (guac_host, 22),
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
        user_ids=[]
        connection_ids=[]          
        if len(usernames) > 0:       
            format_strings = ','.join(['%s'] * len(usernames))                      
            cursor.execute("SELECT entity_id FROM guacamole_user WHERE username IN (%s)" % format_strings,tuple(usernames))
            guacamole_users=cursor.fetchall()  
            for user in guacamole_users:
                user_ids.append(user[0])
        log = api.models.SCLogs({
        "log": ' error while deleting user courses: 211 '
        })
        db.session.add(log)
        db.session.commit()      
        if len(instance_names) > 0:    
            format_strings = ','.join(['%s'] * len(instance_names))
            cursor.execute("SELECT connection_id FROM guacamole_connection WHERE connection_name IN (%s)" % format_strings,tuple(instance_names))
            guacamole_connections=cursor.fetchall() 
            for connection in guacamole_connections:
                connection_ids.append(connection[0]) 
        if len(user_ids) > 0:       
            format_strings = ','.join(['%s'] * len(user_ids))            
            log = api.models.SCLogs({
            "log": ' error while deleting user courses: 222 ' + str(format_strings) + '  ' + str(type(user_ids))
            })
            db.session.add(log)
            db.session.commit()    
            cursor.execute("DELETE FROM guacamole_entity where entity_id IN (%s)" % format_strings,tuple(user_ids))
            conn.commit()
            cursor.execute("DELETE FROM guacamole_user where user_id IN (%s)" % format_strings,tuple(user_ids))
            conn.commit()
        if len(connection_ids) > 0:        
            format_strings = ','.join(['%s'] * len(connection_ids))
            log = api.models.SCLogs({
            "log": ' error while deleting user courses: 234 ' + str(format_strings) + '  ' + str(type(connection_ids))
            })
            db.session.add(log)
            db.session.commit()   
            cursor.execute("DELETE FROM guacamole_connection_permission where permission='READ' and connection_id IN (%s)" % format_strings,tuple(connection_ids))
            conn.commit()
        log = api.models.SCLogs({
        "log": ' error while deleting user courses: 240 '
        })
        db.session.add(log)
        db.session.commit()      
        cursor.close()
        conn.close()    
    return 'OK'            

@users_course_controller.route("/v1/expired_user_courses", methods=['DELETE'])          
def delete_user_course_on_expiration():
    # f= None
    try:             
        # f= open("expired_user_courses.log","a")
        # f.write(str("Beginning with expired_user_courses ") + str(datetime.datetime.utcnow()))
        # f.write(str(os.popen("uptime").read()))
        ten_mins_before_now = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        user_courses = api.models.UserCourse.query\
                .filter(api.models.UserCourse.is_user_active_lab.is_(False), api.models.UserCourse.lab_last_active<ten_mins_before_now)
        vm_name =''      
        user_course_details = []         
        usernames = []
        codes = []
        users = []
        instances = []
        instance_names = []
        if user_courses is None:
            return 'OK'
        for user_course in user_courses:
            if user_course:
                vm_name = user_course.instance_name           
                instance = api.models.GroupInstances.query.filter_by(name=vm_name).first()
                if instance:
                    if instance.odv_options == 'controls' or instance.odv_options == '':
                        continue    
                code = api.models.AccessCodes.query.filter_by(user_course_id=user_course.id).first()
                user = api.models.VendorUsers.query.filter_by(lab=user_course.instance_name, status=True).first()
                if not user:
                    continue
                user_course_details.append({'user':user, 'user_course':user_course, 'code':code})
                usernames.append(user.username)   
                codes.append(code)
                users.append(user)
                instances.append(instance)
                instance_names.append(user_course.instance_name)
                log = api.models.SCLogs({
                    "log": "/v1/expired_user_courses each entry " + str(user_course.course_name) + ' | ' + str(user.username) + ' | ' +str(user_course.instance_name) + ' | ' + str(code)
                    })
                db.session.add(log)
                db.session.commit()   
        # f.write(str(os.popen("uptime").read()))                
        usernames = list(set(usernames))     
        instance_names = list(set(instance_names))  
        if len(usernames) == 0 and len(instance_names) == 0:
            return 'OK'
        log = api.models.SCLogs({
                    "log": "delete_user_course_on_expiration " + str(usernames) + ' | ' +str(instance_names) + ' | ' + str(user_course_details)
                    })
        db.session.add(log)
        db.session.commit()   
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')
        # log = api.models.SCLogs({
        # "log": ' error while deleting user courses: 286 '
        # })
        # db.session.add(log)
        # db.session.commit()      
        # f.write(str(os.popen("uptime").read()))               
        delete_course_session_guacamole(guac_host,guac_user,guac_password,usernames,user_course_details,instance_names)
            # else:
        # log = api.models.SCLogs({
        # "log": ' error while deleting user courses: 287 '
        # })
        # db.session.add(log)
        # db.session.commit()      
        # f.write(str(os.popen("uptime").read()))  
        delete_course_session_guacamole(guac_host2,guac_user,guac_password,usernames,user_course_details,instance_names)
        # log = api.models.SCLogs({
        # "log": ' error while deleting user courses: 290 ' + str(codes) + ' | ' + str(users) + ' | ' + str(instances)
        # })
        # db.session.add(log)
        # db.session.commit()
        # f.write(str(os.popen("uptime").read()))    
        for code in codes:        
            code.status = 0
            db.session.commit()
            log = api.models.SCLogs({
                    "log": ' error while deleting user courses: 292 '
                    })
            db.session.add(log)
            db.session.commit()
            # f.write(str(os.popen("uptime").read()))    
        for user_course in user_courses:      
            db.session.delete(user_course)
            db.session.commit()
            log = api.models.SCLogs({
                    "log": ' error while deleting user courses: 300 '
                    })
            db.session.add(log)
            db.session.commit() 
            # f.write(str(os.popen("uptime").read()))
        for user in users:
            user.status = False
            now = datetime.datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')  
            user.lab_end_session = current_time
            db.session.commit()
            log = api.models.SCLogs({
                    "log": ' error while deleting user courses: 311 '
                    })
            db.session.add(log)
            db.session.commit() 
            # f.write(str(os.popen("uptime").read()))
        for instance in instances:
            instance.lab_end_session = current_time
            instance.status = 0
            instance.is_assigned = False
            instance.provision_buffer_time_flag = True
            now = datetime.datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            instance.provision_buffer_time = current_time
            db.session.commit()
            log = api.models.SCLogs({
                    "log": ' error while deleting user courses: 325 '
                    })
            db.session.add(log)
            db.session.commit() 
            # f.write(str(os.popen("uptime").read()))
            # f.write(str("Ended with expired_user_courses ") + str(datetime.datetime.utcnow()))
            # f.close()
        return 'OK'        
    except Exception as e:
        log = api.models.SCLogs({
                    "log": ' error while deleting user courses: ' + str(e)
                    })
        db.session.add(log)
        db.session.commit()    
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()    
    finally:
        db.session.close()  # optional, depends on use case  
        # f.write(str("Ended with expired_user_courses ") + str(datetime.datetime.utcnow())) 
        # f.close()           
        return 'OK'    
  
@users_course_controller.route("/v1/instances/status/active", methods=['PATCH'])  
def set_instances_active_after_provision_buffer_time():       
    # f = None
    try:             
        # f= open("set_instances_active_after_provision_buffer_time.log","a")
        # # f.write(str("Beginning with set_instances_active_after_provision_buffer_time ") + str(datetime.datetime.utcnow()))
        # # f.write(str(os.popen("uptime").read()))
        five_mins_before_now = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        instances = api.models.GroupInstances.query\
                .filter(api.models.GroupInstances.provision_buffer_time_flag.is_(True), api.models.GroupInstances.provision_buffer_time<five_mins_before_now)
        for instance in instances:
            instance.status = 1
            instance.is_assigned = False
            instance.provision_buffer_time_flag = False
        db.session.commit()
        # # f.write(str(os.popen("uptime").read()))    
        # # f.write(str("Ended with set_instances_active_after_provision_buffer_time ") + str(datetime.datetime.utcnow()))
        # # f.close()
    except Exception as e:
        log = api.models.SCLogs({
                    "log": ' error while deleting courses: ' + str(e)
                    })
        db.session.add(log)
        db.session.commit()    
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()    
    finally:
        db.session.close() 
        # # f.write(str("Ended with set_instances_active_after_provision_buffer_time ") + str(datetime.datetime.utcnow()))
        # # f.close()
        return 'OK'

@users_course_controller.route("/v1/server_performance", methods=['POST'])
def server_performance():
    try:
        
        
        data = json.loads(request.data)
        for key in ['server_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        server = api.models.Servers.query.filter_by(name=data['server_name']).first()
                        
        key = os.environ.get('XE_PASSWORD_KEY').encode('ascii')
        cipher_suite = Fernet(key)
        password = cipher_suite.decrypt(
                    bytes('gAAAAABfs2FvxtBtBKOTi6Vy_hTmBVhQfkYTflXG_46dDzTYw8Wq__8JTMuGDbXeOtqX0F0TlZUkYJhCWU_BWfMXSJyM3p61NA==', 'raw_unicode_escape')).decode("utf-8")
        client = ssh_remotely('root',password,server.ip_address)           
        network_performace_sent = ["xe host-data-source-query data-source=pif_eth0_tx"]   
        status1 = run_command_ssh(client, network_performace_sent,'null')
        val1 = status1[1]  
        network_performace_recv = ["xe host-data-source-query data-source=pif_eth0_rx"]    
        status2 = run_command_ssh(client, network_performace_recv,'null')
        val2 = status2[1]
        network_performace1_sent = ["xe host-data-source-query data-source=pif_eth1_tx"]   
        status5 = run_command_ssh(client, network_performace1_sent,'null')
        val6 = status5[1]  
        network_performace2_recv = ["xe host-data-source-query data-source=pif_eth1_rx"]    
        status6 = run_command_ssh(client, network_performace2_recv,'null')
        val7 = status6[1]
        memory_free = ["xe host-list params=memory-free --minimal"]    
        status3 = run_command_ssh(client, memory_free,'null')
        val3 = status3[1]
        memory_total = ["xe host-list params=memory-total --minimal"]    
        status4 = run_command_ssh(client, memory_total,'null')
        val4 = status4[1]
        val5 = int(val4) - int(val3)
        val5 = (val5 / 1024 / 1024 / 1024)
        cpu_list = ["xe host-cpu-list"]
        cpu_list_result = run_command_ssh(client, cpu_list,'cpu')
        count = 0   
        ret = 0
        for c in cpu_list_result:            
            count = count + 1
            cpu_performance = ["xe host-cpu-param-get uuid="+c+" param-name=utilisation"]    
            status5 = run_command_ssh(client, cpu_performance,'null')
            val6 = status5[1]  
            ret = ret + float(val6)          
            
        key = datetime.datetime.now().strftime("%H:%M:%S") 
         
            
        if len(memory_result) == 10:   
            # network_result.pop(0)  
            # network_result2.pop(0)      
            memory_result.pop(0)    
            cpu_result.pop(0)         
            network_result = ([key+' Nic-0',float(val1)/1024])
            network_result2 = ([key+' Nic-0',float(val2)/1024])
            network_result3 = ([key+' Nic-1',float(val6)/1024])
            network_result4 = ([key+' Nic-1',float(val7)/1024])
            memory_result.append([key,val5])
            temp = ret/count
            temp = float("{:.2f}".format(temp))
            
            cpu_result.append([key,temp])
        else:
            network_result = ([key+' Nic-0',float(val1)/1024])
            network_result2 = ([key+' Nic-0',float(val2)/1024])
            network_result3 = ([key+' Nic-1',float(val6)/1024])
            network_result4 = ([key+' Nic-1',float(val7)/1024])
            memory_result.append([key,val5])
            temp = ret/count
            temp = float("{:.2f}".format(temp))
            
            cpu_result.append([key,temp])
            
        if data['performance_name'] == 'memory_performance':
            new_data = [{'data':memory_result,'label':'Used Memory'}]
            return Response(json.dumps({"chartdata":new_data}),status=200)
        elif data['performance_name'] == 'cpu_performance':
            new_data = [{'data':cpu_result,'label':'Average CPU'}]   
            return Response(json.dumps({"chartdata":new_data}),status=200) 
        else:  
            new_data = [{'data':[network_result,network_result3],'label':'Bytes Sent'},{'data':[network_result2,network_result4],'label':'Bytes Received'}]  
            return Response(json.dumps({"chartdata":new_data}),status=200)
            
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_course_controller.route("/v1/register/user_course", methods=['POST'])
def register_user_course():
    try:
        
        configuration = api.controllers.configuration_controller.get_global_conf()
        data = json.loads(request.data)
        for key in ['user_name', 'course_name', 'status', 'course_duration', 'instance_name', 'access_token','user_id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=400)
        user =  api.models.Users.query.filter_by(name=data['user_name']).first()  
        instance =  api.models.GroupInstances.query.filter_by(name=data['instance_name']).first()  
        
        if user and instance:
            with SSHTunnelForwarder(
                ("172.20.4.50", 22),
                ssh_username="trainee",
                ssh_password="trainee",
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
                key = os.environ.get('XE_PASSWORD_KEY')
                plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                password=plain_text.decode('utf-8') 
                cursor.execute("INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"','USER');")
                conn.commit() 
                cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"';")
                entity_id=cursor.fetchone()[0]                               
                cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(entity_id)+"','"+str(data['user_name'])+"_test_test"+"_"+str(data['course_name'])+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                conn.commit()               
                                
                cursor.execute("SELECT user_id FROM guacamole_user where username='"+user.username+"';")
                vend_id=cursor.fetchone()[0]
                print("vendor id",vend_id)
                print("Ip address of instance",instance.ip_address)
                cursor.execute("SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+instance.ip_address+"';")
                connection_id=cursor.fetchone()[0]                
                         
                cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ');")
                conn.commit()      
                
                cursor.execute("SELECT entity_id FROM guacamole_connection_permission where entity_id='"+str(vend_id)+"';")
                temp = cursor.fetchone()
                print("Temp",temp)    
                if temp is None:
                    cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(vend_id)+","+str(connection_id)+", 'READ');")
                    conn.commit()
                        
                # cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission,user_id) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ',"+str(vend_id)+");")
                # conn.commit()
                
                cursor.close()
                conn.close()
                print("connection closed")
                vendor_user=api.models.VendorUsers.query.filter_by(
                    username=data['user_name']+"_"+"test_test"+"_"+data["course_name"],
                    status=True,
                    lab=instance.name
                    ).first()
                if  vendor_user:    
                        return Response(json.dumps({'Error': "Lab for " + str(data["course_name"]) + " is active and will end on" + vendor_user.lab_end_session}), status=400) 
                course = api.models.Courses.query.filter_by(course_name=data["course_name"]).first()    
                vendor_user=api.models.VendorUsers({
                    "username":data['user_name']+"_"+"test_test"+"_"+data["course_name"],
                    "vendor_id":user.id,
                    "status":True,
                    "lab":instance.name,
                    "vendor_users_user_id":45,
                    "course_id":course.id
                })
               
                db.session.add(vendor_user)
                db.session.commit()
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Access-Control-Allow-Origin':'*'
                }
                user_data = {
                    'username': user.username+"_"+str(instance.ccu_landing),
                    'password': password
                }
                print(user_data)
                authToken = requests.post('https://scig-v2.securitycentric.net/labview/api/tokens', headers=headers, data=user_data,verify=False).json()
                print(authToken)
                if not "authToken" in authToken:
                    raiseException(authToken)
                # token = uuid.uuid4().hex
                user_course = api.models.UserCourse({                   
                    'user_name': user.name+"_"+"test_test"+"_"+data["course_name"],
                    'course_name': data['course_name'], 
                    'status': data['status'], 
                    'instance_name':data['instance_name'],
                    'course_duration': data['course_duration'], 
                    'access_token': data['access_token'], 
                    'lab_access_url': 'https://172.20.4.50/labview/#/client?token='+authToken["authToken"] ,
                    'access_code_status':0,
                    'user_course_user_id':data['user_id']
                })
                
                db.session.add(user_course)

                db.session.commit()
                db.session.refresh(user_course)
                return Response(json.dumps({
                            'Message': "Uses with course Registered succeessfully"
                        }), status=200)    
        else:
            return Response(json.dumps({
                            'Error': "Instance or Vendor doesn't exists"
                        }), status=400) 
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
@users_course_controller.route("/v1/list/user_course", methods=['GET'])
def get_users():
    try:
        user_course = api.models.UserCourse.query.all()
        result=[]
        if user_course:
            for data in user_course:
                ccu = str(data.instance_name).split('_')[1]
                result.append({
                    'id': data.id,
                    'created_at':str(data.created_at),
                    'user_name': data.user_name,
                    'ccu' : ccu,
                    'connection_broker':data.connection_broker,
                    'course_name': data.course_name, 
                    'status': data.status, 
                    'course_duration': data.course_duration, 
                    'access_token': data.access_token, 
                    'lab_access_url': data.lab_access_url,
                    'access_code_status':data.access_code_status,
                    'user_id':data.user_course_user_id,
                    'lab_user_access_url': data.lab_user_access_url,
                    'is_user_active_lab': data.is_user_active_lab,
                    'lab_last_active': str(data.lab_last_active)
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)


@users_course_controller.route("/v1/update/user_course", methods=['POST'])
def update_user():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user_course = api.models.UserCourse.query.filter_by(id=data['id']).first()
        
        if user_course:
#            if 'user_name' in data.keys():
#                user_course.user_name=data['user_name']
#            if 'course_name' in data.keys():
#                user_course.course_name=data['course_name']
            if 'status' in data.keys(): 
                user_course.status=data['status']
            if 'course_duration' in data.keys(): 
                user_course.course_duration=data['course_duration']
#            if 'lab_access_url' in data.keys():
#                user_course.lab_access_url=data['lab_access_url']
            db.session.commit()
            db.session.refresh(user_course)
            return Response(json.dumps({
                'Message': "Successfully updated"
            }), status=200)
        else: 
            return Response(json.dumps({"Error":'User not found'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@users_course_controller.route("/v1/toggle/user_course/status", methods=['PATCH'])
def toggle_user_course_lab_status():
    try:
        data = json.loads(request.data)
        for key in ['should_set_lab_active','user_course']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user_course = api.models.UserCourse.query.filter_by(id=data['user_course']).first()
        log = api.models.SCLogs({
                "log": '/v1/toggle/user_course/status: ' + str(data['user_course']) + ' with status: ' + str(data['should_set_lab_active'])
                })
        db.session.add(log)
        db.session.commit()   
        if user_course:
            user_course.is_user_active_lab = data['should_set_lab_active']
            now = datetime.datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            user_course.lab_last_active = current_time
            db.session.commit()
            return Response(json.dumps({"Message":'Success'}),status=200)
        else: 
            log = api.models.SCLogs({
                            "log": '/v1/toggle/user_course/status User course not found with id: ' + str(data['user_course'])
                            })
            db.session.add(log)
            db.session.commit()                                        
            return Response(json.dumps({"Error":'User Course entry not found'}),status=404)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
                        "log": '/v1/toggle/user_course/status error : ' + str(e)
                        })
        db.session.add(log)
        db.session.commit()                            
        return raiseException(e)    
    finally:
        db.session.close()    

@users_course_controller.route("/v1/user_course/status", methods=['PATCH'])
def user_course_lab_status():
    try:
        data = json.loads(request.data)
        for key in ['access_token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user_course = api.models.UserCourse.query.filter_by(access_token=data['access_token'],is_user_active_lab=True).first()  
        if user_course:
            return Response(json.dumps({"Error":'Lab is already active for the token provided'}),status=403)
        else: 
            user_course = api.models.UserCourse.query.filter_by(access_token=data['access_token']).first()
            if user_course is None:
                return Response(json.dumps({"Message":'No lab currently active for the token. Please proceed.'}),status=404)
            user_course.is_user_active_lab = True
            now = datetime.datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            user_course.lab_last_active = current_time 
            db.session.commit()   
            return Response(json.dumps({"Message":'No lab currently active for the token. Please proceed.'}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()                     
        return raiseException(e)    
    finally:
        db.session.close()

@users_course_controller.route("/v1/delete/user_course", methods=['POST'])
def delete_user():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        log = api.models.SCLogs({
                        "log": 'line 482'
                        })
        db.session.add(log)
        db.session.commit()                            
        user_course = api.models.UserCourse.query.filter_by(id=data['id']).first()
        # key = os.environ.get('XE_PASSWORD_KEY')
        # gauc_cred = api.models.GaucCred.query.filter_by(access_code=data['access_code']).first()
        # code = api.models.AccessCodes.query.filter_by(access_code=data['access_code']).first()

        # vendor_name = code.vendor_name
        # user =  api.models.Users.query.filter_by(name=vendor_name).first()
        # plain_text = crypto.decrypt(key, str.encode(user.password_digest))
        # password=plain_text.decode('utf-8')
        # user_data = {
        #     'username': gauc_cred.username,
        #     'password': password
        # }
        # authToken = requests.delete(str(gauc_cred.load_balancer_url)+'api/tokens', headers=headers, data=user_data,timeout=5,verify=False).json()
        # if(gauc_cred):
        #         db.session.delete(gauc_cred)
        #         db.session.commit()
        vm_name =''
        log = api.models.SCLogs({
                        "log": 'line 505'
                        })
        db.session.add(log)
        db.session.commit()                            

        if user_course:
            vm_name = user_course.instance_name           
            instance = api.models.GroupInstances.query.filter_by(name=vm_name).first()
            if request.headers.get('x-api-key'):
                if request.headers.get('x-api-key') == '':
                    if instance:
                        if instance.odv_options == 'controls' or instance.odv_options == '':
                            return Response(json.dumps({
                                'Error': "ODV is of type:controls, hence won't be closed."
                            }), status=402)
            code = api.models.AccessCodes.query.filter_by(user_course_id=user_course.id).first()
            user = api.models.VendorUsers.query.filter_by(lab=user_course.instance_name, status=True).first()
            print(user)
            if not user:
                return Response(json.dumps({
                    'Error': "EVM3: User not found"
                }), status=402)
            vendor = api.models.Users.query.filter_by(id=user.vendor_id).first()
            print(vendor)
            guac_user=os.environ.get('APP_GUAC_USER')
            guac_password=os.environ.get('APP_GUAC_PASSWORD')
            guac_host=os.environ.get('APP_GUAC_HOST')
            guac_host2=os.environ.get('APP_GUAC_HOST2')
            with SSHTunnelForwarder(
                (guac_host, 22),
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
                cursor.execute("SELECT entity_id FROM guacamole_user WHERE username='"+user.username+"';")
                guacamole_user=cursor.fetchone()            
                log = api.models.SCLogs({
                        "log": 'line 505' + str(guacamole_user)
                        })
                db.session.add(log)
                db.session.commit()                           
                if guacamole_user:                    
                    with SSHTunnelForwarder(
                    (guac_host, 22),
                    ssh_username=guac_user,
                    ssh_password=guac_password,
                    remote_bind_address=("127.0.0.1", 3306)
                    ) as server:
                        log = api.models.SCLogs({
                        "log": 'line 553'
                        })
                        db.session.add(log)
                        db.session.commit()                       
                        time.sleep(1)
                        conn = mysql.connector.connect(host="127.0.0.1",
                        port=server.local_bind_port,
                        user="root",
                        passwd="sqltoor",
                        db="guacamole")
                        cursor =conn.cursor(buffered=True)
                        log = api.models.SCLogs({
                        "log": str(user.username)+ '    ==565'
                        })                      
                        db.session.add(log)
                        db.session.commit()                                    
                        cursor.execute("SELECT entity_id FROM guacamole_user WHERE username='"+user.username+"';")
                        guacamole_user = cursor.fetchone()
                        log = api.models.SCLogs({
                        "log": str(guacamole_user)+ '    ==568'
                        })                      
                        db.session.add(log)
                        db.session.commit()                                                    
                        cursor.execute("SELECT connection_id FROM guacamole_connection WHERE connection_name='"+user_course.instance_name+"';")
                        guacamole_connection = cursor.fetchone()
                        log = api.models.SCLogs({
                        "log": str(guacamole_connection)+ '    ==579'
                        })
                        db.session.add(log)
                        db.session.commit()                            
                        if guacamole_user is not None:    
                            cursor.execute("DELETE FROM guacamole_entity where entity_id="+str(guacamole_user[0])+" ;")
                            conn.commit()                        
                            cursor.execute("DELETE FROM guacamole_user where user_id="+str(guacamole_user[0])+";")
                            conn.commit()
                            log = api.models.SCLogs({
                            "log": 'ran delete command at 914'
                            })
                            db.session.add(log)
                            db.session.commit()        
                                                   
                        if guacamole_user is not None and guacamole_connection is not None:                                
                            cursor.execute("DELETE FROM guacamole_connection_permission where entity_id="+str(guacamole_user[0])+" and connection_id="+str(guacamole_connection[0])+" and permission='READ';")
                            conn.commit()
                            log = api.models.SCLogs({
                            "log": 'ran delete command at 923'
                            })
                            db.session.add(log)
                            db.session.commit()  

                        cursor.close()
                        conn.close()
                else:
                    with SSHTunnelForwarder(
                    (guac_host2, 22),
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
                        log = api.models.SCLogs({
                        "log": str(user.username)+ '   ==606'
                        })                      
                        db.session.add(log)
                        db.session.commit()                         
                        cursor =conn.cursor(buffered=True)
                        cursor.execute("SELECT entity_id FROM guacamole_user WHERE username='"+user.username+"';")
                        guacamole_user = cursor.fetchone()
                        log = api.models.SCLogs({
                        "log": str(guacamole_user)+ '   ===69  ' +str(user_course.instance_name)
                        })
                        db.session.add(log)
                        db.session.commit()                            
                        cursor.execute("SELECT connection_id FROM guacamole_connection WHERE connection_name='"+user_course.instance_name+"';")
                        guacamole_connection = cursor.fetchone()
                        if guacamole_user is not None:                        
                            cursor.execute("DELETE FROM guacamole_entity where entity_id="+str(guacamole_user[0])+" ;")
                            conn.commit()
                            cursor.execute("DELETE FROM guacamole_user where user_id="+str(guacamole_user[0])+";")
                            conn.commit()
                            log = api.models.SCLogs({
                            "log": 'ran delete command at 963'
                            })
                            db.session.add(log)
                            db.session.commit()  
                        if guacamole_user is not None and guacamole_connection is not None:
                            cursor.execute("DELETE FROM guacamole_connection_permission where entity_id="+str(guacamole_user[0])+" and connection_id="+str(guacamole_connection[0])+" and permission='READ';")
                            conn.commit()
                            log = api.models.SCLogs({
                            "log": 'ran delete command at 972'
                            })
                            db.session.add(log)
                            db.session.commit()                              
                        cursor.close()
                        conn.close()
                        log = api.models.SCLogs({
                        "log": 'line 639 conn.close()'
                        })
                        db.session.add(log)
                        db.session.commit() 
                if code:        
                    code.status = 0
                    db.session.commit() 
            log = api.models.SCLogs({
                    "log": 'line 647 start updates to api db'
                    })
            db.session.add(log)
            db.session.commit()              
            db.session.delete(user_course)
            db.session.commit()
            log = api.models.SCLogs({
                    "log": ' user course deleted line 654   '
                    })
            db.session.add(log)
            db.session.commit()                     
            user.status = False
            now = datetime.datetime.utcnow()
            log = api.models.SCLogs({
                    "log": str(now) + ' <- now line 656 current time  '
                    })
            db.session.add(log)
            db.session.commit()                
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            log = api.models.SCLogs({
                    "log": str(now) + ' <- now line 662 current time ->  ' +  str(current_time)
                    })
            db.session.add(log)
            db.session.commit()    
            user.lab_end_session = current_time
            db.session.commit()
            instance.lab_end_session = current_time
            instance.status = 0
            instance.is_assigned = False
            instance.provision_buffer_time_flag = True
            now = datetime.datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            instance.provision_buffer_time = current_time
            db.session.commit()
            user_course = api.models.UserCourse.query.filter_by(id=data['id']).first()
            
            if user_course:
                return Response(json.dumps({"Error":'user deletion failed'}),status=400)
            else:
                
                data= {"name":vm_name}                    
                requests.post('http://127.0.0.1:5000/v1/revertsnapshot/vm', json=data)
                return Response(json.dumps({"Message":'Registered course deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'user not found'}),status=400)
            db.session.commit()
            db.session.refresh(user_course)

    except Exception as e:
        log = api.models.SCLogs({
                    "log": ' error 691  ' + str(e)
                    })
        db.session.add(log)
        db.session.commit()    
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_course_controller.route("/v1/lab/portal", methods=['GET'])
def portal_user_lab():
    try:
        
        data = {}
        profile_user_id = None
        data['user_name'] = request.args.get('user_name')
        if not data['user_name']:
            return Response(json.dumps({
                    'Error': "Invalid Username"
                }), status=400)
           
        data['course_name'] = re.sub(' ','+',request.args.get('course_name'))
        print(request.args.get('course_name'))
        print( data['course_name'])
        if not data['course_name']:
            return Response(json.dumps({
                    'Error': "Invalid Course"
                }), status=400)
        data['uid'] = request.args.get('uid')
        if not data['uid']:
            return Response(json.dumps({
                    'Error': "Invalid uid"
                }), status=400)
        user =  api.models.Users.query.filter_by(name=data['user_name']).first()
      
        if not user:
            return Response(json.dumps({
                'Error': "Invalid Vendor"
            }), status=400)
        
        log = api.models.SCLogs({"log": '/v1/lab/portal 1064 ==> '})
        db.session.add(log)
        db.session.commit()
        vend_user = api.models.VendorUsers.query.filter_by(username=data['user_name']+"_"+str(data["uid"])+"_"+data["course_name"], status=True).first()
        group = api.models.VmGroups.query.filter_by(group_name=data['course_name']).first()
        log = api.models.SCLogs({"log": '/v1/lab/portal 1069 ==>  VM Groups' + str(group)})
        db.session.add(log)
        db.session.commit()                        

        access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
        log = api.models.SCLogs({"log": '/v1/lab/portal 1074 ==>  '})
        db.session.add(log)
        db.session.commit()                
        if vend_user is not None:
            profile_user_id = vend_user.vendor_users_user_id
            log = api.models.SCLogs({"log": '/v1/lab/portal 1079 ==>  '})
            db.session.add(log)
            db.session.commit()                    
            if not group:
                return Response(json.dumps({
                    'Error': 'Invalid Course'
                }), status=400)
            log = api.models.SCLogs({"log": '/v1/lab/portal 1086 ==>  '})
            db.session.add(log)
            db.session.commit()                    
            session_actve= api.models.UserSessions.query.filter_by(user_id=vend_user.id).all()
            if session_actve:
                log = api.models.SCLogs({"log": '/v1/lab/portal 1091 ==>  '})
                db.session.add(log)
                db.session.commit()                        
                for sess in session_actve:
                    if sess.status==1:
                        session = api.models.UserSessions.query.filter_by(id=sess.id).first()
                        session.status=0
                        db.session.commit()
            log = api.models.SCLogs({"log": '/v1/lab/portal Creating UserSessions' + str(access_token) + str(vend_user.id) + str(profile_user_id)})
            db.session.add(log)
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

            vend_lab = api.models.UserCourse.query.filter_by(user_name=vend_user.username).first()
            if vend_lab and vend_lab.status == 0:
                return Response(json.dumps({
                    'Error': "Lab access expired!"
                }), status=400)

            if vend_lab:
                headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
                key = os.environ.get('XE_PASSWORD_KEY')
                plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                password=plain_text.decode('utf-8')
                ccu = vend_lab.instance_name.split("_")[1]
                user_data = {
                    'username': user.username+"_"+ccu,
                    'password': password
                }
                              
                authToken = requests.post('https://scig-v2.securitycentric.net/labview/api/tokens', headers=headers, data=user_data,verify=False).json()
                log = api.models.SCLogs({"log": '/v1/lab/portal authToken' + json.dumps(authToken)})
                db.session.add(log)
                db.session.commit()
                if not "authToken" in authToken:
                    authToken = requests.post('https://scig-v2-lb2.securitycentric.net/labview/api/tokens', headers=headers, data=user_data,verify=False).json() 
                    if not "authToken" in authToken:                   
                        raiseException(authToken)

                lab_access_url = 'https://scig-v2.securitycentric.net/labview/#/client?token='+authToken["authToken"] 
                log = api.models.SCLogs({"log": '/v1/lab/portal lab_access_url' + str(lab_access_url)})
                db.session.add(log)
                db.session.commit()
               
                return redirect(lab_access_url)
        
        if group:
            instances =  api.models.GroupInstances.query.filter_by(group_id=group.id).all()            
            grp_inst=None            
            if instances:
                for instance in instances:
                    print(instance.name)                 
                    profile_user_id = instance.group_instances_user_id  
                    conn_name = instance.name                                      
                    reg_vm =api.models.UserCourse.query.filter_by(instance_name=instance.name).first()
                    print("registered VM",reg_vm)
                    if not reg_vm:
                        grp_inst=instance
                        print("group instance",grp_inst)
                        break
            else:
                print("No instance")
                return Response(json.dumps({
                        'Error': "EVM2: Failed to launch course, please contact admin! ( Error code: 1158 )"
                    }), status=400)

            if not grp_inst:
                print("Reached here")
                return Response(json.dumps({
                        'Error': "EVM2: Failed to launch course, please contact admin! ( Error code: 1164 )"
                    }), status=400)

            elif user and grp_inst:
                # key = os.environ.get('XE_PASSWORD_KEY')
                # plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                # password=plain_text.decode('utf-8')
                
                access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
                guac_user=os.environ.get('APP_GUAC_USER')
                guac_password=os.environ.get('APP_GUAC_PASSWORD')
                guac_host1=os.environ.get('APP_GUAC_HOST')
                guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                    
                    key = os.environ.get('XE_PASSWORD_KEY')
                    plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    password=plain_text.decode('utf-8')
                    log = api.models.SCLogs({"log": '/v1/lab/portal Entering into guacamole phase'})
                    db.session.add(log)
                    db.session.commit()
                    log = api.models.SCLogs({"log": "/v1/lab/portal INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"','USER');"})
                    db.session.add(log)
                    db.session.commit()                        
                    cursor.execute("INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"','USER');")
                    conn.commit() 
                    cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"';")
                    entity_id=cursor.fetchone()[0]   
                    cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(entity_id)+"','"+data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"]+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                    conn.commit()
                    log = api.models.SCLogs({"log": "/v1/lab/portal INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(entity_id)+"','"+data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"]+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());"})
                    db.session.add(log)
                    db.session.commit()                        
                    cursor.execute("SELECT entity_id FROM guacamole_user where username='"+data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"]+"';")
                    vend_id=cursor.fetchone()[0]
                    log = api.models.SCLogs({"log": '/v1/lab/portal  1241=> ' + str(vend_id)})
                    db.session.add(log)
                    db.session.commit()                       
                    cursor.execute("SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';")
                    connection_id=cursor.fetchone()[0]    
                    log = api.models.SCLogs({"log": '/v1/lab/portal  1246=> ' +  str(connection_id)})
                    db.session.add(log)
                    db.session.commit()                        
                    cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ');")
                    conn.commit()
                    log = api.models.SCLogs({"log": "/v1/lab/portal INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ');"})
                    db.session.add(log)
                    db.session.commit()                        
                    cursor.execute("SELECT entity_id FROM guacamole_connection_permission where entity_id='"+str(vend_id)+"';")
                    temp = cursor.fetchone()
                    log = api.models.SCLogs({"log": '/v1/lab/portal 1256==> ' + str(temp)})
                    db.session.add(log)
                    db.session.commit()                                            
                    if temp is None:
                        cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(vend_id)+","+str(connection_id)+", 'READ');")
                        conn.commit()
                    cursor.close()
                    conn.close()
                    log = api.models.SCLogs({"log": '/v1/lab/portal Exiting guacamole phase and creating vendor_users for' + str(data['user_name'])+"_"+str(data['uid'])+"_"+str(data["course_name"])+" | " + str(user.id)+" | " + str(grp_inst.name) +" | " + str(profile_user_id)})
                    db.session.add(log)
                    db.session.commit()  
                    now = datetime.datetime.utcnow()
                    now_plus_60 = now + datetime.timedelta(minutes = 60)                 
                    vendor_user=api.models.VendorUsers.query.filter_by(
                        username=data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"],
                        status=True,
                        lab=grp_inst.name,
                    ).first()
                    if vendor_user:    
                        return Response(json.dumps({'Error': "Lab for " + str(data["course_name"]) + " is active and will end on" + str(vendor_user.lab_end_session)}), status=400) 
                    course = api.models.Courses.query.filter_by(course_name=data["course_name"]).first()    
                    vendor_user=api.models.VendorUsers({
                        "username":data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"],
                        "vendor_id":user.id,
                        "status":True,
                        "lab":grp_inst.name,
                        "vendor_users_user_id":profile_user_id,
                        "lab_update_session":0,
                        "lab_end_session":now_plus_60,
                        "course_id":course.id,
                        "email":""
                    })
                    db.session.add(vendor_user)
                    db.session.commit()

                    headers = {
			'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }
                    user_data = {
                        'username': user.username+"_"+str(instance.ccu_landing),
                        'password': password
                    }
                    log = api.models.SCLogs({"log": '/v1/lab/portal Calling guacamole api tokens'})
                    db.session.add(log)
                    db.session.commit()
                     
                    authToken = requests.post(str(load_balancer) + 'api/tokens', headers=headers, data=user_data,verify=False).json()
                    if not "authToken" in authToken:
                        raiseException(authToken)
                    log = api.models.SCLogs({"log": '/v1/lab/portal Creating user course for ' + str(data['course_name']) + str(str(load_balancer) + '#/client?token=') + str(authToken["authToken"])})
                    db.session.add(log)
                    db.session.commit()                        
                    user_course = api.models.UserCourse({
                        'user_name': data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"],
                        'course_name': data['course_name'], 
                        'status': 1, 
                        'access_token':'adsdsdasfutaufasutdcusvd',
                        'instance_name':grp_inst.name,
                        'course_duration': 30,
                        'lab_access_url': str(load_balancer) + '#/client?token=' + authToken["authToken"],
                        'access_code_status':0,
                        'user_course_user_id':profile_user_id,
                        'connection_broker':connection_broker,
                        'email':''
                    })
                    db.session.add(user_course)
                    db.session.commit()
                    db.session.refresh(user_course)
                    log = api.models.SCLogs({"log": '/v1/lab/portal Fetching VendorUsers first() for' + str(data['user_name'])+"_"+str(data['uid'])+"_"+str(data["course_name"])})
                    db.session.add(log)
                    db.session.commit()                        

                    vend_user=api.models.VendorUsers.query.filter_by(username=data['user_name']+"_"+str(data['uid'])+"_"+data["course_name"], status=True).first()
                    log = api.models.SCLogs({"log": '/v1/lab/portal Creating UserSessions for' + str(access_token) +"_"+str(data['uid'])+"_"+str(data["course_name"])})
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
                    log = api.models.SCLogs({"log": '/v1/lab/portal Redirecting user to' + str(user_course.lab_access_url)})
                    db.session.add(log)
                    db.session.commit()                           
                    user_course.lab_access_url
                    return redirect(user_course.lab_access_url) 
                    
               
        else:
            return Response(json.dumps({
                            'Error': "Course not found"
                        }), status=400) 
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        print(e)
        log = api.models.SCLogs({"log": '/v1/lab/portal Exception: ' + str(e)})
        db.session.add(log)
        db.session.commit()   
        return raiseException(e)
    finally:
        db.session.close()    

@users_course_controller.route("/v1/lab/portal/user-lms", methods=['POST'])
def portal_user_lms(): 
   
    try:
        data = {}
        data['user_name'] = request.values["context_label"]
        if not data['user_name']:
            return Response(json.dumps({
                    'Error': "Invalid Username"
                }), status=400)
            
        data['course_name'] = request.values["context_id"]
            
        
        if not data['course_name']:
            return Response(json.dumps({
                    'Error': "Invalid Course"
                }), status=400)
        data['uid'] = request.values["lis_person_sourcedid"]
        if not data['uid']:
            return Response(json.dumps({
                    'Error': "Invalid uid"
                }), status=400)
        return redirect("https://sca-v2.securitycentric.net/user-lms?context_label="+str(data['user_name'])+"&context_id="+str(data['course_name'])+"&lis_person_sourcedid="+str(data['uid']))
        
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        print(e)
        return raiseException(e)
    finally:
        db.session.close()

@users_course_controller.route("/v1/lab/portal/edx", methods=['POST'])
def portal_user_lab_edx():   
   
    try:
        designated_host=''
        connection_broker=''
        data = {}
        profile_user_id = None 
        data['user_name'] = request.values["context_label"]
        if not data['user_name']:
            return Response(json.dumps({
                    'Error': "Invalid Username"
                }), status=400)
            
        data['course_name'] = request.values["context_id"]
            
        
        if not data['course_name']:
            return Response(json.dumps({
                    'Error': "Invalid Course"
                }), status=400)
        data['uid'] = request.values["lis_person_sourcedid"]
        if not data['uid']:
            return Response(json.dumps({
                    'Error': "Invalid uid"
                }), status=400)
            
        print('>>>??',data['course_name'])
        course_name = str(data['course_name']).replace(" ","_") 
        course_check_name = course_name.split('+')[0]
        course_check_series = course_name.split('+')[1]
        course_check_series_filter = course_check_series[:5] #40001/40002
        print(course_check_series_filter)  
        
        temp_course=''
        course_start_series = ''
        all_course = api.models.Courses.query.all()
        for a in all_course:
            if(a.course_series_start != '' and a.course_series_end != '' ):
                if int(a.course_series_start) <= int(course_check_series_filter) and int(a.course_series_end) >= int(course_check_series_filter):
                    temp_course = a.course_name
                    course_start_series = a.course_series_start
            
        print('temp course ==>',temp_course)
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
            
            user_cou = api.models.UserCourse.query.filter_by(user_name=data['user_name']+"_"+str(data["uid"])+"_"+temp_course).first()
            inst_name=''
            ins_name=''
            if user_cou:
                inst_name = user_cou.instance_name.split("_")[1]
                ins_name = user_cou.instance_name
            print(">>>>>>",data['user_name']+"_"+str(inst_name)+"_"+str(data["uid"])+"_"+temp_course)    
            vend_user = api.models.VendorUsers.query.filter_by(username=data['user_name']+"_"+str(inst_name)+"_"+str(data["uid"])+"_"+temp_course, status=True).first()
            instance = api.models.GroupInstances.query.filter_by(name=ins_name).first()
            if instance:
                odv = instance.odv
                odv_opt = instance.odv_options
                conn_name = instance.name
            group = api.models.VmGroups.query.filter_by(group_name=temp_course).first()
            
            access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
                  
            if vend_user and int(course_check_series) >= int(series_start) and int(course_check_series) <= int(series_end):
                profile_user_id = vend_user.vendor_users_user_id
                print("inside vendor user")
                if not group:
                    return Response(json.dumps({
                        'Error': 'Invalid Course'
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

                vend_lab = api.models.UserCourse.query.filter_by(instance_name=vend_user.lab).first()
                print("Vend lab",vend_lab)
                if vend_lab and vend_lab.status == 0:
                    return Response(json.dumps({
                        'Error': "Lab access expired!"
                    }), status=400)

                if vend_lab:
                    headers = {
			'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }
                    key = os.environ.get('XE_PASSWORD_KEY')
                    plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    password=plain_text.decode('utf-8')
                    ccu = vend_lab.instance_name.split("_")[1]
                    user_data = {
                        'username': user.username+"_"+ccu+"_"+str(data['uid']),
                        'password': password
                    }
                    load_balancer = ''     
                    lb=''               
                    guac_user=os.environ.get('APP_GUAC_USER')
                    guac_password=os.environ.get('APP_GUAC_PASSWORD')
                    guac_host1=os.environ.get('APP_GUAC_HOST')
                    guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                
                    if not "authToken" in authToken:
                        raiseException(authToken)
                    user_cou.access_token = authToken["authToken"]
                    user_cou.lab_access_url = 'http://localhost:3000/labview/#/client?token=' + authToken["authToken"]
                    db.session.commit()
                    db.session.refresh(user_cou) 
                    lab_access_url = str(load_balancer)+'#/client?token='+authToken["authToken"]      
                    time.sleep(10)          
                    return redirect("https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&static="+str(static)+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
                    # return Response(json.dumps({'link': "http://localhost:3000/connection-broker?&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])}), status=200)
            if group:
                print("First time register")
                odv=""
                odv_opt=""
                instances =  api.models.GroupInstances.query.filter_by(group_id=group.id).all()  
                check_connection_name = ''          
                grp_inst=None            
                if instances:
                    for instance in instances:
                        print(instance.name)                 
                        profile_user_id = instance.group_instances_user_id   
                        conn_name = instance.name 
                        odv = instance.odv     
                        odv_opt = instance.odv_options           
                        reg_vm =api.models.UserCourse.query.filter_by(instance_name=instance.name).first()
                        print("registered VM",reg_vm)
                        if not reg_vm:
                            grp_inst=instance
                            print("group instance",grp_inst)
                            break
                else:
                    log = api.models.SCLogs({"log": 'line======>1308'})
                    db.session.add(log)
                    db.session.commit()
                    return Response(json.dumps({
                            'Error': "EVM2: Failed to launch course, please contact admin! ( Error code: 1602 )"
                        }), status=400)

                
                if not grp_inst:
                    log = api.models.SCLogs({"log": 'line======>1315'})
                    db.session.add(log)
                    db.session.commit()
                    return Response(json.dumps({
                            'Error': "EVM2: Failed to launch course, please contact admin! ( Error code: 1611 )"
                        }), status=400)

               
                elif user and grp_inst:
                  
                    # key = os.environ.get('XE_PASSWORD_KEY')
                    # plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    # password=plain_text.decode('utf-8')
                    load_balancer = ''
                    access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
                    guac_user=os.environ.get('APP_GUAC_USER')
                    guac_password=os.environ.get('APP_GUAC_PASSWORD')
                    guac_host1=os.environ.get('APP_GUAC_HOST')
                    guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                        
                        key = os.environ.get('XE_PASSWORD_KEY')
                        plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                        password=plain_text.decode('utf-8')
                        
                        cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';") 
                        check_for_user = cursor.fetchone()
                        if check_for_user is None:
                            cursor.execute("INSERT INTO guacamole_entity (name,type) VALUES ('"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"','USER');")
                            conn.commit()  
                            cursor.execute("SELECT entity_id FROM guacamole_entity where name='"+user.username+"_"+str(instance.ccu_landing)+"_"+data['uid']+"';")
                            entity_id=cursor.fetchone()[0]   
                            cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(entity_id)+"','"+data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                            conn.commit()                 
                            cursor.execute("SELECT user_id FROM guacamole_user where username='"+data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course+"';")
                            user_id=cursor.fetchone()[0] 
                            print('user_id',user_id)                                                       
                            cursor.execute("SELECT entity_id FROM guacamole_user where username='"+user.username+"';")
                            vend_id=cursor.fetchone()[0]                           
                            print('vendor_id',vend_id)
                            cursor.execute("SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';")
                            connection_id=cursor.fetchone()[0] 
                            print('connection_id',connection_id)            
                            cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(entity_id)+","+str(connection_id)+", 'READ');")
                            conn.commit()
                            cursor.execute("SELECT entity_id FROM guacamole_connection_permission where entity_id='"+str(vend_id)+"';")
                            temp = cursor.fetchone()
                            print('temp',temp)                    
                            if temp is None:
                                
                                cursor.execute("INSERT INTO guacamole_connection_permission (entity_id,connection_id,permission) VALUES ("+str(vend_id)+","+str(connection_id)+", 'READ');")
                               
                                conn.commit()
                            cursor.close()
                            conn.close()  
                            now = datetime.datetime.utcnow()
                            print("Current UTC Time",now)
                            now_plus_60 = now + datetime.timedelta(minutes = 60)       
                            vendor_user=api.models.VendorUsers.query.filter_by(
                                username=data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course,
                                status=True,
                                lab=grp_inst.name,
                            ).first()
                            if  vendor_user:    
                                return Response(json.dumps({'Error': "Lab for " + str(data["course_name"]) + " is active and will end on" + vendor_user.lab_end_session}), status=400) 
                            course = api.models.Courses.query.filter_by(course_name=temp_course).first()    
                            vendor_user=api.models.VendorUsers({
                                "username":data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course,
                                "vendor_id":user.id,
                                "status":True,
                                "lab":grp_inst.name,
                                "lab_update_session":0,
                                "lab_end_session":now_plus_60,
                                "vendor_users_user_id":profile_user_id,
                                "course_id":course.id
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
                            
                            authToken = requests.post(str(load_balancer)+'api/tokens', headers=headers, data=user_data,verify=False).json()
                            if not "authToken" in authToken:
                                raiseException(authToken)
                            
                            user_course = api.models.UserCourse({
                                'user_name': data['user_name']+"_"+str(data['uid'])+"_"+temp_course,
                                'course_name': temp_course, 
                                'status': 1, 
                                'access_token':str(authToken["authToken"]),
                                'instance_name':grp_inst.name,
                                'course_duration': 30,
                                'lab_access_url': str(load_balancer)+'#/client?token=' + authToken["authToken"],
                                'access_code_status':0,
                                'connection_broker':connection_broker,
                                'user_course_user_id':profile_user_id
                                
                            })
                            db.session.add(user_course)
                            db.session.commit()
                            timeout = str(now_plus_60).replace(" ", "_")
                            db.session.refresh(user_course)
                            vend_user=db.session.query(api.models.VendorUsers).filter_by(username=data['user_name']+"_"+str(instance.ccu_landing)+"_"+str(data['uid'])+"_"+temp_course).filter_by(status=True).first()
                            session=api.models.UserSessions({
                                'access_token':access_token,
                                'user_id':vend_user.id,
                                'user_login':1,
                                'user_sessions_user_id':profile_user_id
                            })
                            session.expiry=1440
                            db.session.add(session)
                            db.session.commit()
                            
                            # return Response(json.dumps({'link':"http://localhost:3000/connection-broker?&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"])}), status=200)
                            return redirect("https://sca-v2.securitycentric.net/connection-broker?&user_id="+str(vend_user.id)+"&static="+str(static)+"&guide="+str(active)+"&odv="+str(odv)+"&odv_opt="+str(odv_opt)+"&lb="+str(lb)+"&course="+str(registered_course_check)+"&file="+str(course_check_series)+"&vendor="+str(data['user_name'])+"&token="+str(authToken["authToken"]))
                        else:
                            return Response(json.dumps({
                                'Error': "User Already Exist"
                            }), status=400)
                            
            else:
                return Response(json.dumps({
                                'Error': "Course not found"
                            }), status=400) 
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

@users_course_controller.route("/v1/lab/portal/generic-lab", methods=['POST'])
def portal_user_lab_generic():   
   
    try:
        link = ""
        course_name = ""
        ucid = -1
        # log = api.models.SCLogs({
        #     "log": 'Starting the controller'
        # })
        # db.session.add(log)
        # db.session.commit()
        designated_host=''
        connection_broker=''
        data = {}
        profile_user_id = None 
        data['access_code'] = request.values["access_code"] 
        data['portal'] = request.values['portal']  
        data['uid'] = str(request.values["first_name"])+"_"+str(request.values["last_name"])
        if not data['uid']:
            return Response(json.dumps({
                    'Error': "Invalid uid"
                }), status=400)        
        if not data['access_code']:
            return Response(json.dumps({
                    'Error': "Invalid Access Code"
                }), status=400)        
        code = api.models.AccessCodes.query.filter_by(access_code=data['access_code']).first()
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
                log = api.models.SCLogs({"log":'GroupInstance ' + str(instance)})
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
                    key = os.environ.get('XE_PASSWORD_KEY')
                    plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    password=plain_text.decode('utf-8')
                    ccu = vend_lab.instance_name.split("_")[1]
                    user_data = {
                        'username': user.username+"_"+ccu+"_"+str(data['uid']),
                        'password': password
                    }
                    load_balancer = ''     
                    lb=''               
                    guac_user=os.environ.get('APP_GUAC_USER')
                    guac_password=os.environ.get('APP_GUAC_PASSWORD')
                    guac_host1=os.environ.get('APP_GUAC_HOST')
                    guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                    return Response(json.dumps({'link': link, 'course_name':course_name, 'uid':ucid }), status=200)
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
                    key = os.environ.get('XE_PASSWORD_KEY')
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
                    guac_user=os.environ.get('APP_GUAC_USER')
                    guac_password=os.environ.get('APP_GUAC_PASSWORD')
                    guac_host1=os.environ.get('APP_GUAC_HOST')
                    guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                    return Response(json.dumps({'link': link, 'course_name':course_name, 'uid':ucid }), status=200)                                      
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
                code = api.models.AccessCodes.query.filter_by(access_code=data['access_code']).first()
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
                code = api.models.AccessCodes.query.filter_by(access_code=data['access_code']).first()
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
                    # key = os.environ.get('XE_PASSWORD_KEY')
                    # plain_text = crypto.decrypt(key, str.encode(user.password_digest))
                    # password=plain_text.decode('utf-8')
                    load_balancer = ''
                    access_token = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(64)])
                    guac_user=os.environ.get('APP_GUAC_USER')
                    guac_password=os.environ.get('APP_GUAC_PASSWORD')
                    guac_host1=os.environ.get('APP_GUAC_HOST')
                    guac_host2=os.environ.get('APP_GUAC_HOST2')
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
                        
                        key = os.environ.get('XE_PASSWORD_KEY')
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
                            print("BP1",user.username,vend_id)
                            cursor.execute("SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';")
                            connection_id=cursor.fetchone()[0]
                            log = api.models.SCLogs({"log": 'line======>1791'+ "SELECT connection_id FROM guacamole_connection_parameter WHERE parameter_name='hostname' AND parameter_value='"+grp_inst.ip_address+"';"})
                            db.session.add(log)
                            db.session.commit()   
                            print(connection_id)
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
                            return Response(json.dumps({'link': link, 'course_name':course_name, 'uid':ucid }), status=200)
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

@users_course_controller.route("/v1/registered/timeout", methods=['POST'])
def registered_user_timeout():
    try:
        data = json.loads(request.data)
        
        for key in ['token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user = api.models.UserCourse.query.filter_by(access_token=data['token']).first()
        log = api.models.SCLogs({
                        "log": str(user) + '   2141'
                        })
        db.session.add(log)
        db.session.commit()         
        id = user.id
        user_name = user.user_name
        inst_name = user.instance_name.split("_")[1]
        user_name = user_name.split("_")
        user_name.insert(1,inst_name)
        name=""
        for un in user_name:
            name += un+"_"
        name = name[:-1]   
        vend = api.models.VendorUsers.query.filter_by(username=name, status=True).first()
        
        if vend:
            log = api.models.SCLogs({
                        "log": str({"timeout":str(vend.lab_end_session),"extendsession":str(vend.lab_update_session),"username":str(name),"lab":str(vend.lab),"id":str(id)
                                        }) + '   2159'
                        })
            db.session.add(log)
            db.session.commit()    
            return Response(json.dumps({"timeout":str(vend.lab_end_session),"extendsession":str(vend.lab_update_session),"username":str(name),"lab":str(vend.lab),"id":str(id)
                                        }),status=200)
        else:
            return Response(json.dumps({
                                'Error': "Error no registered user"
                            }), status=400) 
    except Exception as e:
        log = api.models.SCLogs({
                        "log": str(e) + '   2171'
                        })
        db.session.add(log)
        db.session.commit()    
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_course_controller.route("/v1/registered/timeoutupdate", methods=['POST'])
def registered_user_timeout_update():
    try:
        data = json.loads(request.data)
       
        for key in ['oldtime','username']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        
        date_time_str = data['oldtime']
        date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        now_plus_30 = date_time_obj + datetime.timedelta(minutes = 30)
        
        
        vend = db.session.query(api.models.VendorUsers).filter_by(username=data['username']).filter_by(status=True).first()
        if vend:
            vend.lab_end_session = now_plus_30
            vend.lab_update_session += 1
            db.session.commit()
            db.session.refresh(vend)       
        vend = db.session.query(api.models.VendorUsers).filter_by(username=data['username']).filter_by(status=True).first()
        if vend:    
            return Response(json.dumps({"timeout":str(vend.lab_end_session),"extendsession":str(vend.lab_update_session),"username":str(data['username']),"lab":str(vend.lab)
                                        }),status=200)
        else:
            return Response(json.dumps({
                                'Error': "Error no registered user"
                            }), status=400) 
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)    
    finally:
        db.session.close()    
    
 

@users_course_controller.route("/v1/list/vendor_users", methods=['GET'])
def get_Vendor_users():
    try:
        users = api.models.VendorUsers.query.filter_by(status=True)
        result = []
        if users:
            for data in users:
                result.append({
                    'id':data.id,
                    'vendor_id': data.vendor_id,
                    'username':data.username
                })
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()           

@users_course_controller.route("/v1/multidelete/user_course", methods=['POST'])
def multidelete():
    try:
        data = json.loads(request.data)
        for key in ['ids']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        print("ids",data["ids"])
        for id in data['ids']:
            print("id-->",  id)
            user_course = api.models.UserCourse.query.filter_by(id=id).first()
            if(user_course):
                db.session.delete(user_course)
                db.session.commit()
                return Response(json.dumps({"Message":'users deleted successfully'}),status=200)
            else:
                return Response(json.dumps({"Error":'users deleted Failed'}),status=400)
        return Response(json.dumps({"Message":'users deleted successfully'}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e) 
    finally:
        db.session.close()    
