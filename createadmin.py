import sqlite3

def create_admin_user():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Admin user details
    id_number = '6969'
    last_name = 'Admin'
    first_name = 'User'
    middle_name = 'Mastah'
    course = 'Admin'
    year_level = '1'
    email = 'admin@example.com'
    username = 'admin'
    password = '1234'
    role = 'admin'

    # Insert admin user
    try:
        cursor.execute("""
            INSERT INTO users (id_number, last_name, first_name, middle_name, course, year_level, email, username, password, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_number, last_name, first_name, middle_name, course, year_level, email, username, password, role))
        conn.commit()
        print("Admin user created successfully!")
    except sqlite3.IntegrityError:
        print("Admin user already exists or there was an error.")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_user()