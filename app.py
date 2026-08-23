import os
import secrets
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Limiteur de requêtes pour éviter le spam et les attaques DoS
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration SocketIO blindée
# Remplace 'http://localhost:5000' par ton domaine réel en prod !
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # En prod, restreins à ton domaine exact
    ping_timeout=10,
    ping_interval=5,
    max_http_buffer_size=1e6  # Limite la taille des messages à 1 Mo max
)

# Stockage ultra-temporaire en mémoire RAM uniquement (Effacé à la déconnexion)
# Structure: { socket_id: room_id }
active_peers = {}

@app.route('/')
def index():
    """ Sert le fichier HTML si nécessaire """
    return render_template('index.html')

# --- LOGIQUE DE SIGNALISATION P2P SECURISEE ---

@socketio.on('connect')
def handle_connect():
    """ Connexion d'un pair """
    print(f"[+] Nouveau client connecté : {request.sid}")

@socketio.on('join_room')
def handle_join(data):
    """
    Permet à un utilisateur de rejoindre un salon P2P privé.
    Validation stricte des données entrantes.
    """
    room = data.get('room')
    if not room or not isinstance(room, str) or len(room) > 64:
        emit('error', {'message': 'Nom de salon invalide.'})
        return

    # Connexion au salon
    join_room(room)
    active_peers[request.sid] = room
    
    # Notifier les autres pairs présents dans la room qu'un nouveau est là
    emit('peer_joined', {'peer_id': request.sid}, to=room, include_self=False)
    print(f"[P2P] Client {request.sid} a rejoint la room: {room}")

@socketio.on('signal')
def handle_signal(data):
    """
    Transmet l'offre/réponse SDP ou le candidat ICE directement au destinataire.
    AUCUNE donnée n'est écrite sur le disque.
    """
    target_id = data.get('target')
    payload = data.get('payload')

    if not target_id or not payload:
        return

    # Transmet le paquet WebRTC directement au destinataire ciblé
    emit('signal', {
        'sender': request.sid,
        'payload': payload
    }, to=target_id)

@socketio.on('disconnect')
def handle_disconnect():
    """
    Nettoyage instantané à la déconnexion.
    Aucune trace laissée dans le système.
    """
    room = active_peers.pop(request.sid, None)
    if room:
        leave_room(room)
        emit('peer_left', {'peer_id': request.sid}, to=room)
    print(f"[-] Client déconnecté et nettoyé : {request.sid}")


if __name__ == '__main__':
    # Mode production sécurisé : désactive le debug !
    # Utilise gevent ou eventlet pour des performances P2P maximales
    print("🚀 Serveur de signalisation P2P blindé lancé...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
