from flask import Flask
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from .config import Config

socketio = SocketIO()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    bcrypt.init_app(app)
    socketio.init_app(app)

    # Import views after initializing extensions to avoid circular import
    from .views import main
    app.register_blueprint(main)

    return app
