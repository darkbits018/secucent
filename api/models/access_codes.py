# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db


class AccessCodes(Base):
    course_name = db.Column(db.String(50), unique=True, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    access_code = db.Column(db.String(50))
    status = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.String(500), nullable=False)
    last_name = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(500), nullable=False)
    key = db.Column(db.String(500), nullable=False)
    access_codes_user_id = db.Column(db.Integer, nullable=False)
    user_course_id=db.Column(db.Integer,nullable=False)
    password = db.Column(db.String(200), nullable=False)
    life_cycle=db.Column(db.Integer,nullable=False)
    percent = db.Column(db.Integer, nullable=False)
    progress = db.Column(db.JSON, nullable=False)
    user_type = db.Column(db.Integer, nullable=False)
    phone_no = db.Column(db.Integer, nullable=False)
    motp = db.Column(db.Integer, nullable=False)
    token= db.Column(db.Text)
    

    def __init__(self, course):
        super()
        self.course_name = course['course_name']
        self.vendor_name = course['vendor_name']
        self.access_code = course['access_code']
        self.status = course['status']
        self.first_name = course['first_name']
        self.last_name = course['last_name']
        self.email = course['email']
        self.key = course['key']
        self.access_codes_user_id = course['access_codes_user_id']
        self.user_course_id=course['user_course_id']
        self.password = course['password']
        self.life_cycle = course['life_cycle']
        self.percent = course['percent']
        self.progress = course['progress']
        self.user_type = course['user_type']
        self.motp = course['motp']
        self.phone_no = course['phone_no']
        self.token = course['token']
        
