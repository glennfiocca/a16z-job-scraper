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
    location = db.Column(db.String(255), nullable=True)
    employment_type = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    posted_date = db.Column(db.String(100), nullable=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Job {self.title} at {self.company}>'