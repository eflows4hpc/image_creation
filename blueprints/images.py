from flask import Blueprint, request, jsonify, abort, g
from builder_service import build_image, get_build, auth

api = Blueprint('api', __name__)

@api.route('/build/', methods= ['POST'])
@auth.login_required
def build():
    content = request.json
    print("Request received: " + str(content))
    
    try:
        if 'force' in content:
            force = content['force']
            if isinstance(force, str):
                force = force.lower() == 'true'
            elif not isinstance(force, bool):
                abort(400, "Bad request: force should be True or False" + str(e))
        else :
            force = False
        machine = content['machine']
        workflow = content['workflow']
        step_id = content['step_id']
        if 'version' in content:
            version = content['version']
        else:
            version = 'latest'
        build_id = build_image(workflow, step_id, version, machine, force, g.user)
        return jsonify({"id" : build_id})
    except KeyError as e:
        abort(400, "Bad request: Key error" + str(e))
    except Exception as e:
        abort(500, "Exception requesting image creation" + str(e))

@api.route('/build/<id>', methods=['GET'])
@auth.login_required
def check (id):
    build = get_build(id)
    if build is not None:
        return {"status" : build.status, "image_id" : build.image , "filename": build.filename, "message": build.message }
    else:
        abort(400, "Build not found")