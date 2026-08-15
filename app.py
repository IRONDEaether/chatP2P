from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aoo1_v5_ultimate_secret'

# Buffer XXL pour les photos, sons et vidéos P2P/Tunnel
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=100 * 1024 * 1024)

users_online = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register')
def handle_register(profile):
    try:
        if isinstance(profile, str):
            profile = json.loads(profile)
    except Exception:
        return

    peer_id = profile.get('peer_id') if isinstance(profile, dict) else None
    if not peer_id:
        return
    
    users_online[request.sid] = {
        'sid': request.sid,
        'peer_id': peer_id,
        'pseudo': profile.get('pseudo') or 'Anonyme',
        'age': profile.get('age') or '?',
        'sexe': profile.get('sexe', 'Mâle'),
        'pays': profile.get('pays') or 'Non spécifié',
        'photo': profile.get('photo', '')
    }
    
    join_room(peer_id)
    emit('update_users', list(users_online.values()), broadcast=True)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
    except Exception:
        return

    target_id = data.get('target_id') if isinstance(data, dict) else None
    if target_id:
        emit('receive_chat_message', data, room=target_id)

@socketio.on('message_seen')
def handle_message_seen(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
    except Exception:
        return

    target_id = data.get('target_id') if isinstance(data, dict) else None
    if target_id:
        emit('confirm_seen', data, room=target_id)

@socketio.on('p2p_signal')
def handle_p2p_signal(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
    except Exception:
        return

    target_id = data.get('target_id') if isinstance(data, dict) else None
    if target_id:
        emit('p2p_signal', data, room=target_id)

@socketio.on('disconnect')
def handle_disconnect():
    try:
        sid = request.sid
        if sid in users_online:
            del users_online[sid]
            emit('update_users', list(users_online.values()), broadcast=True)
    except RuntimeError:
        # Empêche l'erreur "Working outside of request context" si le contexte est déjà détruit
        pass

if __name__ == '__main__':
    print("🚀 Serveur AOO1 V5.2 ULTIME sur http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
