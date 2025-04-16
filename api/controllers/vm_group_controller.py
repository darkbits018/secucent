from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
import ipaddress
import pika
import os
from api.helpers import crypto
from netaddr import *
import ssl
import time
from smtplib import SMTPException
import smtplib
from api.helpers import verify_jwt

vm_group_controller = Blueprint('vm_group_controller', __name__)
CORS(vm_group_controller)

# To create Range of subnets


def handle_token():
    # Get the token from the Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response(json.dumps({"message": "Missing token"}), 401)

    # Extract the token from the header (assuming it's a Bearer token)
    token = auth_header.split(" ")[1]

    # Verify the token
    decoded_token, error = verify_jwt.verify_token(token)
    if error:
        return Response(json.dumps({"message": error}), 401)
    return decoded_token


def list_addr(ip, ccu, ser_ccu_str, ser_ccu_end, subnet):
    ip_list = []
    public_ip_list = []
    reserved_ip_list = []
    print("Subet==>", subnet, "publiclist=>", public_ip_list)
    x = int(ser_ccu_str) - 1000
    j = int(ser_ccu_end) - int(ser_ccu_str)

    count = 0

    for ip in IPNetwork(ip+'/20').iter_hosts():
        check_subnet = str(ip).split(".")[2]
        if check_subnet == str(subnet):
            ip_list.append(ip)

    ip_list.pop(0)
    for i in ip_list:
        test = str(i).split(".")[2]

        if test == str(0):
            value = i + 256
            public_ip_list.append(value)
            reserved_ip_list.append(i)
        else:

            value = i
            public_ip_list.append(value)

    for p in range(j):
        test_count = api.models.GroupInstances.query.filter_by(
            ip_address=str(public_ip_list[p])).first()
        if test_count:
            data = {"ip": public_ip_list[p + 1]}
        else:
            data = {"ip": public_ip_list[p]}
            return data

    # iterator = 0
    # x = x - 1
    # for p in range(j):
    #     test = api.models.GroupInstances.query.filter_by(ip_address=str(public_ip_list[p + x])).first()
    #     if test:
    #         iterator = iterator + 1
    #         if test.ip_address == public_ip_list[p + x]:
    #             print(public_ip_list[p + 1 + x])
    #             data = {"ip":public_ip_list[p + 1 + x],"iterator":iterator}

    #             return data
    #     else:
    #         iterator = iterator + 1
    #         print(public_ip_list[p + x ])
    #         data = {"ip":public_ip_list[p + x ],"iterator":iterator}
    #         return data


def enqueue_credentials(data):
    #    try:
    user = os.environ.get('APP_RABBITMQ_USER')
    password = os.environ.get('APP_RABBITMQ_PASSWORD')
    host = os.environ.get('APP_RABBITMQ_HOST')
    print("RMQ", host)
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(credentials=credentials, host=host))
    try:
        log = api.models.SCLogs({
            "log": 'basic_publish /v1/provision/group'})
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


def join_template_group(data):
    result = (db.session.query(api.models.VmGroups, api.models.TemplateGroup)
              .filter(api.models.VmGroups.group_name == api.models.TemplateGroup.group_name)
              .filter(api.models.VmGroups.group_name == str(data['group_name']))
              .all())
    output = []
    if result:
        for item in result:
            print(item)
            group = item[0]
            template_group = item[1]
            output.append({
                'group_name': group.group_name,
                'ccu_start': group.ccu_start,
                'ccu_end': group.ccu_end,
                'ip_start': group.ip_start,
                'ip_end': group.ip_end,
                'status': group.status,
                'template_name': template_group.template_name
            })
    return output


@vm_group_controller.route("/v1/create/groups", methods=['POST'])
def create():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        data = json.loads(request.data)

        for key in ['group_name', 'landing_vm', 'helpers', 'natter', 'vendor_name', 'user_id', 'connection_type','odv_options']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        vendor_name = decoded_token.get('vendor_name') if vendor_id else data["vendor_name"] 
        if data["group_name"] == "":
            return Response(json.dumps({
                'Error': "Please enter a group name."
            }), status=400)
        if data["landing_vm"] == "":
            return Response(json.dumps({
                'Error': "Select a landing VM"
            }), status=400)
        if vendor_name == "":
            return Response(json.dumps({
                'Error': "Select the Vendor"
            }), status=400)
        if data["natter"] == "":
            return Response(json.dumps({
                'Error': "Select the Natter"
            }), status=400)
        if data["connection_type"] == "":
            return Response(json.dumps({
                'Error': "Select the Connection Type"
            }), status=400)

        if None in data['helpers']:
            return Response(json.dumps({
                'Error': "Select all helpers"
            }), status=400)
        if len(data['group_name'].split(' ')) is not 1:
            return Response(json.dumps({
                'Error': "Group name should not contain spaces"
            }), status=400)
        if len(set(data["helpers"])) != len(data["helpers"]):
            return Response(json.dumps({
                'Error': "Please select distinct Helper Vms"
            }), status=400)
        index = data['natter'].find('_')
        if index > 0:
            natter_name = data['natter'][index+1:]
        else:
            natter_name = data['natter']
        print(natter_name)
        group = api.models.VmGroups({
            'group_name': data['group_name'],
            'landing_vm': data['landing_vm'],
            'natter':data['natter'],
            'vendor': vendor_name,
            'vm_groups_user_id': data['user_id'],
            'connection_type': data['connection_type'],
            'odv_options':data['odv_options']
         
        })
        db.session.add(group)
        db.session.commit()
        db.session.refresh(group)

        group = api.models.VmGroups.query.filter_by(
            group_name=data['group_name']).first()
        if group:
            i = 1
            for helper in data['helpers']:
                helper_list = helper.split('_')
                if helper_list[-1] is 'archive':
                    helper_str = '_'.join(helper_list[:-1])
                else:
                    helper_str = '_'.join(helper_list)
                helper_vm = api.models.HelperVms({
                    'name': '_'.join(helper_list[:-1])+'_'+str(i)+'_'+group.group_name,
                    'helper_clone_name': helper,
                    'group_id': group.id,
                    'helper_vms_user_id': group.vm_groups_user_id
                })
                db.session.add(helper_vm)
                db.session.commit()
                db.session.refresh(helper_vm)
                helper_vm = api.models.HelperVms.query.filter_by(name='_'.join(
                    helper_list[:-1])+'_'+str(i)+'_'+group.group_name).first()
                if helper_vm:
                    i = i+1
                else:
                    return Response(json.dumps({
                        'Message': "Helper vm creation failed"
                    }), status=400)
            return Response(json.dumps({
                'Message': "Group created successfully"
            }), status=200)
        else:
            return Response(json.dumps({
                'Message': "Group creation failed"
            }), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/groups", methods=['PATCH'])
def update():
    try:
        data = json.loads(request.data)

        for key in ['group_name', 'landing_vm', 'helpers', 'natter', 'user_id', 'connection_type','odv_options']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        if data["group_name"] == "":
            return Response(json.dumps({
                'Error': "Please enter a group name."
            }), status=400)
        if data["landing_vm"] == "":
            return Response(json.dumps({
                'Error': "Select a landing VM"
            }), status=400)
        if data["natter"] == "":
            return Response(json.dumps({
                'Error': "Select the Natter"
            }), status=400)
        if data["connection_type"] == "":
            return Response(json.dumps({
                'Error': "Select the Connection Type"
            }), status=400)

        if None in data['helpers']:
            return Response(json.dumps({
                'Error': "Select all helpers"
            }), status=400)
        if len(data['group_name'].split(' ')) is not 1:
            return Response(json.dumps({
                'Error': "Group name should not contain spaces"
            }), status=400)
        if len(set(data["helpers"])) != len(data["helpers"]):
            return Response(json.dumps({
                'Error': "Please select distinct Helper Vms"
            }), status=400)
        index = data['natter'].find('_')
        if index > 0:
            natter_name = data['natter'][index+1:]
        else:
            natter_name = data['natter']
        print(natter_name)
        group = api.models.VmGroups.query.filter_by(
            group_name=data['group_name']).first()
        if group:
            group.landing_vm = data['landing_vm']
            group.natter = data['natter']
            group.vm_groups_user_id = data['user_id']
            group.connection_type = data['connection_type']
            group.odv_options = data['odv_options']
            db.session.commit()
            db.session.refresh(group)

            i = 1
            for helper in data['helpers']:
                helper_list = helper.split('_')
                helper_vm = api.models.HelperVms.query.filter_by(name='_'.join(
                    helper_list[:-1])+'_'+str(i)+'_'+group.group_name).first()
                if helper_vm is None:    
                    if helper_list[-1] is 'archive':
                        helper_str = '_'.join(helper_list[:-1])
                    else:
                        helper_str = '_'.join(helper_list)
                    helper_vm = api.models.HelperVms({
                        'name': '_'.join(helper_list[:-1])+'_'+str(i)+'_'+group.group_name,
                        'helper_clone_name': helper,
                        'group_id': group.id,
                        'helper_vms_user_id': group.vm_groups_user_id
                    })
                    db.session.add(helper_vm)
                    db.session.commit()
                    db.session.refresh(helper_vm)
                    helper_vm = api.models.HelperVms.query.filter_by(name='_'.join(
                        helper_list[:-1])+'_'+str(i)+'_'+group.group_name).first()
                    if helper_vm:
                        i = i+1
                    else:
                        return Response(json.dumps({
                            'Message': "Helper vm creation failed"
                        }), status=400)
            return Response(json.dumps({
                'Message': "Group created successfully"
            }), status=200)
        else:
            return Response(json.dumps({
                'Message': "Group creation failed"
            }), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/list/groups", methods=['GET'])
def get_template():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_name = decoded_token.get('vendor_name')
        groups = None
        if vendor_name:
            groups = api.models.VmGroups.query.filter_by(vendor=vendor_name).all()
        else:
            groups = api.models.VmGroups.query.all()
        result = []
        if groups:
            for data in groups:
                print(data)
                helper = api.models.HelperVms.query.filter_by(
                    group_id=data.id).all()
                helpers = []
                for h in helper:
                    helpers.append(h.helper_clone_name)
                result.append({
                    'id': data.id,
                    'created_at': str(data.created_at),
                    'name': data.group_name,
                    'landing_vm': data.landing_vm,
                    'helpers': helpers,
                    'natter': data.natter,
                    'vendor': data.vendor,
                    'user_id': data.vm_groups_user_id,
                    'odv_options': data.odv_options,
                    'connection_type': data.connection_type
                })
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/list/groups_template", methods=['POST'])
def get_template_group():
    try:
        data = json.loads(request.data)
        if not data['group_name']:
            return Response(json.dumps({
                'Message': "group_name field missing"
            }), status=400)
        output = join_template_group(data)
        return Response(json.dumps({"data": str(output)}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/provision/group", methods=['POST'])
def provision():
    try:
        print("PLEASE WAIT")
        # time.sleep(10)
        
        data = json.loads(request.data)
        new_ccu_start = ''
        new_ccu_end = ''
        subnet = ''
        for key in ['group_name', 'ip_start', 'server_name', 'natter', 'vendor', 'user_id', 'count','shadow','read_only']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        # iterations = int(data['count'])
        # if iterations > 1:
        #     iterations = iterations + 1
        # for i in range(int(iterations)):
        ccu_number = 1001
        for i in range(int(data['count'])):
            time.sleep(20)
            ccu_landing = ccu_number + i
            ip_address = int(data['ip_start'])+i
            ip_address = (ipaddress.IPv4Address(ip_address))
            print(ip_address)
            if data['server_name'] != "":
                server = api.models.Servers.query.filter_by(
                    name=data['server_name']).first()

                new_ccu_start = server.ccu_start.split("-")[0]
                new_ccu_end = server.ccu_end.split("-")[0]
                subnet = server.ccu_start.split("-")[1]

                if not (int(ccu_landing)) >= int(new_ccu_start) and int(ccu_landing) <= int(new_ccu_end):
                    return Response(json.dumps({
                        'Error': "CCU is not in the given server"
                    }), status=400)
            else:
                return Response(json.dumps({
                    'Error': "Missing parameter Server Name"
                }), status=400)
            group = api.models.VmGroups.query.filter_by(
                group_name=data['group_name']).first()
            
            if group:
                
                template = api.models.VmTemplates.query.filter_by(
                    vm_clone_name=group.landing_vm).first()
                natter= None
                if group.natter:
                    natter = api.models.VmTemplates.query.filter_by(
                        template_name=group.natter,template_type=2).first()
                landing_list = group.landing_vm.split('_')

                if landing_list[-1] is 'archive':
                    landing = '_'.join(landing_list[:-1])
                else:
                    landing = '_'.join(landing_list)

                assign_ip = list_addr(
                    str(ip_address),ccu_landing, new_ccu_start, new_ccu_end, subnet)
            
                offset = str(assign_ip["ip"]).split(".")[3]
                offset = int(offset) - 1

                c_l = str(new_ccu_start).split("-")[0]
                c_l = int(c_l)+offset
                c_l = str(c_l)+"-"+str(subnet)

                c_h = str(new_ccu_start).split("-")[0]
                c_h = int(c_h)+offset+1000
                c_h = str(c_h)+"-"+str(subnet)

                print("new_ip >>>", assign_ip["ip"])
                print("Landing CCU>>", c_l)
                print("helper CCU>>", c_h)
                instance = api.models.GroupInstances({
                    "group_id": group.id,
                    "name": group.vendor+'_'+c_l+'_'+landing+'_'+group.group_name,
                    "ip_address": str(assign_ip["ip"]),
                    "ccu_landing": c_l,
                    "ccu_helper": c_h,
                    "odv": 1,
                    "odv_options":group.odv_options,
                    "group_instances_user_id": data["user_id"],
                    "lab_end_session": None,
                    "is_assigned":False
                })
                if "aandf_state" in data.keys():
                    instance.aandf_state = data['aandf_state']
                    # if "odv" in data.keys():
                    #     instance.odv = data['odv']
                    # print("reached")

                db.session.add(instance)
                db.session.commit()
                db.session.refresh(instance)
                instance1 = api.models.GroupInstances.query.filter_by(
                    name=group.vendor+'_'+str(c_l)+'_'+landing+'_'+group.group_name).first()
                helpers = api.models.HelperVms.query.filter_by(
                    group_id=group.id).all()
                if instance1:
                    helper_names = {}
                    for helper in helpers:                    
                        template = api.models.VmTemplates.query.filter_by(vm_clone_name=helper.helper_clone_name).first()
                        print(">>>>>>>>>>>>instance1 ccu helper",
                            instance1.ccu_helper)
                        print(".......... instance 1 cci landing",
                            instance1.ccu_landing)
                        helper_names[helper.helper_clone_name] = group.vendor + \
                            '_'+str(instance1.ccu_helper)+'_'+helper.name
                        helper_instance = api.models.InstanceHelpers({
                            "instance_id": instance1.id,
                            "name": group.vendor+'_'+str(instance1.ccu_helper)+'_'+helper.name+'_'+str(template.firewall),
                            "helper_name": helper.name,
                            "instance_helpers_user_id": data["user_id"]
                        })
                        db.session.add(helper_instance)
                        db.session.commit()
                        db.session.refresh(helper_instance)
                        helper1 = api.models.InstanceHelpers.query.filter_by(
                            name=group.vendor+'_'+str(instance1.ccu_helper)+'_'+helper.name+'_'+str(template.firewall)).first()
                        if helper1:
                            helper_names[helper.helper_clone_name] = helper1.name
                        else:
                            return Response(json.dumps({
                                            'Message': "HelperVm creation failed"
                                            }), status=400)
                    oct1 = str(assign_ip["ip"]).split(".")[0]
                    oct2 = str(assign_ip["ip"]).split(".")[1]
                    oct4 = str(assign_ip["ip"]).split(".")[3]
                    gateway = str(oct1)+"."+str(oct2)+"."+str(0)+"."+str(oct4)                
                    queue_data = {
                        "ip": instance1.ip_address,
                        "gateway": gateway,
                        "ccu": instance1.ccu_landing,
                        "name": instance1.name,
                        "username": "test",
                        "password": "test",
                        "host": server.ip_address,
                        "password_xe": server.password_digest,
                        "user": server.username,
                        "clone_name": group.landing_vm,
                        "helpers": helper_names,
                        "group_name": group.group_name,
                        "vendor": group.vendor,
                        "key": "provision",
                        "shadow":data['shadow'],
                        "read_only":data['read_only'],
                        "user_id": data['user_id'],
                        "natter": natter.vm_clone_name if group.natter and natter is not None else None
                    }
                    log = api.models.SCLogs({
                    "log": 'provision ' + str(queue_data)})
                    db.session.add(log)
                    db.session.commit()  
                    enqueue_credentials(queue_data)

                    db.session.commit()

            else:
                return Response(json.dumps({
                    'Message': "Instance creation failed"
                }), status=400)
        else:
            return Response(json.dumps({"Message": "Group is not found"}), status=200)

        return Response(json.dumps({
            'Message': "Success"
        }), status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/teardown/group", methods=['POST'])
def group_teardown():
    try:
        data = eval(request.data)

        group = api.models.VmGroups.query.filter_by(
            group_name=data['group_name']).first()
        if group:
            
            instances = api.models.GroupInstances.query.filter_by(
                group_id=group.id).all()
            if instances:
                return Response(json.dumps({"Error": "Please delete the instances."}), status=400)
            else:
                helpers = api.models.HelperVms.query.filter_by(
                    group_id=group.id).all()
                if helpers:
                    for helper in helpers:
                        db.session.delete(helper)
                        db.session.commit()
                db.session.delete(group)
                db.session.commit()

                group1 = api.models.VmGroups.query.filter_by(
                    group_name=data['group_name']).first()
                if group1:
                    return Response(json.dumps({"Error": "Group Deletion Failed."}), status=400)
                else:
                    return Response(json.dumps({"Message": "Group Deleted"}), status=200)

        else:
            return Response(json.dumps({"Error": "Error group not found"}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_group_controller.route("/v1/activate/group", methods=['PUT'])
def activate():
    return None
# @vm_group_controller.route("/v1/provision/dynamic", methods=['POST'])
# def dynmamicprovision():
#     try:
       
                
#                 queue_data = {
#                     "ip": '10.20.1.12',
#                     "gateway": '10.20.0.0',
#                     "ccu": '1012-2',                    
#                     "username": "test",
#                     "password": "test",
#                     "clone_name": 'windows_2016_lvm_archive',
#                     "group_name": 'SCI_1012-2_pods1_windows_2016_lvm_archive',
#                     "user": 'root',
#                     "password_xe":'gAAAAABf6-xh_F3T3e9is-noF-TVS1nDqWeApQzog8c6tw7P8XSkYlLee3yDlVIlLJyDHMKnjI3nw500Wg2q6yNzdsjJ7ToE9A==' ,
#                     "host": '172.20.4.100',  
#                     "vendor": 'SCI',
#                     "key": "dprovision",                   
                   
#                 }
                
#                 enqueue_credentials(queue_data)

#                 db.session.commit()
#                 return Response(json.dumps({
#             'Message': "Success"
#         }), status=200)
       

        

#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)