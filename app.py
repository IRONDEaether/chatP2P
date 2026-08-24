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
    default_limits=["5000 per day", "1000 per hour"],
    storage_uri="memory://"
)

# Configuration WebSocket ultra-rapide (Ping ultra court pour P2P instantane)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=5,
    ping_interval=2,
    max_http_buffer_size=5e7
)

# Registry des pairs en ligne
active_peers = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('register')
def handle_register(data):
    peer_id = data.get('peer_id')
    if peer_id:
        join_room('global_room')
        active_peers[peer_id] = {
            'sid': request.sid,
            'peer_id': peer_id,
            'pseudo': data.get('pseudo', 'Anonyme'),
            'title': data.get('title', 'Novice Niv.1'),
            'age': data.get('age', 'N/A'),
            'sexe': data.get('sexe', 'N/A'),
            'pays': data.get('pays', 'N/A'),
            'photo': data.get('photo', '')
        }
        # Diffusion instantanee de la liste des pairs connectes
        emit('peer_discovery', list(active_peers.values()), to='global_room')

@socketio.on('send_chat_message')
def handle_chat_message(data):
    target = data.get('target', 'main')
    # Routine salon public vs Message prive (PV)
    if target in ['main', 'fomo', 'talk'] or str(target).startswith('custom_'):
        emit('chat_message', data, to='global_room', include_self=False)
    else:
        dest = active_peers.get(target)
        if dest:
            emit('chat_message', data, to=dest['sid'])

@socketio.on('typing')
def handle_typing(data):
    target = data.get('target', 'main')
    if target in ['main', 'fomo', 'talk'] or str(target).startswith('custom_'):
        emit('user_typing', data, to='global_room', include_self=False)
    else:
        dest = active_peers.get(target)
        if dest:
            emit('user_typing', data, to=dest['sid'])

@socketio.on('message_seen')
def handle_seen(data):
    target = data.get('target')
    if target and target in active_peers:
        emit('message_seen_ack', data, to=active_peers[target]['sid'])
    else:
        emit('message_seen_ack', data, to='global_room', include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    to_delete = [pid for pid, info in active_peers.items() if info['sid'] == request.sid]
    for pid in to_delete:
        del active_peers[pid]
    emit('peer_discovery', list(active_peers.values()), to='global_room')

if __name__ == '__main__':
    print("🚀 Serveur AOO1 V1.7 Instant-P2P Actif sur port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
