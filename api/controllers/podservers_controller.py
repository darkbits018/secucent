from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
from api.helpers import send_mail
import smtplib
import re
import os
from sshtunnel import SSHTunnelForwarder
import time
import mysql.connector
import pika
import paramiko

podservers_controller = Blueprint('podservers_controller', __name__)
CORS(podservers_controller)

@podservers_controller.route("/v1/provision/dynamic", methods=['POST'])
def register_pod():   
    try:
        data = json.loads(request.data)
        for key in ['ip_address','user_name','password','deviceName','deviceTTYS','user_id','count']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        

        for i in range(int(data['count'])):
            # device = api.models.PodServers.query.filter_by(name=data['deviceName']).all()    
            # if device:
            #     return Response(json.dumps({
            #             'Error': "POd server already exists !"
            #         }), status=400)
                    
            
            new_podserver = api.models.PodServers({
                'ip_address':data['ip_address'],
                'name':data['deviceName']+str(i+1),            
                'device_name':data['deviceTTYS']+str(i+1),   
                'user_name':data['user_name'],        
                'podserver_user_id':data['user_id'],
                
                
            })       
            
            db.session.add(new_podserver)
            db.session.commit()
            db.session.refresh(new_podserver)
            
            server = api.models.PodServers.query.filter_by(name=data['deviceName']).first()
            guac_user = os.environ.get('APP_GUAC_USER')
            guac_password = os.environ.get('APP_GUAC_PASSWORD')
            guac_host1 = os.environ.get('APP_GUAC_HOST')
            guac_host2 = os.environ.get('APP_GUAC_HOST2')
            connection_type='ssh'
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
                    
                    cursor = conn.cursor(buffered=True)
                    cursor.execute("SET @salt = UNHEX(SHA2(UUID(), 256));")
                    conn.commit()
                    password = data["password"]
                    cursor.execute("INSERT INTO guacamole_connection (connection_name, protocol,max_connections,max_connections_per_user) VALUES ( '" +
                                data['deviceName']+str(i+1)+"','"+connection_type+"',1,1);")
                    conn.commit()
                    cursor.execute(
                        'SELECT connection_id FROM guacamole_connection WHERE connection_name="'+data['deviceName']+str(i+1)+'";')
                    connection_id = cursor.fetchone()[0]
                    print(connection_id)
                    command = 'Screen /dev/'+data['deviceTTYS']+str(i+1)
                    print(command)
                    cursor.execute("INSERT INTO guacamole_connection_parameter VALUES ("+str(connection_id)+",'command','"+str(command)+"'),("+str(connection_id)+",'hostname','"+data['ip_address']+"'),("+str(connection_id)+",'password','"+data['password']+"'),("+str(connection_id)+",'port','22'),("+str(connection_id)+",'username','root');")
                    conn.commit()
                    cursor.execute(
                            "INSERT INTO guacamole_entity (name,type) VALUES ('"+data['deviceName']+str(i+1)+'-'+data['user_name']+"','USER');")
                    conn.commit()
                    cursor.execute(
                            "SELECT entity_id FROM guacamole_entity where name='"+data['deviceName']+str(i+1)+'-'+data['user_name']+"';")
                    entity_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(
                            entity_id)+"','"+data['deviceName']+str(i+1)+'-'+data['user_name']+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                    conn.commit()
                    conn.close()
                    user = api.models.Users({
                                'description':'PODS User',
                                'name': data['deviceName']+str(i+1)+'-'+data['user_name'],
                                'status': 1,
                                'user_type': 2,
                                'username': data['deviceName']+str(i+1)+'-'+data['user_name'],
                                'external_res': 0
                            })
                    user.set_password(data['password'])
                    db.session.add(user)
                    db.session.commit()
                    db.session.refresh(user)
                    
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                    ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
                    vmtransport = ssh.get_transport()
                    dest_addr = ('10.22.0.2', 22) #edited#
                    local_addr = (guac_host1, 22) #edited#
                    vmchannel = vmtransport.open_channel("direct-tcpip", dest_addr, local_addr)
                    #
                    jhost = paramiko.SSHClient()
                    jhost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    #jhost.load_host_keys('/home/osmanl/.ssh/known_hosts') #disabled#
                    jhost.connect('10.22.0.2', username='root', password='password', sock=vmchannel)
                    #
                    stdin, stdout, stderr = jhost.exec_command("show version | no-more") #edited#
                    #
                    print(stdout.read()) #edited#
                    #
                    jhost.close()
                    # chan = ssh.invoke_shell()
                    # chan.send('ssh root@10.22.0.2\n')
                    # # time.sleep(10)
                    # print("DONE")
                    # buff = ''
                    # while not buff.endswith('password: '):
                    #     resp = chan.recv(9999)
                    #     # buff+= resp
                    # chan.send('password\n')
                    # print("DONE")
                    # # time.sleep(10)
                    # buff = ''
                    # while not buff.endswith('some-prompt# '):
                    #     resp = chan.recv(9999)
                    #     # buff+= resp
                        
                    # chan.send('echo Screen /dev/ttyS2 > test3.sh')
                    # # time.sleep(10)
                    # buff = ''
                    # while not buff.endswith('some-prompt# '):
                    #     resp = chan.recv(9999)
                    #     # buff+= resp
                    
                    # stdin, stdout, stderr =ssh.exec_command("ssh root@10.22.0.2")
                    # stdin, stdout, stderr =ssh.exec_command("password")
                    # stdin, stdout, stderr =ssh.exec_command("echo Screen /dev/ttyS2 > test.sh")
                    # result = stdout.readline()
                    
                    ssh.close()
                    
           
        return Response(json.dumps({'Message': "Server registration successful"}), status=200)
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@podservers_controller.route("/v1/list/podservers", methods=['GET'])
def get_podservers():
    try:
        servers = api.models.PodServers.query.all()
        result=[]
        if servers:
            for data in servers:
                result.append({
                    'created_at':str(data.created_at),
                    'name': data.name,
                    'user_name':data.user_name,
                    'ip_address':data.ip_address,
                    'device_ttys':data.device_name,
                    
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()


@podservers_controller.route("/v1/update/podservers", methods=['POST'])
def update_podservers():
    try:
        data = json.loads(request.data)
        print(data['name'])
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        server = api.models.PodServers.query.filter_by(name=data['name']).first()
        if server:            
            if 'deviceName' in data.keys():
                server.device_name=data['deviceName']
            if 'ip_address' in data.keys():
                server.ip_address=data['ip_address']
            db.session.commit()
            db.session.refresh(server)
            server = api.models.PodServers.query.filter_by(name=data['name']).first()
            if server:
                guac_user = os.environ.get('APP_GUAC_USER')
                guac_password = os.environ.get('APP_GUAC_PASSWORD')
                guac_host1 = os.environ.get('APP_GUAC_HOST')
                guac_host2 = os.environ.get('APP_GUAC_HOST2')
                connection_type='ssh'
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
                        
                    cursor = conn.cursor(buffered=True)
                    print(cursor)
                    cursor.execute(
                            "SELECT connection_id FROM guacamole_connection where connection_name=PODS1;")
                    connection_id = cursor.fetchone()[0]
                    print(connection_id)
                return Response(json.dumps({
                    'Message': "Successfully updated"
                }), status=200)
        else: 
            return Response(json.dumps({"Error":'Server not found'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@podservers_controller.route("/v1/delete/pod_server", methods=['POST'])
def delete_poderver():
    print("deleted")
    try:
        data = json.loads(request.data)
        for key in ['deviceName']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        server = api.models.PodServers.query.filter_by(name=data['deviceName']).first()
        if server:
            db.session.delete(server)
            db.session.commit()
            server = api.models.Servers.query.filter_by(name=data['deviceName']).first()
            if server:
                return Response(json.dumps({"Error":'Server deletion failed'}),status=400)
            else:
                users = api.models.Users.query.all()
                user_id = ''
                for u in users:                    
                    if str(u.name).split('-')[0] == data['deviceName']:
                        user_id=u.id
                        
                    
                user = api.models.Users.query.filter_by(id=user_id).first()
                db.session.delete(user)
                db.session.commit()
                guac_user = os.environ.get('APP_GUAC_USER')
                guac_password = os.environ.get('APP_GUAC_PASSWORD')
                guac_host1 = os.environ.get('APP_GUAC_HOST')
                guac_host2 = os.environ.get('APP_GUAC_HOST2')
                connection_type='ssh'
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
                        
                    cursor = conn.cursor(buffered=True)
                    print(cursor)
                    print(data['deviceName'])
                    # cursor.execute(
                    # "DELETE FROM guacamole_connection where connection_name="+str(data['deviceName'])+";")
                    # conn.commit()
                    name = data['deviceName']+'-root'
                    print(name)
                    cursor.execute(
                            "SELECT entity_id FROM guacamole_entity where name="+str(name)+";")
                    entity_id = cursor.fetchone()[0]
                    print(entity_id)
                    cursor.execute(
                    "DELETE FROM guacamole_entity where entity_id="+str(entity_id)+";")
                    conn.commit()
                return Response(json.dumps({"Message":'Server deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'Server not found'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    