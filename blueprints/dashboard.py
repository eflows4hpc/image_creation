from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from builder_service import db, Build, Image, User, build_image, get_build_logs_path, remove_build
import time

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/home')
@login_required
def home():
    return render_template('main.html')

@dashboard.route('/')
@login_required
def index():
    return render_template('main.html')

@dashboard.route('/builds', methods=['GET'])
@login_required
def get_builds():
    user = User.query.get(current_user.id)
    return render_template('builds.html', builds=user.builds)

@dashboard.route('/builds/<id>', methods=['GET'])
@login_required
def get_build(id):
     build = Build.query.get(id)
     return render_template('build_details.html', build=build)

@dashboard.route('/builds/<id>/logs', methods=['GET'])
@login_required
def get_build_logs(id):
     return render_template('logs.html', id=id)

@dashboard.route('/builds/<id>/logs/stream', methods=['GET'])
@login_required
def logs_stream(id):
    logs_file = get_build_logs_path(id)
    def generate():
        with open(logs_file) as f:        
            for line in f:
                yield line
    return Response(generate(), mimetype='text/plain')

@dashboard.route('/builds/<id>/delete')
@login_required
def delete_build(id):
     #TODO: cancel execution
     remove_build(id)
     build = db.session.query(Build).get(id)
     db.session.delete(build)
     db.session.commit()
     return redirect(url_for('dashboard.get_builds'))

@dashboard.route('/builds/new')
@login_required
def new_build():
    return render_template('request.html')


@dashboard.route('/builds/new', methods=['POST'])
@login_required
def run_build():
    try:
        machine = {}
        machine['platform'] = request.form.get('platform')
        machine['architecture'] = request.form.get('architecture').strip()
        machine['container_engine'] = request.form.get('container_engine')
        machine['mpi'] = request.form.get('mpi').strip()
        machine['gpu'] = request.form.get('gpu').strip()
        wf_name = request.form.get('wf_name').strip()
        wf_step = request.form.get('wf_step').strip()
        version = request.form.get('wf_version').strip()
        if version is None or version == "" :
            version = 'latest'
        force = False
        push = True
        build_id = build_image (wf_name, wf_step, version, machine, force, push, current_user)
        return redirect(url_for('dashboard.get_build', id=build_id))
    except Exception as e:
        flash("Error submitting request" + str(e))
        return render_template('request.html', form=request.form)


@dashboard.route('/images')
@login_required
def get_images():
    images = Image.query.all()
    return render_template('images.html', images=images)

@dashboard.route('/account/token', methods=['POST'])
@login_required
def generate_token():
    token = current_user.generate_auth_token()
    return render_template('account.html', token=token)

@dashboard.route('/account')
@login_required
def account():
    return render_template('account.html', name=current_user.username)

@dashboard.route('/account/update', methods=['POST'])
@login_required
def update_password():
    new_password = request.form.get('new_password')
    retype_password = request.form.get('retype_password')
    if new_password == retype_password:
        current_user.hash_password(new_password)
        db.commit()
    else:
        flash("Password and retype are not the same")
    return render_template('account.html', password=True)

