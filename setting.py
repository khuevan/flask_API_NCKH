import os
from os.path import join, dirname
from dotenv import load_dotenv


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = os.environ.get('PORT', 5000)
DEBUG = os.environ.get('DEBUG') == 'True'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
MONGODB_STRING = os.environ.get('MONGODB_STRING', 'mongodb://localhost:27017/')