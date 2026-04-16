from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 🔹 DATABASE INIT
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT,
            password TEXT,
            role TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            sender TEXT,
            message TEXT,
            time TEXT
        )
    ''')

    # Default users
    c.execute("INSERT OR IGNORE INTO users VALUES ('doctor', '1234', 'Doctor')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('patient', '1234', 'Patient')")

    conn.commit()
    conn.close()

init_db()

# 🔹 LOGIN (UPDATED WITH ROLE)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('user')
        password = request.form.get('password')
        role = request.form.get('role')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT role FROM users WHERE username=? AND password=? AND role=?",
                  (username, password, role))

        result = c.fetchone()
        conn.close()

        if result:
            return redirect(url_for('chat', user=username, role=role))
        else:
            return "Invalid Login ❌"

    return render_template('login.html')

# 🔹 CHAT PAGE
@app.route('/chat/<user>/<role>')
def chat(user, role):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT sender, message, time FROM messages")
    messages = c.fetchall()
    conn.close()

    return render_template('chat.html', messages=messages, user=user, role=role)

# 🔥 REAL-TIME MESSAGE
@socketio.on('send_message')
def handle_message(data):
    user = data.get('user')
    msg = data.get('message')
    time = datetime.now().strftime("%H:%M")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?, ?, ?)", (user, msg, time))
    conn.commit()
    conn.close()

    socketio.emit('receive_message', {
        'user': user,
        'message': msg,
        'time': time
    })

# 🔹 FILE UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')

    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        time = datetime.now().strftime("%H:%M")

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO messages VALUES (?, ?, ?)",
                  ("System", f"[FILE]::{filename}", time))
        conn.commit()
        conn.close()

        socketio.emit('receive_message', {
            'user': 'System',
            'message': f"[FILE]::{filename}",
            'time': time
        })

    return '', 204

# 🔹 CLEAR CHAT
@app.route('/clear', methods=['POST'])
def clear_chat():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

    socketio.emit('clear')
    return '', 204

# 🔹 SERVE FILES
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 🔐 RUN (NO SSL FOR DEPLOY)
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)