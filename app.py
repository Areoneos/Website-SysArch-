from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__, template_folder='templates')
app.secret_key = "supersecretkey"

# Database connection function
def connect_db():
    return sqlite3.connect("users.db")

@app.route('/')
def index():
    return render_template('index.html', registration_success=request.args.get('success', False))

@app.route('/index', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    
    conn.close()

    if user:
        session['user'] = user[1]  # Store username in session
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html', error="Invalid credentials")

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return f"Welcome, {session['user']}! <a href='/logout'>Logout</a>"
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    id_number = request.form['id_number']
    last_name = request.form['last_name']
    first_name = request.form['first_name']
    middle_name = request.form.get('middle_name', '')  # Optional
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
        return render_template('index.html', error="Username or ID Number already taken")

    conn.close()
    return redirect(url_for('index', success=True))

if __name__ == '__main__':
    app.run(debug=True)
