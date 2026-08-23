import os
import secrets
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://"
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=10,
    ping_interval=5,
    max_http_buffer_size=10e6  # Ajusté à 10MB pour les gros transferts vidéo/médias
)

connected_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"[+] Client connecté : {request.sid}")

@socketio.on('register')
def handle_register(data):
    peer_id = data.get('peer_id')
    if peer_id:
        connected_users[request.sid] = {
            'peer_id': peer_id,
            'pseudo': data.get('pseudo', 'Anonyme'),
            'title': data.get('title', 'Novice Niv.1'),
            'age': data.get('age', 'N/A'),
            'sexe': data.get('sexe', 'N/A'),
            'pays': data.get('pays', 'N/A'),
            'photo': data.get('photo', '')
        }
        emit('peer_discovery', list(connected_users.values()), broadcast=True)

@socketio.on('send_chat_message')
def handle_global_msg(data):
    emit('global_chat_message', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        del connected_users[request.sid]
        emit('peer_discovery', list(connected_users.values()), broadcast=True)
    print(f"[-] Client déconnecté : {request.sid}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
