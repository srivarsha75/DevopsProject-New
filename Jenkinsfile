pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'pip install -r requirements.txt'
                bat 'pip install pytest pytest-flask pytest-cov flake8'
            }
        }

        stage('Linting') {
            steps {
                bat 'flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics'
            }
        }

        stage('Test') {
            steps {
                bat 'pytest --cov=. --cov-report=xml --junitxml=test-reports/results.xml'
            }
            post {
                always {
                    script {
                        try {
                            junit 'test-reports/*.xml'
                        } catch (Exception e) {
                            echo "JUnit report not found."
                        }
                        try {
                            cobertura coberturaReportFile: 'coverage.xml'
                        } catch (Exception e) {
                            echo "Coverage report not found."
                        }
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                    bat """
                        docker build -t %USERNAME%/finance-tracker:latest .
                    """
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    bat """
                        echo %DOCKER_PASS% | docker login -u %DOCKER_USER% --password-stdin
                        docker push %DOCKER_USER%/finance-tracker:latest
                    """
                }
            }
        }

        stage('Deploy') {
            steps {
                bat 'docker-compose down || echo "No containers running"'
                bat 'docker-compose up -d'
            }
        }
    }

    post {
        always {
            // Clean up workspace after pipeline execution
            cleanWs()
        }

        success {
            echo "Pipeline completed successfully!"
        }

        failure {
            echo "Pipeline failed. Please check the logs for more details."
        }
    }
}
