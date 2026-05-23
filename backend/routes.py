import json
import secrets

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, abort
from flask_login import login_user, logout_user, login_required, current_user

from backend.models import db, User, Whiteboard, Shape


bp = Blueprint("routes", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("routes.dashboard"))
    return redirect(url_for("routes.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect(url_for("routes.dashboard"))
        return render_template("login.html")

    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "msg": "用户名和密码不能为空"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "msg": "用户名或密码错误"}), 401

    login_user(user)
    return jsonify({"ok": True, "user": user.to_dict()})


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect(url_for("routes.dashboard"))
        return render_template("register.html")

    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or len(username) < 2:
        return jsonify({"ok": False, "msg": "用户名至少2位"}), 400
    if not password or len(password) < 4:
        return jsonify({"ok": False, "msg": "密码至少4位"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"ok": False, "msg": "用户名已被占用"}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": user.to_dict()})


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("routes.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    owned = Whiteboard.query.filter_by(owner_id=current_user.id).order_by(Whiteboard.updated_at.desc()).all()
    joined = Whiteboard.query.filter(Whiteboard.members.contains(current_user)).order_by(Whiteboard.updated_at.desc()).all()
    return render_template(
        "dashboard.html",
        user=current_user,
        owned_boards=owned,
        joined_boards=joined,
    )


@bp.route("/boards", methods=["POST"])
@login_required
def create_board():
    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip() or "未命名白板"
    token = secrets.token_urlsafe(16)
    while Whiteboard.query.filter_by(invite_token=token).first():
        token = secrets.token_urlsafe(16)

    board = Whiteboard(title=title, owner_id=current_user.id, invite_token=token)
    if current_user not in board.members:
        board.members.append(current_user)
    db.session.add(board)
    db.session.commit()
    return jsonify({"ok": True, "board": board.to_dict()})


@bp.route("/boards/<int:board_id>/delete", methods=["POST"])
@login_required
def delete_board(board_id: int):
    board = Whiteboard.query.get(board_id)
    if not board:
        return jsonify({"ok": False, "msg": "白板不存在"}), 404
    if board.owner_id != current_user.id:
        return jsonify({"ok": False, "msg": "只有创建者可以删除"}), 403
    db.session.delete(board)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/join/<token>")
@login_required
def join_by_token(token: str):
    board = Whiteboard.query.filter_by(invite_token=token).first()
    if not board:
        abort(404, "邀请链接无效")
    if current_user not in board.members:
        board.members.append(current_user)
        db.session.commit()
    return redirect(url_for("routes.board_view", board_id=board.id))


@bp.route("/boards/<int:board_id>")
@login_required
def board_view(board_id: int):
    board = Whiteboard.query.get(board_id)
    if not board:
        abort(404, "白板不存在")
    if board.owner_id != current_user.id and current_user not in board.members:
        abort(403, "你未被邀请加入该白板")
    return render_template("board.html", user=current_user, board=board)


@bp.route("/api/boards/<int:board_id>/shapes")
@login_required
def api_board_shapes(board_id: int):
    board = Whiteboard.query.get(board_id)
    if not board:
        return jsonify({"ok": False, "msg": "白板不存在"}), 404
    if board.owner_id != current_user.id and current_user not in board.members:
        return jsonify({"ok": False, "msg": "无权访问"}), 403
    shapes = [s.to_dict() for s in board.shapes]
    return jsonify({"ok": True, "shapes": shapes})


@bp.route("/api/boards/<int:board_id>/clear", methods=["POST"])
@login_required
def api_board_clear(board_id: int):
    board = Whiteboard.query.get(board_id)
    if not board:
        return jsonify({"ok": False, "msg": "白板不存在"}), 404
    if board.owner_id != current_user.id and current_user not in board.members:
        return jsonify({"ok": False, "msg": "无权访问"}), 403
    for s in board.shapes:
        db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})
