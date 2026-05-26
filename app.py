from flask import Flask, render_template, request, redirect, url_for, session, flash
# pyrefly: ignore [missing-import]
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
# pyrefly: ignore [missing-import]
import joblib
import numpy as np
from datetime import datetime, timedelta   # timedelta is used to set OTP expiry time
import os
import smtplib
import random                               # used to generate the 6-digit OTP
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
    # ── NEW: temporary collection to hold unverified signups ──────────────────
    # Each document here lives for at most 5 minutes (until OTP is confirmed).
    # Once verified, the user is moved to the real 'users' collection.
    otp_col = db['otp_pending']
    print("[SUCCESS] MongoDB connected successfully.")
except Exception as e:
    print(f"[WARNING] MongoDB not available: {e}")
    db = None
    users_col = None
    predictions_col = None
    otp_col = None

# ─── Load ML Model & Scaler ───────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'diabetes_model.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'scaler.pkl')

try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("[SUCCESS] Model and Scaler loaded successfully.")
except Exception as e:
    model = None
    scaler = None
    print(f"[WARNING] Model or Scaler could not be loaded: {e}")


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


# ── NEW HELPER: Generate a random 6-digit OTP ──────────────────────────────────
# random.randint(100000, 999999) gives a number between 100000 and 999999
# str() converts it to a string so we can display/compare it easily
def generate_otp():
    """Return a 6-digit OTP as a string, e.g. '483921'."""
    return str(random.randint(100000, 999999))


# ── NEW HELPER: Send OTP email to the user ─────────────────────────────────────
# Reuses the same Gmail SMTP setup already used in the /contact route.
def send_otp_email(recipient_email, otp_code, user_name):
    """
    Send an OTP email to `recipient_email`.
    Returns True on success, False on failure.
    """
    # Read sender credentials from the .env file
    sender_email    = os.environ.get('EMAIL_USER')
    sender_password = os.environ.get('EMAIL_PASS', '')

    # If the app password is not configured, we cannot send email
    if not sender_password or not sender_email:
        print("[WARNING] EMAIL_USER or EMAIL_PASS not set in .env - cannot send OTP.")
        return False

    # Build the email message
    msg = EmailMessage()
    msg['Subject'] = "Your DiabetesAI Verification Code"
    msg['From']    = sender_email
    msg['To']      = recipient_email

    # Plain-text body (shown if HTML is not supported)
    plain_body = (
        f"Hello {user_name},\n\n"
        f"Your DiabetesAI verification code is: {otp_code}\n\n"
        f"This code expires in 5 minutes.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— The DiabetesAI Team"
    )
    msg.set_content(plain_body)

    # HTML version of the email (prettier, displayed by most modern email clients)
    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:auto;background:#0f172a;
                border-radius:16px;overflow:hidden;border:1px solid #1e3a5f;">
      <div style="background:linear-gradient(135deg,#1e3a5f,#0ea5e9);padding:32px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:24px;">&#10084; DiabetesAI</h1>
        <p style="color:#bae6fd;margin:8px 0 0;">Email Verification</p>
      </div>
      <div style="padding:32px;">
        <p style="color:#cbd5e1;font-size:15px;">Hi <strong style="color:#f8fafc;">{user_name}</strong>,</p>
        <p style="color:#94a3b8;font-size:14px;">Use this code to complete your registration:</p>
        <div style="background:#1e293b;border-radius:12px;padding:24px;text-align:center;margin:24px 0;
                    border:1px solid #334155;">
          <span style="font-size:40px;font-weight:800;letter-spacing:12px;color:#0ea5e9;">{otp_code}</span>
        </div>
        <p style="color:#64748b;font-size:13px;text-align:center;">
          &#9203; This code expires in <strong>5 minutes</strong>.
        </p>
        <p style="color:#475569;font-size:12px;text-align:center;margin-top:24px;">
          If you did not create an account, please ignore this email.
        </p>
      </div>
    </div>
    """
    # Add the HTML version as an alternative (email clients pick the best one)
    msg.add_alternative(html_body, subtype='html')

    # Send via Gmail SMTP over SSL (port 465)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"[SUCCESS] OTP email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[WARNING] Failed to send OTP email: {e}")
        return False


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html', user=session.get('user_name'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, no need to register again
    if 'user_email' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        # ── Step 1: Read form data ────────────────────────────────────────────
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        # ── Step 2: Basic validation ──────────────────────────────────────────
        if not all([name, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        # ── Step 3: Check database availability ───────────────────────────────
        if not db_available():
            flash('Database unavailable — cannot register right now.', 'danger')
            return render_template('register.html')

        # ── Step 4: Check for duplicate email in both the real users
        #           collection AND the pending (not-yet-verified) collection
        if users_col.find_one({'email': email}):
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('login'))

        # ── Step 5: Generate OTP ──────────────────────────────────────────────
        # We create a 6-digit code. We also record when it was created so we
        # can check if it has expired (5 minutes = 300 seconds).
        otp_code   = generate_otp()
        expires_at = datetime.now() + timedelta(minutes=5)  # OTP valid for 5 min

        # ── Step 6: Store pending registration in MongoDB ─────────────────────
        # We do NOT create the real user yet. We only save the data temporarily
        # in the 'otp_pending' collection. Once OTP is verified, we move the
        # user to the real 'users' collection.
        #
        # update_one with upsert=True means:
        #   → If a pending record for this email exists (e.g. they tried before),
        #     update it with the new OTP.
        #   → If not, create a new one.
        otp_col.update_one(
            {'email': email},        # find document by email
            {'$set': {
                'name':       name,
                'email':      email,
                'password':   generate_password_hash(password),  # hash immediately for security
                'otp':        otp_code,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }},
            upsert=True              # create if it doesn't exist
        )

        # ── Step 7: Send OTP email ────────────────────────────────────────────
        email_sent = send_otp_email(email, otp_code, name)
        if not email_sent:
            flash(
                'Could not send verification email. '
                'Check server email configuration and try again.',
                'danger'
            )
            return render_template('register.html')

        # ── Step 8: Save email in session so the verify page knows who to check
        # We use a separate key 'pending_email' (not 'user_email') so the user
        # is NOT logged in yet — logging in happens only after OTP is confirmed.
        session['pending_email'] = email
        session['pending_name']  = name

        flash(f'A 6-digit verification code has been sent to {email}.', 'info')
        return redirect(url_for('verify_otp'))   # go to the OTP page

    return render_template('register.html')


# ── NEW ROUTE: OTP Verification Page ──────────────────────────────────────────
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """
    GET  → Show the OTP input form.
    POST → Validate the OTP the user typed in.
    """
    # Safety check: if there is no pending email in the session, the user
    # should not be on this page at all — redirect them to register.
    if 'pending_email' not in session:
        flash('Please complete the registration form first.', 'warning')
        return redirect(url_for('register'))

    email = session['pending_email']   # the email we sent the OTP to
    name  = session.get('pending_name', '')

    if request.method == 'POST':
        # ── Step 1: Get the OTP the user entered ──────────────────────────────
        # The OTP page sends 6 individual digit inputs (digit1..digit6).
        # We join them into one string here.
        entered_otp = (
            request.form.get('digit1', '') +
            request.form.get('digit2', '') +
            request.form.get('digit3', '') +
            request.form.get('digit4', '') +
            request.form.get('digit5', '') +
            request.form.get('digit6', '')
        ).strip()

        # ── Step 2: Look up the pending record ───────────────────────────────
        if not db_available():
            flash('Database unavailable. Please try again later.', 'danger')
            return render_template('verify_otp.html', email=email, name=name)

        pending = otp_col.find_one({'email': email})

        if not pending:
            # The pending record was deleted or never existed
            flash('Session expired. Please register again.', 'warning')
            session.pop('pending_email', None)
            session.pop('pending_name', None)
            return redirect(url_for('register'))

        # ── Step 3: Check if OTP has expired ─────────────────────────────────
        # expires_at was stored as a datetime object in MongoDB.
        if datetime.now() > pending['expires_at']:
            flash('OTP has expired. Click "Resend OTP" to get a new one.', 'warning')
            return render_template('verify_otp.html', email=email, name=name)

        # ── Step 4: Check if OTP matches ─────────────────────────────────────
        if entered_otp != pending['otp']:
            flash('Incorrect OTP. Please check the code and try again.', 'danger')
            return render_template('verify_otp.html', email=email, name=name)

        # ── Step 5: OTP is correct! Create the real user account ─────────────
        # Check one more time that the email wasn't registered in the meantime
        if users_col.find_one({'email': email}):
            flash('Email already registered. Please log in.', 'warning')
            otp_col.delete_one({'email': email})
            session.pop('pending_email', None)
            session.pop('pending_name', None)
            return redirect(url_for('login'))

        # Insert into the real users collection
        users_col.insert_one({
            'name':       pending['name'],
            'email':      pending['email'],
            'password':   pending['password'],   # already hashed from /register
            'created_at': datetime.now(),
            'verified':   True                   # mark as email-verified
        })

        # ── Step 6: Clean up ──────────────────────────────────────────────────
        otp_col.delete_one({'email': email})      # remove temp record
        session.pop('pending_email', None)        # remove from session
        session.pop('pending_name', None)

        flash(
            f'Account verified! Welcome to DiabetesAI, {pending["name"]}! '
            'Please log in to continue.',
            'success'
        )
        return redirect(url_for('login'))

    # GET request — just show the form
    return render_template('verify_otp.html', email=email, name=name)


# ── NEW ROUTE: Resend OTP ──────────────────────────────────────────────────────
@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """
    Generate a fresh OTP, save it (overwriting the old one), and re-send the email.
    Only works if there is a valid pending session.
    """
    if 'pending_email' not in session:
        flash('Please complete the registration form first.', 'warning')
        return redirect(url_for('register'))

    email = session['pending_email']
    name  = session.get('pending_name', '')

    if not db_available():
        flash('Database unavailable. Please try again later.', 'danger')
        return redirect(url_for('verify_otp'))

    # Generate a brand-new OTP with a fresh 5-minute expiry
    new_otp    = generate_otp()
    expires_at = datetime.now() + timedelta(minutes=5)

    # Update the pending record with the new OTP
    otp_col.update_one(
        {'email': email},
        {'$set': {'otp': new_otp, 'expires_at': expires_at}}
    )

    # Send the new OTP to the user's email
    sent = send_otp_email(email, new_otp, name)
    if sent:
        flash(f'A new verification code has been sent to {email}.', 'success')
    else:
        flash('Failed to send new OTP. Please check server configuration.', 'danger')

    return redirect(url_for('verify_otp'))


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
