import json
import secrets
import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_login import LoginManager

from config import Config
from backend.models import db, User, Whiteboard, Shape
from backend.socket_events import socketio


login_manager = LoginManager()
login_manager.login_view = "routes.login"
login_manager.login_message = "请先登录"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
        static_url_path="/static",
    )
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode=Config.SOCKETIO_ASYNC_MODE, cors_allowed_origins="*")

    from backend.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    print("=======================================")
    print(" 协作白板已启动：http://127.0.0.1:5000")
    print("=======================================")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
