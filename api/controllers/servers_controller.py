from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db
from api.helpers import send_mail
import smtplib
import re

servers_controller = Blueprint('servers_controller', __name__)
CORS(servers_controller)

@servers_controller.route("/v1/register/server", methods=['POST'])
def register():   
    try:
        data = json.loads(request.data)
        for key in ['ip_address','ccu_start','ccu_end','name','password', 'username','user_id','vendor_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)  
        servers = api.models.Servers.query.all()
        
        if re.search("-",data['ccu_start'])is None:
             return Response(json.dumps({
                    'Error': "Invalid CCU Format"
                }), status=400)
        if re.search("-",data['ccu_end'])is None:
             return Response(json.dumps({
                    'Error': "Invalid CCU Format"
                }), status=400)
        temp1 = str(data['ccu_start']).split("-")[1]
        temp2 = str(data['ccu_end']).split("-")[1]
        if temp1 != temp2:
            return Response(json.dumps({
                    'Error': "Mismatch server id"
                }), status=400)                 
        new_ccu_start = str(data['ccu_start']).split("-")[0]
        new_ccu_end = str(data['ccu_end']).split("-")[0] 
            
        if int(new_ccu_start)>=int(new_ccu_end):
            return Response(json.dumps({
                    'Error': "CCU end must be greater than start"
                }), status=400)

        
        ccu_exist = api.models.Servers.query.filter_by(ccu_start=data['ccu_start']).all()
        print(ccu_exist)
        if ccu_exist:
            return Response(json.dumps({
                    'Error': "CCU already exists change range of CCU"
                }), status=400)
            
        # for server in servers:            
        #     if int(data['ccu_start']) in range(server.ccu_end, server.ccu_end+1) or int(data['ccu_end']) in range(server.ccu_end, server.ccu_end+1):
        #         return Response(json.dumps({
        #             'Error': "CCU already exists change range of CCU"
        #         }), status=400)
                
             
        
        new_server = api.models.Servers({
            'ip_address':data['ip_address'],
            'name':data['name'],
            'ccu_start':data['ccu_start'],
            'ccu_end':data['ccu_end'],
            'username':data['username'],
            'servers_user_id':data['user_id'],
            # 'size':data['size'],
            'vendor_name':data['vendor_name']
        })       
        new_server.set_password(data['password'])
        db.session.add(new_server)
        db.session.commit()
        db.session.refresh(new_server)
        server = api.models.Servers.query.filter_by(name=data['name']).first()
        if server:
            return Response(json.dumps({
                    'Message': "Server registration successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Server creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@servers_controller.route("/v1/list/servers", methods=['GET'])
def get_servers():
    try:
        servers = api.models.Servers.query.all()
        result=[]
        if servers:
            for data in servers:
                result.append({
                    'created_at':str(data.created_at),
                    'name': data.name,
                    # 'size':data.size,
                    'ccu_start':data.ccu_start,
                    'ip_address':data.ip_address,
                    'ccu_range':str(data.ccu_start)+" - "+str(data.ccu_end),
                    'user_id':data.servers_user_id
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@servers_controller.route("/v1/update/server", methods=['POST'])
def update_servers():
    try:
        data = json.loads(request.data)
        print(data)
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        server = api.models.Servers.query.filter_by(name=data['name']).first()
        print(data['size'])
        if server:
            if 'password' in data.keys():
                server.set_password(data['password'])
            if 'username' in data.keys():
                server.username=data['username']
            if 'ccu_start' in data.keys():
                server.ccu_start=data['ccu_start']
            if 'ccu_end' in data.keys():
                server.ccu_end=data['ccu_end']
            if 'ip_address' in data.keys():
                server.ip_address=data['ip_address']
            # if 'size' in data.keys():
            #     server.size=str(data['size'])
                    
            if re.search("-",server.ccu_start)is None:
                return Response(json.dumps({
                    'Error': "Invalid CCU Format"
                }), status=400)
            if re.search("-",server.ccu_end)is None:
                return Response(json.dumps({
                    'Error': "Invalid CCU Format"
                }), status=400)    
            
            new_ccu_start = str(server.ccu_start).split("-")[0]
            new_ccu_end = str(server.ccu_end).split("-")[0] 
            
            if int(new_ccu_start)>=int(new_ccu_end):
                return Response(json.dumps({
                    'Error': "CCU end must be greater than start"
                }), status=400)   
                 
            db.session.commit()
            db.session.refresh(server)
            server = api.models.Servers.query.filter_by(name=data['name']).first()
            if server:
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

@servers_controller.route("/v1/delete/server", methods=['POST'])
def delete_server():
    try:
        data = json.loads(request.data)
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        server = api.models.Servers.query.filter_by(name=data['name']).first()
        if server:
            db.session.delete(server)
            db.session.commit()
            server = api.models.Servers.query.filter_by(name=data['name']).first()
            if server:
                return Response(json.dumps({"Error":'Server deletion failed'}),status=400)
            else:
                return Response(json.dumps({"Message":'Server deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'Server not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@servers_controller.route("/v1/info/server", methods=['POST'])
def information_server():
    try:
        data = json.loads(request.data)
        for key in ['name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
       
        server = api.models.Servers.query.filter_by(name=data['name']).first()
        if server:
            server_mask = str(server.ccu_start).split('-')[1]
            data = {'mask':server_mask}            
            return Response(json.dumps({"data":data}),status=200)

        else: 
            return Response(json.dumps({"Error":'Server not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()




