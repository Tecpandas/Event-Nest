from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)

# Configuration settings
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://Root:yes@localhost/event'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    registrations = db.relationship('Registration', backref='user', lazy=True)

# Event model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    registrations = db.relationship('Registration', backref='event', lazy=True)
    messages = db.relationship('Message', backref='event', lazy=True)

# Registration model
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    team_members = db.Column(db.String(500), nullable=True)
    college_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(20), nullable=False)

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

online_users = {}

# Routes
@app.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@app.route('/post_event', methods=['GET', 'POST'])
def post_event():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        date = request.form['date']
        time = request.form['time']
        phone = request.form['phone']
        domain = request.form['domain']
        new_event = Event(name=name, address=address, date=date, time=time, phone=phone, domain=domain)
        db.session.add(new_event)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return str(e), 500
        return redirect(url_for('index'))
    return render_template('post_event.html')

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    event = Event.query.get(event_id)
    if not event:
        return "Event not found", 404
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        team_members = request.form.get('team_members', '')
        college_name = request.form['college_name']
        branch = request.form['branch']
        year = request.form['year']
        if 'user_id' in session:
            user_id = session['user_id']
        else:
            return "User not logged in", 403
        new_registration = Registration(event_id=event_id, user_id=user_id, name=name, phone=phone, team_members=team_members,
                                        college_name=college_name, branch=branch, year=year)
        db.session.add(new_registration)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return str(e), 500
        return redirect(url_for('event_detail', event_id=event_id))
    return render_template('register.html', event=event)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).all()
    return render_template('event_detail.html', event=event, registrations=registrations)

@app.route('/event/<int:event_id>/chat', methods=['GET', 'POST'])
def event_chat(event_id):
    event = Event.query.get_or_404(event_id)
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.name
    else:
        username = 'Guest'
    
    return render_template('chat.html', event=event, username=username)

@socketio.on('join')
def handle_join(data):
    username = data['username']
    event_id = data['event_id']
    room = f"event_{event_id}"
    join_room(room)
    emit('message', {'msg': f'{username} has joined the chat.'}, to=room)

@socketio.on('message')
def handle_message(data):
    event_id = data['event_id']
    room = f"event_{event_id}"
    message = Message(content=data['msg'], user_id=data['user_id'], event_id=event_id)
    db.session.add(message)
    db.session.commit()
    emit('message', {'username': data['username'], 'msg': data['msg']}, to=room)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    event_id = data['event_id']
    room = f"event_{event_id}"
    leave_room(room)
    emit('message', {'msg': f'{username} has left the chat.'}, to=room)

@app.route('/event/<int:event_id>/messages')
def get_messages(event_id):
    messages = Message.query.filter_by(event_id=event_id).all()
    return {'messages': [{'username': User.query.get(m.user_id).name, 'content': m.content} for m in messages]}

@app.route('/event/<int:event_id>/participants')
def get_participants(event_id):
    registrations = Registration.query.filter_by(event_id=event_id).all()
    return {'participants': [{'name': User.query.get(r.user_id).name} for r in registrations]}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return 'Invalid email or password', 401
    return render_template('login.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return str(e), 500
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    upcoming_events = Event.query.join(Registration).filter(Registration.user_id == user.id).filter(Event.date >= '2024-01-01').all()
    past_events = Event.query.join(Registration).filter(Registration.user_id == user.id).filter(Event.date < '2024-01-01').all()
    
    return render_template('profile.html', user=user, upcoming_events=upcoming_events, past_events=past_events)

@app.route('/logout')
def logout():
    session.pop('user_id', None)  
    return redirect(url_for('login'))  

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    socketio.run(app, debug=True)
