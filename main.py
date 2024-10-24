from flask import Flask,render_template, request, redirect, url_for, session, send_file
from flask_mysqldb import MySQL
import mysql.connector
import io

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
        return render_template('home.html', email=session['email'])
    else:
        return render_template('login.html')

# Route for the library page
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
        email = request.form['email']
        pwd = request.form['password']
        cpwd = request.form['confirm-password']
        
        if pwd != cpwd:
            return render_template('register.html')
        
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, pwd))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return render_template('register.html')           
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
    if 'pdf_file' not in request.files:
        return redirect(url_for('library'))

    file = request.files['pdf_file']
    if file.filename == '':
        return redirect(url_for('library'))

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        return "Only PDF files are allowed", 400

    # Read the file in binary
    file_data = file.read()

    # Log file size for debugging
    print(f"Uploading file: {file.filename}, Size: {len(file_data)} bytes")

    cursor = conn.cursor()
    try:
        # Insert the file into the BLOB column
        cursor.execute("INSERT INTO documents (filename, file) VALUES (%s, %s)", (file.filename, file_data))
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

if __name__ == '__main__':
    app.run(debug=True)