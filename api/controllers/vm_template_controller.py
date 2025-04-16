
from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
import ipaddress
import os
import pika
from cryptography.fernet import Fernet
from netaddr import *
import ssl
import re
import paramiko
vm_template_controller = Blueprint('vm_template_controller', __name__)
CORS(vm_template_controller)

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
    result = stdout.read()   
    result = str(result).split('\n')
    result = str(result).split('\\n')
    result = str(result[-4]).split(':')[1]
    result = result.replace("\\", "")
    
   
    print("Error......................", stderr.read())
    if stderr.readline():
        return (0, stderr.read())
    return (int(result) / 1024 / 1024 / 10)

@vm_template_controller.route("/v1/create/template", methods=['POST'])
def create_template():
    try:
        data = json.loads(request.data)
        for key in ['template_name','vm_clone_name', 'template_type','firewall','user_id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        templates = api.models.VmTemplates.query.filter_by(template_name=data["template_name"]).first()        
        if templates:
            return Response(json.dumps({
                'Error': 'Template name already existing!'
            }), status=400)
        else:
            vm_template = api.models.VmTemplates({
                'template_name': data["template_name"],
                'vm_clone_name': data['vm_clone_name'],
                'template_type':data['template_type'],
                'status' : 1,
                'firewall':data['firewall'],
                # 'size':data['size'],
                'vm_templates_user_id':data['user_id']
            })
            db.session.add(vm_template)
            db.session.commit()
            template_type=data['template_type']
            if template_type == 0:
                message = "Landing VM Created"
            elif template_type == 1:
                message = "Helper VM created"
            else:
                message = "Natter Created"
            return Response(json.dumps({
                    'Message': message
                }), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_template_controller.route("/v1/list/template", methods=['GET'])
def get_template():
    try:
        vms = api.models.VmTemplates.query.filter_by(template_type=0).all()
        helpers = api.models.VmTemplates.query.filter_by(template_type=1).all()
        natters = api.models.VmTemplates.query.filter_by(template_type=2).all()
        data=[]
        helper_data=[]
        natter_data=[]
        if vms:
            for vm in vms:
                data.append({'id':vm.id,"template_name":vm.template_name,"vm_clone_name":vm.vm_clone_name,"status":str(vm.status),"created_at":str(vm.created_at),"user_id":vm.vm_templates_user_id})
        if helpers:
            for helper in helpers:
                helper_data.append({'id':helper.id,"template_name":helper.template_name,"vm_clone_name":helper.vm_clone_name,"status":str(helper.status),"created_at":str(helper.created_at),"user_id":helper.vm_templates_user_id})
        if natters:
            for natter in natters:
                natter_data.append({'id':natter.id,"template_name":natter.template_name,"vm_clone_name":natter.vm_clone_name,"status":str(natter.status),"created_at":str(natter.created_at),"user_id":natter.vm_templates_user_id})
        return Response(json.dumps({"data":data,"helper_data":helper_data,"natter_data":natter_data}),status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    

@vm_template_controller.route("/v1/update/template", methods=['POST'])
def update_template():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        template = api.models.VmTemplates.query.filter_by(id=data['id']).first()
        
        if template:
            if 'template_name' in data.keys():
                template.template_name=data['template_name']
            if'vm_clone_name' in data.keys():
                template.vm_clone_name=data['vm_clone_name']
            if'template_type' in data.keys():
                template.template_type=data['template_type']
            # if 'size' in data.keys():
            #     template.size=data['size']
            db.session.commit()
            db.session.refresh(template)
            template = api.models.VmTemplates.query.filter_by(id=data['id']).first()
            if template:
                return Response(json.dumps({
                    'Message': "Successfully updated"
                }), status=200)
        else: 
            return Response(json.dumps({"Error":'Template not found'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_template_controller.route("/v1/delete/template", methods=['POST'])
def delete_template():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        template = api.models.VmTemplates.query.filter_by(id=data['id']).first()
        if template:
            db.session.delete(template)
            db.session.commit()
            template = api.models.VmTemplates.query.filter_by(id=data['id']).first()
            if template:
                return Response(json.dumps({"Error":'Template deletion failed'}),status=400)
            else:
                return Response(json.dumps({"Message":'Template deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'Template not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@vm_template_controller.route("/v1/size/template", methods=['POST'])
def size_template():
    try:
        
        data = json.loads(request.data)
        
        for key in ['names']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        result=[]
        sizes = []
        if len(data['server_ip']) > 0:
            ip = data['server_ip'][0]
            for d in data['names']:  
                print(d)
                key = os.environ.get('XE_PASSWORD_KEY').encode('ascii')
                cipher_suite = Fernet(key)
                password = cipher_suite.decrypt(
                                    bytes('gAAAAABfs2FvxtBtBKOTi6Vy_hTmBVhQfkYTflXG_46dDzTYw8Wq__8JTMuGDbXeOtqX0F0TlZUkYJhCWU_BWfMXSJyM3p61NA==', 'raw_unicode_escape')).decode("utf-8")
                client = ssh_remotely('root',password,ip) 
                
                command = ["xe vm-disk-list vm="+str(d['name'])]    
                status = run_command_ssh(client, command)
                print(status)
                sizes.append(status)
        else:                
            return Response(json.dumps({"message":"Need ip address to get template sizes"}),status=400)   
 
                   
        return Response(json.dumps({"data":sizes}),status=200)       

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    