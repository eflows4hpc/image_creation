
from flask import Flask, flash, request, jsonify, abort, g
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware
import jwt
import logging
import time

from config import configuration
from image_builder.build import ImageBuilder 


app = Flask(__name__)
app.config['APPLICATION_ROOT'] = configuration.application_root
app.config['SECRET_KEY'] = configuration.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = configuration.database
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

builder = ImageBuilder(configuration.repositories_cfg, configuration.build_cfg, configuration.registry_cfg)

db = SQLAlchemy(app)

auth = HTTPBasicAuth()

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(32), index = True)
    password_hash = db.Column(db.String(64))

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=600):
        return jwt.encode(
            {'id': self.id, 'exp': time.time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except:
            return
        return User.query.get(data['id'])


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user:
            flash("Username not found or token not valid")
            return False       
        if not user.verify_password(password):
            flash("Password incorrect")
            return False
    g.user = user
    return True

@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(404, "Incorrect request beacuse of empty username or password")    
    if User.query.filter_by(username=username).first() is not None:
        abort(400, "User already exists.")    
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return (jsonify({'username': user.username}), 201)

@app.route('/login')
@auth.login_required
def get_token():
    token = g.user.generate_auth_token(6000)
    print("generated token: " + token)
    return jsonify({ 'token': token, 'duration': 6000 })


@app.route('/images/download/<name>')
@auth.login_required
def download_image (name):
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = builder.get_filename(name)
    if path is None:
        abort(404, "File " + name + " not found" )
    return send_file(path, as_attachment=True)

@app.route('/build/', methods= ['POST'])
@auth.login_required
def build_Image ():
    logging.debug(str(request))
    content = request.json
    try:
        if 'force' in content:
            force = content['force']
        else :
            force = False
        machine = content['machine']
        if machine['container_engine'] == 'singularity':
            singularity = True
        else:
            singularity = False   
        
        workflow = content['workflow']
        step_id = content['step_id']
        if workflow == 'BASE' and step_id == 'BASE' :
            workflow = None
            step_id = None

        build_id = builder.request_build(workflow, step_id, machine, singularity, force)
        return jsonify({"id" : build_id})
    except KeyError as e:
        abort(400, "Bad request: " + str(e))
    

@app.route('/build/<id>', methods=['GET'])
@auth.login_required
def check (id):
    try:
        return jsonify(builder.check_build(id))
    except KeyError as e:
        abort(400, "Bad request: " + str(e))

def simple(env, resp):
    resp(b'200 OK', [(b'Content-Type', b'text/plain')])
    return [b'Hello WSGI World']

app.wsgi_app = DispatcherMiddleware(simple, {configuration.application_root: app.wsgi_app})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=configuration.port,debug=True, ssl_context='adhoc') 