import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ecommerce.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt_super_secret'