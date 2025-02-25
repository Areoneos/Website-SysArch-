from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3

app = Flask(__name__, template_folder='templates')
app.secret_key = "supersecretkey"

def connect_db():
    return sqlite3.connect("users.db")

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
            session['user'] = user[1]  # Store username in session
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
    if 'user' in session:
        return render_template('dashboard.html', username=session['user'])  # Pass the username to the template
    else:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

@app.route('/info')
def info():
    if 'user' in session:
        return render_template('info.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/edit')
def edit():
    if 'user' in session:
        return render_template('edit.html', username=session['user'])
    return redirect(url_for('login'))

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