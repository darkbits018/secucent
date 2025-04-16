
from flask import Blueprint, request, Response, redirect, render_template
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
import random
import string
import mysql.connector
from sshtunnel import SSHTunnelForwarder
import os
import pika
import time
import base64
from flask_csv import send_csv
import datetime

users_controller = Blueprint('users_controller', __name__)
CORS(users_controller)


def enqueue_credentials(data):
    #    try:
    # log = api.models.SCLogs({
    #     "log": 'basic_publish vendor ' + str(data['operation'])})
    # db.session.add(log)
    # db.session.commit()     
    print("inside Enque")
    user = os.environ.get('APP_RABBITMQ_USER')
    password = os.environ.get('APP_RABBITMQ_PASSWORD')
    host = os.environ.get('APP_RABBITMQ_HOST')
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

@users_controller.route("/v1/reset/user_session", methods=['PATCH'])         
def reset_user_session():
    # f = None
    try:             
        # f= open("reset_user_session.log","a")
        # f.write(str("Beginning with expired_user_courses ") + str(datetime.datetime.utcnow()))
        # f.write(str(os.popen("uptime").read()))
        sessions=api.models.UserSessions.query.filter_by(status=1).all()
        for session in sessions:
            date=str(session.created_at)
            timestamp = time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").timetuple())
            t2 = time.time()
            if timestamp+session.expiry*60<t2:
                session.status=0
                db.session.commit()
        # f.write(str(os.popen("uptime").read()))  
        # f.write(str("Ended with reset_user_session ") + str(datetime.datetime.utcnow()))  
        # f.close()
        return 'OK'        
    except Exception as e:
            log = api.models.SCLogs({
                        "log": ' job1  ' + str(e)
                        })
            db.session.add(log)
            db.session.commit()    
            if e.__class__.__name__ == "IntegrityError":
                db.session.rollback()         
    finally:
        db.session.close() 
        # f.write(str("Ended with reset_user_session ") + str(datetime.datetime.utcnow()))
        # f.close()
        return 'OK'

@users_controller.route("/v1/register", methods=['POST'])
def register():
    try:
        data = json.loads(request.data)
        for key in ['app_secret', 'app_type', 'device_uid']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        if data['app_secret'] != '5ba8b5b241c91842f0e66782':
            return Response({'error': 'Invalid App Secret!'}, status=400)
        dev = api.models.Devices.query.filter_by(
            device_uid=data['device_uid']).first()
        if dev:
            return Response(json.dumps({'api_key': dev.api_key}), status=200)

        device = api.models.Devices({
            'app_type': data['app_type'],
            'device_uid': data['device_uid']
        })
        db.session.add(device)
        db.session.commit()
        db.session.refresh(device)
        device = api.models.Devices.query.filter_by(
            device_uid=data['device_uid']).first()
        if device:
            return Response(json.dumps({'api_key': device.api_key}), status=200)
        else:
            return Response(json.dumps({'error': 'Device registration failed!'}), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/register/user", methods=['POST'])
def register_users():
    user_lb1 = ''
    user_lb2 = ''
    try:
        data = json.loads(request.data)
        for key in ['description', 'status', 'user_type', 'name', 'password', 'username', 'external_res', 'serverSIP', 'serverEIP', 'sSubnet', 'vmStartIP', 'vmEndIP', 'vmSubnet']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        user = api.models.Users.query.filter_by(name=data['name']).first()

        if not user:
            guac_user = os.environ.get('APP_GUAC_USER')
            guac_password = os.environ.get('APP_GUAC_PASSWORD')
            guac_host1 = os.environ.get('APP_GUAC_HOST')
            guac_host2 = os.environ.get('APP_GUAC_HOST2')

            pwd = os.environ.get('XE_PASSWORD_KEY')
            with SSHTunnelForwarder(
                (guac_host1, 22),
                ssh_username=guac_user,
                ssh_password=guac_password,
                remote_bind_address=("127.0.0.1", 3306),
                # local_bind_address=("127.0.0.1", 3306)
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

                cursor.execute(
                    "SELECT COUNT(1) FROM guacamole_entity where name='"+data['username']+"';")
                check = cursor.fetchone()[0]

                if check == 0:
                    cursor.execute(
                        "INSERT INTO guacamole_entity (name,type) VALUES ('"+data['username']+"','USER');")
                    conn.commit()
                    cursor.execute(
                        "SELECT entity_id FROM guacamole_entity where name='"+data['username']+"';")
                    entity_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(
                        entity_id)+"','"+data['username']+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                    conn.commit()

                    cursor.close()
                    conn.close()

                else:
                    cursor.close()
                    conn.close()
                    return Response(json.dumps({
                        'Error': "User name already existing"
                    }), status=400)

            with SSHTunnelForwarder(
                (guac_host2, 22),
                ssh_username=guac_user,
                ssh_password=guac_password,
                remote_bind_address=("127.0.0.1", 3306),
                # local_bind_address=("127.0.0.1", 3306)
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

                cursor.execute(
                    "SELECT COUNT(1) FROM guacamole_entity where name='"+data['username']+"';")
                check = cursor.fetchone()[0]

                if check == 0:
                    cursor.execute(
                        "INSERT INTO guacamole_entity (name,type) VALUES ('"+data['username']+"','USER');")
                    conn.commit()
                    cursor.execute(
                        "SELECT entity_id FROM guacamole_entity where name='"+data['username']+"';")
                    entity_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO guacamole_user (entity_id,username,password_salt,password_hash,password_date) VALUES ('"+str(
                        entity_id)+"','"+data['username']+"',@salt, UNHEX(SHA2(CONCAT('"+password+"', HEX(@salt)), 256)),NOW());")
                    conn.commit()

                    if data['external_res'] == 1:
                        user = api.models.Users({
                            'description': data['description'],
                            'name': data['name'],
                            'status': int(data['status']),
                            'user_type': int(data['user_type']),
                            'username': data['username'],
                            'external_res': data['external_res']
                        })
                        user.set_password(data['password'])
                        db.session.add(user)
                        db.session.commit()
                        db.session.refresh(user)
                        external_config = api.models.ExternalConfiguration({
                            'serverSIP': data['serverSIP'],
                            'serverEIP': data['serverEIP'],
                            'sSubnet': data['sSubnet'],
                            'vmStartIP': data['vmStartIP'],
                            'vmEndIP': data['vmEndIP'],
                            'vmSubnet': data['vmSubnet'],
                            'user_name': data['username']
                        })
                        db.session.add(external_config)
                        db.session.commit()
                        db.session.refresh(external_config)

                    else:
                        user = api.models.Users({
                            'description': data['description'],
                            'name': data['name'],
                            'status': int(data['status']),
                            'user_type': int(data['user_type']),
                            'username': data['username'],
                            'external_res': 0
                        })
                        user.set_password(data['password'])
                        db.session.add(user)
                        db.session.commit()
                        db.session.refresh(user)
                    cursor.close()
                    conn.close()
                    enqueue_credentials({
                        'key': 'vendor', 'operation': 'create', 'directory_name': data['username'], 'vm_name': '1.Guacamole_1.2.0-Development', 'user': 'cara', 'host1': str(guac_host1), 'host2': str(guac_host2), 'password_xe': pwd})

                    user = api.models.Users.query.filter_by(
                        name=data['name']).first()
                    if user:
                        return Response(json.dumps({
                            'Message': "user registration successful"
                        }), status=200)
                    else:
                        return Response(json.dumps({
                            'Error': "user creation failed"
                        }), status=400)

                else:
                    cursor.close()
                    conn.close()
                    return Response(json.dumps({
                        'Error': "User name already existing"
                    }), status=400)

        else:
            return Response(json.dumps({
                'Error': "user already existing"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/list/users", methods=['GET'])
def get_users():
    try:
        users = api.models.Users.query.all()
        profile_groups = api.models.ProfileGroups.query.with_entities(api.models.ProfileGroups.vendor_id).all()
        vendor_ids = [profile_group[0] for profile_group in profile_groups]
        # 2 means all, 0 means profile group not created, 1 means profile group created
        profile_group_created = 2
            # Get the 'page' query parameter and convert it to an integer
        try:
            profile_group_created = int(request.args.get('profile_group_created', 2))  # Default to 2 if not provided
        except ValueError:
            return Response("Invalid number for 'profile_group_created'", 400)  # Handle non-numeric input
        result = []
        if users:
            for data in users:
                if profile_group_created == 0:
                    if data.id in vendor_ids:
                        continue
                if profile_group_created == 1:
                    if data.id not in vendor_ids:
                        continue    
                result.append({
                    'id':data.id,
                    'created_at': str(data.created_at),
                    'name': data.name,
                    'status': data.status,
                    'description': data.description,
                    'user_type': data.user_type,
                    'user_id': data.users_user_id
                })
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/delete/user_session", methods=['POST'])
def delete_user_session():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        user = api.models.UserSessions.query.filter_by(id=data['id']).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            user = api.models.UserSessions.query.filter_by(id=data['id']).first()
            if user:
                return Response(json.dumps({"Error":'User session deletion failed'}),status=400)
            else:
                return Response(json.dumps({"Message":'User session deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'User not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@users_controller.route("/v1/active/sessions", methods=['GET'])
def active_sessions():
    try:
        sessions = api.models.UserSessions.query.filter_by(status=1).all()
        data = []
        servers = api.models.Servers.query.all()
        if sessions:
            for session in sessions:
                server_name = ""
                vendor_name = ""
                lab = ""
                ccu = ""
                course_name = ""
                user_name = ""
                user = api.models.VendorUsers.query.filter_by(
                    id=session.user_id, status=True).first()
                if user:
                    lab = user.lab
                    user_name = user.username
                    user_id = user.vendor_users_user_id
                    vendor = api.models.Users.query.filter_by(
                        id=user.vendor_id).first()
                    if vendor:
                        vendor_name = vendor.name
                    instance = api.models.GroupInstances.query.filter_by(
                        name=user.lab).first()
                    if instance:
                        ccu = instance.ccu_landing
                    reg_vm = api.models.UserCourse.query.filter_by(
                        user_name=user.username).first()
                    ccu_landing_off = ccu.split("-")[1]
                    if reg_vm:
                        course_name = reg_vm.course_name
                    for server in servers:
                        ccu_start = str(server.ccu_start).split("-")[1]
                        ccu_end = str(server.ccu_end).split("-")[0]
                        if int(ccu_start) == int(ccu_landing_off):
                            server_name = server.name
                            break
                    data.append({"vendor_name": vendor_name, "course_name": course_name,
                                 "lab": lab, "user_name": user_name, "ccu": ccu, "server_name": server_name, "user_id": user_id})

        return Response(json.dumps({
            "data": data
        }), status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/update/user", methods=['POST'])
def update_user():
    try:
        data = json.loads(request.data)
        pwd = os.environ.get('XE_PASSWORD_KEY')
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user = api.models.Users.query.filter_by(name=data['name']).first()
        old = user.name
        if user:
            if 'password' in data.keys():
                user.set_password(data['password'])
            if 'username' in data.keys():
                user.username = data['username']
            if 'description' in data.keys():
                user.description = data['description']
            if 'user_type' in data.keys():
                user.user_type = data['user_type']
            if 'status' in data.keys():
                user.status = data['status']
            db.session.commit()
            db.session.refresh(user)

            return Response(json.dumps({
                'Message': "Successfully updated"
            }), status=200)
        else:
            return Response(json.dumps({"Error": 'User not found'}), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/launch/lab", methods=['POST'])
def login():
    try:
        data = json.loads(request.data)
        for key in ['username', 'password', "lab"]:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        current_user = api.models.Users.query.filter_by(
            username=data['username']).first()
        vend_user = api.models.VendorUsers.query.filter_by(
            username=data['username']+"_"+str(data['lab']), status=True).first()
        if not current_user:
            return Response(json.dumps({
                'Error': "Invalid User!"
            }), status=401)
        else:
            if not current_user.check_password(data['password']):
                return Response(json.dumps({
                    'Error': "Password didn't match!"
                }), status=401)
            else:
                access_token = ''.join(
                    [random.choice(string.ascii_letters + string.digits) for n in range(64)])
                session_actve = api.models.UserSessions.query.filter_by(
                    user_id=vend_user.id).all()
                if session_actve:
                    for sess in session_actve:
                        if sess.status == 1:
                            session = api.models.UserSessions.query.filter_by(
                                id=sess.id).first()
                            session.status = 0
                            db.session.commit()

                session = api.models.UserSessions({
                    'access_token': access_token,
                    'user_id': vend_user.id
                })
                session.expiry = 1440
                db.session.add(session)
                db.session.commit()
                lab = api.models.UserCourse.query.filter_by(
                    user_name=vend_user.username).first()
                if lab.status == 0:
                    return Response(json.dumps({
                        'Error': "Lab expired"
                    }), status=400)
                return redirect(lab.lab_access_url)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/delete/user", methods=['POST'])
def delete_user():
    try:
        data = json.loads(request.data)
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        user = api.models.Users.query.filter_by(name=data['name']).first()
        print(user)
        external = api.models.ExternalConfiguration.query.filter_by(
            user_name=data['name']).first()

        lab_users = api.models.VendorUsers.query.filter_by(
            vendor_id=user.id).all()
        if lab_users:
            return Response(json.dumps({"Error": 'Please delete registered labs.'}), status=400)
        if user:
            guac_user = os.environ.get('APP_GUAC_USER')
            guac_password = os.environ.get('APP_GUAC_PASSWORD')
            guac_host1 = os.environ.get('APP_GUAC_HOST')
            guac_host2 = os.environ.get('APP_GUAC_HOST2')
            pwd = os.environ.get('XE_PASSWORD_KEY')
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
                cursor.execute(
                    "SELECT entity_id from guacamole_user where username='"+user.username+"';")
                vendor_id = cursor.fetchone()[0]
                print(vendor_id)
                cursor.execute(
                    "DELETE FROM guacamole_entity where entity_id="+str(vendor_id)+";")
                conn.commit()
                cursor.close()
                conn.close()

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
                cursor = conn.cursor(buffered=True)
                cursor.execute(
                    "SELECT entity_id from guacamole_user where username='"+user.username+"';")
                vendor_id = cursor.fetchone()[0]
                print(vendor_id)
                cursor.execute(
                    "DELETE FROM guacamole_entity where entity_id="+str(vendor_id)+";")
                conn.commit()
                db.session.delete(user)
                db.session.commit()
                if external:
                    db.session.delete(external)
                    db.session.commit()
                cursor.close()
                conn.close()
                enqueue_credentials({
                    'key': 'vendor', 'operation': 'delete', 'directory_name': user.username, 'vm_name': '1.Guacamole_1.2.0-Development', 'user': 'cara', 'host1': str(guac_host1), 'host2': str(guac_host2), 'password_xe': pwd})
                user = api.models.Users.query.filter_by(
                    name=data['name']).first()
                if user:
                    return Response(json.dumps({"Error": 'user deletion failed'}), status=400)

                else:
                    return Response(json.dumps({"Message": 'user deleted successfully'}), status=200)

        else:
            return Response(json.dumps({"Error": 'User not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/list/license", methods=['GET'])
def list_license():
    try:
        codes = api.models.LicenseKeys.query.all()
        result = []
        if codes:
            

            for data in codes:
                # encrypting key
                code_bytes=data.key.encode('ascii')
                base64_bytes=base64.b64decode(code_bytes)
                base64_key = base64_bytes.decode('ascii')

                # encrypting limit
                code_bytes=data.limit.encode('ascii')
                base64_limit_bytes=base64.b64decode(code_bytes)
                base64_limit = base64_limit_bytes.decode('ascii')

                result.append({
                        'id':data.id,
                        'client_name': str(data.client_name),
                        'key': base64_key,
                        'limit':int(base64_limit),
                        'active_users': data.active_users,
                        
                                             
                    })
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/add/license_key", methods=['POST'])
def  addLicenceKey():
    try:
        data = json.loads(request.data)
        key=data['key']
        key_bytes=key.encode('ascii')
        base64_bytes = base64.b64encode(key_bytes)
        base64_key = base64_bytes.decode('ascii')

        limit=data['limit']
        limit_bytes=limit.encode('ascii')
        base64_limits = base64.b64encode(limit_bytes)
        base64_limit = base64_limits.decode('ascii')

        print("dddddddddddddddddddddd")
        print("base64_limit",base64_limit)
     
        new_licence_key = api.models.LicenseKeys({
                'client_name': data['client_name'],
                'key': base64_key,
                'limit': base64_limit,
                'active_users':0

        })
        db.session.add(new_licence_key)
        db.session.commit()
        db.session.refresh(new_licence_key)

        all_codes = api.models.LicenseKeys.query.filter_by(
            key=str(base64_key)).first()
        if all_codes:
            return Response(json.dumps({
                'Message': "License Key creation successful"
            }), status=200)
        else:
            return Response(json.dumps({
                'Error': "License Key creation failed"
            }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@users_controller.route("/v1/delete/license_key", methods=['POST'])
def delete_licencekey():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        code = api.models.LicenseKeys.query.filter_by(
            id=data['id']).first()
        if code:
            db.session.delete(code)
            db.session.commit()
            code = api.models.LicenseKeys.query.filter_by(
                id=data['id']).first()
            if code:
                return Response(json.dumps({"Error": 'Licence Key deletion failed'}), status=400)
            else:
                return Response(json.dumps({"Message": 'Licence Key deleted successfully'}), status=200)

        else:
            return Response(json.dumps({"Error": 'Id not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@users_controller.route("/v1/update/license_key", methods=['POST'])
def update_licencekey():
    try:
        data = json.loads(request.data)
        lkeys = api.models.LicenseKeys.query.filter_by(id=int(data['id'])).first()    
        limit=str(data['limit'])
        limit_bytes=limit.encode('ascii')
        base64_limits = base64.b64encode(limit_bytes)
        base64_limit = base64_limits.decode('ascii')    
        if lkeys: 
            print(data['limit'])
            lkeys.client_name = data['client_name']
            lkeys.limit=base64_limit
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

@users_controller.route("/v1/get/icense_key_report", methods=['POST'])
def get_license_report():
    try:
        data = json.loads(request.data)
        print(data['report_type'])
        report_data = []

        if data['report_type'] == 'license_key':
            access_codes =  api.models.LicenseKeys.query.all()

            if access_codes:
                for ac in access_codes:
                    code_bytes=ac.key.encode('ascii')
                    base64_bytes=base64.b64decode(code_bytes)
                    base64_key = base64_bytes.decode('ascii')

                    limit=ac.limit.encode('ascii')
                    base64_limit_bytes=base64.b64decode(limit)
                    base64_limit = base64_limit_bytes.decode('ascii')
                    d = {
                        "Client name": ac.client_name,
                        "key": base64_key,
                        "Limit": base64_limit,
                        "Active Users":ac.active_users

                    }
                    report_data.append(d)
        name="licensekeys"
        file_name = name+".csv"
        print(file_name)
        if report_data != []:
            return send_csv(report_data, "test.csv", report_data[0].keys())
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