# 🐶 Dog Finder Analytics POC

## 📋 Overview
This application allows users to report lost dog sightings. It captures the location (via Google Maps), date, and a photo. The data is processed by a Flask backend, authenticating users via Google OAuth, storing images in GCS, persisting user and sighting data in Firestore, and publishing event data to Pub/Sub for analytics in BigQuery.

## ✨ Features
- **Frontend**: Responsive, premium-styled UI with Google Maps integration.
- **Authentication**: Secure Google OAuth 2.0 Login with session management.
- **Data Persistence**: Firestore database for Users and Sightings.
- **Cloud Integration**: Google Cloud Storage (Images) and Pub/Sub (Events).
- **Deployment**: Dockerized and ready for Cloud Run.

## 🏗️ System Architecture

```mermaid
flowchart TD
    User([User]) <--> Client["Frontend (Flask/Jinja)"]
    Client -- "OAuth 2.0" --> Auth["Google Identity Services"]
    Client -- "Submit Sighting (POST)" --> Backend["Flask Backend"]
    
    subgraph "Google Cloud Platform"
        Backend -- "Store Image" --> GCS["Cloud Storage"]
        Backend -- "Persist Data" --> Firestore[(Firestore)]
        Backend -- "Publish Event" --> PubSub["Pub/Sub"]
        PubSub -- "Subscription" --> BigQuery[(BigQuery)]
    end

    Auth --> Backend
```

## 🛠️ Prerequisites
- Google Cloud Project with Billing enabled.
- API's enabled: 
    - Maps JavaScript API & Geocoding API
    - Cloud Storage
    - Pub/Sub
    - Cloud Run
    - **Firestore API**
- Service Account with appropriate permissions.

## ⚙️ Configuration
The application uses a `.env` file for configuration.
A template has been provided in `.env.example`. Copy it to `.env` and fill the values.

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
BUCKET_NAME=your-bucket-name
TOPIC_ID=your-topic-id
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
SERVICE_NAME=dog-finder-app
REGION=us-central1
BIGQUERY_DATASET=lost_dogs
BIGQUERY_TABLE=publications
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_OAUTH_CLIENT_SECRET
FLASK_SECRET_KEY=YOUR_RANDOM_FLASK_SECRET_KEY
LOAD_TEST_API_KEY=your_secret_api_key_here
```

> [!IMPORTANT]
> You must replace credentials like `YOUR_API_KEY`, `YOUR_OAUTH_CLIENT_SECRET`, and `FLASK_SECRET_KEY` with real values for the app to function correctly. `LOAD_TEST_API_KEY` is required if you intend to run the load testing script.

## 🚀 Running Locally
1.  **Build the Docker Image**:
    ```bash
    docker build -t dog-finder .
    ```

2.  **Run the Container (with Credentials)**:
    To allow the container to access GCP services locally, mount your Application Default Credentials:

    ```bash
    docker run -p 8080:8080 \
      --env-file .env \
      -v $HOME/.config/gcloud/application_default_credentials.json:/tmp/keys/gcp-creds.json \
      -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/gcp-creds.json \
      dog-finder
    ```

3.  **Access the App**:
    Open [http://localhost:8080](http://localhost:8080) in your browser.

## ☁️ Cloud Resources
Before deploying, use the helper script to create the GCS Bucket, Pub/Sub Topic, and Firestore resources roughly automatically:

```bash
./scripts/setup_resources.sh
```

**Note**: This script handles:
- GCS Bucket creation
- Pub/Sub Topic & Schema
- BigQuery Dataset & Table
- Firestore Database & Composite Indexes

## ☁️ Deployment
A helper script `deploy.sh` is provided to build and deploy to Cloud Run.

1.  **Ensure you are authenticated**:
    ```bash
    gcloud auth login
    gcloud config set project YOUR_PROJECT_ID
    ```

2.  **Run the deploy script**:
    ```bash
    ./scripts/deploy.sh
    ```

This will:
- Build the image using Cloud Build.
- Deploy the service to Cloud Run (Region: `us-central1`).
- Set the environment variables from your `.env` file.

## 🧪 Development & Testing

1.  **Virtual Environment**: We use `uv` for Python virtual environments.
    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

2.  **Pre-commit Hooks**: The project uses `pre-commit` to ensure code quality and prevent secrets leakage (via `gitleaks`).
    ```bash
    pre-commit install
    ```

3.  **Running Tests**:
    Tests are written using `pytest`. You can run them via:
    ```bash
    pytest tests/
    ```

4.  **Load Testing**:
    A script is provided to simulate load. Make sure to set `LOAD_TEST_API_KEY` in your `.env` file first.
    ```bash
    ./scripts/load_test.sh
    ```
