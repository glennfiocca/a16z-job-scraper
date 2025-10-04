from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
import os

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=True)
    location = db.Column(db.Text, nullable=True)
    alternate_locations = db.Column(db.Text, nullable=True)
    employment_type = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)
    benefits = db.Column(db.Text, nullable=True)
    salary_range = db.Column(db.String(255), nullable=True)
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    experience_level = db.Column(db.String(100), nullable=True)
    work_environment = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    posted_date = db.Column(db.String(100), nullable=True)
    source = db.Column(db.Text, nullable=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Job {self.title} at {self.company}>'