from flask import Blueprint, render_template, request, redirect, url_for, session
from .models import fetch_query, execute_query

main = Blueprint('main', __name__)

@main.route('/')
def index():
    events = fetch_query("SELECT * FROM event")
    # Fetch user data if logged in, else pass None for 'username'
    username = None
    if 'user_id' in session:
        user = fetch_query("SELECT * FROM user WHERE id = %s", (session['user_id'],))
        if user:
            username = user[0]['name']
    
    return render_template('index.html', events=events, username=username)

@main.route('/post_event', methods=['GET', 'POST'])
def post_event():
    if request.method == 'POST':
        event_name = request.form.get('name')
        address = request.form.get('address')
        date = request.form.get('date')
        time = request.form.get('time')
        phone = request.form.get('phone')
        domain = request.form.get('domain')
        max_participants = request.form.get('max_participants')

        query = """
            INSERT INTO event (name, address, date, time, phone, domain, max_participants)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (event_name, address, date, time, phone, domain, max_participants)
        execute_query(query, params)
        return redirect(url_for('main.index'))

    return render_template('post_event.html')

@main.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    event = fetch_query("SELECT * FROM event WHERE id = %s", (event_id,))
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
        
        query = """
            INSERT INTO registration (event_id, user_id, name, phone, team_members, college_name, branch, year)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (event_id, user_id, name, phone, team_members, college_name, branch, year)
        try:
            execute_query(query, params)
        except Exception as e:
            return str(e), 500
        return redirect(url_for('main.event_detail', event_id=event_id))

    return render_template('register.html', event=event[0])

@main.route('/event/<int:event_id>')
def event_detail(event_id):
    event = fetch_query("SELECT * FROM event WHERE id = %s", (event_id,))
    registrations = fetch_query("SELECT * FROM registration WHERE event_id = %s", (event_id,))
    return render_template('event_detail.html', event=event[0], registrations=registrations)

@main.route('/event/<int:event_id>/chat', methods=['GET', 'POST'])
def event_chat(event_id):
    event = fetch_query("SELECT * FROM event WHERE id = %s", (event_id,))
    if 'user_id' in session:
        user = fetch_query("SELECT * FROM user WHERE id = %s", (session['user_id'],))
        username = user[0]['name']
    else:
        username = 'Guest'
    
    return render_template('chat.html', event=event[0], username=username)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Import bcrypt locally to avoid circular import
        from . import bcrypt
        user = fetch_query("SELECT * FROM user WHERE email = %s", (email,))
        if user and bcrypt.check_password_hash(user[0]['password'], password):
            session['user_id'] = user[0]['id']
            return redirect(url_for('main.index'))
        else:
            return 'Invalid email or password', 401
    return render_template('login.html')

@main.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Import bcrypt locally to avoid circular import
        from . import bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        query = """
            INSERT INTO user (name, email, password) 
            VALUES (%s, %s, %s)
        """
        params = (name, email, hashed_password)
        try:
            execute_query(query, params)
        except Exception as e:
            return str(e), 500
        return redirect(url_for('main.login'))
    return render_template('signup.html')

@main.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user = fetch_query("SELECT * FROM user WHERE id = %s", (session['user_id'],))[0]
    upcoming_events = fetch_query("""
        SELECT * FROM event 
        WHERE date >= CURDATE() 
        AND id IN (SELECT event_id FROM registration WHERE user_id = %s)
    """, (user['id'],))
    
    past_events = fetch_query("""
        SELECT * FROM event 
        WHERE date < CURDATE() 
        AND id IN (SELECT event_id FROM registration WHERE user_id = %s)
    """, (user['id'],))

    badge = None
    registration_count = len(fetch_query("SELECT * FROM registration WHERE user_id = %s", (user['id'],)))
    if registration_count > 10:
        badge = 'gold'
    elif registration_count > 5:
        badge = 'red'

    return render_template('profile.html', user=user, upcoming_events=upcoming_events, past_events=past_events, badge=badge)

@main.route('/edit_profile', methods=['POST'])
def edit_profile():
    return redirect(url_for('main.profile'))

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))
