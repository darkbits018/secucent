# from sqlalchemy.orm import validates
# import secrets
# import validators
# import re
from .base import Base, db
from werkzeug.security import generate_password_hash, check_password_hash

class ErrorLogs(Base):
    vm_name = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='unresolved')
    
    def __init__(self, error):
        super()
        self.vm_name = error['vm_name']
        self.message = error['message']
    
