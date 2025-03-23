from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3

app = Flask(__name__, template_folder='templates')
app.secret_key = "supersecretkey"
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

def connect_db():
    return sqlite3.connect("users.db")

def query_db(query, args=(), one=False):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        result = cursor.fetchall()
        conn.commit()
    return (result[0] if result else None) if one else result

def get_current_user():
    if 'user' not in session:
        return None

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (session['user'],))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "id_number": user[0],
            "last_name": user[1],
            "first_name": user[2],
            "middle_name": user[3],
            "course": user[4],
            "year_level": user[5],
            "email": user[6],
            "username": user[7],
            "password": user[8],
            "profile_picture": user[9] if len(user) > 9 else None,
            "role": user[10]
        }
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[7]  # Store username in session
            session['role'] = user[10]  # Store role in session
            return redirect(url_for('dashboard'))  # Redirect to dashboard.html after login
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        id_number = request.form['id_number']
        last_name = request.form['last_name']
        first_name = request.form['first_name']
        middle_name = request.form.get('middle_name', '')
        course = request.form['course']
        year_level = request.form['year_level']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = 'user'

        conn = connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (id_number, last_name, first_name, middle_name, course, year_level, email, username, password, role) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                (id_number, last_name, first_name, middle_name, course, year_level, email, username, password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Username or ID Number already taken")

        conn.close()
        return redirect(url_for('login', success=True))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Fetch announcements
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', user=user, announcements=announcements)


@app.route('/edit')
def edit():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Fetch the current user's data from the database
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (session['user'],))
    user = cursor.fetchone()

     # Fetch announcements from the database
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    conn.close()

    if user:
        # Convert the tuple to a dictionary for easier access in the template
        user_data = {
            "id_number": user[0],
            "last_name": user[1],
            "first_name": user[2],
            "middle_name": user[3],
            "course": user[4],
            "year_level": user[5],
            "email": user[6],
            "username": user[7],
            "password": user[8],
            "profile_picture": user[9] if len(user) > 9 else None,  # Add profile_picture field
            "role": user[10]
        }
        return render_template('edit.html', user=user_data)


import os
from flask import request, redirect, url_for, session, flash
import sqlite3

# Function to connect to the database
def connect_db():
    return sqlite3.connect("users.db")

# Function to get the absolute path of the profile_pictures folder
def get_profile_pictures_folder():
    # Get the absolute path of the current directory
    base_dir = os.path.abspath(os.path.dirname(__file__))
    # Create the profile_pictures folder if it doesn't exist
    profile_pictures_dir = os.path.join(base_dir, 'static', 'profile_pictures')
    if not os.path.exists(profile_pictures_dir):
        os.makedirs(profile_pictures_dir)
    return profile_pictures_dir

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Get the current username from the session
    username = session['user']

    # Fetch form data
    id_number = request.form['id_number']
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    middle_name = request.form.get('middle_name', '')
    course = request.form['course']
    year_level = request.form['year_level']
    email = request.form['email']
    new_username = request.form['username']
    new_password = request.form['password']

    # Handle profile picture upload
    profile_picture = None
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename != '':
            # Generate a unique filename
            filename = f"user_{username}_profile_picture.{file.filename.split('.')[-1]}"
            # Get the absolute path to the profile_pictures folder
            profile_pictures_dir = get_profile_pictures_folder()
            file_path = os.path.join(profile_pictures_dir, filename)
            # Save the file
            file.save(file_path)
            profile_picture = filename

    # Connect to the database
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Update user data in the database
        if new_password:
            # Hash the new password if provided
            hashed_password = hash_password(new_password)
            if profile_picture:
                cursor.execute("""
                    UPDATE users 
                    SET id_number = ?, last_name = ?, first_name = ?, middle_name = ?, 
                        course = ?, year_level = ?, email = ?, username = ?, password = ?, profile_picture = ?
                    WHERE username = ?
                """, (id_number, last_name, first_name, middle_name, course, year_level, email, new_username, hashed_password, profile_picture, username))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET id_number = ?, last_name = ?, first_name = ?, middle_name = ?, 
                        course = ?, year_level = ?, email = ?, username = ?, password = ?
                    WHERE username = ?
                """, (id_number, last_name, first_name, middle_name, course, year_level, email, new_username, hashed_password, username))
        else:
            if profile_picture:
                cursor.execute("""
                    UPDATE users 
                    SET id_number = ?, last_name = ?, first_name = ?, middle_name = ?, 
                        course = ?, year_level = ?, email = ?, username = ?, profile_picture = ?
                    WHERE username = ?
                """, (id_number, last_name, first_name, middle_name, course, year_level, email, new_username, profile_picture, username))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET id_number = ?, last_name = ?, first_name = ?, middle_name = ?, 
                        course = ?, year_level = ?, email = ?, username = ?
                    WHERE username = ?
                """, (id_number, last_name, first_name, middle_name, course, year_level, email, new_username, username))

        conn.commit()
        flash('Profile updated successfully!', 'success')
    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Username or email already taken.', 'error')
    finally:
        conn.close()

    # Update the session username if it was changed
    if new_username != username:
        session['user'] = new_username

    return redirect(url_for('dashboard'))



@app.route('/announcement')
def announcement():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('announcement.html', user=user, username=session['user'])

@app.route('/post_announcement', methods=['POST'])
def post_announcement():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    username = session['user']
    announcement = request.form['announcement']

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (username, announcement) VALUES (?, ?)", (username, announcement))
    conn.commit()
    conn.close()

    flash('Announcement posted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reservations')
def reservations():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('reservations.html', user=user, username=session['user'])

@app.route('/feedback')
def feedback():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('feedback.html', user=user, username=session['user'])

@app.route('/search')
def search():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('search.html', user=user, username=session['user'])

@app.route('/sit-in-reports')
def sit_in_reports():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('sit-in-reports.html', user=user, username=session['user'])

@app.route('/sit-in')
def sit_in():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('sit-in.html', user=user, username=session['user'])

@app.route('/students')
def students():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('students.html', user=user, username=session['user'])

@app.route('/view-sit-in-records')
def view_sit_in_records():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('view-sit-in-records.html', user=user, username=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    print("User logged out")  # Debugging purpose
    return redirect(url_for('login'))

app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'    

def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    
    # Create sit-in records table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sit_in_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            purpose TEXT NOT NULL,
            laboratory TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id_number)
        )
    ''')
    
    # Create reservations table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            purpose TEXT NOT NULL,
            laboratory TEXT NOT NULL,
            reservation_date DATE NOT NULL,
            reservation_time TIME NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id_number)
        )
    ''')
    
    # Check if sessions_remaining column exists in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'sessions_remaining' not in columns:
        cursor.execute('''
            ALTER TABLE users ADD COLUMN sessions_remaining INTEGER DEFAULT 30
        ''')
    
    conn.commit()
    conn.close()

# Initialize database tables
init_db()

@app.route('/search_student', methods=['POST'])
def search_student():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    search_term = request.form.get('search_term', '')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Search by ID number or name
    cursor.execute('''
        SELECT id_number, first_name, last_name 
        FROM users 
        WHERE id_number LIKE ? OR first_name LIKE ? OR last_name LIKE ?
    ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
    
    students = cursor.fetchall()
    conn.close()
    
    if students:
        return {
            'success': True,
            'student': {
                'id_number': students[0][0],
                'name': f"{students[0][1]} {students[0][2]}"
            }
        }
    return {'error': 'Student not found'}, 404

@app.route('/get_remaining_sessions', methods=['GET'])
def get_remaining_sessions():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    # Get student_id from query parameters if provided, otherwise use current user's ID
    student_id = request.args.get('student_id', get_current_user()['id_number'])
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT sessions_remaining FROM users WHERE id_number = ?', (student_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {'success': True, 'sessions_remaining': result[0]}
    return {'error': 'User not found'}, 404

@app.route('/start_sit_in', methods=['POST'])
def start_sit_in():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    student_id = request.form.get('student_id')
    purpose = request.form.get('purpose')
    laboratory = request.form.get('laboratory')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if student is already active
    cursor.execute('SELECT COUNT(*) FROM sit_in_records WHERE student_id = ? AND status = "Active"', (student_id,))
    active_count = cursor.fetchone()[0]
    
    if active_count > 0:
        conn.close()
        return {'error': 'Student already has an active sit-in session'}, 400
    
    # Check remaining sessions
    cursor.execute('SELECT first_name, last_name, sessions_remaining FROM users WHERE id_number = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return {'error': 'Student not found'}, 404
    
    if student[2] <= 0:
        conn.close()
        return {'error': 'No remaining sessions'}, 400
    
    student_name = f"{student[0]} {student[1]}"
    
    try:
        # Create sit-in record with current timestamp in local time
        cursor.execute('''
            INSERT INTO sit_in_records (student_id, student_name, purpose, laboratory, status, start_time)
            VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        ''', (student_id, student_name, purpose, laboratory, 'Active'))
        
        # Decrease remaining sessions
        cursor.execute('''
            UPDATE users 
            SET sessions_remaining = sessions_remaining - 1
            WHERE id_number = ?
        ''', (student_id,))
        
        conn.commit()
        conn.close()
        return {'success': True}
        
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return {'error': f'Database error: {str(e)}'}, 500

@app.route('/end_sit_in', methods=['POST'])
def end_sit_in():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    student_id = request.form.get('student_id')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE sit_in_records 
        SET status = 'Inactive', end_time = CURRENT_TIMESTAMP
        WHERE student_id = ? AND status = 'Active'
    ''', (student_id,))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

@app.route('/get_active_sit_ins', methods=['GET'])
def get_active_sit_ins():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT student_id, student_name, purpose, laboratory,
               strftime('%Y-%m-%d', start_time) as start_date,
               strftime('%H:%M', start_time) as start_time
        FROM sit_in_records
        WHERE status = 'Active'
        ORDER BY start_time DESC
    ''')
    
    active_sit_ins = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'active_sit_ins': [
            {
                'student_id': record[0],
                'student_name': record[1],
                'purpose': record[2],
                'laboratory': record[3],
                'start_date': record[4],
                'start_time': record[5]
            }
            for record in active_sit_ins
        ]
    }

@app.route('/create_reservation', methods=['POST'])
def create_reservation():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    # Get current user's ID
    student_id = get_current_user()['id_number']
    purpose = request.form.get('purpose')
    laboratory = request.form.get('laboratory')
    reservation_date = request.form.get('reservation_date')
    reservation_time = request.form.get('reservation_time')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get student name and check remaining sessions
    cursor.execute('SELECT first_name, last_name, sessions_remaining FROM users WHERE id_number = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return {'error': 'Student not found'}, 404
    
    if student[2] <= 0:
        conn.close()
        return {'error': 'No remaining sessions'}, 400
    
    student_name = f"{student[0]} {student[1]}"
    
    # Create reservation record
    cursor.execute('''
        INSERT INTO reservations (student_id, student_name, purpose, laboratory, reservation_date, reservation_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, student_name, purpose, laboratory, reservation_date, reservation_time, 'Pending'))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

@app.route('/get_user_reservations', methods=['GET'])
def get_user_reservations():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    student_id = get_current_user()['id_number']
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, purpose, laboratory, reservation_date, reservation_time, status, created_at
        FROM reservations
        WHERE student_id = ?
        ORDER BY created_at DESC
    ''', (student_id,))
    
    reservations = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'reservations': [
            {
                'id': record[0],
                'purpose': record[1],
                'laboratory': record[2],
                'reservation_date': record[3],
                'reservation_time': record[4],
                'status': record[5],
                'created_at': record[6]
            }
            for record in reservations
        ]
    }

@app.route('/get_pending_reservations', methods=['GET'])
def get_pending_reservations():
    if not get_current_user() or get_current_user()['role'] != 'admin':
        return {'error': 'Not authorized'}, 403
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, student_id, student_name, purpose, laboratory, reservation_date, reservation_time, created_at
        FROM reservations
        WHERE status = 'Pending'
        ORDER BY created_at DESC
    ''')
    
    reservations = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'reservations': [
            {
                'id': record[0],
                'student_id': record[1],
                'student_name': record[2],
                'purpose': record[3],
                'laboratory': record[4],
                'reservation_date': record[5],
                'reservation_time': record[6],
                'created_at': record[7]
            }
            for record in reservations
        ]
    }

@app.route('/update_reservation_status', methods=['POST'])
def update_reservation_status():
    if not get_current_user() or get_current_user()['role'] != 'admin':
        return {'error': 'Not authorized'}, 403
    
    reservation_id = request.form.get('reservation_id')
    status = request.form.get('status')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if status == 'Approved':
        # Get reservation details
        cursor.execute('''
            SELECT student_id, student_name, purpose, laboratory, reservation_date, reservation_time
            FROM reservations
            WHERE id = ?
        ''', (reservation_id,))
        reservation = cursor.fetchone()
        
        if reservation:
            # Create sit-in record with current timestamp in local time (same as direct sit-in)
            cursor.execute('''
                INSERT INTO sit_in_records (student_id, student_name, purpose, laboratory, status, start_time)
                VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            ''', (reservation[0], reservation[1], reservation[2], reservation[3], 'Active'))
            
            # Decrease remaining sessions
            cursor.execute('''
                UPDATE users 
                SET sessions_remaining = sessions_remaining - 1
                WHERE id_number = ?
            ''', (reservation[0],))
    
    # Update reservation status
    cursor.execute('''
        UPDATE reservations
        SET status = ?
        WHERE id = ?
    ''', (status, reservation_id))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

if __name__ == '__main__':
    app.run(debug=True)