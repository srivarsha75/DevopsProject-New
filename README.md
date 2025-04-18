# Finance Tracker Flask App

A web-based application for tracking personal finances, expenses, and income.

## Project Description

Finance Tracker is a Flask-based web application that allows users to:
- Register and log in to a personal account
- Add financial transactions with details like amount, category, date, etc.
- View transaction history
- Generate charts and statistics about spending habits
- Track spending by different payment methods (Cash, UPI, Credit/Debit Cards)

## CI/CT/CD Pipeline

This project implements a complete CI/CT/CD pipeline using Git, Jenkins, and Docker:

### Pipeline Flow:

1. **Continuous Integration**
   - Code is pushed to GitHub repository
   - Webhook triggers Jenkins pipeline
   - Jenkins checks out the code
   - Dependencies are installed
   - Code is linted for quality
   - Tests are executed

2. **Continuous Testing**
   - Unit tests verify core functionality
   - Integration tests check API endpoints
   - Test coverage reports are generated

3. **Continuous Deployment**
   - Docker image is built
   - Image is pushed to Docker Hub
   - Application is deployed using Docker Compose

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **CI/CD**: Jenkins, Docker
- **Testing**: pytest, pytest-flask

## Setup & Run Instructions

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/Ayush-Bitla/DevOpsProject.git
   cd DevOpsProject
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Access the application at `http://localhost:5000`

### Docker Deployment

1. Build and start with Docker Compose:
   ```
   docker-compose up -d
   ```

2. Access the application at `http://localhost:5000`

## Running Tests

```
pip install pytest pytest-flask pytest-cov
pytest --cov=. --cov-report=term
```

## Docker Commands

- **Build image**: `docker build -t finance-tracker:latest .`
- **Run container**: `docker run -p 5000:5000 finance-tracker:latest`
- **Docker Compose deployment**: `docker-compose up -d`

## Project Structure

```
DevOpsProject/
│
├── app.py                # Main application file
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── Jenkinsfile           # Jenkins pipeline definition
├── test_app.py           # Test suite
│
├── static/               # Static assets (CSS, JS)
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/            # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── transaction.html
│   └── statistics.html
│
└── screenshots/          # Application screenshots
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
