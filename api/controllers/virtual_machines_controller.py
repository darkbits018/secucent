
from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
import ipaddress
import mysql.connector
from sshtunnel import SSHTunnelForwarder
import os
import pika
from flask_csv import send_csv
from datetime import datetime
import time
import paramiko
from cryptography.fernet import Fernet
from netaddr import *
import ssl
import re


virtual_machines_controller = Blueprint(
    'virtual_machines_controller', __name__)
CORS(virtual_machines_controller)

def enqueue_credentials(data):
    #    try:
    log = api.models.SCLogs({
        "log": 'basic_publish /v1/create/vm'})
    db.session.add(log)
    db.session.commit()     
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

def teardown_enqueue_credentials(data):
    #    try:
    user = os.environ.get('APP_RABBITMQ_USER')
    password = os.environ.get('APP_RABBITMQ_PASSWORD')
    host = os.environ.get('APP_RABBITMQ_HOST')
    # host = '172.20.4.48'
    
    log = api.models.SCLogs({
    "log": "basic_publish Starting teardown_enqueue for " + data["vm_name"]})
    db.session.add(log)
    db.session.commit()  
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(credentials=credentials, host=host))
    try:
        channel = connection.channel()
        channel.queue_declare(queue='scia_queue')
        channel.basic_publish(
            exchange='', routing_key='scia_queue', body=str(data))
        connection.close()
        log = api.models.SCLogs({
        "log": "Connection closed for teardown_enqueue"})
        db.session.add(log)
        db.session.commit()  
        print("Connection closed for teardown_enqueue")
    except Exception as e:
        connection.close()
        log = api.models.SCLogs({
        "log": "Error while teardown_enqueue: "+ str(e)})
        db.session.add(log)
        db.session.commit()  
        print(e)

def reset_enqueue_credentials(data):
    #    try:
    user = os.environ.get('APP_RABBITMQ_USER')
    password = os.environ.get('APP_RABBITMQ_PASSWORD')
    host = os.environ.get('APP_RABBITMQ_HOST')
    # host = '172.20.4.49'
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(credentials=credentials, host=host))
    try:
        log = api.models.SCLogs({
        "log": "basic_publish reset_enqueue_credentials " + data["key"]})
        db.session.add(log)
        db.session.commit()        
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


def run_command_ssh(client, command):
    stdin, stdout, stderr = client.exec_command(command[0])
    result = stdout.readline()   
    print(result)
    print("Error......................", stderr.read())
    if stderr.readline():
        return (0, stderr.read())
    return (1, result.strip())

def run_command_ssh2(client, command,per_type):
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

@virtual_machines_controller.route("/v1/server_memory_performance", methods=['POST'])
def server_memory_performance():
    try:
        data = json.loads(request.data)
        for key in ['landing_vm']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        key = os.environ.get('XE_PASSWORD_KEY').encode('ascii')
        cipher_suite = Fernet(key)
        password = cipher_suite.decrypt(
                    bytes('gAAAAABfs2FvxtBtBKOTi6Vy_hTmBVhQfkYTflXG_46dDzTYw8Wq__8JTMuGDbXeOtqX0F0TlZUkYJhCWU_BWfMXSJyM3p61NA==', 'raw_unicode_escape')).decode("utf-8")
        client = ssh_remotely('root',password,'172.20.4.104')           
        command = ["xe host-list"]   
        status = run_command_ssh(client, command)        
        val = str(status[1]).split(':')[1]        
        val=val.replace(' ','')     
        command2 = ["xe host-list uuid="+val+ " params=memory-free"]
        status2 = run_command_ssh(client, command2)        
        val2 = str(status2[1]).split(':')[1]  
        val2 = val2.replace(' ','')
        print("Total Free Memory in a Server:",val2)
        command3 = ["xe vm-compute-maximum-memory vm="+data['landing_vm'] +" total="+val2]
        status3 = run_command_ssh(client, command3) 
        val3 = status3[1]
        print("free memory that can be allocated to the VM",val3) 
        data={'server_free':val2,'vm_free':val3}
        return Response(json.dumps({'data': data}), status=200)       
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@virtual_machines_controller.route("/v1/create/vm", methods=['POST'])
def create():
    try:
        data = json.loads(request.data)
        for key in ['name', 'username', 'password', 'vm_clone_name', 'helpers']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        machines = api.models.VirtualMachines.query.filter_by(
            name=data["name"]).first()
        if machines:
            return Response(json.dumps({
                'error': 'Ip already existing!'
            }), status=400)
        else:

            machines = api.models.VirtualMachines.query.all()
            ip_address = ''
            ccu_number = 1001
            print(machines)
            if machines:
                ips = []
                ccus = []
                for machine in machines:
                    ips.append(int(ipaddress.ip_address(machine.ip_address)))
                    ccus.append(int(machine.ccu_number))
                ccu_number = max(ccus)+1
                ip_address = str(ipaddress.IPv4Address(max(ips)+1))
            else:
                ip_address = os.environ.get('APP_VM_START_IP')
            template = api.models.VmTemplates.query.filter_by(
                vm_clone_name=data['vm_clone_name']).first()
            lock = api.models.LockedIps({
                'ip_address': ip_address,
                'locked_template': int(template.id)
            })
            db.session.add(lock)
            db.session.commit()

            vm_name = str(ccu_number)+"_" + \
                data['name']+"_"+data['vm_clone_name']
            vm = api.models.VirtualMachines({
                'name': vm_name,
                'ip_address': ip_address,
                'ccu_number': ccu_number
            })
            db.session.add(vm)
            db.session.commit()
            db.session.refresh(vm)
            vms = api.models.VirtualMachines.query.filter_by(name=vm_name)
            if vms:
                machine = api.models.VirtualMachines.query.filter_by(
                    name=vm_name).first()
                if machine:
                    vm_user = api.models.VmCredentials({
                        'vm_id': machine.id,
                        'username': data['username'],
                    })
                    vm_user.set_password(data['password'])
                    db.session.add(vm_user)
                    db.session.commit()
                    db.session.refresh(vm_user)
                    vmuser = api.models.VmCredentials.query.filter_by(
                        username=data['username']).first()
                    helper = []
                    if data['helper'] != [] or data['helper'] != None:
                        helper = data['helper']
                        for h in helper:
                            hlp = api.models.HelperVms.query.filter_by(
                                name=h).first()
                            l_h = api.models.LandingHelper({
                                "helper_vm_id": hlp.id,
                                "landing_vm_id": vmuser.id
                            })
                            db.session.add(l_h)
                        db.session.commit()

                    if vmuser:
                        queue_data = {
                            "ip": machine.ip_address,
                            "gateway": "10.20.4.1",
                            "ccu": machine.ccu_number,
                            "name": machine.name,
                            "username": vmuser.username,
                            "password": data['password'],
                            "clone_name": data['vm_clone_name'],
                            "helpers": helper,
                            "key": "provision"
                        }
                        log = api.models.SCLogs({
                        "log": 'provision ' + str(queue_data)})
                        db.session.add(log)
                        db.session.commit()  
                        enqueue_credentials(queue_data)
                        return Response(json.dumps({
                            'message': 'Success!'
                        }), status=200)
                    else:
                        return Response(json.dumps({
                            'error': 'Account creation failed!'
                        }), status=400)
                else:
                    return Response(json.dumps({
                        'error': 'Account creation failed!'
                    }), status=400)
            else:
                return Response(json.dumps({'error': 'Virtual Machine Creation failed!'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    


@virtual_machines_controller.route("/v1/get/new_vms", methods=['POST'])
def get_new_vms():
    try:
        requestData = json.loads(request.data)
        vms = api.models.VirtualMachines.query.filter_by(
            status=1, virtual_machines_user_id=requestData['user_id']).all()
        data = []
        sessions = api.models.UserSessions.query.filter_by(
            status=1, user_sessions_user_id=requestData['user_id']).all()
        count_sessions = len(sessions)
        new_sessions = 0
        if sessions:
            for session in sessions:
                date = str(session.created_at)
                timestamp = time.mktime(datetime.strptime(
                    date, "%Y-%m-%d %H:%M:%S").timetuple())
                t2 = time.time()
                if t2-60*60*24 < timestamp:
                    new_sessions += 1

        active_count = len(vms)
        if vms:
            today = datetime.now().strftime("%Y-%m-%d")
            for vm in vms:
                formated_created_at = datetime.strptime(vm.created_at.strftime(
                    "%Y-%m-%d  %H:%M:%S"), '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d")
                if formated_created_at == today:
                    data.append({"name": vm.name, "ip_address": vm.ip_address,
                                 "status": vm.status, "created_at": str(vm.created_at)})

        return Response(json.dumps({"data": data, "count_sessions": count_sessions, "new_sessions": new_sessions, "count_vms": len(data), "active_vms": active_count}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    


@virtual_machines_controller.route("/v1/get/report", methods=['POST'])
def get_report():
    try:
        data = json.loads(request.data)
        if 'report_type' not in data.keys():
            return Response(json.dumps({
                'Error': "Missing parameter 'report_type'"
            }), status=402)
        report_data = []
        report_name = 'report.csv'
        now = datetime.utcnow()             
        current_time = now.strftime('%Y-%m-%d_%H_%M_%S')
        if data['report_type'] == 0:
            report_name = 'usersessions_' +str(current_time)+ '.csv'
            log = api.models.SCLogs({
            "log": 'report_name ' + str(report_name)})
            db.session.add(log)
            db.session.commit()  
            sessions = api.models.UserSessions.query.filter_by(status=1).all()
            if sessions:
                for session in sessions:
                    vendor = api.models.VendorUsers.query.filter_by(
                        id=session.user_id, status=True).first()
                    if vendor:
                        reg_vm = api.models.UserCourse.query.filter_by(
                            user_name=vendor.username).first()
                    d = {
                        "user_id": session.user_id,
                        "session_token": session.session_token,
                        "status": session.status,
                        "created_at": session.created_at
                    }
                    if vendor:
                        d["username"] = vendor.username.split("_")[0]
                        if reg_vm:
                            d["lab"] = reg_vm.instance_name
                    else:
                        d["username"] = "NIL"
                        d["lab"] = "NIL"
                    report_data.append(d)
        elif data['report_type'] == 1:
            report_name = 'serverutilization_' +str(current_time)+ '.csv'
            log = api.models.SCLogs({
            "log": 'report_name ' + str(report_name)})
            db.session.add(log)
            db.session.commit()  
            sessions = api.models.UserSessions.query.filter_by(status=0).all()
            if sessions:
                for session in sessions:
                    vendor = api.models.VendorUsers.query.filter_by(
                        id=session.user_id, status=True).first()
                    if vendor:
                        reg_vm = api.models.UserCourse.query.filter_by(
                            user_name=vendor.username).first()
                    d = {
                        "user_id": session.user_id,
                        "session_token": session.session_token,
                        "status": session.status,
                        "created_at": session.created_at
                    }
                    if vendor:
                        d["username"] = vendor.username.split("_")[0]
                        if reg_vm:
                            d["lab"] = reg_vm.instance_name
                    else:
                        d["username"] = "NIL"
                        d["lab"] = "NIL"
                    report_data.append(d)
        elif data['report_type'] == 2:
            report_name = 'vendors_' +str(current_time)+ '.csv'
            log = api.models.SCLogs({
            "log": 'report_name ' + str(report_name)})
            db.session.add(log)
            db.session.commit()  
            vendors = api.models.Users.query.filter_by(user_type=2).all()
            if vendors:
                for vendor in vendors:
                    report_data.append({
                        "name": vendor.name,
                        "description": vendor.description,
                        "status": vendor.status,
                        "username": vendor.username,
                        "created_at": vendor.created_at
                    })

        elif data['report_type'] == 3:
            report_name = 'machines_' +str(current_time)+ '.csv'
            log = api.models.SCLogs({
            "log": 'report_name ' + str(report_name)})
            db.session.add(log)
            db.session.commit()  
            machines = api.models.VirtualMachines.query.all()
            if machines:
                for machine in machines:
                    report_data.append({
                        "name": machine.name,
                        "ip_address": machine.ip_address,
                        "status": machine.status,
                        "created_at": machine.created_at
                    })

        log = api.models.SCLogs({
        "log": 'report_name ' + str(report_name)})
        db.session.add(log)
        db.session.commit()  
        if report_data != []:
            log = api.models.SCLogs({
            "log": 'report_name 439 => ' + str(report_name)})
            db.session.add(log)
            db.session.commit()  
            return send_csv(report_data, report_name, report_data[0].keys())
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


@virtual_machines_controller.route("/v1/get/charts", methods=['POST'])
def get_chart():
    try:
        vm_data = []
        vm = []
        vms = api.models.VirtualMachines.query.all()
        if vms:
            for v in vms:
                res = str(v.created_at).split(" ")[0]
                vm_data.append(res)

        my_dict = {i: vm_data.count(i) for i in vm_data}
        for key, val in my_dict.items():
            vm.append([key, val])
        vm_chart = {'label': 'Virtual Machines', 'data': vm}
        result = []
        result.append(vm_chart)

        sess_a_data = []
        sess_i_data = []
        sess_a = []
        sess_i = []
        active_sess = api.models.UserSessions.query.filter_by(status=1).all()
        inactive_sess = api.models.UserSessions.query.filter_by(status=0).all()
        if active_sess:
            for s in active_sess:
                res = str(s.created_at).split(" ")[0]
                sess_a_data.append(res)

        my_dict1 = {i: sess_a_data.count(i) for i in sess_a_data}
        for key, val in my_dict1.items():
            sess_a.append([key, val])

        sess_a = sess_a[-30:]
        if inactive_sess:
            for s in inactive_sess:
                res = str(s.created_at).split(" ")[0]
                sess_i_data.append(res)

        my_dict2 = {i: sess_i_data.count(i) for i in sess_i_data}

        for key, val in my_dict2.items():
            sess_i.append([key, val])

        vm_chart_active = {'label': 'Active Sessions', 'data': sess_a[-10:]}
        vm_chart_inactive = {'label': 'Expired Sessions', 'data': sess_i[-10:]}
        result1 = []
        result1.append(vm_chart_active)
        result1.append(vm_chart_inactive)

        ven_data = []
        ven = []
        vendors = api.models.Users.query.all()
        if vendors:
            for ve in vendors:
                res = str(ve.created_at).split(" ")[0]
                temp1 = res.split("-")[0]
                temp2 = res.split("-")[1]
                res = str(temp1)+'-'+str(temp2)
                ven_data.append(res)

        my_dict3 = {i: ven_data.count(i) for i in ven_data}
        for key, val in my_dict3.items():
            ven.append([key, val])
        ven_chart = {'label': 'Vendors', 'data': ven}
        result3 = []
        result3.append(ven_chart)

        ser_data = []
        ser = []
        servers = api.models.Servers.query.all()
        util_data = []
        result4 = []
        if servers:
            for se in servers:
                temp1 = str(se.ccu_start).split("-")[0]
                temp2 = str(se.ccu_end).split("-")[0]
                temp = int(temp2) - int(temp1)
                offset = str(se.ccu_end).split("-")[1]
                res = [str(se.name), temp]
                ser_data.append(res)

                util = api.models.VirtualMachines.query.all()
                if util:
                    count = 0
                    for u in util:
                        nw = str(u.nw_name).split("-")[1]
                        if nw == offset:
                            count = count + 1
                    res1 = [str(se.name), count]
                    util_data.append(res1)

        ser_chart = {'label': 'Total', 'data': ser_data}
        uit_chart = {'label': 'Utilized', 'data': util_data}
        result4.append(ser_chart)
        result4.append(uit_chart)

        print(result4)
        return Response(json.dumps({"vm": result, "sess": result1, "ven": result3, "ser": result4}), status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    


@virtual_machines_controller.route("/v1/list/vms", methods=['GET'])
def get_vms():
    try:
        vms = api.models.VirtualMachines.query.all()
        servers = api.models.Servers.query.all()
        data = []
        course_name=''
        if vms:
            for vm in vms:
                user = api.models.UserCourse.query.filter_by(instance_name=vm.name).first()
                name = ''
                if user:
                    lab = api.models.VendorUsers.query.filter_by(lab=user.instance_name, status=True).first()
                    if lab:
                        user_id = lab.id
                        course_name = str(lab.username).split('_')[-1]
                        sessions = api.models.UserSessions.query.filter_by(user_id=user_id,user_login=1,status=1).all()
                        logs_array = []
                        if sessions:
                            for l in sessions:                            
                                logs_array.append(l)
                
                            session = logs_array[-1]
                            
                            if session:                            
                                id = session.user_id
                                print("Session id",id)
                                user_name = api.models.VendorUsers.query.filter_by(id=id, status=True).first()
                                if user_name:
                                    names = str(user_name.username).split("_")
                                    name = names[2] + " "+ names[3]
                   
                else:
                    name = ''
                # ccu=int(vm.name.split("_")[1])
                server_name = ""
                net_end = str(vm.nw_name).split("-")[1]
                for server in servers:                    
                    ccu_start = str(server.ccu_start).split("-")[1]

                    if str(ccu_start) == str(net_end):

                        server_name = server.name
                        data.append({"id":vm.id,"name": vm.name,"user":name,"ip_address":vm.ip_address, "course_name": course_name, "server": server_name, "status": vm.status, "created_at": str(
                            vm.created_at), "user_id": vm.virtual_machines_user_id})
                        break
        return Response(json.dumps({"data": data}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    


@virtual_machines_controller.route("/v1/report", methods=['POST'])
def activate():
    try:
        data = eval(request.data)

        for key in ['key', 'message']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        guac_user = os.environ.get('APP_GUAC_USER')
        guac_password = os.environ.get('APP_GUAC_PASSWORD')
        guac_host1 = os.environ.get('APP_GUAC_HOST')
        guac_host2 = os.environ.get('APP_GUAC_HOST2')
        log = api.models.SCLogs({
        "log": 'v1 report 584 ' + str(data)})
        db.session.add(log)
        db.session.commit()  
        if data['key'] == 'provision' and data['status'] == 1:
            for key in ['group', "status", "vm_uuid", "vm_name", "nw_uuid", "nw_name", "helper_data", "snap_shot_uuid", "snap_shot","shadow","read_only","user_id"]:
                if key not in data.keys():
                    return Response(json.dumps({
                        'Error': "Missing parameter '" + key + "'"
                    }), status=402)
            instance = api.models.GroupInstances.query.filter_by(
                name=data['vm_name']).first()
            instance.provision_buffer_time_flag = True
            instance.status = 1
            now = datetime.utcnow()             
            current_time = now.strftime('%Y-%m-%d %H:%M:%S')
            instance.provision_buffer_time = current_time
            log = api.models.SCLogs({
            "log": 'v1 report 596' + str(data["vm_name"])})
            db.session.add(log)
            db.session.commit()  
            vm = api.models.VirtualMachines.query.filter_by(name=data['vm_name']).first()
            if vm is None:
                vm = api.models.VirtualMachines({
                    'name': data['vm_name'],
                    'nw_name': data['nw_name'],
                    'nw_uuid': data['nw_uuid'],
                    'vm_uuid': data['vm_uuid'],
                    'status': data['status'],
                    'snap_shot_name': data['snap_shot'],
                    'snap_shot_uuid': data['snap_shot_uuid'],
                    'virtual_machines_user_id': data['user_id']
                })
                vm.group_id = 0 
                if instance:
                    vm.group_id = instance.id
                vm.ip_address = instance.ip_address
                db.session.add(vm)
                db.session.commit()
                db.session.refresh(vm)
            if 'helper_data' in data and isinstance(data['helper_data'], dict):
                helper_vms = list(data['helper_data'].keys())
                if len(helper_vms) > 0:
                    log = api.models.SCLogs({
                    "log": 'v1 report 623 => ' + str(len(helper_vms))})
                    db.session.add(log)
                    db.session.commit()  
                    for helper_vm in helper_vms:
                        helper_vm_record = api.models.VirtualMachines.query.filter_by(name=helper_vm).first()
                        log = api.models.SCLogs({
                        "log": 'v1 report 629 => ' + str(helper_vm) + '    .    ' +str(helper_vm_record is None)})
                        db.session.add(log)
                        db.session.commit()  
                        if helper_vm_record is None:
                            helper_vm_record = api.models.VirtualMachines({
                                                'name': helper_vm,
                                                'nw_name': data['nw_name'],
                                                'nw_uuid': data['helper_data'][helper_vm],
                                                'vm_uuid': data['vm_uuid'],
                                                'status': data['status'],
                                                'snap_shot_name': data['snap_shot'],
                                                'snap_shot_uuid': data['snap_shot_uuid'],
                                                'virtual_machines_user_id': data['user_id']
                                                })
                            helper_vm_record.group_id = 0 
                            if instance:
                                helper_vm_record.group_id = instance.id
                            helper_vm_record.ip_address = instance.ip_address
                            db.session.add(helper_vm_record)
                            db.session.commit()
                            db.session.refresh(helper_vm_record)
            log = api.models.SCLogs({
            "log": 'v1 report 644'})
            db.session.add(log)
            db.session.commit()  
            lb1 = ''
            lb2 = ''
            group = data['vm_name'].split("_")[-1]
            vm = api.models.VmGroups.query.filter_by(group_name=group).first()
            connection_type = str(vm.connection_type).lower()
            print("Connection type =>", connection_type)
            log = api.models.SCLogs({
            "log": 'v1 report 652'})
            db.session.add(log)
            db.session.commit()  
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
                cursor.execute("select * from guacamole_connection")
                row = cursor.fetchall()
                lb1 = (cursor.rowcount)
                log = api.models.SCLogs({
                "log": 'v1 report 674'})
                db.session.add(log)
                db.session.commit()  
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
                cursor.execute("select * from guacamole_connection")
                row = cursor.fetchall()
                lb2 = (cursor.rowcount)
                cursor.close()
                conn.close()
                designated_host = ''
                if lb1 > lb2:
                    designated_host = guac_host2
                else:
                    designated_host = guac_host1
            log = api.models.SCLogs({
            "log": 'v1 report 703'})
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
                cursor = conn.cursor(buffered=True)
                cursor.execute("INSERT INTO guacamole_connection (connection_name, protocol,max_connections,max_connections_per_user) VALUES ( '" +
                               data['vm_name']+"','"+connection_type+"',2,1);")
                conn.commit()
                cursor.execute(
                    'SELECT connection_id FROM guacamole_connection WHERE connection_name="'+data['vm_name']+'";')
                connection_id = cursor.fetchone()[0]
                sharing_name_array = str(data['vm_name']).split("_")
                sharing_name = sharing_name_array[0]+'_'+sharing_name_array[1]+"_Shadow"          
                log = api.models.SCLogs({
                "log": 'v1 report 695'+str(sharing_name)})
                db.session.add(log)
                db.session.commit()   
                if data['shadow'] == 1:
                    cursor.execute("INSERT INTO guacamole_sharing_profile (sharing_profile_name,primary_connection_id) VALUES ( '" +str(sharing_name)+"','"+str(connection_id)+"');")
                    conn.commit()
                    cursor.execute(
                        'SELECT sharing_profile_id FROM guacamole_sharing_profile WHERE sharing_profile_name="'+str(sharing_name)+'";')
                    sharing_profile_id = cursor.fetchone()[0]
                    log = api.models.SCLogs({
                    "log": 'v1 report 738'+str(sharing_profile_id)})
                    db.session.add(log)
                    db.session.commit()   
                    if data['read_only'] == 1:
                        cursor.execute("INSERT INTO guacamole_sharing_profile_parameter (sharing_profile_id,parameter_name,parameter_value) VALUES ( '" +str(sharing_profile_id)+"','read-only','true');")
                        conn.commit()
                log = api.models.SCLogs({
                "log": 'v1 report 745'+str(connection_id)})
                db.session.add(log)
                db.session.commit()  
                
                cursor.execute("INSERT INTO guacamole_connection_parameter VALUES ("+str(connection_id)+",'hostname','"+instance.ip_address+"'),("+str(connection_id)+",'port','3389'), ("+str(
                    connection_id)+",'username','administrator'),("+str(connection_id)+",'password','P@ssw0rd!'),("+str(connection_id)+",'security','any'), ("+str(connection_id)+",'ignore-cert','true');")
                conn.commit()
                log = api.models.SCLogs({
                "log": 'v1 report 753'+str(connection_id)})
                db.session.add(log)
                db.session.commit()  
                if instance.aandf_state == 1:
                    cursor.execute("INSERT INTO guacamole_connection_parameter VALUES ("+str(connection_id)+",'enable-drive','true'),("+str(connection_id) +
                                   ",'create-drive-path','true'),("+str(connection_id)+",'enable-audio-input','true'), ("+str(connection_id)+",'drive-path','/Downloads/${GUAC_USERNAME}');")
                    conn.commit()
                cursor.close()
                conn.close()
                log = api.models.SCLogs({
                "log": 'v1 report 763'})
                db.session.add(log)
                db.session.commit()   
                print("Update in guac system")
                vm1 = api.models.VirtualMachines.query.filter_by(
                    name=data['vm_name']).first()
                if vm1:
                    return Response(json.dumps({
                        'Message': data['message']
                    }), status=200)
                else:
                    return Response(json.dumps({
                        'Message': data['message']
                    }), status=400)

        elif data['key'] == 'provision' and data['status'] == 0:
            log = api.models.SCLogs({
            "log": 'v1 report 780'})
            db.session.add(log)
            db.session.commit()   
            instance = api.models.GroupInstances.query.filter_by(
                name=data['vm_name']).first()
            instance.status = -1    
            instance.status_message = str(data['message'])
            log = api.models.SCLogs({
            "log": 'v1 report 596' + str(data["vm_name"])})
            db.session.add(log)
            db.session.commit() 
            error = api.models.ErrorLogs({
                'vm_name': data['vm_name'],
                'message': data['message']
            })
            db.session.add(error)
            db.session.commit()
            db.session.refresh(error)
            error = api.models.ErrorLogs.query.filter_by(
                vm_name=data['vm_name']).first()
            if error:
                return Response(json.dumps({
                    'Message': data['message']
                }), status=200)
            else:
                return Response(json.dumps({
                    'Message': "Failed error log creatin"
                }), status=400)

        elif data['key'] == 'revertsnapshot':
            print(">>>> Revert Snapshot")
            return Response(json.dumps({
                'Message': "Success"
            }), status=200)

        elif data['key'] == 'resetsnapshot':
            print(">>>> Reset Snapshot")
            return Response(json.dumps({
                'Message': "Success"
            }), status=200)

        elif data['key'] == 'capturehelpersnapshot':
            snap = api.models.HelperSnapshots({
                'vm_name': data['vm_name'],
                'snapshot_uuid': data['snap_uuid']
            })
            db.session.add(snap)
            db.session.commit()
            db.session.refresh(snap)
            snap = api.models.HelperSnapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()
            log = api.models.SCLogs({
            "log": 'v1 report 824'})
            db.session.add(log)
            db.session.commit()   
            if snap:
                return Response(json.dumps({
                    'Message': data['message']
                }), status=200)
            else:
                return Response(json.dumps({
                    'Message': "Failed creation of snapshot"
                }), status=400)

        elif data['key'] == 'capturesnapshot':
            print(data['vm_name'], data['snap_uuid'])
            snap = api.models.Snapshots({
                'vm_name': data['vm_name'],
                'snapshot_uuid': data['snap_uuid']
            })
            db.session.add(snap)
            db.session.commit()
            db.session.refresh(snap)
            snap = api.models.Snapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()

            if snap:
                return Response(json.dumps({
                    'Message': data['message']
                }), status=200)
            else:
                return Response(json.dumps({
                    'Message': "Failed creation of snapshot"
                }), status=400)

        elif data['key'] == 'deletesnapshot':
            print(">>>> Delete Snapshot")
            return Response(json.dumps({
                'Message': "Success"
            }), status=200)

        elif data['key'] == 'restoresnapshot':
            print(">>>> Restore Snapshot")
            return Response(json.dumps({
                'Message': "Success"
            }), status=200)

        else:
            log = api.models.SCLogs({
            "log": 'v1 report 871 '})
            db.session.add(log)
            db.session.commit()  
            designated_host = ''
            group = None
            if 'group_name' in data:
                group = api.models.VmGroups.query.filter_by(
                group_name=data['group_name']).first()
            if 'group' in data:
                group = api.models.VmGroups.query.filter_by(
                group_name=data['group']).first()    
            group_instance = api.models.GroupInstances.query.filter_by(
                name=data['vm_name']).first()
            if group and group_instance:
                helpers = api.models.InstanceHelpers.query.filter_by(
                instance_id=group_instance.id).all()
                log = api.models.SCLogs({
                "log": 'v1 report 836'})
                db.session.add(log)
                db.session.commit()   
                if helpers:
                    for i in helpers:
                        helper_snapshots = api.models.HelperSnapshots.query.filter_by(
                            vm_name=i.name)
                        if helper_snapshots:
                            for h in helper_snapshots:
                                db.session.delete(h)
                                db.session.commit()
                                print("Deleted all Helper snapshots")
                    for helper in helpers:
                        helper1 = api.models.InstanceHelpers.query.filter_by(
                            name=helper.name).first()
                        db.session.delete(helper1)
                        db.session.commit()
                log = api.models.SCLogs({
                "log": 'v1 report 906'})
                db.session.add(log)
                db.session.commit()   
                # else:
                #     return Response(json.dumps({
                #         'Error': "Instance does not exist."
                #     }), status=400)
                log = api.models.SCLogs({
                "log": 'v1 report 914'})
                db.session.add(log)
                db.session.commit()  
                vm = api.models.VirtualMachines.query.filter_by(
                    name=group_instance.name).first()
                log = api.models.SCLogs({
                "log": 'v1 report 920 ' + str(vm)})
                db.session.add(log)
                db.session.commit()
                db.session.delete(group_instance)
                db.session.commit()   
                if vm:
                    log = api.models.SCLogs({
                    "log": 'v1 report 927'})
                    db.session.add(log)
                    db.session.commit()   
                    snapshots = api.models.Snapshots.query.filter_by(
                        vm_name=vm.name)
                    db.session.delete(vm)
                    db.session.commit()   
                    log = api.models.SCLogs({
                    "log": 'v1 report 935'})
                    db.session.add(log)
                    db.session.commit()    
                    if snapshots:
                        for s in snapshots:
                            db.session.delete(s)
                            db.session.commit()
                            print("Deleted all snapshots")

                    log = api.models.SCLogs({
                    "log": 'v1 report 945'})
                    db.session.add(log)
                    db.session.commit()   
                    reg_vm = api.models.UserCourse.query.filter_by(
                        instance_name=data['vm_name']).first()
                    username = ""
                    log = api.models.SCLogs({
                    "log": 'v1 report 952'})
                    db.session.add(log)
                    db.session.commit()   
                    if reg_vm:
                        user = api.models.VendorUsers.query.filter_by(
                            username=reg_vm.user_name, status=True).first()
                        username = user.username
                        db.session.delete(user)
                        db.session.commit()
                        db.session.delete(reg_vm)
                        db.session.commit()
                    log = api.models.SCLogs({
                    "log": 'v1 report 964'})
                    db.session.add(log)
                    db.session.commit()   
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
                        print(data['vm_name'])

                        cursor.execute(
                            'SELECT connection_id FROM guacamole_connection where connection_name="'+data['vm_name']+'";')
                        check_for_connection = cursor.fetchone()
                        if check_for_connection is None:
                            designated_host = guac_host2
                        else:
                            designated_host = guac_host1

                        cursor.close()
                        conn.close()
                    log = api.models.SCLogs({
                    "log": 'v1 report 969 ' + str(designated_host)})
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
                        cursor = conn.cursor(buffered=True)
                        cursor.execute(
                            'SELECT connection_id FROM guacamole_connection where connection_name="'+data['vm_name']+'";')
                        connection_id = cursor.fetchone()[0]
                        cursor.execute(
                            'DELETE FROM guacamole_connection WHERE connection_id='+str(connection_id)+';')
                        conn.commit()
                        log = api.models.SCLogs({
                        "log": 'v1 report 992'})
                        db.session.add(log)
                        db.session.commit()   
                        if username != "":
                            print("inside if")
                            cursor.execute(
                                'SELECT user_id FROM guacamole_user where username="'+username+'";')
                            user_id = cursor.fetchone()[0]
                            cursor.execute(
                                'DELETE FROM guacamole_user WHERE user_id='+str(user_id)+';')
                            conn.commit()
                            cursor.close()
                            conn.close()
                            return Response(json.dumps({
                                'Message': "Success"
                            }), status=200)
                        else:
                            cursor.close()
                            conn.close()
                            return Response(json.dumps({
                                'Message': "Success"
                            }), status=200)

                    return Response(json.dumps({
                                    'Message': "Success"
                                    }), status=200)

                else:
                    return Response(json.dumps({
                        'Message': "Teardown Failed"
                    }), status=400)
            else:
                return Response(json.dumps({
                    'Message': "Group not found"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        e_string = str(e) or ""
        log = api.models.SCLogs({
        "log": 'v1 report 964' + e_string[0:483]})
        db.session.add(log)
        db.session.commit()   
        return raiseException(e)
    finally:
        db.session.close()    


@virtual_machines_controller.route("/v1/list/logs", methods=['GET'])
def get_log():
    try:
        logs = api.models.ErrorLogs.query.all()
        data = []
        if logs:
            for log in logs:
                data.append({'id': log.id, 'created_at': str(log.created_at).split(" ")[
                            0], "vm_name": log.vm_name, "message": log.message, "status": log.status})
        return Response(json.dumps({"data": data}), status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/update/log", methods=['POST'])
def update_log():
    try:
        data = eval(request.data)
        log = api.models.ErrorLogs.query.filter_by(id=data['id']).first()
        if log:
            log.status = 'resolved'
            db.session.commit()
            db.session.refresh(log)
            return Response(json.dumps({"Message": "Resolved Error"}), status=200)
        else:
            return Response(json.dumps({"Error": "Error log not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    
    
@virtual_machines_controller.route("/v1/update/user_session", methods=['POST'])
def update_user_session():
    try:
        data = eval(request.data) 
        print(data['id'],data['user_login'])       
        logs = api.models.UserSessions.query.filter_by(user_id=data['id']).all()
        logs_array = []
        for l in logs:
            logs_array.append(l)
            
        log = logs_array[-1]
        print('log==>',log)
        if log:
            log.user_login = int(data['user_login'])
            db.session.commit()
            db.session.refresh(log)
            return Response(json.dumps({"Message": "Resolved Error"}), status=200)
        else:
            return Response(json.dumps({"Error": "Session log not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/delete/log", methods=['POST'])
def delete_log():
    try:
        data = eval(request.data)
        log = api.models.ErrorLogs.query.filter_by(id=data['id']).first()
        if log:
            db.session.delete(log)
            db.session.commit()
            return Response(json.dumps({"Message": "Resolved and deleted the Error"}), status=200)
        else:
            return Response(json.dumps({"Error": "Error log not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/list/instances", methods=['POST'])
def instances_list():
    try:
        data = eval(request.data)
        subnets = []
        for key in ['group_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        if data['group_name'] is "":
            instances = api.models.GroupInstances.query.filter_by(
                status=1).all()
            if instances:
                data = []
                for instance in instances:                    
                    data.append({
                        'name': instance.name,
                        'created_at': str(instance.created_at),
                        'ip_address': instance.ip_address,
                        'ccu_landing': instance.ccu_landing,
                        'ccu_helper': instance.ccu_helper,
                        'status': instance.status,
                        'status_message': instance.status_message
                    })
            else:
                data = []
            return Response(json.dumps({'data': data}), status=200)
        else:
            group = api.models.VmGroups.query.filter_by(
                group_name=data['group_name']).first()
            if group:                
                instances = api.models.GroupInstances.query.filter_by(
                    group_id=group.id).all()
                
                if instances:
                    data = []             
                
                    
                    for instance in instances:
                        user_info = api.models.UserCourse.query.filter_by(instance_name=instance.name).first()
                        subnets.append(str(instance.ccu_landing).split('-')[1])
                        if user_info is not None:
                            data.append({
                            'name': instance.name,
                            'created_at': str(instance.created_at),
                            'ip_address': instance.ip_address,
                            'ccu_landing': instance.ccu_landing,
                            'ccu_helper': instance.ccu_helper,
                            'status': instance.status,
                            'user_status':1,
                             })
                        else:
                            data.append({
                            'name': instance.name,
                            'created_at': str(instance.created_at),
                            'ip_address': instance.ip_address,
                            'ccu_landing': instance.ccu_landing,
                            'ccu_helper': instance.ccu_helper,
                            'status': instance.status,
                            'status_message': instance.status_message
                            })

                        
                else:
                    data = []
                subnets = list(set(subnets))    
                servers = api.models.Servers.query.all()
                server_memory = []
                server_ip = []
                for s in servers:                    
                    subnet = str(s.ccu_start).split('-')[1]                    
                    if subnet in subnets:
                        server_ip.append(s.ip_address)
                        key = os.environ.get('XE_PASSWORD_KEY').encode('ascii')
                        cipher_suite = Fernet(key)
                        password = cipher_suite.decrypt(
                                bytes('gAAAAABfs2FvxtBtBKOTi6Vy_hTmBVhQfkYTflXG_46dDzTYw8Wq__8JTMuGDbXeOtqX0F0TlZUkYJhCWU_BWfMXSJyM3p61NA==', 'raw_unicode_escape')).decode("utf-8")
                        client = ssh_remotely('root',password,s.ip_address) 
                        memory_free = ["xe host-list params=memory-free --minimal"]    
                        status3 = run_command_ssh2(client, memory_free,'null')
                        val3 = int(status3[1])
                        memory_total = ["xe host-list params=memory-total --minimal"]    
                        status4 = run_command_ssh2(client, memory_total,'null')
                        val4 = int(status4[1])                
                        server_memory.append({'name':s.name,'subnet':subnet,'memory_free':val3 / 1024 / 1024 /1024,'memory_total':val4 / 1024 / 1024 /1024})
                server_ip = list(set(server_ip))            
                return Response(json.dumps({'data': data,'performance':server_memory,'server_ip':server_ip}), status=200)
            else:
                return Response(json.dumps({"Error": "Group not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
    
@virtual_machines_controller.route("/v1/list/instances_all", methods=['GET'])
def instances_list_all():
    try:    
            
               
            instances = api.models.GroupInstances.query.all()
            if instances:
                data = []
                for instance in instances:
                    data.append({
                        'name': instance.name,
                        'created_at': str(instance.created_at),
                        'ip_address': instance.ip_address,
                        'ccu_landing': instance.ccu_landing,
                        'ccu_helper': instance.ccu_helper,
                        'status': instance.status
                       
                    })
            else:
                data = []
            return Response(json.dumps({'data': data, 'performance':server_memory}), status=200)       
            

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/teardown/vm", methods=['POST'])
def vm_teardown():
    try:
        data = json.loads(request.data)
        if data['masterTeardown']:

            instances = api.models.GroupInstances.query.all()
            for instance in instances:

                temp_name = instance.name.split("_")[-1]

                if temp_name == data['groupName']:
                    group = api.models.VmGroups.query.filter_by(
                        id=instance.group_id).first()
                    log = api.models.SCLogs({
                        "log": 'teardown vm 1144'})
                    db.session.add(log)
                    db.session.commit()  
                    if instance:
                        subnet = str(instance.ccu_landing).split("-")[1]

                        if instance.status == 0 and instance.is_assigned == True:
                            continue
                            # return Response(json.dumps({"Message":"Teardown completed"}),status=200)
                        else:
                            servers = api.models.Servers.query.all()
                            log = api.models.SCLogs({
                                "log": 'teardown vm 1182'})
                            db.session.add(log)
                            db.session.commit()  
                            for server in servers:
                                if str(server.ccu_start).split("-")[1] == subnet:
                                    host = server.ip_address
                                    password_xe = server.password_digest
                                    user = server.username

                            helper_names = []
                            if instance:
                                helpers = api.models.InstanceHelpers.query.filter_by(
                                    instance_id=instance.id).all()
                                for helper in helpers:
                                    helper_names.append(helper.name)
                                    db.session.delete(helper)
                                    db.session.commit()
                            # db.session.delete(instance)
                            # db.session.commit()
                            teardown_enqueue_credentials({
                                'key': 'teardown', 'ccu': instance.ccu_landing, "group_name": group.group_name, 'vm_name': instance.name,
                                'helpers': helper_names, 'host': host, 'password_xe': password_xe, 'user': user
                            })
                            instance.status = 0
                            db.session.commit()
                            log = api.models.SCLogs({
                                "log": 'teardown vm 1208'})
                            db.session.add(log)
                            db.session.commit()  
                            time.sleep(200)
                        # return Response(json.dumps({"Message":"Teardown completed"}),status=200)
                    else:
                        log = api.models.SCLogs({
                            "log": 'teardown vm 1216'})
                        db.session.add(log)
                        db.session.commit()  
                        return Response(json.dumps({"Error": "Error group not found"}), status=400)

            

            return Response(json.dumps({"Message": "Teardown completed"}), status=200)

        else:
            for key in ['name']:
                if key not in data.keys():
                    return Response(json.dumps({
                        'Error': "Missing parameter '" + key + "'"
                    }), status=402)
            instance = api.models.GroupInstances.query.filter_by(
                name=data['name']).first()
            group = api.models.VmGroups.query.filter_by(
                id=instance.group_id).first()
            log = api.models.SCLogs({
                "log": 'teardown vm 1235'})
            db.session.add(log)
            db.session.commit()  
            if instance:
                subnet = str(instance.ccu_landing).split("-")[1]
                log = api.models.SCLogs({
                    "log": 'teardown vm 1241'})
                db.session.add(log)
                db.session.commit()  
                if instance.status == 0 and instance.is_assigned == True:
                    return Response(json.dumps({"Message": "Teardown not possible as it is assigned"}), status=403)
                else:
                    servers = api.models.Servers.query.all()
                    log = api.models.SCLogs({
                    "log": 'teardown vm 1279'})
                    db.session.add(log)
                    db.session.commit() 
                    for server in servers:
                        if str(server.ccu_start).split("-")[1] == subnet:
                            host = server.ip_address
                            password_xe = server.password_digest
                            user = server.username
                    helper_names = []
                    if instance:
                        helpers = api.models.InstanceHelpers.query.filter_by(
                            instance_id=instance.id).all()
                        for helper in helpers:
                            helper_names.append(helper.name)
                            db.session.delete(helper)
                            db.session.commit()
                        # db.session.delete(instance)
                        # db.session.commit()
                    teardown_enqueue_credentials({
                        'key': 'teardown', 'ccu': instance.ccu_landing, "group_name": group.group_name, 'vm_name': instance.name,
                        'helpers': helper_names, 'host': host, 'password_xe': password_xe, 'user': user})
                    instance.status = 0
                    db.session.commit()
                    log = api.models.SCLogs({
                    "log": 'teardown vm 1304'})
                    db.session.add(log)
                    db.session.commit() 
                    return Response(json.dumps({"Message": "Teardown completed"}), status=200)
            else:
                return Response(json.dumps({"Error": "Error group not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
        "log": 'teardown vm 1316' + str(e)})
        db.session.add(log)
        db.session.commit()     
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/revertsnapshot/vm", methods=['POST'])
def vm_revertsnapshot():
    print("vm_revertsnapshot")
    try:
        data = eval(request.data)
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        instance = api.models.GroupInstances.query.filter_by(
            name=data['name']).first()
        group = api.models.VmGroups.query.filter_by(
            id=instance.group_id).first()
        if instance:
            host=None
            subnet = str(instance.ccu_landing).split("-")[1]
            if instance.status == 1:
                servers = api.models.Servers.query.all()
                for server in servers:
                    if str(server.ccu_start).split("-")[1] == subnet:
                        host = server.ip_address
                        password_xe = server.password_digest
                        user = server.username
                        break
                log = api.models.SCLogs({
                "log": "revert 1512: " + str(host)})
                db.session.add(log)
                db.session.commit()  
                helpers = api.models.InstanceHelpers.query.filter_by(
                    instance_id=instance.id).all()
                helper_names = []
                for helper in helpers:
                    helper_names.append(helper.name)
                reset_enqueue_credentials({
                    'key': 'revertsnapshot', 'ccu': instance.ccu_landing, "group_name": group.group_name, 'vm_name': instance.name,
                    'helpers': helper_names, 'host': host, 'password_xe': password_xe, 'user': user})
                instance_group = api.models.GroupInstances.query.filter_by(
                    name=instance.name)
                return Response(json.dumps({"Message": "Revert Snapshot completed"}), status=200)
            else:
                servers = api.models.Servers.query.all()
                for server in servers:
                    if server.ccu_start <= instance.ccu_landing <= server.ccu_end:
                        host = server.ip_address
                        password_xe = server.password_digest
                        user = server.username
                        break
                log = api.models.SCLogs({
                "log": "revert 1535: " + str(host)})
                db.session.add(log)
                db.session.commit()  
                helpers = api.models.InstanceHelpers.query.filter_by(
                    instance_id=instance.id).all()
                helper_names = []
                for helper in helpers:
                    helper_names.append(helper.name)

                reset_enqueue_credentials({
                    'key': 'revertsnapshot', 'ccu': instance.ccu_landing, "group_name": group.group_name, 'vm_name': instance.name,
                    'helpers': helper_names, 'host': host, 'password_xe': password_xe, 'user': user})
                instance_group = api.models.GroupInstances.query.filter_by(
                    name=instance.name)

                return Response(json.dumps({"Message": "Snapshot Revert completed"}), status=200)
        else:
            return Response(json.dumps({"Error": "Error group not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/capturesnapshot", methods=['POST'])
def vm_capturesnapshot():
    try:
        data = eval(request.data)
        for key in ['token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user = api.models.UserCourse.query.filter_by(
            access_token=data['token']).first()

        if user:
            inst = user.instance_name
            vm = api.models.VirtualMachines.query.filter_by(
                name=str(inst)).first()
            log = api.models.SCLogs({
            "log": "VM for snapshot 1461 " + str(vm)})
            db.session.add(log)
            db.session.commit()                  
            if vm:
                vm_name = vm.name
                vm_uuid = vm.vm_uuid
                ccu = vm.nw_name
                ccu = str(ccu).split("-")[1]
                servers = api.models.Servers.query.all()

                host = ''
                password_xe = ''
                user = ''
                for server in servers:
                    offset = str(server.ccu_start).split("-")[1]
                    if (offset == ccu) and (server):
                        host = server.ip_address
                        password_xe = server.password_digest
                        user = server.username
                reset_enqueue_credentials({
                    'key': 'capturesnapshot', 'host': host, 'password_xe': password_xe, 'user': user, 'vm_name': vm_name, 'vm_uuid': vm_uuid})
                time.sleep(10)
                return Response(json.dumps({'Message': 'Captured'}), status=200)
            else:
                log = api.models.SCLogs({
                "log": "No such VM available"})
                db.session.add(log)
                db.session.commit()  
                return Response(json.dumps({'Message': 'No such VM available'}), status=400)
                
        else:
            return Response(json.dumps({'Error': "Invalid token"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/capturehelpersnapshot", methods=['POST'])
def vm_capturehelpersnapshot():
    try:
        data = eval(request.data)
        for key in ['token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user = api.models.UserCourse.query.filter_by(
            access_token=data['token']).first()

        if user:
            inst = user.instance_name
            print(inst)
            vm = api.models.VirtualMachines.query.filter_by(
                name=str(inst)).first()
            vm_name = vm.name
            print(vm_name)
            temp1 = vm_name.split("_")[0]
            temp2 = vm_name.split("_")[1]

            sucession = temp2.split("-")

            temp_succe = sucession[0]
            print(temp_succe)
            temp3 = int(temp_succe) + 1000

            temp4 = str(temp3)+"-"+str(sucession[1])
            print(temp4)
            prefix = temp1+"_"+temp4
            vm_uuid = vm.vm_uuid
            ccu = vm.nw_name
            ccu = str(ccu).split("-")[1]
            servers = api.models.Servers.query.all()
            host = ''
            password_xe = ''
            user = ''
            for server in servers:
                offset = str(server.ccu_start).split("-")[1]

                if offset == ccu:
                    host = server.ip_address
                    password_xe = server.password_digest
                    user = server.username

            reset_enqueue_credentials({
                'key': 'capturehelpersnapshot', 'host': host, 'password_xe': password_xe, 'user': user, 'vm_name': prefix+"_"+data['hlpr_name'], 'vm_uuid': vm_uuid})
            time.sleep(10)
            return Response(json.dumps({'Message': 'Captured'}), status=200)

        else:
            return Response(json.dumps({'Error': "Invalid token"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/listsnapshot", methods=['POST'])
def vm_listsnapshot():
    try:
        time.sleep(10)
        data = eval(request.data)
        for key in ['token']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        user = api.models.UserCourse.query.filter_by(
            access_token=data['token']).first()

        if user:
            inst = user.instance_name

            instance = api.models.GroupInstances.query.filter_by(
                name=inst).first()
            inst_id = instance.id

            helper_vm_items = []
            helper_vm = api.models.InstanceHelpers.query.filter_by(
                instance_id=inst_id).all()
            log = api.models.SCLogs({
            "log": "log 1584 listsnaphot"})
            db.session.add(log)
            db.session.commit()      
            if helper_vm:
                hlp_name = helper_vm[0].name
                print(hlp_name)
                succession = str(hlp_name).split("_")[1]
                print(succession)
                count = 0
                for h in helper_vm:
                    count = count + 1
                    temp1 = h.helper_name.split("_")[0]
                    temp2 = h.helper_name.split("_")[1]
                    name = temp1+"_"+temp2
                    helper_vm_items.append({'label': str(
                        succession)+"_"+name+'_'+str(count), 'name': h.helper_name, 'vm_name': h.name})
            print(helper_vm_items)
            snap = api.models.Snapshots.query.filter_by(vm_name=inst).all()
            snap_items = []
            log = api.models.SCLogs({
            "log": "log 1604 listsnaphot"})
            db.session.add(log)
            db.session.commit()    
            if snap:
                for i in snap:
                    snap_items.append(
                        {'date': str(i.created_at), 'snap_uuid': i.snapshot_uuid, 'type':'landing'})
            helper_snap_items = []
            log = api.models.SCLogs({
            "log": "log 1613 listsnaphot"})
            db.session.add(log)
            db.session.commit()  
            for h in helper_vm_items:
                vm_name = h['vm_name'][0:h['vm_name'].rfind('_')]
                temp = api.models.HelperSnapshots.query.filter_by(
                    vm_name=vm_name).all()
                if temp:
                    for j in temp:
                        helper_snap_items.append(
                            {'date': str(j.created_at), 'snap_uuid': j.snapshot_uuid, 'type':'helper'})
            log = api.models.SCLogs({
            "log": "log 1624 listsnaphot"})
            db.session.add(log)
            db.session.commit()  
            return Response(json.dumps({'data': snap_items, 'data2': helper_snap_items, 'helper_data': helper_vm_items, 'lvm': inst}), status=200)

        else:
            return Response(json.dumps({'Error': "Invalid token"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/deletesnapshot", methods=['POST'])
def vm_deletesnapshot():
    try:
        data = eval(request.data)
        for key in ['snap_uuid']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        print(data['snap_uuid'])
        vm = None
        vm_name = ''
        if data['type'] == 'landing':
            snap = api.models.Snapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()
        else:
            snap = api.models.HelperSnapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()

        if snap:
            db.session.delete(snap)
            db.session.commit()
            if data['type'] == 'landing':
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name
                vm_uuid = vm.vm_uuid
            else:
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name
                vm_uuid = vm.vm_uuid

            ccu = vm.nw_name
            ccu = str(ccu).split("-")[1]
            servers = api.models.Servers.query.all()
            host = ''
            password_xe = ''
            user = ''
            for server in servers:
                offset = str(server.ccu_start).split("-")[1]

                if offset == ccu:
                    host = server.ip_address
                    password_xe = server.password_digest
                    user = server.username
            instance = api.models.GroupInstances.query.filter_by(
                name=data['vm_name']).first()
            helpers = api.models.InstanceHelpers.query.filter_by(
                instance_id=instance.id).all()
            helper_names = []

            reset_enqueue_credentials({
                'key': 'deletesnapshot', 'host': host, 'password_xe': password_xe, 'user': user, 'vm_name': vm_name, 'helpers': helper_names, 'snap_uuid': data['snap_uuid']})
            time.sleep(10)
            return Response(json.dumps({'Message': 'Deleted Snapshot'}), status=200)

        else:
            return Response(json.dumps({'Error': "Invalid Snapshot"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/restoresnapshot", methods=['POST'])
def vm_restoresnapshot():
    try:
        data = eval(request.data)
        for key in ['snap_uuid']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        print(data['snap_uuid'])
        vm = None
        vm_name = ''
        if data['type'] == 'landing':
            snap = api.models.Snapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()
            print("Snap",snap)
        else:
            snap = api.models.HelperSnapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()

        if snap:
            if data['type'] == 'landing':
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name
                vm_uuid = vm.vm_uuid
            else:
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name    
                vm_uuid = vm.vm_uuid

            ccu = vm.nw_name
            ccu = str(ccu).split("-")[1]
            servers = api.models.Servers.query.all()
            host = ''
            password_xe = ''
            user = ''
            for server in servers:
                offset = str(server.ccu_start).split("-")[1]

                if offset == ccu:
                    host = server.ip_address
                    password_xe = server.password_digest
                    user = server.username
            reset_enqueue_credentials({
                'key': 'restoresnapshot', 'host': host, 'password_xe': password_xe, 'user': user, 'vm_name': vm_name, 'snap_uuid': data['snap_uuid']})
            time.sleep(10)
            return Response(json.dumps({'Message': 'Restore Snapshot'}), status=200)

        else:
            return Response(json.dumps({'Error': "Invalid Snapshot"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@virtual_machines_controller.route("/v1/resetsnapshot", methods=['POST'])
def vm_resetsnapshot():
    try:
        data = eval(request.data)
        for key in ['snap_uuid']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        print(data['snap_uuid'])
        if data['type'] == 'landing':
            snap = api.models.Snapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()
        else:
            snap = api.models.HelperSnapshots.query.filter_by(
                snapshot_uuid=data['snap_uuid']).first()

        if snap:
            db.session.delete(snap)
            db.session.commit()
            if data['type'] == 'landing':
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name
                vm_uuid = vm.vm_uuid
            else:
                vm = api.models.VirtualMachines.query.filter_by(
                    name=str(snap.vm_name)).first()
                vm_name = vm.name    
                vm_uuid = vm.vm_uuid

            ccu = vm.nw_name
            ccu = str(ccu).split("-")[1]
            servers = api.models.Servers.query.all()
            host = ''
            password_xe = ''
            user = ''
            for server in servers:
                offset = str(server.ccu_start).split("-")[1]

                if offset == ccu:
                    host = server.ip_address
                    password_xe = server.password_digest
                    user = server.username
            instance = api.models.GroupInstances.query.filter_by(
                name=data['vm_name']).first()
            helpers = api.models.InstanceHelpers.query.filter_by(
                instance_id=instance.id).all()
            helper_names = []

            reset_enqueue_credentials({
                'key': 'resetsnapshot', 'host': host, 'password_xe': password_xe, 'user': user, 'vm_name': vm_name, 'helpers': helper_names, 'snap_uuid': data['snap_uuid']})
            time.sleep(10)
            return Response(json.dumps({'Message': 'Reset Snapshot'}), status=200)

        else:
            return Response(json.dumps({'Error': "Invalid Snapshot"}), status=402)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()