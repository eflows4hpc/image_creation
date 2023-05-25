from builder_service import create_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound

app = create_app()
#app.use_x_sendfile = True
application = DispatcherMiddleware(NotFound(), {"/image_creation": app })
