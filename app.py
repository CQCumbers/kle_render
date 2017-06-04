#!bin/python
from flask import Flask, Blueprint, redirect, send_file, render_template, flash
from flask_restplus import Api, Resource, fields

from flask_cors import CORS, cross_origin
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField

from github import Github
from io import BytesIO
import requests, json

import kle_render

app = Flask(__name__)
app.config.from_object('config')
CORS(app)
api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_blueprint, version='1.0', title='KLE-Render API', description='Get prettier images of Keyboard Layout Editor designs')
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
    pil_img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@api.route('/<id>', endpoint='from_gist')
@api.doc(params={'id': 'Copy from keyboard-layout-editor.com/#/gists/<id>'})
class FromGist(Resource):
    def get(self, id):
        token = app.config['API_TOKEN']
        g = Github(token) # authenticate to avoid rate limits
        content = json.loads([value for key, value in g.get_gist(id).files.items() if key.endswith('.kbd.json')][0].content)
        data = kle_render.deserialise(content)
        img = kle_render.render_keyboard(data)
        return serve_pil_image(img)

@api.route('/', endpoint='from_json')
@api.expect(post)
class FromJSON(Resource):
    def post(self):
        data = kle_render.deserialise(json.loads(api.payload))
        img = kle_render.render_keyboard(data)
        return serve_pil_image(img)

app.register_blueprint(api_blueprint)



class InputForm(FlaskForm):
    url = StringField('Copy the URL of a saved layout:')
    json = FileField('Or upload raw JSON:', validators=[FileAllowed(['json'], 'Upload must be JSON')])

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(error)

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = InputForm()
    if form.validate_on_submit():
        if len(form.url.data) > 0:
            if 'keyboard-layout-editor.com/#/gists/' in g.form.url.data:
                return redirect('/api/'+form.url.data.split('gists/', 1)[1])
            else:
                flash("Not a valid Keyboard Layout Editor Gist")
        elif form.json.data != None:
            str_data = form.json.data.read().decode('utf-8')
            data = kle_render.deserialise(json.loads(str_data))
            img = kle_render.render_keyboard(data)
            return serve_pil_image(img)
    flash_errors(form)
    return render_template('index.html', form=form)

if __name__ == '__main__':
    app.run(debug=True) # Use debug=False on actual server
