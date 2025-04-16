# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db


class Configuration(Base):
    user_id = db.Column(db.Integer, nullable=True)
    msHost = db.Column(db.String(50), unique=True, nullable=False)
    msdName = db.Column(db.String(50), unique=True, nullable=False)
    msPort = db.Column(db.Integer, unique=True, nullable=False)
    msUser = db.Column(db.String(50), unique=True, nullable=False)
    msPassword = db.Column(db.String(50), unique=True, nullable=False)
    serverSIP = db.Column(db.String(50), unique=True, nullable=False)
    serverEIP = db.Column(db.String(50), unique=True, nullable=False)
    sSubnet = db.Column(db.Integer, unique=True, nullable=False)
    xePasswordKey = db.Column(db.String(200), unique=True, nullable=False)
    vmStartIP = db.Column(db.String(50), unique=True, nullable=False)
    vmEndIP = db.Column(db.String(50), unique=True, nullable=False)
    vmSubnet = db.Column(db.Integer, unique=True, nullable=False)
    rMQHost = db.Column(db.String(50), unique=True, nullable=False)
    rMQUser = db.Column(db.String(50), unique=True, nullable=False)
    rMQPassword = db.Column(db.String(50), unique=True, nullable=False)
    rMQ2Host = db.Column(db.String(50), unique=True, nullable=False)
    rMQ2User = db.Column(db.String(50), unique=True, nullable=False)
    rMQ2Password = db.Column(db.String(50), unique=True, nullable=False)
    rMQ3Host = db.Column(db.String(50), unique=True, nullable=False)
    rMQ3User = db.Column(db.String(50), unique=True, nullable=False)
    rMQ3Password = db.Column(db.String(50), unique=True, nullable=False)
    cBrokerHost = db.Column(db.String(50), unique=True, nullable=False)
    cBrokerUser = db.Column(db.String(50), unique=True, nullable=False)
    cBrokerPassword = db.Column(db.String(50), unique=True, nullable=False)
    cBroker2Host = db.Column(db.String(50), unique=True, nullable=False)
    cBroker2User = db.Column(db.String(50), unique=True, nullable=False)
    cBroker2Password = db.Column(db.String(50), unique=True, nullable=False)
    gateway = db.Column(db.String(50), unique=True, nullable=False)
    cbData = db.Column(db.JSON)

    def __init__(self, config):
        super()
        self.user_id = config['user_id']
        self.msHost = config['msHost']
        self.msdName = config['msdName']
        self.msPort = config['msPort']
        self.msUser = config['msUser']
        self.msPassword = config['msPassword']
        self.serverSIP = config['serverSIP']
        self.serverEIP = config['serverEIP']
        self.sSubnet = config['sSubnet']
        self.xePasswordKey = config['xePasswordKey']
        self.vmStartIP = config['vmStartIP']
        self.vmEndIP = config['vmEndIP']
        self.vmSubnet = config['vmSubnet']
        self.rMQHost = config['rMQHost']
        self.rMQUser = config['rMQUser']
        self.rMQPassword = config['rMQPassword']
        self.rMQ2Host = config['rMQ2Host']
        self.rMQ2User = config['rMQ2User']
        self.rMQ2Password = config['rMQ2Password']
        self.rMQ3Host = config['rMQ3Host']
        self.rMQ3User = config['rMQ3User']
        self.rMQ3Password = config['rMQ3Password']
        self.cBrokerHost = config['cBrokerHost']
        self.cBrokerUser = config['cBrokerUser']
        self.cBrokerPassword = config['cBrokerPassword']
        self.cBroker2Host = config['cBroker2Host']
        self.cBroker2User = config['cBroker2User']
        self.cBroker2Password = config['cBroker2Password']
        self.gateway = config['gateway']
        self.cbData = config['cbData']
