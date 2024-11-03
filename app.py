from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error, errorcode
import time
import hashlib
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Database Connection Configuration with Retry Mechanism
while True:
    try:
        db = mysql.connector.connect(
            host="db",
            user="root",
            password="password",
            database="user_db"
        )
        if db.is_connected():
            print("Connected to the database.")
            break
    except Error as e:
        print("Error connecting to MySQL, retrying in 5 seconds...")
        time.sleep(5)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()

        # Hash the password with MD5
        hashed_password = hashlib.md5(password.encode()).hexdigest()

        try:
            # Attempt to insert the new user with the hashed password
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            db.commit()
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError as err:
            if err.errno == errorcode.ER_DUP_ENTRY:
                flash('Username already exists. Please choose a different username.', 'error')
                return redirect(url_for('register'))
            else:
                flash('An error occurred. Please try again.', 'error')
                return redirect(url_for('register'))
    # Render the registration form if the request is GET
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor(dictionary=True)
        
        # Hash the entered password to compare with the stored hash
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_password))
        user = cursor.fetchone()
        
        if user:
            session['username'] = user['username']
            session['user_id'] = user['id']  # Store user_id in the session
            return redirect(url_for('profile'))
        flash("Invalid username or password. Please try again.", "error")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        linkedin = request.form.get('linkedin')
        about_me = request.form.get('about_me')

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print("warning")
            #flash("Invalid email format.", "error")
            #return redirect(url_for('profile'))
        
        if linkedin and not re.match(r"https?://(www\.)?linkedin\.com/.*", linkedin):
            print("warning")
            #flash("Invalid LinkedIn URL.", "error")
            #return redirect(url_for('profile'))
        
        cursor.execute("""
            UPDATE users
            SET name = %s, email = %s, phone = %s, linkedin_url = %s, about_me = %s
            WHERE username = %s
        """, (name, email, phone, linkedin, about_me, session['username']))
        
        db.commit()
        flash('Profile updated successfully', 'success')
    
    cursor.execute("SELECT * FROM users WHERE username=%s", (session['username'],))
    profile = cursor.fetchone()
    
    return render_template('profile.html', profile=profile)

@app.route('/profiles')
def public_profiles():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, phone, linkedin_url, about_me FROM users")
    profiles = cursor.fetchall()
    return render_template('public_profiles.html', profiles=profiles)

@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, email, phone, linkedin_url, about_me FROM users WHERE id=%s", (user_id,))
    profile = cursor.fetchone()
    if profile:
        return render_template('public_profile.html', profile=profile)
    else:
        return "Profile not found", 404

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if request.method == 'POST':
        if 'username' in session and 'user_id' in session:
            user_id = session['user_id']  # Get the user_id from session if it exists
            message_body = request.form['message']
            timestamp = datetime.now()

            cursor = db.cursor()
            cursor.execute("INSERT INTO messages (user_id, message_body, timestamp) VALUES (%s, %s, %s)", (user_id, message_body, timestamp))
            db.commit()
            flash('Message posted successfully!', 'success')
        else:
            flash('You need to be logged in to post a message.', 'error')
            return redirect(url_for('login'))
        return redirect(url_for('messages'))

    # Handle GET request to display messages
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT m.user_id, u.username, m.message_body, m.timestamp FROM messages m JOIN users u ON m.user_id = u.id ORDER BY m.timestamp DESC")
    messages = cursor.fetchall()
    return render_template('messages.html', messages=messages)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        if username == 'root' and hashed_password == hashlib.md5("root".encode()).hexdigest():
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, username, name, email, phone, linkedin_url FROM users")
    users = cursor.fetchall()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_users', methods=['POST'])
def reset_users():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor = db.cursor()
    cursor.execute("DELETE FROM users")
    cursor.execute("ALTER TABLE users AUTO_INCREMENT = 1")
    db.commit()
    flash('All users deleted and ID counter reset successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_messages', methods=['POST'])
def delete_messages():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor = db.cursor()
    cursor.execute("DELETE FROM messages")
    db.commit()
    flash('All messages deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_password/<int:user_id>', methods=['POST'])
def update_password(user_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    new_password = request.form['new_password']
    hashed_password = hashlib.md5(new_password.encode()).hexdigest()

    cursor = db.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
    db.commit()
    flash('Password updated successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
