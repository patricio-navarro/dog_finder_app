# 🐶 Dog Finder Analytics POC

## 📋 Overview
This application allows users to report lost dog sightings. It captures the location (via Google Maps), date, and a photo. The data is processed by a Flask backend, storing images in GCS and publishing event data to Pub/Sub.

## ✨ Features
- **Frontend**: Responsive, premium-styled UI with Google Maps integration.
- **Backend**: Flask app handling uploads and geocoding.
- **Cloud Integration**: Google Cloud Storage (Images) and Pub/Sub (Events).
- **Deployment**: Dockerized and ready for Cloud Run.

## 🏗️ System Architecture
![System Architecture Sketch](static/architecture_sketch.png)



## 🛠️ Prerequisites
- Google Cloud Project with Billing enabled.
- APIs enabled: Maps JavaScript API, Geocoding API, Cloud Storage, Pub/Sub, Cloud Run.
- Service Account with appropriate permissions.

## ⚙️ Configuration
The application uses a `.env` file for configuration.
A template has been created at `.env`.

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
BUCKET_NAME=analytics-presentation-poc-lost-dogs
TOPIC_ID=dog-found-topic
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
SERVICE_NAME=dog-finder-app
REGION=us-central1
```

> [!IMPORTANT]
> You must replace `YOUR_GOOGLE_MAPS_API_KEY` and `your-project-id` with real values for the app to function correctly.

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
Before deploying, you can use the helper script to create the GCS Bucket and Pub/Sub Topic automatically:

```bash
./setup_resources.sh
```

## ☁️ Deployment
A helper script `deploy.sh` is provided to build and deploy to Cloud Run.

1.  **Ensure you are authenticated**:
    ```bash
    gcloud auth login
    gcloud config set project YOUR_PROJECT_ID
    ```

2.  **Run the deploy script**:
    ```bash
    ./deploy.sh
    ```

This will:
- Build the image using Cloud Build.
- Deploy the service to Cloud Run (Region: `us-central1`).
- Set the environment variables from your `.env` file.
