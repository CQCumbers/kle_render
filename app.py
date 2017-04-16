#!bin/python
from flask import Flask, request, send_file
from flask_restplus import Api, Resource, fields
from flask_cors import CORS, cross_origin
from io import BytesIO
import requests, json
import kle_render

app = Flask(__name__)
app.config.from_object('config')
CORS(app)
api = Api(app, version='1.0', title='KLE-Render API', description='Get prettier images of Keyboard Layout Editor designs', doc='/api/')
parser = api.parser()

post = parser.copy()
post.add_argument(
        "data",
        required=True,
        location="json",
        help="Downloaded JSON (strict) from Raw Data tab of Keyboard Layout Editor"
)

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', optimize=True, quality=80)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@api.route('/api/<id>', endpoint='from_gist')
@api.doc(params={'id': 'Copy from keyboard-layout-editor.com/#/gists/<id>'})
class FromGist(Resource):
    def get(self, id):
        data = kle_render.deserialise(json.loads([value for key, value in requests.get('http://api.github.com/gists/%s' % id).json()['files'].items() if key.endswith('.kbd.json')][0]['content']))
        img = kle_render.render_keyboard(data)
        return serve_pil_image(img)

@api.route('/api', endpoint='from_json')
@api.expect(post)
class FromJSON(Resource):
    def post(self):
        data = kle_render.deserialise(api.payload)
        img = kle_render.render_keyboard(data)
        return serve_pil_image(img)


if __name__ == '__main__':
    app.run(debug=True) # Use debug=False on actual server
