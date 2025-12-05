import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import io

# Ensure we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

@pytest.fixture
def client():
    main.app.config['TESTING'] = True
    with main.app.test_client() as client:
        yield client

@patch('main.storage_client')
@patch('main.pubsub_publisher')
@patch('main.gmaps')
def test_submit_dog_success(mock_gmaps, mock_pubsub, mock_storage, client):
    # Setup mocks
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    # Mock Pub/Sub future
    mock_future = MagicMock()
    mock_future.result.return_value = "msg_id_123"
    mock_pubsub.publish.return_value = mock_future

    # Mock Geocoding
    mock_gmaps.reverse_geocode.return_value = [{
        'address_components': [
            {'long_name': 'San Francisco', 'types': ['locality']},
            {'long_name': 'California', 'types': ['administrative_area_level_1']},
            {'long_name': 'USA', 'types': ['country']}
        ]
    }]

    # Prepare data
    data = {
        'lat': '37.7749',
        'lng': '-122.4194',
        'date': '2023-10-27',
        'image': (io.BytesIO(b'fake_image_bytes'), 'dog.jpg', 'image/jpeg')
    }

    response = client.post('/submit', data=data, content_type='multipart/form-data')
    
    # Verify
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['data']['location']['city'] == 'San Francisco'
    
    # Verify calls
    mock_storage.bucket.assert_called()
    mock_blob.upload_from_file.assert_called()
    mock_pubsub.publish.assert_called()
    mock_gmaps.reverse_geocode.assert_called_with(('37.7749', '-122.4194'))

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Dog Finder" in response.data

def test_submit_missing_fields(client):
    response = client.post('/submit', data={})
    assert response.status_code == 400
    assert b"Missing required fields" in response.data
