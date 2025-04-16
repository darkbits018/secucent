from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
from api import db


register_vm_controller = Blueprint('register_vm_controller', __name__)
CORS(register_vm_controller)

@register_vm_controller.route("/v1/register/vm_course", methods=['POST'])
def register():
    try:
        data = json.loads(request.data)
        for key in ['course_name', 'group_name', 'server_name', 'course_duration', 'username']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        register_vms = api.models.RegisterVms({
            'course_name':data['course_name'],
            'group_name':data['group_name'],
            'server_name':data['server_name'],
            'username':data['username'],
            'course_duration':data['course_duration'],
            'status': True
        })
        db.session.add(register_vms)
        db.session.commit()
        db.session.refresh(register_vms)
        register = api.models.RegisterVms.query.filter_by(
            course_name=data['course_name'], group_name=data['group_name'], 
            server_name=data['server_name'], username=data['username'],
            course_duration=data['course_duration']).first()
        if register:
            return Response(json.dumps({
                    'Message': "Vm registration successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Vm registration failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@register_vm_controller.route("/v1/list/register_vm", methods=['GET'])
def get_courses():
    try:
        registers = api.models.RegisterVms.query.all()
        result=[]
        if registers:
            for data in registers:
                result.append({
                    'id': data.id,
                    'course_name': data.course_name,
                    'group_name': data.group_name,
                    'server_name': data.server_name,
                    'username': data.username,
                    'course_duration': data.course_duration,
                    'status': str(data.status),
                    'created_at': str(data.created_at)
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@register_vm_controller.route("/v1/enable_disable/register_vms", methods=['POST'])
def update_courses():
    try:
        data = json.loads(request.data)
        for key in ['id', 'status']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        register = api.models.RegisterVms.query.filter_by(id=data['id']).first()
        
        if register:
            register.status=eval(data['status'])
            db.session.commit()
            db.session.refresh(register)
            register = api.models.RegisterVms.query.filter_by(id=data['id']).first()
            if register:
                return Response(json.dumps({
                    'Message': "Successfully updated"
                }), status=200)
        else: 
            return Response(json.dumps({"Error":'Course not found'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()