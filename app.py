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

        conn = connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (id_number, last_name, first_name, middle_name, course, year_level, email, username, password) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                (id_number, last_name, first_name, middle_name, course, year_level, email, username, password)
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
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch the current user's data from the database
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (session['user'],))
    user = cursor.fetchone()
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
            "password": user[8]
        }
        return render_template('dashboard.html', user=user_data)
    else:
        return redirect(url_for('login'))

@app.route('/info')
def info():
    if 'user' in session:
        return render_template('info.html', username=session['user'])
    return redirect(url_for('login'))



@app.route('/edit')
def edit():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch the current user's data from the database
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (session['user'],))
    user = cursor.fetchone()
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
            "password": user[8]
        }
        return render_template('edit.html', user=user_data)
    else:
        return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get form data
    id_number = request.form['id_number']
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    middle_name = request.form.get('middle_name', '')
    course = request.form['course']
    year_level = request.form['year_level']
    email = request.form['email']
    username = request.form['username']
    new_password = request.form['password']

    # Connect to the database
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Update user data
        if new_password:
            # Hash the new password if provided
            hashed_password = hash_password(new_password)
            cursor.execute("""
                UPDATE users 
                SET last_name = ?, first_name = ?, middle_name = ?, course = ?, year_level = ?, email = ?, username = ?, password = ?
                WHERE id_number = ?
            """, (last_name, first_name, middle_name, course, year_level, email, username, hashed_password, id_number))
        else:
            # Keep the old password if no new password is provided
            cursor.execute("""
                UPDATE users 
                SET last_name = ?, first_name = ?, middle_name = ?, course = ?, year_level = ?, email = ?, username = ?
                WHERE id_number = ?
            """, (last_name, first_name, middle_name, course, year_level, email, username, id_number))

        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template('edit.html', error="Username or email already taken", user=request.form)

    conn.close()
    return redirect(url_for('dashboard'))




@app.route('/announcement')
def announcement():
    if 'user' in session:
        return render_template('announcement.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/sessions')
def sessions():
    if 'user' in session:
        return render_template('sessions.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/rules')
def rules():
    if 'user' in session:
        return render_template('rules.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/labrules')
def labrules():
    if 'user' in session:
        return render_template('labrules.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/history')
def history():
    if 'user' in session:
        return render_template('history.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/reservations')
def reservations():
    if 'user' in session:
        return render_template('reservations.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    print("User logged out")  # Debugging purpose
    return redirect(url_for('login'))

app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'    

if __name__ == '__main__':
    app.run(debug=True)