from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import numpy as np
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_dev_key_if_not_set')

# ─── MongoDB Setup ────────────────────────────────────────────────────────────
try:
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client['diabetes_ai_db']
    users_col = db['users']
    predictions_col = db['predictions']
    print("✅ MongoDB connected successfully.")
except Exception as e:
    print(f"⚠️  MongoDB not available: {e}")
    db = None
    users_col = None
    predictions_col = None

# ─── Load ML Model & Scaler ───────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'diabetes_model.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'scaler.pkl')

try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Model and Scaler loaded successfully.")
except Exception as e:
    model = None
    scaler = None
    print(f"⚠️  Model or Scaler could not be loaded: {e}")


# ─── Helper Functions ─────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def db_available():
    return db is not None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html', user=session.get('user_name'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_email' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Validation
        if not all([name, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        if db_available():
            if users_col.find_one({'email': email}):
                flash('Email already registered. Please log in.', 'warning')
                return redirect(url_for('login'))

            users_col.insert_one({
                'name': name,
                'email': email,
                'password': generate_password_hash(password),
                'created_at': datetime.now()
            })
        else:
            # Fallback: store in session for demo purposes
            flash('Database unavailable — demo mode.', 'info')

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_email' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')

        if db_available():
            user = users_col.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                session['user_email'] = email
                session['user_name'] = user['name']
                flash(f"Welcome back, {user['name']}! 👋", 'success')
                return redirect(url_for('predict'))
            else:
                flash('Invalid email or password.', 'danger')
        else:
            flash('Database unavailable. Cannot authenticate.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    result = None

    if request.method == 'POST':
        try:
            pregnancies        = float(request.form['pregnancies'])
            glucose            = float(request.form['glucose'])
            blood_pressure     = float(request.form['blood_pressure'])
            skin_thickness     = float(request.form['skin_thickness'])
            insulin            = float(request.form['insulin'])
            bmi                = float(request.form['bmi'])
            dpf                = float(request.form['dpf'])
            age                = float(request.form['age'])

            # --- Exact Feature Engineering from Notebook ---
            
            # 1. BMI Categories
            bmi_cat_normal = 1 if 18.5 < bmi <= 24.9 else 0
            bmi_cat_over   = 1 if 24.9 < bmi <= 29.9 else 0
            bmi_cat_ob1    = 1 if 29.9 < bmi <= 34.9 else 0
            bmi_cat_ob2    = 1 if 34.9 < bmi <= 39.9 else 0
            bmi_cat_ob3    = 1 if bmi > 39.9 else 0
            
            # 2. Glucose Categories
            gluc_cat_normal = 1 if 70 < glucose <= 99 else 0
            gluc_cat_pre    = 1 if 99 < glucose <= 126 else 0
            gluc_cat_diab   = 1 if glucose > 126 else 0
            
            # 3. Insulin Categories
            ins_cat_normal  = 1 if 16 <= insulin <= 166 else 0

            # --- Construct 17-Feature Array ---
            # Order must match X.columns from training:
            # ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI', 
            #  'DiabetesPedigreeFunction', 'Age', 'BMI_CAT_Normal', 'BMI_CAT_Overweight', 
            #  'BMI_CAT_Obesity1', 'BMI_CAT_Obesity2', 'BMI_CAT_Obesity3', 'GLUCOSE_CAT_Normal', 
            #  'GLUCOSE_CAT_Prediabetes', 'GLUCOSE_CAT_Diabetes', 'INSULIN_CAT_Normal']
            
            raw_features = np.array([[
                pregnancies, glucose, blood_pressure, skin_thickness, insulin, 
                bmi, dpf, age, 
                bmi_cat_normal, bmi_cat_over, bmi_cat_ob1, bmi_cat_ob2, bmi_cat_ob3,
                gluc_cat_normal, gluc_cat_pre, gluc_cat_diab, 
                ins_cat_normal
            ]])

            if model is None or scaler is None:
                flash('Model or scaler implies not loaded. Please contact the administrator.', 'danger')
                return render_template('predict.html', result=None)

            # --- Apply Same RobustScaler Used in Training ---
            features_scaled = scaler.transform(raw_features)

            prediction = model.predict(features_scaled)[0]

            # Try to get probability
            probability = None
            try:
                proba = model.predict_proba(features_scaled)[0]
                probability = round(float(proba[1]) * 100, 1)
            except Exception:
                pass

            result = {
                'prediction': int(prediction),
                'label': 'High Risk of Diabetes' if prediction == 1 else 'Low Risk of Diabetes',
                'risk_class': 'danger' if prediction == 1 else 'success',
                'icon': 'bi-exclamation-triangle-fill' if prediction == 1 else 'bi-shield-check',
                'probability': probability,
                'inputs': {
                    'Pregnancies': pregnancies, 'Glucose': glucose,
                    'Blood Pressure': blood_pressure, 'Skin Thickness': skin_thickness,
                    'Insulin': insulin, 'BMI': bmi,
                    'Diabetes Pedigree Function': dpf, 'Age': age
                }
            }

            # Save to MongoDB
            if db_available():
                predictions_col.insert_one({
                    'user_email': session['user_email'],
                    'pregnancies': pregnancies, 'glucose': glucose,
                    'blood_pressure': blood_pressure, 'skin_thickness': skin_thickness,
                    'insulin': insulin, 'bmi': bmi,
                    'diabetes_pedigree_function': dpf, 'age': age,
                    'prediction_result': int(prediction),
                    'prediction_label': result['label'],
                    'prediction_probability': probability,
                    'timestamp': datetime.now()
                })

        except (ValueError, KeyError) as e:
            flash(f'Invalid input: please check all fields. ({e})', 'danger')

    return render_template('predict.html', result=result)


@app.route('/dashboard')
@login_required
def dashboard():
    history = []
    if db_available():
        cursor = predictions_col.find(
            {'user_email': session['user_email']},
            sort=[('timestamp', -1)]
        )
        history = list(cursor)
        for h in history:
            h['_id'] = str(h['_id'])
            if 'timestamp' in h:
                h['timestamp'] = h['timestamp'].strftime('%b %d, %Y %I:%M %p')
    return render_template('dashboard.html', history=history)


@app.route('/about')
def about():
    return render_template('about.html', user=session.get('user_name'))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        c_name = request.form.get('c_name', '')
        c_email = request.form.get('c_email', '')
        c_subject = request.form.get('c_subject', '')
        c_message = request.form.get('c_message', '')

        if not all([c_name, c_email, c_subject, c_message]):
            flash('All contact fields are required.', 'danger')
            return redirect(url_for('contact'))

        # Retrieve email credentials from the .env file
        sender_email = os.environ.get('EMAIL_USER')
        sender_password = os.environ.get('EMAIL_PASS', '') 
        receiver_email = os.environ.get('RECEIVER_EMAIL', 'fallback@email.com')

        if not sender_password:
            flash('Email configuration (App Password) is missing on the server. Message not sent.', 'danger')
            return redirect(url_for('contact'))

        msg = EmailMessage()
        msg['Subject'] = f"DiabetesAI Contact: {c_subject}"
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg.add_header('reply-to', c_email)
        
        body = f"New message from DiabetesAI Contact Form:\n\nName: {c_name}\nEmail: {c_email}\nSubject: {c_subject}\n\nMessage:\n{c_message}\n"
        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            flash('Thank you for your message! We have received it and will get back to you soon.', 'success')
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('An error occurred while sending the message. Please try again later.', 'danger')

        return redirect(url_for('contact'))
    return render_template('contact.html', user=session.get('user_name'))


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
