from flask import Blueprint, request, jsonify, abort, g
from builder_service import build_image, get_build, auth
from image_builder.utils import check_bool
api = Blueprint('api', __name__)

@api.route('/build/', methods= ['POST'])
@auth.login_required
def build():
    content = request.json
    print("Request received: " + str(content))
    
    try:
        force = check_bool(content, 'force', False)
        push = check_bool(content, 'push', True)
        machine = content['machine']
        workflow = content['workflow']
        step_id = content['step_id']
        if 'version' in content:
            version = content['version']
        else:
            version = 'latest'
        build_id = build_image(workflow, step_id, version, machine, force, push, g.user)
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