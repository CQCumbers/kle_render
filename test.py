import kle_render
import requests, json
from timeit import default_timer as timer

id = '4de8adb88cb4c45c2f43'
start = timer()

data = kle_render.deserialise(json.loads([value for key, value in requests.get('http://api.github.com/gists/%s' % id).json()['files'].items() if key.endswith('.kbd.json')][0]['content']))
end = timer()
print("--- deserialised at %s seconds ---" % (end - start))

img = kle_render.render_keyboard(data)
end = timer()
print("--- rendered at %s seconds ---" % (end - start))

img.save("render_output.png", 'PNG')
