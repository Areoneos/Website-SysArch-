from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__, template_folder='templates')
app.secret_key = "supersecretkey"

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
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = user[1]  # Store username in session
        return redirect(url_for('info'))  # Redirect to info.html after login
    else:
        return render_template('index.html', error="Invalid credentials")

@app.route('/info')
def info():
    if 'user' in session:
        return render_template('info.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/edit')
def edit():
    if 'user' in session:
        return render_template('edit.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/announcement')
def announcement():
    if 'user' in session:
        return render_template('announcement.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/sessions')
def sessions():
    if 'user' in session:
        return render_template('sessions.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/rules')
def rules():
    if 'user' in session:
        return render_template('rules.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/labrules')
def labrules():
    if 'user' in session:
        return render_template('labrules.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/history')
def history():
    if 'user' in session:
        return render_template('history.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/reservations')
def reservations():
    if 'user' in session:
        return render_template('reservations.html', username=session['user'])
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logs out the user by clearing the session and redirecting to the login page."""
    session.clear()  # Clear all session data
    return redirect(url_for('index'))  # Redirect to the login page

@app.route('/register', methods=['POST'])
def register():
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
        return render_template('index.html', error="Username or ID Number already taken")

    conn.close()
    return redirect(url_for('index', success=True))

if __name__ == '__main__':
    app.run(debug=True)
