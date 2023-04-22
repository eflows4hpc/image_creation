
from platform import architecture
from flask import Flask, flash, abort, g
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager, login_user, UserMixin
from werkzeug.serving import run_simple
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound
import jwt
import time
import uuid
import traceback

from config import configuration
from image_builder.build import ImageBuilder 
from image_builder.build import PENDING,STARTED,BUILDING,CONVERTING

app = Flask(__name__)
app.config['APPLICATION_ROOT'] = configuration.application_root
app.config['SECRET_KEY'] = configuration.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = configuration.database
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CAPTCHA_WEBSITE_KEY= configuration.captcha_web_site_key
CAPTCHA_SERVER_KEY= configuration.captcha_site_key
builder = ImageBuilder(configuration.repositories_cfg, configuration.build_cfg, configuration.registry_cfg)

db = SQLAlchemy(app)
#db.session().expire_on_commit = False
#Basic Auth for API
auth = HTTPBasicAuth()

#Login for GUI
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

from contextlib import contextmanager

@contextmanager
def no_expire():
    s = db.session()
    s.expire_on_commit = False
    try:
        yield
    finally:
        s.expire_on_commit = True


user_build = db.Table('user_build',
                    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                    db.Column('build_id', db.String(64), db.ForeignKey('build.id'))
                    )

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(32), index = True)
    password_hash = db.Column(db.String(64))
    email = db.Column(db.String(100))
    builds = db.relationship('Build', secondary=user_build, backref='users')

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_auth_token(self, expires_in=600):
        return jwt.encode(
            {'id': self.id, 'exp': time.time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')


class Build(db.Model):
    id = db.Column(db.String(64), primary_key = True)
    status = db.Column(db.String(32))
    image = db.Column(db.String(64))
    filename = db.Column(db.String(64))
    message = db.Column(db.String(64))
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    machine = db.relationship("Machine", backref=db.backref("build", uselist=False))
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'))
    workflow = db.relationship("Workflow", backref=db.backref("build", uselist=False))

class Machine(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    platform = db.Column(db.String(64))
    architecture = db.Column(db.String(64))
    mpi = db.Column(db.String(64))
    gpu = db.Column(db.String(64))

class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(64))
    step = db.Column(db.String(64))
    version = db.Column(db.String(64))

class Image(db.Model):
    id = db.Column(db.String(64), primary_key = True)
    filename = db.Column(db.String(64))
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    machine = db.relationship("Machine", backref=db.backref("image", uselist=False))
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'))
    workflow = db.relationship("Workflow", backref=db.backref("image", uselist=False))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def check_and_log_user(username, password, remember):
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    if user.verify_password(password):
        login_user(user, remember=remember)
        return True 
    else:
        return False
  
def verify_auth_token(token):
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except:
        return
    return User.query.get(data['id'])

@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = verify_auth_token(username_or_token)
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

'''
#Moved to auth blue print
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

@app.route('/update', methods=['PUT'])
@auth.login_required
def update_password():
    password = request.json.get('password')
    g.user.hash_password(password)
    db.session.commit()
    print("Password updated")
    return jsonify({ "Response" : "Updated" }, 202)
'''

@app.route('/images/download/<name>')
def download_image (name):
    path = builder.get_filename(name)
    if path is None:
        abort(404, "File " + name + " not found" )
    return send_file(path, as_attachment=True)

def build_image (workflow_name, step_id, version, machine, force, user):
    try:
        if machine['container_engine'] == 'singularity':
            singularity = True
        else:
            singularity = False
        
        if workflow_name == 'BASE' and step_id == 'BASE':
            workflow_name = None
            step_id = None
        if version is None:
            version = 'latest'
        workflow = {"name" : workflow_name, "step" : step_id, "version" : version}
        machine_orm = Machine(platform=machine['platform'], architecture=machine['architecture'], mpi=machine.get('mpi', None), gpu=machine.get('gpu', None))
        workflow_orm = Workflow(name=workflow, step=step_id, version=version)

        image_id = builder.gen_image_id(workflow_orm, machine_orm)
        image = Image.query.get(image_id)
        if image is None:
            # If there is not an image add and build
            db.session.add(machine_orm)
            db.session.add(workflow_orm)
            image = Image(id=image_id, machine=machine_orm, workflow=workflow_orm)
            db.session.add(image)
            build_id = str(uuid.uuid4())
            build = Build(id=build_id, status=PENDING, machine=machine_orm,
                          workflow=workflow_orm, image=image_id)
            db.session.add(build)
            user = db.session.query(User).get(user.id)
            user.builds.append(build)
            db.session.commit()
            builder.request_build(build_id, image_id, workflow, machine,
                              singularity, force, _update_build, _update_image)
        else:
            # If there is an image check if it is currently building it
            build = check_image_currently_build(image_id)
            if build:
                print("Build already running ")
                if build in user.builds:
                    print("Build already requested by the same user")
                else:
                    user = db.session.query(User).get(user.id)
                    user.builds.append(build)
                    db.session.commit()
                build_id = build.id

            else:
                user = db.session.query(User).get(user.id)
                db.session.add(machine_orm)
                db.session.add(workflow_orm)
                build_id = str(uuid.uuid4())
                build = Build(id=build_id, status=PENDING,
                              machine=machine, workflow=workflow, image=image_id)
                db.session.add(build)
                user.builds.append(build)
                db.session.commit()
                builder.request_build(build_id, image_id, workflow, machine,
                                  singularity, force, _update_build, _update_image)
        return build_id
    except Exception as e:
        print(traceback.format_exc())
        flash("Exception: " + str(e))
        raise e

def check_image_currently_build(image_id):
    return Build.query.filter(Build.image==image_id, Build.status.in_([PENDING,STARTED,BUILDING,CONVERTING])).first()
    

def _update_build(id, status, image=None, filename=None, message=None):
    build = Build.query.get(id)
    if build is not None:
        build.status=status
        if image is not None:
            build.image=image
        if filename is not None:
            build.filename=filename
        if message is not None:
            build.message=message
        db.session.commit()
    else:
        print("ERROR: Build with id " + str(id) + " not found")

def _update_image(id, filename=None, machine=None, workflow=None):
    print("Updating Image " + str(id))
    image = Image.query.get(id)
    if image is not None:
        if filename is not None:
            image.filename=filename
        if machine is not None:
            image.machine=machine
        if workflow is not None:
            image.workflow=workflow
        db.session.commit()
        print("Updating Image " + str(id) + " updated.")
    else:
        print("Image with id " + str(id) + " not found.")
        
    db.session.commit()

def get_build_logs_path(id):
    return builder.get_build_logs_path(id)

def remove_build(id):
    return builder.delete_build(id)

def get_build(id):
    return Build.query.get(id)

def create_app():
    login_manager.init_app(app)

    from blueprints.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from blueprints.dashboard import dashboard as dashboard_blueprint
    app.register_blueprint(dashboard_blueprint)

    from blueprints.images import api as api_blueprint
    app.register_blueprint(api_blueprint)
    return app


if __name__ == '__main__':
    application = DispatcherMiddleware(NotFound(), {"/image_creation": create_app()})
    run_simple("0.0.0.0", configuration.port, application, use_debugger=True, ssl_context='adhoc', threaded=True) 
