import json, github, io, flask_wtf, flask_wtf.file, wtforms, flask_cors
from flask import Flask, Blueprint, redirect, send_file, render_template, flash, Markup
from flask_restplus import Api, Resource
from keyboard import Keyboard


app = Flask(__name__)
app.config.from_object('config')
flask_cors.CORS(app)
github_api = github.Github(app.config['API_TOKEN'])  
blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(
    blueprint, version='1.0', title='KLE-Render API',
    description='Prettier images of Keyboard Layout Editor designs. URLs relative to this page'
)
kle_parser = api.parser()
kle_parser.add_argument(
    'data', required=True, location='json',
    help='Downloaded strict JSON from Raw Data tab of Keyboard Layout Editor'
)
app.register_blueprint(blueprint)


def serve_pil_image(pil_img):
    img_io = io.BytesIO()
    pil_img.save(img_io, 'PNG', compress_level=3)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')


@api.route('/<id>')
@api.param('id', 'Copy from keyboard-layout-editor.com/#/gists/<id>')
class FromGist(Resource):
    def get(self, id):
        files = [v for k, v in github_api.get_gist(id).files.items() if k.endswith('.kbd.json')]
        img = Keyboard(json.loads(files[0].content)).render()
        return serve_pil_image(img)


@api.route('/')
@api.expect(kle_parser)
class FromJSON(Resource):
    def post(self):
        img = Keyboard(api.payload).render()
        return serve_pil_image(img)



class InputForm(flask_wtf.FlaskForm):
    url = wtforms.StringField('Copy the URL of a saved layout:')
    json = flask_wtf.file.FileField(
        'Or upload raw JSON:', validators=[flask_wtf.file.FileAllowed(['json'], 'Upload must be JSON')]
    )


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
            if ('keyboard-layout-editor.com/#/gists/' in form.url.data):
                return redirect('/api/'+form.url.data.split('gists/', 1)[1])
            flash('Not a Keyboard Layout Editor gist')
        elif form.json.data:
            try:
                content = json.loads(form.json.data.read().decode('utf-8'))
                img = Keyboard(content).render()
                return serve_pil_image(img)
            except ValueError:
                flash(Markup('Invalid JSON input - see (?) for help'))
    flash_errors(form)
    return render_template('index.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
