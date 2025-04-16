from flask import Blueprint, request, Response
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
import mysql.connector
from sshtunnel import SSHTunnelForwarder
from api import db
import time

profile_group_roles_controller = Blueprint('profile_group_roles_controller', __name__)
CORS(profile_group_roles_controller)

    
@profile_group_roles_controller.route("/v1/list/profile_group_roles", methods=['GET'])
def get_roles():
    try:
        profile_groups = api.models.GroupRoles.query.all()
        result=[]
        if profile_groups:
            for data in profile_groups:
                result.append({
                    'id': data.id,                    
                    'role_name': data.group_roles_name,                                   
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    