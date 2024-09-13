from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:yes@localhost/event'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    registrations = db.relationship('Registration', backref='event', lazy=True)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    team_members = db.Column(db.String(500), nullable=True)
    college_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(20), nullable=False)

# Dictionary to keep track of online users per room
online_users = {}

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
        team_members = request.form.get('team_members', '')  # Use .get to handle the case when the field is not provided
        college_name = request.form['college_name']
        branch = request.form['branch']
        year = request.form['year']
        new_registration = Registration(event_id=event_id, name=name, phone=phone, team_members=team_members,
                                        college_name=college_name, branch=branch, year=year)
        db.session.add(new_registration)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return str(e), 500
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
    
    # Separate online and offline users
    room = str(event_id)
    online_users_list = online_users.get(room, [])
    online_usernames = [user['username'] for user in online_users_list]
    offline_users = [registration for registration in registrations if registration.name not in online_usernames]

    return render_template('chat.html', event=event, registrations=registrations, 
                           online_users=online_users_list, offline_users=offline_users,
                           online_users_count=len(online_users_list), offline_users_count=len(offline_users))

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = str(data['room'])
    
    join_room(room)
    if room not in online_users:
        online_users[room] = []
    online_users[room].append({'username': username})
    
    send(f'{username} has joined the room.', room=room)
    socketio.emit('user_update', {'online_users': online_users[room]}, room=room)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = str(data['room'])
    
    leave_room(room)
    if room in online_users:
        online_users[room] = [user for user in online_users[room] if user['username'] != username]
        if not online_users[room]:
            del online_users[room]
    
    send(f'{username} has left the room.', room=room)
    socketio.emit('user_update', {'online_users': online_users.get(room, [])}, room=room)

@socketio.on('message')
def handle_message(data):
    send(data['message'], room=data['room'])

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
        
        # Hash the password using bcrypt
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

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="Root",
        password="yes",
        database="event"
    )
    return connection

@app.route('/profile')
def profile():
    # Sample data (replace with your database query)
    user = {
        "name": "Prem Mishra",
        "email": "try.prem@gmail.com",
        "upcoming_events": [
            {"title": "Box Cricket", "date": "August 15-17, 2023", "location": "Theem Coe, CA"},
            {"title": "Badminton", "date": "October 5-7, 2023", "location": "Main Ground, NY"},
        ],
        "past_events": [
            {"title": "Blind Coding", "date": "November 10-12, 2022", "location": "Web lab, IL"},
            {"title": "Pubg", "date": "November 10-12, 2022", "location": "Old building, IL"},
        ],
    }
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
