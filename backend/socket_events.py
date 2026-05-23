import json
from flask import request
from flask_login import current_user
from flask_socketio import SocketIO, emit, join_room, leave_room

from backend.models import db, Whiteboard, Shape


socketio = SocketIO()


def _get_board_or_403(board_id: int):
    if not current_user or not current_user.is_authenticated:
        return None
    board = Whiteboard.query.get(board_id)
    if not board:
        return None
    if board.owner_id != current_user.id and current_user not in board.members:
        return None
    return board


@socketio.on("connect")
def on_connect():
    if not current_user.is_authenticated:
        return False


@socketio.on("join_board")
def on_join_board(data):
    board_id = data.get("board_id") if isinstance(data, dict) else None
    if not board_id:
        emit("error", {"msg": "缺少 board_id"})
        return
    board = _get_board_or_403(int(board_id))
    if not board:
        emit("error", {"msg": "无权访问该白板"})
        return
    room = f"board:{board.id}"
    join_room(room)
    emit("joined", {"board_id": board.id, "title": board.title})


@socketio.on("leave_board")
def on_leave_board(data):
    board_id = data.get("board_id") if isinstance(data, dict) else None
    if board_id:
        leave_room(f"board:{int(board_id)}")


@socketio.on("draw")
def on_draw(data):
    board_id = int(data.get("board_id") or 0)
    shape_type = data.get("type")
    color = data.get("color", "#000000")
    width = int(data.get("width") or 3)
    points = data.get("points") or []

    if shape_type not in ("pen", "rect", "circle"):
        emit("error", {"msg": "不支持的图形类型"})
        return
    board = _get_board_or_403(board_id)
    if not board:
        emit("error", {"msg": "无权访问"})
        return
    if shape_type == "pen" and (not isinstance(points, list) or len(points) < 2):
        return
    if shape_type in ("rect", "circle") and (not isinstance(points, list) or len(points) < 2):
        return

    last_index = db.session.query(db.func.max(Shape.order_index)).filter(
        Shape.whiteboard_id == board.id
    ).scalar() or 0

    shape = Shape(
        whiteboard_id=board.id,
        type=shape_type,
        color=color,
        width=width,
        data=json.dumps(points),
        order_index=last_index + 1,
    )
    db.session.add(shape)
    db.session.commit()

    payload = shape.to_dict()
    payload["author"] = current_user.username
    emit("draw", payload, to=f"board:{board.id}", skip_sid=request.sid)
    emit("shape_saved", {"id": shape.id, "client_id": data.get("client_id")})


@socketio.on("undo")
def on_undo(data):
    board_id = int(data.get("board_id") or 0)
    board = _get_board_or_403(board_id)
    if not board:
        return
    last = (
        Shape.query.filter_by(whiteboard_id=board.id)
        .order_by(Shape.order_index.desc(), Shape.id.desc())
        .first()
    )
    if not last:
        return
    info = last.to_dict()
    db.session.delete(last)
    db.session.commit()
    emit("undo_applied", {"id": last.id, "shape": info}, to=f"board:{board.id}")


@socketio.on("redo")
def on_redo(data):
    board_id = int(data.get("board_id") or 0)
    shape = data.get("shape") or {}
    board = _get_board_or_403(board_id)
    if not board:
        return
    shape_type = shape.get("type")
    color = shape.get("color", "#000000")
    width = int(shape.get("width") or 3)
    points = shape.get("points") or []
    if shape_type not in ("pen", "rect", "circle"):
        return

    last_index = db.session.query(db.func.max(Shape.order_index)).filter(
        Shape.whiteboard_id == board.id
    ).scalar() or 0

    new_shape = Shape(
        whiteboard_id=board.id,
        type=shape_type,
        color=color,
        width=width,
        data=json.dumps(points),
        order_index=last_index + 1,
    )
    db.session.add(new_shape)
    db.session.commit()

    payload = new_shape.to_dict()
    payload["author"] = current_user.username
    emit("draw", payload, to=f"board:{board.id}")


@socketio.on("clear_board")
def on_clear_board(data):
    board_id = int(data.get("board_id") or 0)
    board = _get_board_or_403(board_id)
    if not board:
        return
    for s in board.shapes:
        db.session.delete(s)
    db.session.commit()
    emit("board_cleared", {}, to=f"board:{board.id}")
