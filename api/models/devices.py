# from sqlalchemy.orm import validates
import secrets
import validators
from .base import Base, db

class Devices(Base):
    app_type = db.Column(db.Integer, nullable=False)
    device_uid = db.Column(db.String(50), unique=True, nullable=False)
    api_key = db.Column(db.String(100), nullable=False)

    def __init__(self, device):
        super()
        self.app_type = device['app_type']
        self.device_uid = device['device_uid']
        self.api_key = secrets.token_urlsafe(60)

    # @validates('app_type')
    def validate_app_type(self, key, app_type):
        """
            Valid App Types:
                0: Desktop Terminal App
                1: Web-based Terminal App
        """
        if not app_type in [0,1]:
            raise AssertionError('Invalid App Type!')
        return app_type

    # @validates('device_uid')
    def validate_device_uid(self, key, device_uid):
        """
            Device Uid:
                For 'Desktop Terminal App', MAC Address is used.
                For 'Web-based Terminal App', Browser Fingerprint is used.
        """
        if self.app_type == 0 and not validators.mac_address(device_uid):
            raise AssertionError('Invalid MAC Address!')
        return device_uid