# Type-2 Diabetes Prediction Web App

A Flask-based web application that predicts diabetes risk using machine learning. Users can register, log in, input health metrics, and receive predictions based on a trained model. Predictions and user data are stored in MongoDB.

## Features

- **User Authentication**: Register and log in to access personalized features.
- **Diabetes Prediction**: Input health parameters (e.g., glucose levels, BMI) to get a risk assessment.
- **Dashboard**: View past predictions and manage your account.
- **Responsive UI**: Built with HTML, CSS, and JavaScript for a clean user experience.
- **Machine Learning**: Uses a pre-trained scikit-learn model for predictions.
- **Data Storage**: MongoDB integration for users and prediction history.

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Machine Learning**: scikit-learn, joblib
- **Frontend**: HTML, CSS, JavaScript
- **Data Processing**: NumPy, Pandas
- **Other**: Werkzeug (for security)

## Installation

1. **Clone the repository**:
   ```
   git clone <your-repo-url>
   cd ml
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Environment Setup**:
   Create a `.env` file in the root directory to configure the email contact form:
   ```env
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_16_char_google_app_password
   RECEIVER_EMAIL=your_receiver_email@example.com
   ```

4. **Set up MongoDB**:
   - Ensure MongoDB is running locally (default: `mongodb://localhost:27017/`).
   - The app will create databases `diabetes_ai_db` with collections `users` and `predictions`.

5. **Run the app**:
   ```
   python app.py
   ```
   - Open your browser to `http://127.0.0.1:5000/`.

## Usage

- **Home**: Overview of the app.
- **Register/Login**: Create an account or sign in.
- **Predict**: Enter health data (based on `feature_columns.json`) and get a prediction.
- **Dashboard**: View your prediction history.
- **About/Contact**: Learn more about the project.

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

- `app.py`: Main Flask application.
- `diabetes.csv`: Dataset used for training the model.
- `feature_columns.json`: Feature configuration for predictions.
- `diabetes_model.pkl` & `scaler.pkl`: Trained ML model and data scaler.
- `main.ipynb`: Jupyter notebook for data analysis and model training.
- `templates/`: HTML templates for web pages.
- `static/`: CSS, JS, and images.
- `requirements.txt`: Python dependencies.

## Model Details

- **Algorithms Tested**: Logistic Regression (LR), Decision Tree, Gradient Boosting, and Random Forest.
- **Final Algorithm**: Gradient Boosting (selected due to highest accuracy).
- **Features**: See `feature_columns.json` for input fields.
- **Accuracy**: 91%
- **Retraining**: Use `main.ipynb` to retrain the model with new data.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Praveen Kumar - namekr567@gmail.com
