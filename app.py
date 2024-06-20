from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

peers = []
group_call_rooms = []

broadcast_event_types = {
    'ACTIVE_USERS': 'ACTIVE_USERS',
    'GROUP_CALL_ROOMS': 'GROUP_CALL_ROOMS'
}

# Hello World endpoint
@app.route('/hello', methods=['GET'])
def hello():
    return "Hello World!"

@socketio.on('connect')
def handle_connection():
    emit('connection', None)
    print('new user connected')
    print(request.sid)

@socketio.on('register-new-user')
def handle_register_new_user(data):
    peers.append({
        'username': data['username'],
        'socketId': data['socketId']
    })
    print('registered new user')
    print(peers)
    
    emit('broadcast', {
        'event': broadcast_event_types['ACTIVE_USERS'],
        'activeUsers': peers
    }, broadcast=True)

    emit('broadcast', {
        'event': broadcast_event_types['GROUP_CALL_ROOMS'],
        'groupCallRooms': group_call_rooms
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('user disconnected')
    global peers, group_call_rooms
    peers = [peer for peer in peers if peer['socketId'] != request.sid]
    
    emit('broadcast', {
        'event': broadcast_event_types['ACTIVE_USERS'],
        'activeUsers': peers
    }, broadcast=True)
    
    group_call_rooms = [room for room in group_call_rooms if room['socketId'] != request.sid]
    
    emit('broadcast', {
        'event': broadcast_event_types['GROUP_CALL_ROOMS'],
        'groupCallRooms': group_call_rooms
    }, broadcast=True)

@socketio.on('pre-offer')
def handle_pre_offer(data):
    print('pre-offer handled')
    emit('pre-offer', {
        'callerUsername': data['caller']['username'],
        'callerSocketId': request.sid
    }, room=data['callee']['socketId'])

@socketio.on('pre-offer-answer')
def handle_pre_offer_answer(data):
    print('handling pre offer answer')
    emit('pre-offer-answer', {
        'answer': data['answer']
    }, room=data['callerSocketId'])

@socketio.on('webRTC-offer')
def handle_webrtc_offer(data):
    print('handling webRTC offer')
    emit('webRTC-offer', {
        'offer': data['offer']
    }, room=data['calleeSocketId'])

@socketio.on('webRTC-answer')
def handle_webrtc_answer(data):
    print('handling webRTC answer')
    emit('webRTC-answer', {
        'answer': data['answer']
    }, room=data['callerSocketId'])

@socketio.on('webRTC-candidate')
def handle_webrtc_candidate(data):
    print('handling ice candidate')
    emit('webRTC-candidate', {
        'candidate': data['candidate']
    }, room=data['connectedUserSocketId'])

@socketio.on('user-hanged-up')
def handle_user_hanged_up(data):
    emit('user-hanged-up', {}, room=data['connectedUserSocketId'])

@socketio.on('group-call-register')
def handle_group_call_register(data):
    room_id = str(uuid4())
    join_room(room_id)

    new_group_call_room = {
        'peerId': data['peerId'],
        'hostName': data['username'],
        'socketId': request.sid,
        'roomId': room_id
    }

    group_call_rooms.append(new_group_call_room)
    emit('broadcast', {
        'event': broadcast_event_types['GROUP_CALL_ROOMS'],
        'groupCallRooms': group_call_rooms
    }, broadcast=True)

@socketio.on('group-call-join-request')
def handle_group_call_join_request(data):
    join_room(data['roomId'])
    emit('group-call-join-request', {
        'peerId': data['peerId'],
        'streamId': data['streamId']
    }, room=data['roomId'])

@socketio.on('group-call-user-left')
def handle_group_call_user_left(data):
    leave_room(data['roomId'])
    emit('group-call-user-left', {
        'streamId': data['streamId']
    }, room=data['roomId'])

@socketio.on('group-call-closed-by-host')
def handle_group_call_closed_by_host(data):
    global group_call_rooms
    group_call_rooms = [room for room in group_call_rooms if room['peerId'] != data['peerId']]
    emit('broadcast', {
        'event': broadcast_event_types['GROUP_CALL_ROOMS'],
        'groupCallRooms': group_call_rooms
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, port=10000, debug=True)