from flask import Flask,render_template, request, redirect, url_for, session, send_file
from flask_mysqldb import MySQL
import mysql.connector
import io
import time

app=Flask(__name__)
app.secret_key = 'your_secret_key_here'

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''
MYSQL_DB = 'library'

conn = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB
)

@app.route('/')
def home():
    if 'email' in session:
        email = session['email']
        user_info = None

        cursor = conn.cursor()
        cursor.execute("SELECT username, email, telephone, dob FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()

        # Convert result tuple to dictionary if user info is found
        if result:
            user_info = {
                'username': result[0],
                'email': result[1],
                'telephone': result[2],
                'dob': result[3]
            }

        return render_template('home.html', user_info=user_info, email=session['email'])
    else:
        return render_template('login.html')

@app.route('/library')
def library():
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, filename FROM documents")
    files = cursor.fetchall()
    cursor.close()
    return render_template('library.html', files=files)    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        telephone = request.form['phone']
        dob = request.form['dob']
        pwd = request.form['password']
        cpwd = request.form['confirm-password']
        
        if pwd != cpwd:
            return render_template('register.html', error="Passwords do not match.")
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, telephone, password, dob) 
                VALUES (%s, %s, %s, %s, %s)
            """, (username, email, telephone, pwd, dob))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return render_template('register.html', error="Registration failed.")
        finally:
            cursor.close()

        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods =['GET','POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        pwd = request.form['password']

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email, password FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        except Exception as e:
            return render_template('login.html')
        cursor.close()

        if user and pwd == user[1]:
            session['email'] = user[0]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid email or password')
        
    return render_template('login.html')

@app.route('/logout', methods =['GET','POST'])
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files or 'cover_photo' not in request.files:
        return redirect(url_for('library'))

    pdf_file = request.files['pdf_file']
    cover_photo = request.files['cover_photo']

    if pdf_file.filename == '' or cover_photo.filename == '':
        return redirect(url_for('library'))

    # Validate PDF file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        return "Only PDF files are allowed", 400

    # Validate cover photo file type
    if not (cover_photo.filename.lower().endswith('.png') or cover_photo.filename.lower().endswith('.jpg')):
        return "Only PNG and JPG files are allowed for the cover photo", 400

    # Read the files in binary
    pdf_data = pdf_file.read()
    cover_data = cover_photo.read()

    cursor = conn.cursor()
    try:
        # Insert the files into the respective BLOB columns
        cursor.execute(
            "INSERT INTO documents (filename, file, coverphoto) VALUES (%s, %s, %s)",
            (pdf_file.filename, pdf_data, cover_data)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error during file upload: {str(e)}")  # Log the error
        return str(e)
    finally:
        cursor.close()

    return redirect(url_for('library'))

@app.route('/download/<int:file_id>')
def download_file(file_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT filename, file FROM documents WHERE id = %s", (file_id,))
    file = cursor.fetchone()
    cursor.close()

    if file:
        # Check the length of the file data
        if file['file'] is not None:
            print(f"Retrieved file size: {len(file['file'])} bytes")
            return send_file(io.BytesIO(file['file']),
                             download_name=file['filename'],
                             as_attachment=True,
                             mimetype='application/pdf')
    return "File not found", 404

@app.route('/cover/<int:file_id>')
def cover_photo(file_id):
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT coverphoto FROM documents WHERE id = %s", (file_id,))
        cover = cursor.fetchone()
        
        cursor.close()

        if cover and cover['coverphoto'] is not None:
            return send_file(io.BytesIO(cover['coverphoto']), mimetype='image/jpeg')
        return "Cover photo not found", 404

    except Exception as e:
        print(f"Database error: {e}")
        cover_photo(file_id)
        return "An error occurred with the database connection", 500

def is_valid_pdf(file_data):
    # Basic check for PDF header
    return file_data.startswith(b'%PDF')

if __name__ == '__main__':
    app.run(debug=True)