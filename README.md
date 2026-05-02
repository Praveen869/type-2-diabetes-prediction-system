# Type-2 Diabetes Prediction Web App

A Flask-based web application that predicts diabetes risk using machine learning. Users can register (with email OTP verification), log in, input health metrics, and receive predictions based on a trained model. Predictions and user data are stored in MongoDB.

## Features

- **Secure Registration with Email OTP**: New accounts are verified via a 6-digit one-time password sent to the user's email — unverified signups are never saved permanently.
- **User Authentication**: Log in and out securely with hashed passwords (bcrypt via Werkzeug).
- **Diabetes Prediction**: Input health parameters (e.g., glucose levels, BMI) to get a risk assessment.
- **Dashboard**: View past predictions and manage your account.
- **Responsive UI**: Built with HTML, CSS, and JavaScript for a clean user experience.
- **Machine Learning**: Uses a pre-trained scikit-learn model for predictions.
- **Data Storage**: MongoDB integration for users, prediction history, and temporary OTP records.
- **Contact Form**: Send messages directly via Gmail SMTP.

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Machine Learning**: scikit-learn, joblib
- **Frontend**: HTML, CSS, JavaScript
- **Data Processing**: NumPy, Pandas
- **Email**: Python `smtplib` + Gmail SMTP (App Password)
- **Other**: Werkzeug (password hashing), python-dotenv

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd ml
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS / Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**:
   Create a `.env` file in the root directory. This file powers **both** the contact form and the OTP email sender:
   ```env
   SECRET_KEY=your_random_flask_secret_key

   # Gmail account that sends OTP emails and receives contact messages
   EMAIL_USER=your_gmail@gmail.com
   EMAIL_PASS=your_16_char_google_app_password

   # Where contact-form messages get delivered
   RECEIVER_EMAIL=your_receiver_email@example.com

   # MongoDB connection (leave as-is for local MongoDB)
   MONGO_URI=mongodb://localhost:27017/
   ```

   > **How to get a Gmail App Password:**
   > 1. Enable 2-Step Verification on your Google account.
   > 2. Go to **Google Account → Security → App Passwords**.
   > 3. Generate a password for "Mail" → copy the 16-character code (no spaces).
   > 4. Paste it as `EMAIL_PASS` in your `.env` file.

5. **Set up MongoDB**:
   - Ensure MongoDB is running locally (default: `mongodb://localhost:27017/`).
   - The app auto-creates the database `diabetes_ai_db` with three collections:
     | Collection | Purpose |
     |---|---|
     | `users` | Verified, active user accounts |
     | `predictions` | Per-user prediction history |
     | `otp_pending` | Temporary store for unverified signups (auto-cleared after verification) |

6. **Run the app**:
   ```bash
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5000/`.

## Usage

| Page | URL | Description |
|---|---|---|
| Home | `/` | Overview of the app |
| Register | `/register` | Create an account — triggers OTP email |
| Verify OTP | `/verify-otp` | Enter the 6-digit code from your email |
| Login | `/login` | Sign in to your verified account |
| Predict | `/predict` | Enter health data and get a diabetes risk prediction |
| Dashboard | `/dashboard` | View your full prediction history |
| About | `/about` | Learn more about the project |
| Contact | `/contact` | Send a message via the contact form |

### Registration Flow

```
Fill Register form → Receive OTP email → Enter 6-digit code → Account activated → Login
```

- The OTP is valid for **5 minutes**.
- If the code expires, click **Resend Code** to get a fresh one.
- The account is only created in the database **after** the OTP is successfully verified.

## Screenshots

*(These images are located in the `screenshots/` folder.)*

### Home Page
![Homepage image](<screenshots/Screenshot 2026-03-27 224237.png>)

![Homepaage image](<screenshots/Screenshot 2026-03-27 224304.png>)

![Homepage image](<screenshots/Screenshot 2026-03-27 225058.png>)

### Dashboard
![Dashboard Page](<screenshots/Screenshot 2026-03-27 225205.png>)

### Prediction Page
![Prediction Page](<screenshots/Screenshot 2026-03-27 225500.png>)

### Login / Register
![Register Page](<screenshots/Screenshot 2026-03-27 225639.png>)

![Login page](<screenshots/Screenshot 2026-03-27 225628.png>)


## Project Structure

```
ml/
├── app.py                  # Main Flask application (routes, OTP logic, email helpers)
├── diabetes.csv            # Dataset used for training the model
├── feature_columns.json    # Feature configuration for predictions
├── diabetes_model.pkl      # Trained Gradient Boosting model
├── scaler.pkl              # RobustScaler fitted during training
├── main.ipynb              # Jupyter notebook for data analysis & model training
├── requirements.txt        # Python dependencies
├── .env                    # Secret keys & email credentials (not committed to git)
├── templates/
│   ├── base.html           # Shared layout (navbar, footer, flash messages)
│   ├── home.html           # Landing page
│   ├── register.html       # Signup form
│   ├── verify_otp.html     # OTP verification page
│   ├── login.html          # Login form
│   ├── predict.html        # Health data input & prediction result
│   ├── dashboard.html      # Prediction history
│   ├── about.html          # About page
│   └── contact.html        # Contact form
└── static/
    ├── css/style.css       # Custom styles
    └── js/script.js        # Custom scripts
```

## Model Details

- **Algorithms Tested**: Logistic Regression, Decision Tree, Gradient Boosting, Random Forest.
- **Final Algorithm**: Gradient Boosting (highest accuracy).
- **Features**: See `feature_columns.json` for input fields.
- **Accuracy**: 91%
- **Retraining**: Use `main.ipynb` to retrain the model with new data.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Contact

Praveen Kumar — namekr567@gmail.com
