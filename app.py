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
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=10,
    ping_interval=5,
    max_http_buffer_size=1e6
)

# Registre des pairs connectés { socket_id: { peer_id, room, pseudo, title } }
active_peers = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"[+] Nouveau client connecté : {request.sid}")

@socketio.on('register')
def handle_register(data):
    peer_id = data.get('peer_id')
    pseudo = data.get('pseudo', 'Anonyme')
    title = data.get('title', 'Novice Niv.1')
    
    if peer_id:
        active_peers[request.sid] = {
            'peer_id': peer_id,
            'pseudo': pseudo,
            'title': title
        }
        # Découverte automatique des pairs
        peers_list = list(active_peers.values())
        emit('peer_discovery', peers_list, broadcast=True)

@socketio.on('join_room')
def handle_join(data):
    room = data.get('room')
    if not room or not isinstance(room, str) or len(room) > 64:
        emit('error', {'message': 'Nom de salon invalide.'})
        return

    join_room(room)
    if request.sid in active_peers:
        active_peers[request.sid]['room'] = room
    
    emit('peer_joined', {'peer_id': request.sid}, to=room, include_self=False)

@socketio.on('signal')
def handle_signal(data):
    target_id = data.get('target')
    payload = data.get('payload')

    if target_id and payload:
        emit('signal', {
            'sender': request.sid,
            'payload': payload
        }, to=target_id)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    emit('chat_message', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    peer_info = active_peers.pop(request.sid, None)
    if peer_info:
        room = peer_info.get('room')
        if room:
            leave_room(room)
            emit('peer_left', {'peer_id': peer_info['peer_id']}, to=room)
        peers_list = list(active_peers.values())
        emit('peer_discovery', peers_list, broadcast=True)
    print(f"[-] Client déconnecté : {request.sid}")

if __name__ == '__main__':
    print("🚀 Serveur P2P AOO1 lancé...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
