import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SWAGGER_UI_DOC_EXPANSION = 'full'
SWAGGER_UI_JSONEDITOR = True
DEBUG = False
CORS_HEADERS = 'Content-Type'
CORS_RESOURCES = r'/api/*'
WTF_CSRF_ENABLED = False
SECRET_KEY = os.environ.get("SECRET_KEY")
