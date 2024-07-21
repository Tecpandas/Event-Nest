from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    registrations = db.relationship('Registration', backref='event', lazy=True)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    team_members = db.Column(db.String(500), nullable=True)

@app.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@app.route('/post_event', methods=['GET', 'POST'])
def post_event():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        time = request.form['time']
        domain = request.form['domain']
        new_event = Event(name=name, address=address, time=time, domain=domain)
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('post_event.html')

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        team_members = request.form['team_members']
        new_registration = Registration(event_id=event_id, name=name, phone=phone, team_members=team_members)
        db.session.add(new_registration)
        db.session.commit()
        return redirect(url_for('event_detail', event_id=event_id))
    return render_template('register.html', event_id=event_id)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).all()
    return render_template('event_detail.html', event=event, registrations=registrations)

@app.route('/chat/<int:event_id>')
def chat(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).all()
    return render_template('chat.html', event=event, registrations=registrations)

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(f'{username} has joined the room.', room=room)

@socketio.on('message')
def handle_message(data):
    send(data['message'], room=data['room'])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
