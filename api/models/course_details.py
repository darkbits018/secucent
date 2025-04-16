# from sqlalchemy.orm import validates
# import secrets
# import validators
from .base import Base, db

class CourseDetails(Base):
    course_name = db.Column(db.String(50), unique=True, nullable=False)
    syllabus_data = db.Column(db.JSON)
    curriculum_data=db.Column(db.JSON)

    def __init__(self, course):
        super()
        self.course_name = course['course_name']
        self.syllabus_data = course['syllabus_data']
        self.curriculum_data = course['curriculum_data']