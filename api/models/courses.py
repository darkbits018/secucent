# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db

class Courses(Base):
    course_name = db.Column(db.String(50), unique=True, nullable=False)
    course_description = db.Column(db.String(50), nullable=False)
    course_duration = db.Column(db.Integer, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    course_activation = db.Column(db.Integer, nullable=False)
    course_series_start = db.Column(db.String(50))
    course_series_end = db.Column(db.String(50))
    static_file  = db.Column(db.Integer, nullable=False)  
    course_user_id = db.Column(db.Integer, nullable=False)
    chat_room= db.Column(db.Integer, nullable=False)

    def __init__(self, course):
        super()
        self.course_name = course['course_name']
        self.course_description = course['course_description']
        self.course_duration = course['course_duration']
        self.static_file = course['static_file']
        self.vendor_name = course['vendor_name']
        self.course_activation = course['course_activation']
        self.course_series_start = course['course_series_start']
        self.course_series_end = course['course_series_end']
        self.course_user_id = course['course_user_id']
        self.chat_room=course['chat_room']