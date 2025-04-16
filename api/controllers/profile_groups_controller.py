from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
import mysql.connector
from sshtunnel import SSHTunnelForwarder
from api import db
import time

profile_groups_controller = Blueprint('profile_groups_controller', __name__)
CORS(profile_groups_controller)

@profile_groups_controller.route("/v1/profile_groups", methods=['POST'])
def register():
    try:
        data = json.loads(request.data)
        for key in ['group_name','group_type','vendor_id']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        new_group = api.models.ProfileGroups({
            'group_name':data['group_name'],
            'group_type':data['group_type'],
            'vendor_id':data['vendor_id'],
        })
        print(new_group)
        db.session.add(new_group)
        db.session.commit()
        db.session.refresh(new_group)
        course = api.models.ProfileGroups.query.filter_by(group_name=data['group_name']).first()
        if course:
            return Response(json.dumps({
                    'Message': "Group created successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Group creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
            
@profile_groups_controller.route("/v1/list/profile_groups", methods=['GET'])
def get_groups():
    try:
        profile_groups = api.models.ProfileGroups.query.all()
        result=[]
        if profile_groups:
            for data in profile_groups:
                result.append({
                    'id': data.id,
                    'created_at':str(data.created_at),
                    'group_name': data.group_name, 
                    'group_type': data.group_type,    
                    'vendor_id': data.vendor_id              
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    