# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db


class ExternalConfiguration(Base):   
    serverSIP = db.Column(db.String(50), unique=True, nullable=False)
    serverEIP = db.Column(db.String(50), unique=True, nullable=False)
    sSubnet = db.Column(db.Integer, unique=True, nullable=False)    
    vmStartIP = db.Column(db.String(50), unique=True, nullable=False)
    vmEndIP = db.Column(db.String(50), unique=True, nullable=False)
    vmSubnet = db.Column(db.Integer, unique=True, nullable=False)
    user_name = db.Column(db.String(45), nullable=True)

    def __init__(self, config):
        super()      
        self.serverSIP = config['serverSIP']
        self.serverEIP = config['serverEIP']
        self.sSubnet = config['sSubnet']        
        self.vmStartIP = config['vmStartIP']
        self.vmEndIP = config['vmEndIP']
        self.vmSubnet = config['vmSubnet']
        self.user_name = config['user_name']
        
