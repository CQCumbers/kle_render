import os

SWAGGER_UI_DOC_EXPANSION = 'full'
SWAGGER_UI_JSONEDITOR = True
DEBUG = False
CORS_HEADERS = 'Content-Type'
CORS_RESOURCES = r'/api/*'
WTF_CSRF_ENABLED = False
SECRET_KEY = os.environ.get('SECRET_KEY')
API_TOKEN = os.environ.get('API_TOKEN')
