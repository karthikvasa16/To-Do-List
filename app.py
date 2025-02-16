from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

# Flask App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a strong key

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'todo_db'
}

# Database Connection
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Create Tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(256) NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            category VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Call table creation function
create_tables()

# Flask Forms
class TaskForm(FlaskForm):
    id = HiddenField()  # Hidden field to track edit ID
    title = StringField('Title', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Work', 'Work'), ('Personal', 'Personal'), ('Urgent', 'Urgent')])
    status = SelectField('Status', choices=[('Pending', 'Pending'), ('Progressing', 'Progressing'), ('Completed', 'Completed')])
    submit = SubmitField('Add Task')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = TaskForm()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the username
    cursor.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    username = user['username'] if user else 'User'

    task_to_edit = None
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')

    if request.method == 'POST':
        task_id = form.id.data
        title = form.title.data
        category = form.category.data
        status = form.status.data  # Include status field
        
        if task_id:  # If an ID exists, update the task
            cursor.execute("UPDATE tasks SET title = %s, category = %s, status = %s WHERE id = %s AND user_id = %s",
                           (title, category, status, task_id, session['user_id']))
        else:  # Otherwise, add a new task
            cursor.execute("INSERT INTO tasks (title, category, status, user_id) VALUES (%s, %s, %s, %s)",
                           (title, category, status, session['user_id']))
        
        conn.commit()
        return redirect(url_for('index'))

    if request.args.get('edit_id'):  # Prefill the form for editing
        cursor.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s",
                       (request.args.get('edit_id'), session['user_id']))
        task_to_edit = cursor.fetchone()
        if task_to_edit:
            form.id.data = task_to_edit['id']
            form.title.data = task_to_edit['title']
            form.category.data = task_to_edit['category']
            form.status.data = task_to_edit['status']

    # Filter tasks based on search and status
    query = "SELECT * FROM tasks WHERE user_id = %s"
    params = [session['user_id']]
    
    if search_query:
        query += " AND title LIKE %s"
        params.append(f"%{search_query}%")
    
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    
    cursor.execute(query, tuple(params))
    tasks = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', form=form, tasks=tasks, username=username, task_to_edit=task_to_edit, search_query=search_query, status_filter=status_filter)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (form.username.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], form.password.data):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                           (form.username.data, hashed_password))
            conn.commit()
        except mysql.connector.IntegrityError:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))

        cursor.close()
        conn.close()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>')
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('index', edit_id=task_id))

@app.route('/complete/<int:task_id>')
def complete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'Completed' WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('index'))

# Run App
if __name__ == '__main__':
    app.run(debug=True)
