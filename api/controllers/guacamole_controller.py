import mysql.connector
from sshtunnel import SSHTunnelForwarder
from flask_cors import CORS
from flask import Blueprint, Response
from api.helpers.raise_exception import raiseException
import json
import os
import json
# import urllib
import urllib.request as urllib2
# import sys
# import pandas
import argparse
import requests
from urllib.request import urlopen

guacamole_controller = Blueprint('guacamole_controller', __name__)
CORS(guacamole_controller)
guacbase = "https://scig-v2.securitycentric.net"

def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Guacamole Command Line Utility.')
    parser.add_argument('-a', dest='active', action='store_true', help='Show active connections')
    parser.add_argument('-l', dest='history', action='store_true', help='List session history')
    parser.add_argument('-k', '--kill', dest='kill', type=str, metavar='UUID', help='Kill the session with the specified UUID.')

    return parser.parse_args()

# Login to Guacamole with username/password
def login(username, password):
    
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    }
                            
    user_data = {
    'username': 'guacadmin',
    'password': '956f2c5S3^!'
    }
    print(user_data)
                            
    authToken = requests.post('https://scig-v2.securitycentric.net/labview/api/tokens', headers=headers, data=user_data,verify=False).json()
    print(authToken['authToken'])
    TOKEN = authToken['authToken'] 
    DATASOURCES = authToken['dataSource']
    ACTIVE = getActiveConnections(TOKEN, 'mysql')
    for datasource in DATASOURCES:
        if len(ACTIVE[datasource]) > 0:
            print(ACTIVE[datasource].items())
            
    # loginData = urllib.urlencode({ u'username' : username, u'password' : password })
    # loginHeaders = { 'Content-type' : 'application/x-www-form-urlencoded', 'Accept' : 'application/json' }
    # loginRequest = urllib2.Request(guacbase + '/api/tokens', data=loginData, headers=loginHeaders)
    # loginResponse = urllib2.urlopen(loginRequest)

    # if loginResponse.code > 299:
    #     return -1

    # else:
    #     return json.loads(loginResponse.read())
    
def getActiveConnections(token, dataSources):
    activeConnections = {}
    # activeRequest = requests.post('https://scig-v2.securitycentric.net/labview/api/session/data/' + datasource + '/activeConnections?token=' + token,verify=False).json()
    # print(activeRequest)
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    }

  
    
    activeRequest = urllib2.Request('https://scig-v2.securitycentric.net/labview/api/session/data/'+str(dataSources)+'/activeConnections?token='+token)
    print(activeRequest)
        
    webpage = urlopen(activeRequest).read()
    print('Web page',webpage)
        # activeResponse = urllib2.urlopen(activeRequest)
        # if activeResponse.code > 299:
        #     break
    activeConnections[datasource] = json.loads(activeResponse.read())

    return activeConnections   

@guacamole_controller.route("/v1/get/guac", methods=['GET'])
def get_guac():
    try:
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host=os.environ.get('APP_GUAC_HOST')
        with SSHTunnelForwarder(
            (guac_host, 22),
            ssh_username=guac_user,
            ssh_password=guac_password,
            remote_bind_address=("127.0.0.1", 3306)
        ) as server:
            time.sleep(1)
            conn = mysql.connector.connect(host="127.0.0.1",
            port=server.local_bind_port,
            user="root",
            passwd="sqltoor",
            db="guacamole")
            cursor =conn.cursor(buffered=True)
            cursor.execute("select * from guacamole_user")
            users=cursor.fetchall()
            print(users)
            data=[]

            # conn.close()
            print(users)
            for user in users:
                data.append({"name":user[1],"id":user[0]})
            conn.close()
            return Response(json.dumps({'users':data}),status=200)
            
    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()
        
@guacamole_controller.route("/v1/create/guac", methods=['GET'])
def create():
    try:
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host=os.environ.get('APP_GUAC_HOST')
        with SSHTunnelForwarder(
            (guac_host, 22),
            ssh_username=guac_user,
            ssh_password=guac_password,
            remote_bind_address=("127.0.0.1", 3306)         
        ) as server:
            time.sleep(1)
            conn = mysql.connector.connect(host="127.0.0.1",
            port=server.local_bind_port,
            user="root",
            passwd="sqltoor",
            db="guacamole")
            cursor =conn.cursor(buffered=True)
            cursor.execute("SET @salt = UNHEX(SHA2(UUID(), 256));")
            conn.commit()
            cursor.execute("INSERT INTO guacamole_user (username,password_salt,password_hash,password_date) VALUES ('myuser',@salt, UNHEX(SHA2(CONCAT('mypassword', HEX(@salt)), 256)),NOW());")
            conn.commit()
            cursor.close()
            conn.close()
            return Response(json.dumps({'Message':"Success"}),status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@guacamole_controller.route("/v1/connect/guac", methods=['GET'])
def connect():
    try:
        guac_user=os.environ.get('APP_GUAC_USER')
        guac_password=os.environ.get('APP_GUAC_PASSWORD')
        guac_host=os.environ.get('APP_GUAC_HOST')
        with SSHTunnelForwarder(
            (guac_host, 22),
            ssh_username=guac_user,
            ssh_password=guac_password,
            remote_bind_address=("127.0.0.1", 3306)
        ) as server:
            time.sleep(1)
            conn = mysql.connector.connect(host="127.0.0.1",
            port=server.local_bind_port,
            user="root",
            passwd="sqltoor",
            db="guacamole")
            cursor =conn.cursor(buffered=True)
            cursor.execute("INSERT INTO guacamole_connection (connection_name, protocol,max_connections,max_connections_per_user) VALUES ( 'scia_1002_win2k16_std_archive_blueprint1','rdp',1,1);")
            conn.commit()
            print('ddddddddddd')
            cursor.execute('SELECT connection_id FROM guacamole_connection WHERE connection_name="scia_1002_win2k16_std_archive_blueprint1";')
            connection_id=cursor.fetchone()[0]
            cursor.execute("INSERT INTO guacamole_connection_parameter VALUES ("+str(connection_id)+",'hostname','10.20.6.2'),("+str(connection_id)+",'port','3389'), ("+str(connection_id)+",'username','administrator'),("+str(connection_id)+",'password','P@ssw0rd!') ;")
            conn.commit()
            cursor.close()
            conn.close()
            return Response(json.dumps({'Message':"Success"}),status=200)

    except Exception as e:
        if e.__class__.__name__ == "IntegrityError":
            db.session.rollback()
        return raiseException(e)
    finally:
        db.session.close()

@guacamole_controller.route("/v1/connect/guacamole-session", methods=['GET'])
    
def getActiveLogin():
    myLoginData = login('guacadmin','P@ssw0rd!')
    
    # activeConnections = {}
    # for datasource in dataSources:
    #     activeRequest = urllib2.Request(guacbase + '/api/session/data/' + datasource + '/activeConnections?token=' + token)
    #     activeResponse = urllib2.urlopen(activeRequest)
    #     if activeResponse.code > 299:
    #         break
    #     activeConnections[datasource] = json.loads(activeResponse.read())

    # return activeConnections
    

