from flask import Blueprint, send_file, abort
from builder_service import image_path

download = Blueprint('download', __name__)

@download.route('/images/download/<name>')
def download_image (name):
    path = image_path(name)
    if path is None:
        abort(404, "File " + name + " not found" )
    return send_file(path, as_attachment=True)