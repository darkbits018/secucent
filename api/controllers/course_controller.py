from flask import Blueprint, request, Response, send_file
from paramiko import sftp
from flask_cors import CORS
import api.models
from api.helpers.raise_exception import raiseException
import json
import mysql.connector
from sshtunnel import SSHTunnelForwarder
from api import db
import time
import os
import pika
import paramiko
from datetime import datetime
from cryptography.fernet import Fernet
import os
from pathlib import Path
from api.helpers import verify_jwt


course_controller = Blueprint('course_controller', __name__)
CORS(course_controller)

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

def enqueue_credentials(data):
#    try:    
    # log = api.models.SCLogs({
    #     "log": 'basic_publish /v1/delete/course'})
    # db.session.add(log)
    # db.session.commit()      
    print("inside Enque")
    user=os.environ.get('APP_RABBITMQ_USER')
    password=os.environ.get('APP_RABBITMQ_PASSWORD')
    host=os.environ.get('APP_RABBITMQ_HOST')
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(pika.ConnectionParameters( credentials=credentials, host=host))
    try:
        channel = connection.channel()
        channel.queue_declare(queue='scia_queue')        
        channel.basic_publish(exchange='', routing_key='scia_queue', body=str(data))
        connection.close()
    except Exception as e:
        connection.close()
        print(e)
        

@course_controller.route("/v1/register/course", methods=['POST'])
def register():
    try:

        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name') if vendor_id is not None else request.values['vendor_name']
        log = api.models.SCLogs({
            "log": "/v1/register/course 65   " +  str(decoded_token)})
        db.session.add(log)
        db.session.commit() 
        print("Reached")
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')   
        print(guac_host2)
        file = request.files['directory']
        fn = file.filename
        course_name = request.values['name']     
        description = request.values['description']
        chat_room=request.values['chat_room']
        duration = request.values['duration']
        edx = request.values['edx']
        course_series_start = request.values['startCourseSeries']
        course_series_end = request.values['endCourseSeries']
        user_id = request.values['user_id'] 
        static_file = request.values['static_file']        
        log = api.models.SCLogs({
            "log": "/v1/register/course 84   " +  str(vendor_name)})
        db.session.add(log)
        db.session.commit() 
        vendor = api.models.Users.query.filter_by(name=str(vendor_name)).first()    
        log = api.models.SCLogs({
            "log": "/v1/register/course 84   " +  str(vendor_name)})
        db.session.add(log)
        db.session.commit() 
        v_n = vendor.username         
        
        course_name = str(course_name).replace(" ","_") 
               
        new_course = api.models.Courses({
            'course_name':course_name,
            'course_description':description,
            'course_duration':duration,
            'vendor_name':vendor_name,
            'static_file':static_file,
            'course_activation':1,
            'course_series_start':course_series_start,
            'course_series_end':course_series_end,         
            'course_user_id':user_id,
	    'chat_room':chat_room
           
        })
        db.session.add(new_course)
        db.session.commit()
        db.session.refresh(new_course)
        log = api.models.SCLogs({
            "log": "/v1/register/course line 90   " })
        db.session.add(log)
        db.session.commit() 
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()
        log = api.models.SCLogs({
            "log": "/v1/register/course line 97   "})
        db.session.add(log)
        db.session.commit() 
        stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/"+v_n+"/Courses/"+course_name+"")
        result = stdout.readline()
        log = api.models.SCLogs({
            "log": "/v1/register/ line 104   " + str(result)})
        db.session.add(log)
        db.session.commit() 
        print("Error......................", stderr.read()) 
        log = api.models.SCLogs({
            "log": "/v1/register/ line 109   " + str(stderr.read())})
        db.session.add(log)
        db.session.commit()   
        sftp_client.putfo(file,"/Guides/vendors/"+v_n+"/Courses/"+course_name+"/"+fn)         
        log = api.models.SCLogs({
            "log": "/v1/register/ course line 114   "})
        db.session.add(log)
        db.session.commit()     
        stdin, stdout, stderr =ssh.exec_command("unzip -o -d /Guides/vendors/"+v_n+"/Courses/"+course_name+" /Guides/vendors/"+v_n+"/Courses/"+course_name+"/"+fn)
        result = stdout.readline()
        log = api.models.SCLogs({
            "log": "/v1/register/ course line 117   " + str(result)})
        db.session.add(log)
        db.session.commit()  
        print("Error......................", stderr.read())        
        log = api.models.SCLogs({
            "log": "/v1/register/ course line 121   " + str(stderr.read())})
        db.session.add(log)
        db.session.commit() 
        sftp_client.close()   
        ssh.close()  
            
        course = api.models.Courses.query.filter_by(course_name=str(course_name)).first()
        if course:
            return Response(json.dumps({
                    'Message': "Course registration successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Course creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
            "log": "/v1/register/ course line 141   " + str(e)})
        db.session.add(log)
        db.session.commit() 
        sftp_client.close()      
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/register/inactive-course", methods=['POST'])
def registerInactiveCourse():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
        required_fields = ['name', 'description','duration','edx','startCourseSeries','endCourseSeries','user_id','iframeActivate']
        if vendor_id is None:
            required_fields = ['vendor_name', 'name', 'description','duration','edx','startCourseSeries','endCourseSeries','user_id','iframeActivate']
        for key in required_fields:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        vendor_name = vendor_name if vendor_id is not None else data['vendor_name']    
        if data['startCourseSeries'] != '' and  data['endCourseSeries'] != '':
            if int(data['startCourseSeries']) > int(data['endCourseSeries']):
                return Response(json.dumps({
                        'Error': "Invalid start and end '" + key + "'"
                    }), status=402)
            
        course_name = str(data['name']).replace(" ","_") 
        
        if len(course_name.split(' ')) is not 1:
            return Response(json.dumps({
                    'Error': "Course name should not contain spaces"
                }), status=400)
        guide_activation = ''
        if data['iframeActivate'] == 1:
            guide_activation = 1
        else:
            guide_activation = 0       
        vendor = api.models.Users.query.filter_by(name=str(vendor_name)).first()    
        v_n = vendor.username      
        new_course = api.models.Courses({
            'course_name':course_name,
            'course_description':data['description'],
            'course_duration':data['duration'],
            'vendor_name': vendor_name,
            'course_activation':guide_activation,
            'static_file':data['static_file'],
            'course_series_start':data['startCourseSeries'],
            'course_series_end':data['endCourseSeries'],
            'course_user_id':data['user_id'],
	    'chat_room':data['chat_room']
        })
        db.session.add(new_course)
        db.session.commit()
        db.session.refresh(new_course)
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY') 
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()
        stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/"+v_n+"/Courses/"+course_name+"")
        stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/"+v_n+"/Courses/"+course_name+"/images")
        result = stdout.readline()
        stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/"+v_n+"/Courses/"+course_name+"/videos")
        result = stdout.readline()
        
        print("Error......................", stderr.read()) 
          
        sftp_client.close()   
        ssh.close()      
        
        course = api.models.Courses.query.filter_by(course_name=str(course_name)).first()
        if course:
            return Response(json.dumps({
                    'Message': "Course registration successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Course creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)    
    finally:
        db.session.close()

@course_controller.route("/v1/list/course", methods=['GET'])
def get_courses():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        courses = None
        if vendor_id is None:
            courses = api.models.Courses.query.all()
        else:
            courses = api.models.Courses.query.filter_by(vendor_name=vendor_name)
        log = api.models.SCLogs({
            "log": '/v1/list/course 271 ' + str(courses)
            })
        db.session.add(log)
        db.session.commit()    
        result=[]
        temp=''
        if courses:
            for data in courses:
                if data.course_series_start == '':
                    temp = False
                else:
                    temp = True    
                result.append({
                    'created_at':str(data.created_at),
                    'course_name': data.course_name,
                    'course_description':data.course_description,
                    'duration':data.course_duration,
                    'vendor_name':data.vendor_name,
                    'course_activation':data.course_activation,
                    'course_series_start':data.course_series_start,
                    'course_series_end':data.course_series_end,
                    'edx_status':temp,
                    'guide_type':data.static_file,
                    'user_id':data.course_user_id,
        		    'chat_room':data.chat_room              
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/update/course", methods=['POST'])
def update_courses():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')    
             
        file = request.files['directory']
        fn = file.filename
        
        course_name = request.values['course_name']     
        description = request.values['description']
        duration = request.values['duration']
        v_n = decoded_token.get('vendor_name') if vendor_id else request.values['vendor_name']
        course_series_start = request.values['course_series_start']
        course_series_end = request.values['course_series_end']
        static_file = request.values['static_file']
        chat_room=request.values['chat_room']
        print(course_name)
        course = api.models.Courses.query.filter_by(course_name=course_name).first()
        if course:
            course.course_description=description
            course.course_duration = duration               
            course.course_series_start = course_series_start
            course.course_series_end = course_series_end
            course.static_file = static_file
            course.chat_room=chat_room
            course.course_activation = 1         
            db.session.commit()
            db.session.refresh(course)
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
            sftp_client = ssh.open_sftp()
            
            stdin, stdout, stderr =ssh.exec_command("rm -r -f /Guides/vendors/"+v_n+"/Courses/"+course_name+"")
            result = stdout.readline()
            
            stdin, stdout, stderr =ssh.exec_command("mkdir /Guides/vendors/"+v_n+"/Courses/"+course_name+"")
            result = stdout.readline()
            
            print("Error......................", stderr.read()) 
            sftp_client.putfo(file,"/Guides/vendors/"+v_n+"/Courses/"+course_name+"/"+fn)         
            
                
            stdin, stdout, stderr =ssh.exec_command("unzip -o -d /Guides/vendors/"+v_n+"/Courses/"+course_name+" /Guides/vendors/"+v_n+"/Courses/"+course_name+"/"+fn)
            result = stdout.readline()
            
            print("Error......................", stderr.read())        
            sftp_client.close()          
             
              
            print('done')
            ssh.close()
            
            course = api.models.Courses.query.filter_by(course_name=course_name).first()
            if course:
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

@course_controller.route("/v1/upload/logo", methods=['POST'])
def upload_guide_logo():
    try:
        
        # guac_user=os.environ.get('APP_GUAC_USER')
        # guac_password=os.environ.get('APP_GUAC_PASSWORD')
        # guac_host1=os.environ.get('APP_GUAC_HOST')
        # guac_host2=os.environ.get('APP_GUAC_HOST2')           
        # pwd  = os.environ.get('XE_PASSWORD_KEY')           
        file = request.files['file']
        fn = file.filename
        file.save('/home/cara/autoprov1.2/git/Provisioner_v1.2/securitycentric_api/uploads/syllabus/images' + fn)
        # ssh = paramiko.SSHClient()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        # ssh.connect(hostname=guac_host1,username=guac_user, password=guac_password, port=22)
        # sftp_client = ssh.open_sftp()        
        # sftp_client.putfo(file,"/syllabus/images/"+fn)   
        # sftp_client.close()         
        # print('done')
        # ssh.close()          
        return Response(json.dumps({
                    'Message': "Successfully updated",'filename':fn
                }), status=200)
        
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/logo/<file_name>", methods=['GET'])
def download_guide_logo(file_name):
    try:
        if file_name is None:
            return Response(json.dumps({
                    'Message': "Invalid file name"
                }), status=400)
        return send_file('/home/cara/autoprov1.2/git/Provisioner_v1.2/securitycentric_api/uploads/syllabus/images'+ file_name,as_attachment=True)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/download/<file_name>", methods=['GET'])
def download_guide_media(file_name):
    try:
        data = json.loads(request.data)        
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')         
        path = data['filepath']  
        temp=path.split("/")
        localpath=str(Path.home())   
        print("localpath is",localpath)      
        testpath=''+localpath+'\\'+temp[-1]+''
        dummypath=localpath.replace(":","_")
        filename=temp[-1].replace(":", "")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname=guac_host1 ,username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()  
        sftp_client.get(path,''+localpath+'/'+filename+'')        
        sftp_client.close()     
        ssh.close()        
        return Response(json.dumps({
                    'Message': "Downloaded Successfully",
                    
                }), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/upload/guide_image", methods=['POST'])
def upload_guide():
    try:
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')    
       
        file = request.files['file']
        fn = file.filename
        
        course_name = request.values['course_name']    
       
        v_n = request.values['vendor_name']
        
        course = api.models.Courses.query.filter_by(course_name=course_name).first()
        if course:           
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
            sftp_client = ssh.open_sftp()        
            url = 'https://scig-v2.securitycentric.net' + "/guides/"+v_n+"/Courses/"+course_name+"/images/"+ str(round(time.time()*1000)) + '_' + fn
            sftp_client.putfo(file,"/Guides/vendors/"+v_n+"/Courses/"+course_name+"/images/"+ str(round(time.time()*1000)) + '_' + fn)   
            sftp_client.close()         
            ssh.close()            
            course = api.models.Courses.query.filter_by(course_name=course_name).first()
            if course:
                return Response(json.dumps({
                    'Message': "Successfully updated",'filename':fn, 'url': url
                }), status=200)
        else: 
            return Response(json.dumps({"Error":'Lab guide not updated'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/upload/guide_video", methods=['POST'])
def upload_guide_video():
    try:
        print(request.values['course_name'])
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')    
       
        file = request.files['file']
        fn = file.filename
        
        course_name = request.values['course_name']    
       
        v_n = request.values['vendor_name']
        print(fn,v_n,course_name)
        
        course = api.models.Courses.query.filter_by(course_name=course_name).first()
        if course:           
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
            sftp_client = ssh.open_sftp()        
            url ='https://scig-v2.securitycentric.net' + "/guides/"+v_n+"/Courses/"+course_name+"/videos/"+str(round(time.time()*1000)) + '_' + fn;
            sftp_client.putfo(file,"/Guides/vendors/"+v_n+"/Courses/"+course_name+"/videos/"+str(round(time.time()*1000)) + '_' + fn)   
            sftp_client.close()         
            print('done')
            ssh.close()            
            course = api.models.Courses.query.filter_by(course_name=course_name).first()
            if course:
                return Response(json.dumps({
                    'Message': "Successfully updated"
                    ,'filename':fn, 'url': url
                }), status=200)
        
        else: 
            return Response(json.dumps({"Error":'Lab guide not updated'}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    
    
@course_controller.route("/v1/update/inactive_course", methods=['POST'])
def update_inactiveCourses():
    try:
        decoded_token = handle_token()
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)
      
        for key in ['course_name', 'course_description','duration','edx','course_series_start','course_series_end','static_file','iframeActivate']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        if data['edx'] == True:        
            if int(data['course_series_start']) > int(data['course_series_end']):
                return Response(json.dumps({
                        'Error': "Invalid start and end '" + key + "'"
                    }), status=402)
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=data['course_name'],vendor_name=vendor_name).all()
            if not course:
                return Response(json.dumps({
                    'Error': "You are not allowed to update this course"
                }), status=400)
                    
        course = api.models.Courses.query.filter_by(course_name=data['course_name']).first()
        guide_activation = ''
        if data['iframeActivate'] == 0:
            guide_activation = 0
        else:
            guide_activation = 1
        if course:
            if 'course_description' in data.keys():
                course.course_description=data['course_description']
                course.course_duration = data['duration']        
                course.static_file = data['static_file']                
                course.course_activation = guide_activation                 
                course.course_series_start = str(data['course_series_start'])
                course.course_series_end = str(data['course_series_end'])
                course.chat_room=data['chat_room']
            db.session.commit()
            db.session.refresh(course)
            course = api.models.Courses.query.filter_by(course_name=data['course_name']).first()
            if course:
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

@course_controller.route("/v1/delete/course", methods=['POST'])
def delete_courses():
    try:
        decoded_token = handle_token()
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')  
        data = json.loads(request.data)
        
        for key in ['course_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=data['course_name'],vendor_name=vendor_name).all()
            if not course:
                return Response(json.dumps({
                    'Error': "You are not allowed to delete this course"
                }), status=400)
        course = api.models.Courses.query.filter_by(course_name=data['course_name']).first()
        
            
        reg_course = api.models.UserCourse.query.filter_by(course_name=data['course_name']).all()
        
        
        if reg_course:
            return Response(json.dumps({
                    'Error': "Delete active labs linked with this course"
                }), status=400)
        if course:
            ven_name = course.vendor_name
            
            db.session.delete(course)
            db.session.commit()
            guac_user=os.environ.get('APP_GUAC_USER')
            guac_password=os.environ.get('APP_GUAC_PASSWORD')
            guac_host1=os.environ.get('APP_GUAC_HOST')
            guac_host2=os.environ.get('APP_GUAC_HOST2')           
            pwd  = os.environ.get('XE_PASSWORD_KEY') 
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
            sftp_client = ssh.open_sftp()
                    
            stdin, stdout, stderr =ssh.exec_command("rm -r -f /Guides/vendors/"+ven_name+"/Courses/"+data['course_name']+"")
            result = stdout.readline()
            sftp_client.close() 
            print('done')
            ssh.close()
            if course.course_activation == 1:
                
                enqueue_credentials({
                        'key':'course','operation':'delete','path':ven_name,'directory_name':data['course_name'],'vm_name':'1.Guacamole_1.2.0-Development','user':'cara','host1': guac_host1,'host2':guac_host2, 'password_xe': pwd}) 
            course_verify = api.models.Courses.query.filter_by(course_name=data['course_name']).first()
            if course_verify:
                return Response(json.dumps({"Error":'Course deletion failed'}),status=400)
            else:
                return Response(json.dumps({"Message":'Course deleted successfully'}),status=200)

        else: 
            return Response(json.dumps({"Error":'Course not found'}),status=400)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/get_vendor/course", methods=['POST'])
def get_vendors_courses():
    try:
        decoded_token = handle_token()
        vendor_id = decoded_token.get('vendor_id')
        data = json.loads(request.data)
        print(data)
        for key in ['vendor_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        vendor_name = decoded_token.get('vendor_name') if vendor_id else data['vendor_name']
        courses = api.models.Courses.query.filter_by(vendor_name=vendor_name).all()
        
        result=[]
        if courses:
            for data in courses:
                result.append({
                    'created_at':str(data.created_at),
                    'course_name': data.course_name,
                    'course_description':data.course_description,
                    'duration':data.course_duration,
                    'vendor_name':data.vendor_name,
                    'user_id':data.course_user_id
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/vendor/courses", methods=['POST'])
def get_vendors_courses_by_coursenames():
    try:
        data = json.loads(request.data)
        print(data)
        for key in ['vendor_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        courses = api.models.Courses.query.filter(api.models.Courses.vendor_name==data['vendor_name'],api.models.Courses.in_(data['courses'])).all()
        
        result=[]
        if courses:
            for data in courses:
                result.append({
                    'created_at':str(data.created_at),
                    'course_name': data.course_name,
                    'course_description':data.course_description,
                    'duration':data.course_duration,
                    'vendor_name':data.vendor_name,
                    'user_id':data.course_user_id
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/instructor_recording", methods=['POST'])
def upload_session():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=request.values['course_name'],vendor_name=vendor_name).first()
            if not course:
                return Response(json.dumps({
                    'Error': "Recording not allowed to be placed"
                }), status=403)
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')   
        
        file = request.files['directory']
        fn = file.filename
        course_name = request.values['course_name']
        # v_n = request.values['vendor_name']
                
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()  
        
        stdin, stdout, stderr =ssh.exec_command("mkdir /recordings/"+course_name)
        result = stdout.readline()
        
        print("Error......................", stderr.read()) 
        sftp_client.putfo(file,"/recordings/"+course_name+"/"+fn)           
        
        
           
        sftp_client.close()   
        ssh.close()       
        return Response(json.dumps({
                    'Message': "Session uploaded successful"
                }), status=200)
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/replace/session_recording", methods=['POST'])
def replace_session():
    print("hi")
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        course_names = None
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=request.values['course_name'],vendor_name=vendor_name).first()
            if not course:
                return Response(json.dumps({
                    'Error': "Recording not allowed to be placed"
                }), status=403)
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')   
        
        file = request.files['directory']
        fn = file.filename
        course_name = request.values['course_name']
        filepath = request.values['filepath']     
        # return Response(json.dumps({
        #             'Message': "Playlist",
        #             'files':["https://scig-v2.securitycentric.net/recordings/test.mp4"]
        #         }), status=200)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()       
        stdin, stdout, stderr =ssh.exec_command("rm -f "+filepath)
        sftp_client.putfo(file,"/recordings/"+course_name+"/"+fn)    
        sftp_client.close()   
        ssh.close()               
        return Response(json.dumps({
                    'Message': "Session uploaded successful"
                }), status=200)
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()


@course_controller.route("/v1/preview_recording", methods=['POST'])
def preview_session():
    
    try:
        
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')     
        
        course_name = request.values['course_name']
        if course_name == 'course-v1:SCI-ParFor':
            course_name = 'course-v1:SCI-ParFor+'        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp() 

        stdin, stdout, stderr =ssh.exec_command("ls  /recordings/"+course_name)
        result = stdout.read()
        result = result.decode("utf-8")
        result= str(result).replace('\n',' ').split(' ')       
        files=[]
        if len(result) > 1:
            for r in result:
                temp = 'https://scig-v2.securitycentric.net/recordings/'+course_name+'/'+r
                files.append(temp)
            return Response(json.dumps({
                    'Message': "Playlist",
                    'files':files
                }), status=200)
        else:
            return Response(json.dumps({
                    'Message': "No playlist"
                }), status=200)

      
        sftp_client.close()   
        ssh.close()       
        
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list_recording", methods=['GET'])
def list_session():
    
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        course_names = None
        if vendor_id:
            course_names = api.models.Courses.query.with_entities(api.models.Courses.course_name).filter_by(vendor_name=vendor_name).all()
            course_names = [course[0] for course in course_names]
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')     
        
        
        
        # return Response(json.dumps({
        #             'Message': "Playlist",
        #             'files':["https://scig-v2.securitycentric.net/recordings/test.mp4"]
        #         }), status=200)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()       
        stdin, stdout, stderr =ssh.exec_command("find /recordings -type f -name '*.mp4' ")
        
        result = stdout.read()
        result = result.decode("utf-8")
        result= str(result).replace('\n',' ').split(' ')
        # stdin, stdout, stderr =ssh.exec_command("find /Guides -type f -size '*.mp4' ")
        
        
        files=[]
        if result is not None:
            for r in result:
                print(r)
                log = api.models.SCLogs({
                    "log": ' error in list_recording 837: ' + str(r)
                    })
                db.session.add(log)
                db.session.commit()   
                if r != '':
                    stdin, stdout, stderr =ssh.exec_command("du -h "+r)        
                    size = stdout.read()  
                    print(size)   
                    log = api.models.SCLogs({
                        "log": ' error in list_recording 847: ' + str(size)
                        })
                    db.session.add(log)
                    db.session.commit()                                           
                    size = size.decode("utf-8")
                    log = api.models.SCLogs({
                        "log": ' error in list_recording 853: ' + str(size)
                        })
                    db.session.add(log)
                    db.session.commit()   
                    size = str(size).replace('\t',' ').split(' ')[0]                    
                    file_name = str(r).split('/')[-1]
                    course_name = str(r).split('/')[-2]
                    if course_name not in course_names:
                        continue
                    temp = {'file_name':file_name,'course_name':course_name,'size':size,'fullpath':r}
                    log = api.models.SCLogs({
                        "log": ' error in list_recording 847: ' + str(temp)
                        })
                    db.session.add(log)
                    db.session.commit()                       
                    files.append(temp)
            return Response(json.dumps({
                    'Message': "Playlist",
                    'data':files
                }), status=200)
        else:
            return Response(json.dumps({
                    'Message': "No playlist"
                }), status=200)

      
        sftp_client.close()   
        ssh.close()       
        
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    
    
@course_controller.route("/v1/delete/session_recording", methods=['POST'])
def delete_recording():    
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        data = json.loads(request.data)        
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=data['course_name'],vendor_name=vendor_name).first()
            if not course:
                return Response(json.dumps({
                    'Error': "Recording not allowed to be placed"
                }), status=403)
            log = api.models.SCLogs({
                        "log": ' /v1/delete/session_recording belongs to vendor: ' + str(course)
                        })
            db.session.add(log)
            db.session.commit()  
        # guac_password=os.environ.get('APP_GUAC_PASSWORD')
        # guac_host1=os.environ.get('APP_GUAC_HOST')
        # guac_host2=os.environ.get('APP_GUAC_HOST2')           
        # pwd  = os.environ.get('XE_PASSWORD_KEY')         
        path = data['filepath']  
        print("rm -f "+path)     
        log = api.models.SCLogs({
                    "log": ' /v1/delete/session_recording path ' + str(path)
                    })
        db.session.add(log)
        db.session.commit()   
        # return Response(json.dumps({
        #             'Message': "Playlist",
        #             'files':["https://scig-v2.securitycentric.net/recordings/test.mp4"]
        #         }), status=200)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        log = api.models.SCLogs({
                    "log": ' /v1/delete/session_recording ssh connect ' + str(course)
                    })
        db.session.add(log)
        db.session.commit()  
        sftp_client = ssh.open_sftp()       
        ssh.exec_command("rm -f "+path)
        log = api.models.SCLogs({"log": ' /v1/delete/session_recording deleted '})
        db.session.add(log)
        db.session.commit()    
        sftp_client.close()   
        ssh.close()        
        return Response(json.dumps({
                    'Message': "Deleted Successfully",
                }), status=200)  
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        log = api.models.SCLogs({
                    "log": ' /v1/delete/session_recording error ' + str(e)
                    })
        db.session.add(log)
        db.session.commit()    
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/download/session_recording", methods=['POST'])
def download_recording():    
    try:
        data = json.loads(request.data)        
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')         
        path = data['filepath']  
        temp=path.split("/")
        localpath=str(Path.home())   
        print("localpath is",localpath)      
        testpath=''+localpath+'\\'+temp[-1]+''
        dummypath=localpath.replace(":","_")
        filename=temp[-1].replace(":", "")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname='172.20.9.50',username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()  
        sftp_client.get(path,''+localpath+'/'+filename+'')        
        sftp_client.close()     
        ssh.close()        
        return Response(json.dumps({
                    'Message': "Downloaded Successfully",
                    
                }), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/publish/lab_guide", methods=['POST'])
def publishCourseGuide():
    try:
        data = json.loads(request.data)     
        for key in ['course_name', 'guide', 'vendor_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        
        new_guide = api.models.Guides({
            'course_name':data['course_name'],
            'guide_data':data['guide'],
            'username':data['vendor_name'],
            'vendor_name':data['vendor_name']
        })
        db.session.add(new_guide)
        db.session.commit()
        db.session.refresh(new_guide)      
        
        guide = api.models.Guides.query.filter_by(username=str(data['vendor_name']),course_name=str(data['course_name'])).first()
        if guide:
            return Response(json.dumps({
                    'Message': "Guide published successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Guide creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/copy/lab_guide", methods=['POST'])
def copyCourseGuide():
    try:
        data = json.loads(request.data)
        for key in ['source_vendor', 'source_course', 'destination_vendor', 'destination_course']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)

        guide = api.models.Guides.query.filter_by(username=str(data['source_vendor']),course_name=str(data['source_course'])).first()

        if not guide:
            return Response(json.dumps({
                'Error': "Guide not found for source course"
            }), status=400)

        existing_guide = api.models.Guides.query.filter_by(username=str(data['destination_vendor']),course_name=str(data['destination_course'])).first()

        if not existing_guide:
            new_guide = api.models.Guides({
            'vendor_name': data['destination_vendor'],
            'course_name': data['destination_course'],
            'guide_data': guide.guide_data,
            'username': data['destination_vendor']
            })
            db.session.add(new_guide)
            db.session.commit()
            db.session.refresh(new_guide)
        else:
            existing_guide.guide_data = guide.guide_data
            db.session.commit()
            
        updated_guide = api.models.Guides.query.filter_by(username=str(data['destination_vendor']),course_name=str(data['destination_course'])).first()

        if not updated_guide:
            return Response(json.dumps({
                'Error': 'Guide copy failed'
            }), status=400)
        
        return Response(json.dumps({
                'Message': "Guide copy successful"
            }), status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list/guides", methods=['GET'])
def get_guides():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        guide = api.models.Guides.query.all()
        result=[]      
        if guide:
            for data in guide:
                if vendor_id and vendor_name != data.vendor_name:
                    continue
                result.append({
                    'id':data.id,
                    'guide_data':data.guide_data,
                    'created_at':str(data.created_at),
                    'vendor_name': data.vendor_name,
                    'course_name': data.course_name
                })                 
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list/guide", methods=['POST'])
def get_guide():
    try:
        data = json.loads(request.data)
        print(data['course_name'])
        guide = api.models.Guides.query.filter_by(course_name=data['course_name']).first()    
        print(guide)    
        if guide:       
            return Response(json.dumps({"data":guide.guide_data}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/delete/guide", methods=['POST'])
def delete_guide():
    try:
        data = json.loads(request.data)
        guide = api.models.Guides.query.filter_by(id=int(data['id'])).first()        
        if guide:  
            db.session.delete(guide)
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/update/guide", methods=['POST'])
def update_guide():
    try:
        data = json.loads(request.data)
        guide = api.models.Guides.query.filter_by(id=int(data['id'])).first()        
        if guide: 
             
            guide.guide_data = data['guide']
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/course/calander_api", methods=['POST'])
def get_calander_api():
    try:
        data = json.loads(request.data)
        course = api.models.Courses.query.filter_by(course_name=data['course_name']).first()        
        if course:       
            return Response(json.dumps({"data":course.api_key,"data2":course.calanders}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()


@course_controller.route("/v1/publish/coursedetails", methods=['POST'])
def publishCourseDetails():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')
        curriculumdata=" "
        data = json.loads(request.data)
        for key in ['course_name', 'syllabus']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        
        syllabus=data['syllabus']
        curriculum=data['curriculum']
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=data['course_name'],vendor_name=vendor_name).first()
            if not course:
                return Response(json.dumps({
                    'Error': "Your are not allowed to modify the details"
                        }), status=403)
        if  syllabus:
            dbdata = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()  
            if dbdata:       
                new_syllabus = api.models.CourseDetails({                  
                    'course_name':data['course_name'],
                    'syllabus_data':data['syllabus'],
                    'curriculum_data':dbdata.curriculum_data
                     })
                db.session.add(new_syllabus)
                db.session.commit()
                db.session.refresh(new_syllabus)   
                syllabus = api.models.CourseDetails.query.filter_by(course_name=str(data['course_name'])).first()
                if syllabus:
                    return Response(json.dumps({
                        'Message': "Syllabus published successful"
                        }), status=200)
                else:
                    return Response(json.dumps({
                        'Error': "Syllabus creation failed"
                        }), status=400)
            else:      
                new_syllabus = api.models.CourseDetails({                  
                    'course_name':data['course_name'],
                    'syllabus_data':data['syllabus'],
                    'curriculum_data':None
                     })
                db.session.add(new_syllabus)
                db.session.commit()
                db.session.refresh(new_syllabus)   
                syllabus = api.models.CourseDetails.query.filter_by(course_name=str(data['course_name'])).first()
                if syllabus:
                    return Response(json.dumps({
                        'Message': "Syllabus published successful"
                        }), status=200)
                else:
                    return Response(json.dumps({
                        'Error': "Syllabus creation failed"
                        }), status=400)
        elif curriculum:
            print('curriculm is not emplty')
            dbdata = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()
            if dbdata:
                new_syllabus = api.models.CourseDetails({
                    'course_name':data['course_name'],
                    'syllabus_data':dbdata.syllabus_data,
                    'curriculum_data':data['curriculum']
                    })
                db.session.add(new_syllabus)
                db.session.commit()
                db.session.refresh(new_syllabus)
                syllabus = api.models.CourseDetails.query.filter_by(course_name=str(data['course_name'])).first()
                if syllabus:
                    return Response(json.dumps({
                        'Message': "Syllabus published successful"
                        }), status=200)
                else:
                    return Response(json.dumps({
                    'Error': "Syllabus creation failed"
                        }), status=400)
            else:     
                new_syllabus = api.models.CourseDetails({                  
                    'course_name':data['course_name'],
                    'syllabus_data':None,
                    'curriculum_data':data['curriculum']
                     })
                db.session.add(new_syllabus)
                db.session.commit()
                db.session.refresh(new_syllabus)   
                syllabus = api.models.CourseDetails.query.filter_by(course_name=str(data['course_name'])).first()
                if syllabus:
                    return Response(json.dumps({
                        'Message': "Syllabus published successful"
                        }), status=200)
                else:
                    return Response(json.dumps({
                        'Error': "Syllabus creation failed"
                        }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list/coursedetails", methods=['POST'])
def getcoursedetails_data():
    try:
        data = json.loads(request.data)
        syllabus = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()    
        if syllabus:       
            return Response(json.dumps({"data":syllabus.syllabus_data}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
# @course_controller.route("/v1/list/curriculum", methods=['POST'])
# def getcurriculum_data():
#     try:
#         data = json.loads(request.data)
#         print("selectedcourseName",data['course_name'])
#         curriculum = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()    
#         print(curriculum.curriculum_data)    
#         if curriculum:       
#             return Response(json.dumps({"data":curriculum.curriculum_data}),status=200)
#         else:
#             return Response(json.dumps({"Message":"No Data"}),status=400)
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)

@course_controller.route("/v1/update/coursedetails", methods=['POST'])
def update_coursedetails():
    try:
        data = json.loads(request.data)
        syllabus = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()         
        if syllabus: 
            syllabus.syllabus_data = data['syllabus']
            db.session.commit()     
            return Response(json.dumps({"Message":"Success"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
# @course_controller.route("/v1/update/curriculum", methods=['POST'])
# def update_curriculum():
#     try:
#         data = json.loads(request.data)
#         print("selectedcourseName",data['course_name'])
#         print("passed curriculum data", data['curriculum'])
#         curriculum = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()         
#         if curriculum: 
#             print(curriculum.curriculum_data) 
#             curriculum.curriculum_data = data['curriculum']
#             db.session.commit()     
#             return Response(json.dumps({"Message":"Success"}),status=200)
#         else:
#             return Response(json.dumps({"Message":"No Data"}),status=400)
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)
@course_controller.route("/v1/delete/syllabus", methods=['POST'])
def delete_syllabus():
    try:
        data = json.loads(request.data)
        syllabus = api.models.CourseDetails.query.filter_by(course_name=data['course_name']).first()  
       
        if syllabus:  
            db.session.delete(syllabus)
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/upload/curriculum_image", methods=['POST'])
def upload_coursedetailsfiles():
    try:  
        destination= request.values['filetype'] 
        print(request.values['filetype'])
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host1=os.environ.get('APP_GUAC_HOST')
        guac_host2=os.environ.get('APP_GUAC_HOST2')           
        pwd  = os.environ.get('XE_PASSWORD_KEY')    
        file = request.files['file']
        # filetype= request.files['filetype']
        # print(filetype)
        fn = file.filename
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
        sftp_client = ssh.open_sftp()        
        url = 'https://scig-v2.securitycentric.net' + "/syllabus/"+destination+"/"+str(round(time.time()*1000)) + '_' + fn
        sftp_client.putfo(file,"/syllabus/"+destination+"/"+str(round(time.time()*1000)) + '_' + fn)    
        sftp_client.close()         
        ssh.close()          
        return Response(json.dumps({
                    'Message': "Successfully updated",'filename':fn,'url':url
                }), status=200)
        
        
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

# @course_controller.route("/v1/upload/curriculum_video", methods=['POST'])
# def upload_curriculum_video():
#     try:      
#         guac_user=os.environ.get('APP_GUAC_USER')
#         guac_password=os.environ.get('APP_GUAC_PASSWORD')
#         guac_host1=os.environ.get('APP_GUAC_HOST')
#         guac_host2=os.environ.get('APP_GUAC_HOST2')           
#         pwd  = os.environ.get('XE_PASSWORD_KEY')    
#         print("iam executing")
#         file = request.files['file']
#         fn = file.filename
#         ssh = paramiko.SSHClient()
#         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#         ssh.connect(hostname=guac_host1,username="trainee", password="trainee", port=22)
#         sftp_client = ssh.open_sftp()        
#         sftp_client.putfo(file,"/Guides/"+fn)   
#         sftp_client.close()         
#         print('done')
#         ssh.close()          
#         return Response(json.dumps({
#                     'Message': "Successfully updated",'filename':fn
#                 }), status=200)
        
        
#     except Exception as e:
#         if e.__class__.__name__ == "IntegrityError":
#             db.session.rollback()
#         return raiseException(e)

@course_controller.route("/v1/list/quiz", methods=['POST'])
def getQuiz_data():
    try:
        data = json.loads(request.data)
        quiz = api.models.Quizes.query.filter_by(quiz_name=data['quiz_name']).first()    
        if quiz:       
            return Response(json.dumps({"data":quiz.quiz_data,"quizname":quiz.quiz_name,"quizid":quiz.id}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/update/quiz", methods=['POST'])
def update_quizData():
    try:
        data = json.loads(request.data)
        quiz = api.models.Quizes.query.filter_by(id=data['quiz_id']).first()         
        if quiz: 
            quiz.quiz_data = data['quiz_data']
            quiz.quiz_name = data['quiz_name']
            db.session.commit()     
            return Response(json.dumps({"Message":"Success"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/publish/quiz", methods=['POST'])
def publishQuizData():
    try:
        decoded_token = handle_token()
        # Access the payload from the decoded token
        vendor_id = decoded_token.get('vendor_id')
        vendor_name = decoded_token.get('vendor_name')      
        if vendor_id:
            course = api.models.Courses.query.filter_by(course_name=data['course_name'],vendor_name=vendor_name).first()
            if not course:
                return Response(json.dumps({
                    'Error': "Your are not allowed to add quiz for this course"
                        }), status=403)
        data = json.loads(request.data)
        for key in ['course_name', 'quiz_data','quiz_name']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=402)
        new_quiz = api.models.Quizes({
            'course_name':data['course_name'],
            'quiz_data':data['quiz_data'],
            'quiz_name':data['quiz_name']
        })
        db.session.add(new_quiz)
        db.session.commit()
        db.session.refresh(new_quiz)      
        quiz = api.models.Quizes.query.filter_by(course_name=str(data['course_name'])).first()
        if quiz:
            return Response(json.dumps({
                    'Message': "Quiz published successful"
                }), status=200)
        else:
            return Response(json.dumps({
                    'Error': "Quiz creation failed"
                }), status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list/quiznames", methods=['POST'])
def getQuiz_names():
    try:
        data = json.loads(request.data)
        quiz = api.models.Quizes.query.filter_by(course_name=data['course_name']).all() 
        print(data['course_name'])
        result=[]
        if quiz:       
            for data in quiz:
                result.append({
                    # 'created_at':str(data.created_at),
                    'course_name': data.course_name,
                    'quiz_name':data.quiz_name,
                    'quiz_id':data.id
                    # 'quiz_data':data.quiz_data,
                    # 'updated_at':data.updated_at
                })
            return Response(json.dumps({"data":result}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/delete/quiz", methods=['POST'])
def delete_quiz():
    try:
        data = json.loads(request.data)
        quiz = api.models.Quizes.query.filter_by(quiz_name=data['quiz_name']).first()  
       
        if quiz:  
            db.session.delete(quiz)
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/copy/guides", methods=['POST'])
def copy_guides():
    try:
        data = json.loads(request.data)
        guide = api.models.Guides.query.all()
        coursename = data['course_name'].split(":")
        coursetype=coursename[1]
        substringone="-"
        substringtwo="+"
        selectedcourse=''
        if substringone in coursetype:
            selectedcourse=coursetype.split("-")
        elif  substringtwo in coursetype:
             print("+ is present")
             selectedcourse=coursetype.split("+")       
        result=[]
        if guide:
            for coursedata in guide:
                dbcoursename = coursedata.course_name.split(":")
                dbcoursename=dbcoursename[1]
                dbsubstringone="-"
                dbsubstringtwo="+"
                dbselectedcourse=''
                if dbsubstringone in dbcoursename:
                    dbselectedcourse=dbcoursename.split("-")
                elif dbsubstringtwo in dbcoursename:
                    dbselectedcourse=dbcoursename.split("+")
                if(selectedcourse[-1]==dbselectedcourse[-1]):
                     result.append({
                    'guide_data':coursedata.guide_data,
                    'course_name': coursedata.course_name
                })      
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()



@course_controller.route("/v1/update/quizscore", methods=['POST'])
def update_quiz_score():
    try:
        data = json.loads(request.data)
        for key in ['student_id','quiz_id','score','quiz_index','quiz_status']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=400)
        quiz = api.models.QuizReports.query.filter_by(quiz_id=int(data['quiz_id']),student_id=int(data['student_id'])).first() 
        if quiz and data['quiz_id']==int(quiz.quiz_id):      
            quiz.quiz_index = data['quiz_index']
            quiz.score = data['score'],
            quiz.quiz_status=data['quiz_status']
            db.session.commit()     
            return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            quiz_score = api.models.QuizReports({
                'student_id':data['student_id'],
                'quiz_id':data['quiz_id'],
                'score':data['score'],
                'quiz_index':data['quiz_index'],
                'quiz_status':data['quiz_status'],
                'total_grade':data['total_grade']
                 })
            db.session.add(quiz_score)
            db.session.commit()
            db.session.refresh(quiz_score) 
            return Response(json.dumps({"data":"Updated successfully"}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list_quiz", methods=['GET'])
def list_quiz():
    try:
        quizdata = api.models.QuizReports.query.all()
        result=[]
        if quizdata:
            for data in quizdata:
                result.append({
                    'student_id':data.student_id,
                    'quiz_id':data.quiz_id,
                    'quiz_status':data.quiz_status             
                })
        return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/end/quiz", methods=['POST'])
def end_quiz():
    try:
        data = json.loads(request.data)

        for key in ['student_id','quiz_id','score','quiz_index','quiz_status','total_grade']:
            if key not in data.keys():
                return Response(json.dumps({
                    'Error': "Missing parameter '" + key + "'"
                }), status=400)
        quiz = api.models.QuizReports.query.filter_by(quiz_id=int(data['quiz_id']),student_id=int(data['student_id'])).first() 
        if quiz and data['quiz_id']==int(quiz.quiz_id):      
                quiz.quiz_index = data['quiz_index']
                quiz.score = data['score']
                db.session.commit()     
                return Response(json.dumps({"Message":"Sucess"}),status=200)
        else:
            print("ELSE")
            quiz_score = api.models.QuizReports({
                'student_id':data['student_id'],
                'quiz_id':data['quiz_id'],
                'score':data['score'],
                'quiz_index':data['quiz_index'],
                'quiz_status':data['quiz_status'],
                'total_grade':data['total_grade']
                 })
            db.session.add(quiz_score)
            db.session.commit()
            db.session.refresh(quiz_score) 
            return Response(json.dumps({"data":"Updated successfully"}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/logs", methods=['POST'])
def getLogs():
    try:
        data = json.loads(request.data)
        if data:
            # f= open("uierrors.log","a")
            # f.write(str(data))
            # f.close()
            return Response(json.dumps({"data":"Updated successfully"}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            log = api.models.SCLogs({
                    "log": ' error in/v1/logs ' + str(e)
                    })
            db.session.add(log)
            db.session.commit()    
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/resume/quiz", methods=['POST'])
def resume_quiz():
    try:
        data = json.loads(request.data)
        quiz = api.models.QuizReports.query.filter_by(quiz_id=data['quiz_id'],student_id=data['student_id']).first()    
        if quiz:       
            return Response(json.dumps({"quiz_status":quiz.quiz_status,"quiz_index":quiz.quiz_index,"quiz_score":quiz.score,"quiz_id":quiz.quiz_id}),status=200)
        else:
            return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/list_student_info", methods=['GET'])
def list_student_info():
    try:
        accescode = api.models.AccessCodes.query.filter_by(user_type=0).all() 
        quizes = api.models.QuizReports.query.all()
        quizCompleted=[]
        quizPending=[]
        studentId = []
        for quiz in quizes:
            if quiz.quiz_status==0:
                quizPending.append(quiz.quiz_status)
            else:
                quizCompleted.append(quiz.quiz_status)
                studentId.append(quiz.student_id)
        
        result=[]
        studentsCount=[]
        if accescode:
            for data in accescode:
                if data.key != 'null' and data.id in studentId:
                    studentsCount.append(data.id) 
                    key = data.key 
                    print(key)
                    f = Fernet(key)
                    encoded_first_name = bytes(data.first_name, 'utf-8')
                    print(encoded_first_name)
                    decrypted_first_name = f.decrypt(encoded_first_name)
                    decrypted_first_name = decrypted_first_name.decode()
                    encoded_last_name = bytes(data.last_name, 'utf-8')
                    decrypted_last_name = f.decrypt(encoded_last_name)
                    decrypted_last_name = decrypted_last_name.decode()      
                    result.append({
                        'first_name':decrypted_first_name,
                        'last_name':decrypted_last_name ,
                        'course_name':data.course_name,
                        'email': data.email,
                        'progress':data.percent,
                        'id':data.id,
                        'students_count':len(studentsCount),  
                        'completed_quiz':len(quizCompleted),
                        'pending_quiz':len(quizPending),
                        'total_quiz':len(quizCompleted)+len(quizPending)
                    })
        
            return Response(json.dumps({"data":result}),status=200)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@course_controller.route("/v1/quiz_report", methods=['POST'])
def quiz_report():
    try:
        data = json.loads(request.data)
        print(data['student_id'])
        print(data['course_name'])
        accesscodes = api.models.AccessCodes.query.filter_by(id=data['student_id']).first()
        quizreports = api.models.QuizReports.query.filter_by(student_id=data['student_id']).all()
       
        result=[]
        for q in quizreports:
            quiz = api.models.Quizes.query.filter_by(id=int(q.quiz_id),course_name=data['course_name']).first()
            if quiz is not None and q.quiz_id == quiz.id:
                quizname=quiz.quiz_name
                key = accesscodes.key               
                f = Fernet(key)
                encoded_first_name = bytes(accesscodes.first_name, 'utf-8')
                encoded_last_name = bytes(accesscodes.last_name, 'utf-8') 
                decrypted_first_name = f.decrypt(encoded_first_name)
                first_name = (decrypted_first_name.decode())

                decrypted_last_name = f.decrypt(encoded_last_name)
                last_name = (decrypted_last_name.decode())
                result.append(
                {
                "quiz_status":q.quiz_status,
                "quiz_score":q.score,
                "quiz_id":q.quiz_id,
                'total_grade':q.total_grade,
                'student_firstname':first_name,
                'student_lastname':last_name,
                'quiz_name':quizname
                })
        print(result) 
        if result:
            return Response(json.dumps({"data":result}),status=200)
        else:
             return Response(json.dumps({"Message":"No Data"}),status=400)
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()    