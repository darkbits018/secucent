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
from cryptography.fernet import Fernet
# import base64
# from Crypto.Cipher import AES
# from Crypto.Hash import SHA256
# from Crypto import Random
# from smtplib import SMTPException
# import smtplib
# import os
student_users_controller = Blueprint('student_users_controller', __name__)
CORS(student_users_controller)

    
@student_users_controller.route("/v1/student_users", methods=['POST'])
def register():
    try:       
        data = json.loads(request.data)
        for key in ['user_name','password']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
         
        key = Fernet.generate_key()
        encoded_message = str(data['password']).encode()
        f = Fernet(key)
        
        encrypted_message = f.encrypt(encoded_message)        
        new_user = api.models.StudentUsers({
            'user_name':data['user_name'],
            'password':encrypted_message,            
            'key':key     
            
        })
        user = api.models.StudentUsers.query.filter_by(user_name=new_user.user_name).all()        
        if not user:
            db.session.add(new_user)
            db.session.commit()
            db.session.refresh(new_user)
           
            return Response(json.dumps({'Message': "user created successful"}), status=200)
            
                     
        else:
            return Response(json.dumps({
                    'Error': "user name already exist"
                }), status=400)
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
            
# @student_users_controller.route("/v1/list/student_users", methods=['GET'])
# def get_users():
#     try:
#         student_users = api.models.studentUsers.query.all()
#         result=[]
#         if student_users:
#             for data in student_users:
#                 u_g = api.models.studentGroups.query.filter_by(id=data.user_group).first()                
#                 user_group = u_g.group_name
#                 user_group_id = u_g.group_type
                
#                 result.append({
#                     'id': data.id,
#                     'user_name':data.user_name,
#                     'email_id':data.email_id,
#                     'created_at':str(data.created_at),
#                     'user_group': user_group, 
#                     'user_group_id': user_group_id,
#                     'status': data.status,
#                     'user_id':data.student_users_user_id                    
#                 })
#         return Response(json.dumps({"data":result}),status=200)
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)

# @student_users_controller.route("/v1/delete/student_user", methods=['POST'])
# def delete_user():
#     try:
#         data = json.loads(request.data)
#         for key in ['id']:
#             if key not in data.keys():
#                 return Response(json.dumps({
#                     'Error': "Missing parameter '" + key + "'"
#                 }), status=402)

#         user = api.models.studentUsers.query.filter_by(id=data['id']).first()
#         if user:
#             db.session.delete(user)
#             db.session.commit()
#             user = api.models.studentUsers.query.filter_by(id=data['id']).first()
#             if user:
#                 return Response(json.dumps({"Error":'User deletion failed'}),status=400)
#             else:
#                 return Response(json.dumps({"Message":'User deleted successfully'}),status=200)

#         else: 
#             return Response(json.dumps({"Error":'User not found'}),status=400)

#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)
    
# @student_users_controller.route("/v1/update/student_user", methods=['POST'])
# def update_user():
#     try:
#         data = json.loads(request.data)
#         for key in ['id','user_group','status']:
#             if key not in data.keys():
#                 return Response(json.dumps({
#                     'Error': "Missing parameter '" + key + "'"
#                 }), status=402)

#         user = api.models.studentUsers.query.filter_by(id=data['id']).first()       
#         if user:   
           
#             if 'user_group' in data.keys():
#                 user.user_group=data['user_group']
#             if 'status' in data.keys():
#                 user.status=data['status']
      
                    
#             db.session.commit()
#             db.session.refresh(user)
#             user = api.models.studentUsers.query.filter_by(id=data['id']).first()
#             if user:
#                 return Response(json.dumps({
#                     'Message': "Successfully updated"
#                 }), status=200)   
         

#         else: 
#             return Response(json.dumps({"Error":'User not found'}),status=400)

#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)

# @student_users_controller.route("/v1/check_student", methods=['POST'])
# def check_user():
#     try:
#         data = json.loads(request.data)
#         for key in ['user_name']:
#             if key not in data.keys():
#                 return Response(json.dumps({
#                     'Error': "Missing parameter '" + key + "'"
#                 }), status=402)

#         user = api.models.studentUsers.query.filter_by(user_name=data['user_name']).first()
#         if user:            
#             return Response(json.dumps({"Message":'User Found'}),status=200)

#         else: 
#             return Response(json.dumps({"Error":'User not found'}),status=400)

#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)
# @student_users_controller.route("/v1/rest_password/student_users", methods=['POST'])
# def reset_password():
#     try:
#         data = json.loads(request.data)
#         for key in ['user_name','password']:
#             if key not in data.keys():
#                 return Response(json.dumps({
#                     'Error': "Missing parameter '" + key + "'"
#                 }), status=402)
        
#         user = api.models.studentUsers.query.filter_by(user_name=data['user_name']).first()       
#         if user:   
#             key = Fernet.generate_key()
#             encoded_message = str(data['password']).encode()
#             f = Fernet(key)        
#             encrypted_message = f.encrypt(encoded_message)
#             if 'password' in data.keys():
#                 user.password=encrypted_message            
#                 print(key)               
#                 user.key=key   
                    
#             db.session.commit()
#             db.session.refresh(user)
#             user = api.models.studentUsers.query.filter_by(user_name=data['user_name']).first()
#             if user:
#                 return Response(json.dumps({
#                     'Message': "Password Changed Sucessfully"
#                 }), status=200) 
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)
    
# @student_users_controller.route("/v1/forgot_password/student_users", methods=['POST'])
# def forgot_password():
#     try:
#         host = os.environ.get('APP_RABBITMQ_HOST')
#         data = json.loads(request.data)
#         for key in ['email']:
#             if key not in data.keys():
#                 return Response(json.dumps({
#                     'Error': "Missing parameter '" + key + "'"
#                 }), status=402)
        
#         user = api.models.studentUsers.query.filter_by(email_id=data['email']).first()       
#         if user:
#             sender = 'support@securitycentric.net'
#             receivers = [data['email']]
#             SUBJECT = "Forgot Password"
#             TEXT = "Reset your password with User Name:"+user.user_name +", link to access: http://"+host+":3000/reset-password"
#             message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
                        

#             try:
#                 smtpObj = smtplib.SMTP('127.0.0.1')
#                 smtpObj.sendmail(sender, receivers, message)                 
                    
#             except SMTPException:
#                 print("Error: unable to send email")
                
#             return Response(json.dumps({'Message': "Check your mail inbox"}), status=200)            


#         else: 
#             return Response(json.dumps({"Error":'Email id not found'}),status=400)    
            
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)