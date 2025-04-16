from sqlalchemy.orm import validates
# import secrets
# import validators
import ipaddress
from .base import Base, db
import os

class GroupInstances(Base):
    group_id = db.Column(db.Integer, nullable=False,unique=False)
    name = db.Column(db.String(100), nullable=False, unique=False)
    ip_address = db.Column(db.String(50), nullable=False,unique=False)
    ccu_landing = db.Column(db.String(50), nullable=False, unique=False)
    ccu_helper = db.Column(db.String(50), nullable=False, unique=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    status_message = db.Column(db.Text, nullable=True, default='')
    aandf_state= db.Column(db.Integer, nullable=False, default=0)
    odv = db.Column(db.Integer, nullable=False, default=0)
    odv_options = db.Column(db.String(50), nullable=False, unique=False,default='controls')
    group_instances_user_id = db.Column(db.Integer, nullable=False,unique=False)
    lab_end_session = db.Column(db.DateTime, nullable = True,default=None)
    is_assigned = db.Column(db.Boolean, nullable=False, default=False)
    provision_buffer_time_flag = db.Column(db.Boolean, nullable=False, default=False)
    provision_buffer_time = db.Column(db.DateTime, nullable = True,default=None)
    def __init__(self, group):
        super()
        self.group_id = group['group_id']
        self.name = group['name']
        self.ip_address = group['ip_address']
        self.ccu_landing = group['ccu_landing']
        self.ccu_helper = group['ccu_helper']
        self.odv = group['odv']
        self.odv_options = group['odv_options']
        self.group_instances_user_id = group['group_instances_user_id']
        self.lab_end_session = group['lab_end_session']
        self.is_assigned = group['is_assigned']
    @validates('ip_address')
    def validate_ip_address_start(self, key, ip_address):
        ip0=os.environ.get('APP_VM_START_IP')
        ip1=os.environ.get('APP_VM_END_IP')
        start_ip=int(ipaddress.ip_address(ip0))
        end_ip=int(ipaddress.ip_address(ip1))
        ip_int=int(ipaddress.ip_address(ip_address))        
        if ip_int < start_ip or ip_int > end_ip:
            raise AssertionError('Invalid IP Address!')
        return ip_address

    @validates('ccu_landing')
    def validate_ccu_landing(self, key, ccu_landing):
        c_l = str(ccu_landing).split("-")[0]        
        offset = str(ccu_landing).split("-")[1]
        if int(c_l)<1001:
            raise AssertionError("Invalid CCU number")
        return str(c_l) + '-' +str(offset)  
    @validates('ccu_helper')
    def validate_ccu_helper(self, key, ccu_helper):
        c_h = str(ccu_helper).split("-")[0]        
        offset = str(ccu_helper).split("-")[1]
        if int(c_h)<2001:
            raise AssertionError("Invalid CCU number")
        return str(c_h) +'-'+ str(offset)

