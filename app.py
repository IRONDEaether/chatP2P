from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

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
    peer_id = profile.get('peer_id')
    if not peer_id:
        return
    
    users_online[request.sid] = {
        'sid': request.sid,
        'peer_id': peer_id,
        'pseudo': profile.get('pseudo', 'Junior'),
        'age': profile.get('age', '16'),
        'sexe': profile.get('sexe', 'Mâle'),
        'pays': profile.get('pays', 'Mali'),
        'photo': profile.get('photo', '')
    }
    
    join_room(peer_id)
    emit('update_users', list(users_online.values()), broadcast=True)

# Envoi de message avec notification & accusé
@socketio.on('send_chat_message')
def handle_chat_message(data):
    target_id = data.get('target_id')
    if target_id:
        emit('receive_chat_message', data, room=target_id)

# Relais de confirmation "Vu" (Accusé de lecture)
@socketio.on('message_seen')
def handle_message_seen(data):
    target_id = data.get('target_id')
    if target_id:
        emit('confirm_seen', data, room=target_id)

# Signalement WebRTC P2P (Vidéo/Fin d'appel)
@socketio.on('p2p_signal')
def handle_p2p_signal(data):
    target_id = data.get('target_id')
    if target_id:
        emit('p2p_signal', data, room=target_id)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users_online:
        del users_online[request.sid]
        emit('update_users', list(users_online.values()), broadcast=True)

if __name__ == '__main__':
    print("🚀 Serveur AOO1 V5.2 ULTIME sur http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
