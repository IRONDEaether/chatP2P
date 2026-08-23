import os
import secrets
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
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
    max_http_buffer_size=1e6
)

# Stockage des profils connectés { socket_id: { peer_id, pseudo, title } }
connected_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"[+] Client connecté : {request.sid}")

@socketio.on('register')
def handle_register(data):
    """ Enregistre le pair et informe tous les autres utilisateurs """
    peer_id = data.get('peer_id')
    pseudo = data.get('pseudo', 'Anonyme')
    title = data.get('title', 'Novice Niv.1')
    
    if peer_id:
        connected_users[request.sid] = {
            'peer_id': peer_id,
            'pseudo': pseudo,
            'title': title
        }
        # Diffuse la liste globale mise à jour des pairs en ligne
        emit('peer_discovery', list(connected_users.values()), broadcast=True)

@socketio.on('send_chat_message')
def handle_global_msg(data):
    """ Relais des messages globaux pour synchroniser l'ensemble du réseau """
    emit('global_chat_message', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        del connected_users[request.sid]
        emit('peer_discovery', list(connected_users.values()), broadcast=True)
    print(f"[-] Client déconnecté : {request.sid}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
