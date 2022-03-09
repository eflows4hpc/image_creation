
from flask import Flask, request, jsonify, abort, g
from flask import send_file

import logging

from config import configuration
from image_builder.build import ImageBuilder 


app = Flask(__name__)


builder = ImageBuilder(configuration.repositories_cfg, configuration.build_cfg, configuration.registry_cfg)



@app.route('/images/download/<name>')
def download_image (name):
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = builder.get_filename(name)
    if path is None:
        abort(404, "File " + name + " not found" )
    return send_file(path, as_attachment=True)

@app.route('/build/', methods= ['POST'])
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
        build_id = builder.request_build(content['workflow'], content['step_id'], machine, singularity, force)
        return jsonify({"id" : build_id})
    except KeyError as e:
        abort(400, "Bad request: " + str(e))
    

@app.route('/build/<id>', methods=['GET'])
def check (id):
    try:
        return jsonify(builder.check_build(id))
    except KeyError as e:
        abort(400, "Bad request: " + str(e))

if __name__ == '__main__':
    #app.run(port=5000,debug=True, ssl_context='adhoc') 
    app.run(port=5000,debug=True)
    