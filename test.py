from timeit import default_timer as timer
from .keyboard import Keyboard, deserialise
import json, github, dotenv, os

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)
gist_id = '4de8adb88cb4c45c2f43'

g = github.Github(os.environ.get('API_TOKEN'))
files = [v for k, v in g.get_gist(gist_id).files.items() if k.endswith('.kbd.json')]
content = json.loads(files[0].content)

start = timer()
img = Keyboard(content).render()
end = timer()
print("--- rendered at %s seconds ---" % (end - start))

img.save("render_output.png", 'PNG')
