import os, dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)

SWAGGER_UI_DOC_EXPANSION = 'full'
SWAGGER_UI_JSONEDITOR = True
DEBUG = False
CORS_HEADERS = 'Content-Type'
CORS_RESOURCES = r'/api/*'
WTF_CSRF_ENABLED = False
SECRET_KEY = os.environ.get('SECRET_KEY')
API_TOKEN = os.environ.get('API_TOKEN')
