import sqlite3
from flask import Flask, jsonify, request, render_template, g
from datetime import datetime

app = Flask(__name__)
DATABASE = 'snippets.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                code TEXT NOT NULL,
                language TEXT DEFAULT 'text',
                description TEXT DEFAULT '',
                is_starred INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snippet_tags (
                snippet_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(snippet_id) REFERENCES snippets(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
            );
        ''')
        db.commit()

init_db()

if __name__ == '__main__':
    app.run(debug=True)
