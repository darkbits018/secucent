from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
# import mysql.connector
# from sshtunnel import SSHTunnelForwarder
from api import db
# import time
# from passlib.hash import sha256_crypt
# from werkzeug.security import generate_password_hash, check_password_hash
# from cryptography.fernet import Fernet
# import base64
# from Crypto.Cipher import AES
# from Crypto.Hash import SHA256
# from Crypto import Random
# from smtplib import SMTPException
# import smtplib
from netaddr import *
import paramiko
# from cryptography.fernet import Fernet
from netaddr import *
# import ssl
# import pika
# import re
# import os

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
    print("result",result)  
    print("Error......................", stderr.read())
    if stderr.readline():
        return (0, stderr.read())
    return (1, result.strip())

ip_list = []

configuration_controller = Blueprint('configuration_controller', __name__)
CORS(configuration_controller)


@configuration_controller.route("/v1/configuration", methods=['POST'])
def config():

    try:
        data = json.loads(request.data)
        for key in ['user_id', 'msHost', 'msdName', 'msPort', 'msUser', 'msPassword', 'serverSIP', 'serverEIP', 'sSubnet', 'xePasswordKey', 'vmStartIP', 'vmEndIP', 'vmSubnet', 'rMQHost', 'rMQUser', 'rMQPassword', 'rMQ2Host', 'rMQ2User', 'rMQ2Password','rMQ3Host', 'rMQ3User', 'rMQ3Password','cBrokerHost', 'cBrokerUser', 'cBrokerPassword', 'cBroker2Host', 'cBroker2User', 'cBroker2Password', 'gateway','cbData']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        for ip in IPNetwork(data['gateway']+'/22').iter_hosts():
            ip_list.append(ip)
        gateway = ip_list[0]
        configuration = api.models.Configuration({
            'msHost': data['msHost'],
            'msdName': data['msdName'],
            'msPort': data['msPort'],
            'msUser': data['msUser'],
            'msPassword': data['msPassword'],
            'serverSIP': data['serverSIP'],
            'serverEIP': data['serverEIP'],
            'sSubnet': data['sSubnet'],
            'xePasswordKey': data['xePasswordKey'],
            'vmStartIP': data['vmStartIP'],
            'vmEndIP': data['vmEndIP'],
            'vmSubnet': data['vmSubnet'],
            'rMQHost': data['rMQHost'],
            'rMQUser': data['rMQUser'],
            'rMQPassword': data['rMQPassword'],
            'rMQHost': data['rMQHost'],
            'rMQ2User': data['rMQ2User'],
            'rMQ2Password': data['rMQ2Password'],
            'rMQ3Host': data['rMQ3Host'],
            'rMQ3User': data['rMQ3User'],
            'rMQ3Password': data['rMQ3Password'],
            'cBrokerHost': data['cBrokerHost'],
            'cBrokerUser': data['cBrokerUser'],
            'cBrokerPassword': data['cBrokerPassword'],
            'cBroker2Host': data['cBroker2Host'],
            'cBroker2User': data['cBroker2User'],
            'cBroker2Password': data['cBroker2Password'],
            'user_id': data['user_id'],
            'gateway': gateway,
            'cbData':data['cbData']
        })
        print(configuration)

        db.session.add(configuration)
        db.session.commit()
        db.session.refresh(configuration)
        return Response(json.dumps({
            'Message': "Configured successful"
        }), status=200)
        # conf = api.models.Configuration.query.filter_by(user_id=data['user_id']).first()
        # if conf:
        #     return Response(json.dumps({
        #         'Message': "Configured successful"
        #     }), status=200)
        # else:
        #     return Response(json.dumps({
        #         'Error': "Configured failed"
        #     }), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

def get_global_conf():
    try:

        conf = api.models.Configuration.query.all()
        result = []
        if conf:
            for data in conf:
                result.append({
                    'id': data.id,
                    'msHost': data.msHost,
                    'msdName': data.msdName,
                    'msPort': data.msPort,
                    'msUser': data.msUser,
                    'msPassword': data.msPassword,
                    'serverSIP': data.serverSIP,
                    'serverEIP': data.serverEIP,
                    'sSubnet': data.sSubnet,
                    'xePasswordKey': data.xePasswordKey,
                    'vmStartIP': data.vmStartIP,
                    'vmEndIP': data.vmEndIP,
                    'vmSubnet': data.vmSubnet,
                    'rMQHost': data.rMQHost,
                    'rMQUser': data.rMQUser,
                    'rMQPassword': data.rMQPassword,
                    'rMQ2Host': data['rMQ2Host'],
                    'rMQ2User': data['rMQ2User'],
                    'rMQ2Password': data['rMQ2Password'],
                    'rMQ3Host': data['rMQ3Host'],
                    'rMQ3User': data['rMQ3User'],
                    'rMQ3Password': data['rMQ3Password'],
                    'cBrokerHost': data.cBrokerHost,
                    'cBrokerUser': data.cBrokerUser,
                    'cBrokerPassword': data.cBrokerPassword,
                    'cBroker2Host': data.cBroker2Host,
                    'cBroker2User': data.cBroker2User,
                    'cBroker2Password': data.cBroker2Password,
                    'user_id': data.user_id,
                    'gateway': data.gateway
                })
        return result
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@configuration_controller.route("/v1/list/configuration", methods=['GET'])
def get_config():
    try:
        conf = api.models.Configuration.query.all()
        print(conf)
        result = []
        if conf:
            for data in conf:
                print(data.id)
                print(data.cbData)
                cbData=[]
                cbData=data.cbData
                result.append({
                    'id': data.id,
                    'msHost': data.msHost,
                    'msdName': data.msdName,
                    'msPort': data.msPort,
                    'msUser': data.msUser,
                    'msPassword': data.msPassword,
                    'serverSIP': data.serverSIP,
                    'serverEIP': data.serverEIP,
                    'sSubnet': data.sSubnet,
                    'xePasswordKey': data.xePasswordKey,
                    'vmStartIP': data.vmStartIP,
                    'vmEndIP': data.vmEndIP,
                    'vmSubnet': data.vmSubnet,
                    'rMQHost': data.rMQHost,
                    'rMQUser': data.rMQUser,
                    'rMQPassword': data.rMQPassword,
                    'rMQ2Host': data.rMQ2Host,
                    'rMQ2User': data.rMQ2User,
                    'rMQ2Password': data.rMQ2Password,
                    'rMQ3Host': data.rMQ3Host,
                    'rMQ3User': data.rMQ3User,
                    'rMQ3Password': data.rMQ3Password,
                    'cBrokerHost': data.cBrokerHost,
                    'cBrokerUser': data.cBrokerUser,
                    'cBrokerPassword': data.cBrokerPassword,
                    'cBroker2Host': data.cBroker2Host,
                    'cBroker2User': data.cBroker2User,
                    'cBroker2Password': data.cBroker2Password,
                    'user_id': data.user_id,
                    'gateway': data.gateway,
                    'cbData':cbData
                })
                print("hereee")
        return Response(json.dumps({"data": result}), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@configuration_controller.route("/v1/delete/configuration", methods=['POST'])
def delete_config():
    try:
        data = json.loads(request.data)
        for key in ['id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        conf = api.models.Configuration.query.filter_by(id=data['id']).first()
        if conf:
            db.session.delete(conf)
            db.session.commit()
            conf = api.models.Configuration.query.filter_by(
                id=data['id']).first()
            if conf:
                return Response(json.dumps({"Error": 'Configuration deletion failed'}), status=400)
            else:
                return Response(json.dumps({"Message": 'Configuration deleted successfully'}), status=200)

        else:
            return Response(json.dumps({"Error": 'Configuration not found'}), status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@configuration_controller.route("/v1/update/configuration", methods=['POST'])
def update_config():
    try:
        data = json.loads(request.data)
        for key in ['id', 'user_id', 'msHost', 'msdName', 'msPort', 'msUser', 'msPassword', 'serverSIP', 'serverEIP', 'sSubnet', 'xePasswordKey', 'vmStartIP', 'vmEndIP', 'vmSubnet', 'rMQHost', 'rMQUser', 'rMQPassword','rMQ2Host', 'rMQ2User', 'rMQ2Password','rMQ3Host', 'rMQ3User', 'rMQ3Password', 'cBrokerHost', 'cBrokerUser', 'cBrokerPassword', 'cBroker2Host', 'cBroker2User', 'cBroker2Password', 'gateway']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        for ip in IPNetwork(data['gateway']+'/22').iter_hosts():
            ip_list.append(ip)
        gateway = ip_list[0]
        config = api.models.Configuration.query.filter_by(
            id=data['id']).first()
        if config: 
            if config.rMQPassword != data['rMQPassword']:                
                client = ssh_remotely('root','toor',data['rMQHost'])
                command = ["sudo rabbitmqctl change_password admin "+data['rMQPassword']]
                status = run_command_ssh(client,command)
            if config.rMQ2Password != data['rMQ2Password']:                
                client = ssh_remotely('cara','toor',data['rMQ2Host'])
                command = ["sudo rabbitmqctl change_password admin "+data['rMQ2Password']]
                status = run_command_ssh(client,command)
            if config.rMQ3Password != data['rMQ3Password']:                
                client = ssh_remotely('cara','toor',data['rMQ3Host'])
                command = ["sudo rabbitmqctl change_password admin "+data['rMQ3Password']]
                status = run_command_ssh(client,command)
                
        configuration = api.models.Configuration({
            'msHost': data['msHost'],
            'msdName': data['msdName'],
            'msPort': data['msPort'],
            'msUser': data['msUser'],
            'msPassword': data['msPassword'],
            'serverSIP': data['serverSIP'],
            'serverEIP': data['serverEIP'],
            'sSubnet': data['sSubnet'],
            'gateway': gateway,
            'xePasswordKey': data['xePasswordKey'],
            'vmStartIP': data['vmStartIP'],
            'vmEndIP': data['vmEndIP'],
            'vmSubnet': data['vmSubnet'],
            'rMQHost': data['rMQHost'],
            'rMQUser': data['rMQUser'],
            'rMQPassword': data['rMQPassword'],
            'rMQ2Host': data['rMQ2Host'],
            'rMQ2User': data['rMQ2User'],
            'rMQ2Password': data['rMQ2Password'],
            'rMQ3Host': data['rMQ3Host'],
            'rMQ3User': data['rMQ3User'],
            'rMQ3Password': data['rMQ3Password'],
            'cBrokerHost': data['cBrokerHost'],
            'cBrokerUser': data['cBrokerUser'],
            'cBrokerPassword': data['cBrokerPassword'],
            'cBroker2Host': data['cBroker2Host'],
            'cBroker2User': data['cBroker2User'],
            'cBroker2Password': data['cBroker2Password'],
            'user_id': data['user_id'],

            'id': data['id'],
            'cbData':data['cbData']
        })
       
        config = api.models.Configuration.query.filter_by(
            id=data['id']).first()
        if config:
            if 'id' in data.keys():
                config.id = data['id']
            if 'msHost' in data.keys():
                config.msHost = data['msHost']
            if 'msdName' in data.keys():
                config.msdName = data['msdName']
            if 'msPort' in data.keys():
                config.msPort = data['msPort']
            if 'msUser' in data.keys():
                config.msUser = data['msUser']
            if 'msPassword' in data.keys():
                config.msPassword = data['msPassword']
            if 'serverSIP' in data.keys():
                config.serverSIP = data['serverSIP']
            if 'serverEIP' in data.keys():
                config.serverEIP = data['serverEIP']
            if 'sSubnet' in data.keys():
                config.sSubnet = data['sSubnet']
            if 'xePasswordKey' in data.keys():
                config.xePasswordKey = data['xePasswordKey']
            if 'vmStartIP' in data.keys():
                config.vmStartIP = data['vmStartIP']
            if 'vmEndIP' in data.keys():
                config.vmEndIP = data['vmEndIP']
            if 'vmSubnet' in data.keys():
                config.vmSubnet = data['vmSubnet']
            if 'rMQHost' in data.keys():
                config.rMQHost = data['rMQHost']
            if 'rMQUser' in data.keys():
                config.rMQUser = data['rMQUser']
            if 'rMQPassword' in data.keys():
                config.rMQPassword = data['rMQPassword']
            if 'rMQ2Host' in data.keys():
                config.rMQ2Host = data['rMQ2Host']
            if 'rMQ2User' in data.keys():
                config.rMQ2User = data['rMQ2User']
            if 'rMQ2Password' in data.keys():
                config.rMQ2Password = data['rMQ2Password']
            if 'rMQ3Host' in data.keys():
                config.rMQ3Host = data['rMQ3Host']
            if 'rMQ3User' in data.keys():
                config.rMQ3User = data['rMQ3User']
            if 'rMQ3Password' in data.keys():
                config.rMQ3Password = data['rMQ3Password']
            if 'cBrokerHost' in data.keys():
                config.cBrokerHost = data['cBrokerHost']
            if 'cBrokerUser' in data.keys():
                config.cBrokerUser = data['cBrokerUser']
            if 'cBrokerPassword' in data.keys():
                config.cBrokerPassword = data['cBrokerPassword']
            if 'cBroker2Host' in data.keys():
                config.cBroker2Host = data['cBroker2Host']
            if 'cBroker2User' in data.keys():
                config.cBroker2User = data['cBroker2User']
            if 'cBroker2Password' in data.keys():
                config.cBroker2Password = data['cBroker2Password']
            if 'user_id' in data.keys():
                config.user_id = data['user_id']
            if 'gateway' in data.keys():
                config.gateway = data['gateway']
            if 'cbData' in data.keys():
                config.cbData=data['cbData']
            db.session.commit()
            db.session.refresh(config)
            config = api.models.Configuration.query.filter_by(
                id=data['id']).first()
            if config:
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