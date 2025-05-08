from flask import Flask, render_template, request, redirect, url_for, session, make_response, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
import time

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


# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'lab_resources')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/lab-resources')
def lab_resources():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('lab-resources.html', user=user)

@app.route('/upload_lab_resource', methods=['POST'])
def upload_lab_resource():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    if 'file' not in request.files:
        return {'error': 'No file part'}, 400
    
    file = request.files['file']
    title = request.form.get('title')
    enabled = request.form.get('enableDownload') == 'on'
    
    if file.filename == '':
        return {'error': 'No selected file'}, 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        filename = f"{int(time.time())}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lab_resources (title, filename, file_path, enabled, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, filename, file_path, enabled, get_current_user()['username']))
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    return {'error': 'File type not allowed'}, 400

@app.route('/get_lab_resources')
def get_lab_resources():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get all resources for all authenticated users
    cursor.execute('''
        SELECT id, title, filename, enabled, uploaded_at
        FROM lab_resources
        ORDER BY uploaded_at DESC
    ''')
    
    resources = cursor.fetchall()
    conn.close()
    
    files = []
    for resource in resources:
        file_path = os.path.join('static', 'lab_resources', resource[2])
        preview_url = url_for('static', filename=f'lab_resources/{resource[2]}')
        
        files.append({
            'id': resource[0],
            'title': resource[1],
            'filename': resource[2],
            'enabled': bool(resource[3]),
            'uploaded_at': resource[4],
            'preview_url': preview_url
        })
    
    return {'files': files}

@app.route('/download_lab_resource/<int:file_id>')
def download_lab_resource(file_id):
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT filename, enabled FROM lab_resources WHERE id = ?', (file_id,))
    resource = cursor.fetchone()
    conn.close()
    
    if not resource:
        return {'error': 'File not found'}, 404
    
    # Check if download is enabled or user is admin
    if not resource[1] and get_current_user()['role'] != 'admin':
        return {'error': 'Download not enabled for this file'}, 403
    
    file_path = os.path.join('static', 'lab_resources', resource[0])
    return send_file(file_path, as_attachment=True)

@app.route('/delete_lab_resource/<int:file_id>', methods=['DELETE'])
def delete_lab_resource(file_id):
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get file information
    cursor.execute('SELECT filename FROM lab_resources WHERE id = ?', (file_id,))
    resource = cursor.fetchone()
    
    if not resource:
        conn.close()
        return {'error': 'File not found'}, 404
    
    # Delete file from filesystem
    file_path = os.path.join('static', 'lab_resources', resource[0])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete record from database
    cursor.execute('DELETE FROM lab_resources WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()
    
    return {'success': True}

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
def sit_in_records():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('sit-in-records.html', user=user, username=session['user'])

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
    
    # Check if points column exists in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'points' not in columns:
        cursor.execute('''
            ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0
        ''')
    
    # Create notifications table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id_number)
        )
    ''')
    
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
            feedback TEXT,
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
    
    # Create lab resources table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            uploaded_by TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users (username)
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
    
    try:
        # Search by ID number or name (case insensitive)
        cursor.execute('''
            SELECT id_number, first_name, last_name, sessions_remaining 
            FROM users 
            WHERE role = 'user' AND (
                LOWER(id_number) LIKE LOWER(?) OR 
                LOWER(first_name) LIKE LOWER(?) OR 
                LOWER(last_name) LIKE LOWER(?)
            )
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        
        students = cursor.fetchall()
        conn.close()
        
        if students:
            # Return the first matching student
            return {
                'success': True,
                'student': {
                    'id_number': students[0][0],
                    'first_name': students[0][1],
                    'last_name': students[0][2],
                    'sessions_remaining': students[0][3]
                }
            }
        return {'error': 'Student not found'}, 404
    except sqlite3.Error as e:
        conn.close()
        return {'error': f'Database error: {str(e)}'}, 500

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
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (student_id, student_name, purpose, laboratory, 'Active'))
        
        # Decrease remaining sessions
        cursor.execute('''
            UPDATE users 
            SET sessions_remaining = sessions_remaining - 1
            WHERE id_number = ?
        ''', (student_id,))
        
        # Create notification for the student
        cursor.execute('''
            INSERT INTO notifications (user_id, message, type)
            VALUES (?, ?, ?)
        ''', (student_id, f'You have been granted a sit-in session for {purpose} in Lab {laboratory}', 'sit_in_granted'))
        
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
        SET status = 'Inactive', end_time = datetime('now', 'localtime')
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
        SELECT s.student_id, s.student_name, s.purpose, s.laboratory,
               strftime('%Y-%m-%d', s.start_time) as start_date,
               strftime('%H:%M', s.start_time) as start_time,
               u.sessions_remaining
        FROM sit_in_records s
        JOIN users u ON s.student_id = u.id_number
        WHERE s.status = 'Active'
        ORDER BY s.start_time DESC
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
                'start_time': record[5],
                'sessions_remaining': record[6]
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
    
    try:
        # Create reservation record
        cursor.execute('''
            INSERT INTO reservations (student_id, student_name, purpose, laboratory, reservation_date, reservation_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, student_name, purpose, laboratory, reservation_date, reservation_time, 'Pending'))
        
        # Create notifications for all admin users
        cursor.execute('SELECT id_number FROM users WHERE role = "admin"')
        admin_ids = cursor.fetchall()
        
        for admin_id in admin_ids:
            cursor.execute('''
                INSERT INTO notifications (user_id, message, type)
                VALUES (?, ?, ?)
            ''', (admin_id[0], f'New reservation request from {student_name} for {purpose} in Lab {laboratory}', 'new_reservation'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return {'error': f'Database error: {str(e)}'}, 500

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
            
            # Create notification for the student
            cursor.execute('''
                INSERT INTO notifications (user_id, message, type)
                VALUES (?, ?, ?)
            ''', (reservation[0], f'Your reservation for {reservation[2]} in Lab {reservation[3]} has been approved!', 'reservation_approved'))
    else:  # Rejected
        # Get reservation details for rejection notification
        cursor.execute('''
            SELECT student_id, student_name, purpose, laboratory, reservation_date, reservation_time
            FROM reservations
            WHERE id = ?
        ''', (reservation_id,))
        reservation = cursor.fetchone()
        
        if reservation:
            # Create notification for the student about rejection
            cursor.execute('''
                INSERT INTO notifications (user_id, message, type)
                VALUES (?, ?, ?)
            ''', (reservation[0], f'Your reservation for {reservation[2]} in Lab {reservation[3]} on {reservation[4]} at {reservation[5]} has been rejected.', 'reservation_rejected'))
    
    # Update reservation status
    cursor.execute('''
        UPDATE reservations
        SET status = ?
        WHERE id = ?
    ''', (status, reservation_id))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

@app.route('/get_user_details/<id_number>', methods=['GET'])
def get_user_details(id_number):
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id_number, first_name, last_name, course, year_level, email, sessions_remaining
        FROM users 
        WHERE id_number = ?
    ''', (id_number,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'success': True,
            'user': {
                'id_number': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'course': user[3],
                'year_level': user[4],
                'email': user[5],
                'sessions_remaining': user[6]
            }
        }
    return {'error': 'User not found'}, 404

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id_number, first_name, last_name, course, year_level, email, sessions_remaining
        FROM users 
        ORDER BY last_name, first_name
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'users': [
            {
                'id_number': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'course': user[3],
                'year_level': user[4],
                'email': user[5],
                'sessions_remaining': user[6]
            }
            for user in users
        ]
    }

@app.route('/get_sit_in_records', methods=['GET'])
def get_sit_in_records():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    date_filter = request.args.get('date', None)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if date_filter:
        cursor.execute('''
            SELECT student_id, student_name, purpose, laboratory, 
                   strftime('%Y-%m-%d %H:%M:%S', start_time) as start_time,
                   strftime('%Y-%m-%d %H:%M:%S', end_time) as end_time,
                   feedback
            FROM sit_in_records 
            WHERE date(start_time) = ?
            ORDER BY start_time DESC
        ''', (date_filter,))
    else:
        cursor.execute('''
            SELECT student_id, student_name, purpose, laboratory, 
                   strftime('%Y-%m-%d %H:%M:%S', start_time) as start_time,
                   strftime('%Y-%m-%d %H:%M:%S', end_time) as end_time,
                   feedback
            FROM sit_in_records 
            ORDER BY start_time DESC
        ''')
    
    records = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'records': [
            {
                'student_id': record[0],
                'student_name': record[1],
                'purpose': record[2],
                'laboratory': record[3],
                'start_time': record[4],
                'end_time': record[5],
                'feedback': record[6]
            }
            for record in records
        ]
    }

@app.route('/get_sit_in_statistics', methods=['GET'])
def get_sit_in_statistics():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    date_filter = request.args.get('date', None)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Base query for filtering by date
    date_condition = "WHERE date(start_time) = ?" if date_filter else ""
    params = (date_filter,) if date_filter else ()
    
    # Get purpose statistics
    cursor.execute(f'''
        SELECT purpose, COUNT(*) as count
        FROM sit_in_records
        {date_condition}
        GROUP BY purpose
        ORDER BY count DESC
    ''', params)
    purpose_stats = [{'purpose': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    # Get laboratory statistics
    cursor.execute(f'''
        SELECT laboratory, COUNT(*) as count
        FROM sit_in_records
        {date_condition}
        GROUP BY laboratory
        ORDER BY count DESC
    ''', params)
    laboratory_stats = [{'laboratory': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'success': True,
        'purpose_stats': purpose_stats,
        'laboratory_stats': laboratory_stats
    }

@app.route('/get_dashboard_statistics', methods=['GET'])
def get_dashboard_statistics():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Get total registered students
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "user"')
        total_students = cursor.fetchone()[0]
        
        # Get currently active sit-ins
        cursor.execute('SELECT COUNT(*) FROM sit_in_records WHERE status = "Active"')
        active_sit_ins = cursor.fetchone()[0]
        
        # Get total sit-ins
        cursor.execute('SELECT COUNT(*) FROM sit_in_records')
        total_sit_ins = cursor.fetchone()[0]
        
        # Get purpose distribution
        cursor.execute('''
            SELECT purpose, COUNT(*) as count 
            FROM sit_in_records 
            GROUP BY purpose 
            ORDER BY count DESC
        ''')
        purpose_stats = [{'purpose': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        return {
            'success': True,
            'statistics': {
                'total_students': total_students,
                'active_sit_ins': active_sit_ins,
                'total_sit_ins': total_sit_ins,
                'purpose_stats': purpose_stats
            }
        }
    except sqlite3.Error as e:
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/reset_all_sessions', methods=['POST'])
def reset_all_sessions():
    if not get_current_user() or get_current_user()['role'] != 'admin':
        return {'error': 'Not authorized'}, 403
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Reset all users' sessions to 30
        cursor.execute('''
            UPDATE users 
            SET sessions_remaining = 30
            WHERE role = 'user'
        ''')
        conn.commit()
        return {'success': True, 'message': 'All sessions have been reset to 30'}
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    feedback = request.form.get('feedback')
    student_id = get_current_user()['id_number']
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # First, find the most recent inactive sit-in record for this student
        cursor.execute('''
            SELECT id FROM sit_in_records 
            WHERE student_id = ? AND status = 'Inactive'
            ORDER BY end_time DESC
            LIMIT 1
        ''', (student_id,))
        
        record = cursor.fetchone()
        
        if record:
            # Update the found record with feedback
            cursor.execute('''
                UPDATE sit_in_records 
                SET feedback = ?
                WHERE id = ?
            ''', (feedback, record[0]))
            
            conn.commit()
            return {'success': True}
        else:
            return {'error': 'No completed sit-in session found'}, 404
            
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/get_lab_resource/<int:file_id>')
def get_lab_resource(file_id):
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, filename, enabled
        FROM lab_resources
        WHERE id = ?
    ''', (file_id,))
    resource = cursor.fetchone()
    conn.close()
    
    if not resource:
        return {'error': 'File not found'}, 404
    
    return {
        'success': True,
        'file': {
            'id': resource[0],
            'title': resource[1],
            'filename': resource[2],
            'enabled': bool(resource[3])
        }
    }

@app.route('/update_lab_resource', methods=['POST'])
def update_lab_resource():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    file_id = request.form.get('fileId')
    title = request.form.get('title')
    enabled = request.form.get('enableDownload') == 'on'
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if file exists
    cursor.execute('SELECT filename FROM lab_resources WHERE id = ?', (file_id,))
    resource = cursor.fetchone()
    
    if not resource:
        conn.close()
        return {'error': 'File not found'}, 404
    
    # Handle file upload if a new file is provided
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        if file and allowed_file(file.filename):
            # Delete old file
            old_file_path = os.path.join('static', 'lab_resources', resource[0])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # Save new file
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Update database with new filename
            cursor.execute('''
                UPDATE lab_resources
                SET title = ?, filename = ?, file_path = ?, enabled = ?
                WHERE id = ?
            ''', (title, filename, file_path, enabled, file_id))
        else:
            conn.close()
            return {'error': 'Invalid file type'}, 400
    else:
        # Update only title and enabled status
        cursor.execute('''
            UPDATE lab_resources
            SET title = ?, enabled = ?
            WHERE id = ?
        ''', (title, enabled, file_id))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

@app.route('/add_points', methods=['POST'])
def add_points():
    if not get_current_user() or get_current_user()['role'] != 'admin':
        return {'error': 'Not authorized'}, 403
    
    student_id = request.form.get('student_id')
    points = int(request.form.get('points', 0))
    
    if points not in [1, 2, 3]:
        return {'error': 'Invalid points value'}, 400
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Get current points
        cursor.execute('SELECT points FROM users WHERE id_number = ?', (student_id,))
        current_points = cursor.fetchone()[0]
        
        # Calculate new total points
        new_points = current_points + points
        
        # Calculate additional sessions (1 session per 3 points)
        additional_sessions = (new_points // 3) - (current_points // 3)
        
        # Update points and sessions
        cursor.execute('''
            UPDATE users 
            SET points = points + ?,
                sessions_remaining = sessions_remaining + ?
            WHERE id_number = ?
        ''', (points, additional_sessions, student_id))
        
        conn.commit()
        
        # Get updated user data
        cursor.execute('SELECT points, sessions_remaining FROM users WHERE id_number = ?', (student_id,))
        updated_data = cursor.fetchone()
        
        return {
            'success': True,
            'message': f'Successfully added {points} point(s)!',
            'additional_sessions': additional_sessions,
            'total_points': updated_data[0],
            'sessions_remaining': updated_data[1]
        }
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/get_leaderboard')
def get_leaderboard():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id_number, first_name, last_name, points, sessions_remaining
        FROM users 
        WHERE role = 'user'
        ORDER BY points DESC
        LIMIT 5
    ''')
    
    leaderboard = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'leaderboard': [
            {
                'id_number': user[0],
                'name': f"{user[1]} {user[2]}",
                'points': user[3],
                'sessions_remaining': user[4]
            }
            for user in leaderboard
        ]
    }

@app.route('/create_notification', methods=['POST'])
def create_notification():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    notification_type = request.form.get('type')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO notifications (user_id, message, type)
            VALUES (?, ?, ?)
        ''', (user_id, message, notification_type))
        
        conn.commit()
        return {'success': True}
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/get_notifications', methods=['GET'])
def get_notifications():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    user_id = get_current_user()['id_number']
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, message, type, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    ''', (user_id,))
    
    notifications = cursor.fetchall()
    conn.close()
    
    return {
        'success': True,
        'notifications': [
            {
                'id': n[0],
                'message': n[1],
                'type': n[2],
                'is_read': bool(n[3]),
                'created_at': n[4]
            }
            for n in notifications
        ]
    }

@app.route('/mark_notification_read', methods=['POST'])
def mark_notification_read():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    notification_id = request.form.get('notification_id')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE notifications
            SET is_read = 1
            WHERE id = ? AND user_id = ?
        ''', (notification_id, get_current_user()['id_number']))
        
        conn.commit()
        return {'success': True}
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

@app.route('/delete_notification', methods=['POST'])
def delete_notification():
    if not get_current_user():
        return {'error': 'Not authenticated'}, 401
    
    notification_id = request.form.get('notification_id')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Verify the notification belongs to the current user
        cursor.execute('''
            SELECT id FROM notifications 
            WHERE id = ? AND user_id = ?
        ''', (notification_id, get_current_user()['id_number']))
        
        if not cursor.fetchone():
            return {'error': 'Notification not found or unauthorized'}, 404
        
        # Delete the notification
        cursor.execute('''
            DELETE FROM notifications
            WHERE id = ? AND user_id = ?
        ''', (notification_id, get_current_user()['id_number']))
        
        conn.commit()
        return {'success': True}
    except sqlite3.Error as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)