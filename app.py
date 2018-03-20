import json, github, io, flask_wtf, flask_wtf.file, wtforms, flask_cors
from flask import Flask, Blueprint, redirect, send_file, render_template, flash, Markup
from flask_restplus import Api, Resource, fields
from keyboard import Keyboard


app = Flask(__name__)
app.config.from_object('config')
flask_cors.CORS(app)
api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(
    api_blueprint, version='1.0', title='KLE-Render API',
    description='Get prettier images of Keyboard Layout Editor designs'
)
parser = api.parser()
post = parser.copy()
post.add_argument(
    'data', required=True, location='json',
    help='Downloaded JSON (strict) from Raw Data tab of Keyboard Layout Editor'
)
app.register_blueprint(api_blueprint)


def serve_pil_image(pil_img):
    img_io = io.BytesIO()
    pil_img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')


@api.route('/<id>', endpoint='from_gist')
@api.doc(params={'id': 'Copy from keyboard-layout-editor.com/#/gists/<id>'})
class FromGist(Resource):
    def get(self, id):
        # authenticate with Github to avoid rate limits
        g = github.Github(app.config['API_TOKEN'])  
        files = [v for k, v in g.get_gist(id).files.items() if k.endswith('.kbd.json')]
        img = Keyboard(json.loads(files[0].content)).render()
        return serve_pil_image(img)


@api.route('/', endpoint='from_json')
@api.expect(post)
class FromJSON(Resource):
    def post(self):
        content = json.loads(api.payload)
        img = Keyboard(content).render()
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
