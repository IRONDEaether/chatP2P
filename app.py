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
    max_http_buffer_size=1e7
)

# Registre complet des utilisateurs connectés
active_peers = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"[+] Nouveau client : {request.sid}")

@socketio.on('register')
def handle_register(data):
    peer_id = data.get('peer_id')
    if peer_id:
        active_peers[request.sid] = {
            'peer_id': peer_id,
            'pseudo': data.get('pseudo', 'Anonyme'),
            'title': data.get('title', 'Novice Niv.1'),
            'age': data.get('age', 'N/A'),
            'sexe': data.get('sexe', 'N/A'),
            'pays': data.get('pays', 'N/A'),
            'photo': data.get('photo', '')
        }
        peers_list = list(active_peers.values())
        emit('peer_discovery', peers_list, broadcast=True)

@socketio.on('join_room')
def handle_join(data):
    room = data.get('room')
    if room:
        join_room(room)
        if request.sid in active_peers:
            active_peers[request.sid]['room'] = room
        emit('peer_joined', {'peer_id': request.sid}, to=room, include_self=False)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    # Diffusion du message à tout le réseau ou au destinataire ciblé
    target = data.get('target', 'main')
    if target in ['main', 'fomo', 'talk'] or target.startsWith('custom_'):
        emit('chat_message', data, broadcast=True, include_self=False)
    else:
        # Message privé pour un pair spécifique
        for sid, p_data in active_peers.items():
            if p_data['peer_id'] == target:
                emit('chat_message', data, to=sid)

@socketio.on('typing')
def handle_typing(data):
    emit('user_typing', data, broadcast=True, include_self=False)

@socketio.on('message_seen')
def handle_seen(data):
    emit('message_seen_ack', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    peer_info = active_peers.pop(request.sid, None)
    if peer_info:
        peers_list = list(active_peers.values())
        emit('peer_discovery', peers_list, broadcast=True)
    print(f"[-] Client déconnecté : {request.sid}")

if __name__ == '__main__':
    print("🚀 Serveur AOO1 V1.7 Opérationnel sur le port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
