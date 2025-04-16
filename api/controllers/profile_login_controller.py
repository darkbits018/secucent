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
# import base64 
# from Crypto.Cipher import AES
# from Crypto.Hash import SHA256
# from Crypto import Random
from cryptography.fernet import Fernet
import jwt
import datetime
import os
profile_login_controller = Blueprint('profile_login_controller', __name__)
CORS(profile_login_controller)

# Function to generate JWT
def generate_token(email, vendor, is_vendor=False):
    # Payload containing the email and vendorId
    payload = {
        'email': email,
        'vendor_id': None if vendor is None else vendor.id,
        'vendor_name': None if vendor is None else vendor.name,
        'is_vendor': is_vendor,
        # Expiration time set to 7 days from now
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    }

    # Secret key (store this securely)
    secret_key = os.environ.get('APP_SECRET')

    # Generate token using the HS256 algorithm
    token = jwt.encode(payload, secret_key, algorithm='HS256')

    return token
    
@profile_login_controller.route("/v1/profile_login", methods=['POST'])
def login():
    try:
        data = json.loads(request.data)
        for key in ['user_name','password']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
            u_name = data['user_name']            
            pwsd = data['password']
           
            
        check = api.models.ProfileUsers.query.filter_by(user_name=u_name).first()
        if check is not None:
            user_id = check.id
            user_group = check.user_group  
            status=check.status
            key = check.key
            encoded_message = bytes(check.password, 'utf-8')            
            f = Fernet(key)
            decrypted_message = f.decrypt(encoded_message)
            test = (decrypted_message.decode())         
            db_access = check.db_access
            if(test == data['password']):
                profile_group = api.models.ProfileGroups.query.filter_by(id=check.user_group).first()
                vendor = None
                if profile_group.vendor_id is not None:
                    vendor = api.models.Users.query.filter_by(id=profile_group.vendor_id).first()
                token = generate_token(check.email_id,vendor, check.user_group > 3)    
                response = Response(json.dumps({'Message': "Login Success",'user_group':user_group,'user_id':user_id,'status':status,'db_access':db_access}), status=200)
                response.headers['Authorization'] = f'Bearer {token}'
                return response
            else:
                return Response(json.dumps({'Error': "Invalid Password"}), status=400)
                     
        else:
            return Response(json.dumps({'Error': "user not exist!"}), status=400)        
       
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    
