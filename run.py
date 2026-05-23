from backend.app import app, socketio

if __name__ == "__main__":
    print("=======================================")
    print(" 协作白板已启动：http://127.0.0.1:5000")
    print("=======================================")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
