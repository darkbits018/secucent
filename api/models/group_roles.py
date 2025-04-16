# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db

class GroupRoles(Base):  
    group_roles_name = db.Column(db.String(30), nullable=False)



    def __init__(self, role):
        super()       
        self.group_roles_name = role['group_roles_name']
       