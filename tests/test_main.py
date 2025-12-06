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

@patch('app.services.firestore_client')
@patch('app.services.storage_client')
@patch('app.services.pubsub_publisher')
@patch('app.services.gmaps')
def test_submit_dog_success(mock_gmaps, mock_pubsub, mock_storage, mock_firestore, client):
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
        'comments': 'Found near the park',
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
    # Verify Pub/Sub message content
    pubsub_args, _ = mock_pubsub.publish.call_args
    # pubsub_args[0] is topic, pubsub_args[1] is message bytes
    import json
    msg_json = json.loads(pubsub_args[1].decode('utf-8'))
    assert msg_json['user_id'] == 'mock_user_123'

    mock_firestore.collection.assert_called_with("sightings")
    
    # Verify user_id in firestore set call
    doc_ref_mock = mock_firestore.collection.return_value.document.return_value
    args, _ = doc_ref_mock.set.call_args
    assert args[0]['user_id'] == 'mock_user_123'

    mock_gmaps.reverse_geocode.assert_called_with(('37.7749', '-122.4194'))

@patch('app.services.firestore_client')
def test_get_sightings(mock_firestore, client):
    # Mock data
    mock_doc = MagicMock()
    mock_doc.id = "doc123"
    mock_doc.to_dict.return_value = {
        "sighting_date": "2023-10-27",
        "image_url": "http://image.url",
        "location": MagicMock(latitude=37.77, longitude=-122.41),
        "location_details": {"city": "SF"},
        "comments": "Friendly dog"
    }
    
    mock_stream = MagicMock()
    mock_stream.stream.return_value = [mock_doc]
    
    # Chain: client.collection().order_by().order_by().limit().stream()
    mock_firestore.collection.return_value.order_by.return_value.order_by.return_value.limit.return_value = mock_stream

    response = client.get('/api/sightings')
    
    assert response.status_code == 200
    assert response.status_code == 200
    json_data = response.get_json()
    data = json_data['data']
    assert len(data) == 1
    assert data[0]['id'] == 'doc123'
    assert data[0]['location']['lat'] == 37.77
    assert data[0]['location_details']['city'] == 'SF'
    assert data[0]['comments'] == 'Friendly dog'

@patch('app.services.storage_client')
@patch('app.services.firestore_client')
def test_get_sightings_public_url(mock_firestore, mock_storage, client):
    # Setup Storage Mock (Not actually called for public URLs but we patch it to mimic env)
    
    # Mock Firestore Data with GS URL
    mock_doc = MagicMock()
    mock_doc.id = "doc123"
    mock_doc.to_dict.return_value = {
        "sighting_date": "2023-10-27",
        "image_url": "gs://analytics-presentation-poc-lost-dogs/dog_123.jpg",
        "location": MagicMock(latitude=37.77, longitude=-122.41),
        "location_details": {}
    }
    
    mock_stream = MagicMock()
    mock_stream.stream.return_value = [mock_doc]
    mock_firestore.collection.return_value.order_by.return_value.order_by.return_value.limit.return_value = mock_stream

    # Make request
    response = client.get('/api/sightings')
    
    assert response.status_code == 200
    json_data = response.get_json()
    data = json_data['data']
    
    # Assertions
    assert len(data) == 1
    # Expect Public URL
    assert data[0]['image_url'] == "https://storage.googleapis.com/analytics-presentation-poc-lost-dogs/dog_123.jpg"

@patch('app.services.firestore_client')
def test_get_sightings_with_bounds(mock_firestore, client):
    # Mock data: One inside SF bounds, one outside (e.g., NY)
    doc_in = MagicMock()
    doc_in.id = "in_sf"
    doc_in.to_dict.return_value = {
        "sighting_date": "2023-10-27",
        "location": MagicMock(latitude=37.77, longitude=-122.42), # SF
        "location_details": {"city": "San Francisco"}
    }
    
    doc_out = MagicMock()
    doc_out.id = "out_sf"
    doc_out.to_dict.return_value = {
        "sighting_date": "2023-10-27",
        "location": MagicMock(latitude=40.71, longitude=-74.00), # NY
        "location_details": {"city": "New York"}
    }
    
    # Mock stream to return both
    mock_stream = MagicMock()
    mock_stream.stream.return_value = [doc_in, doc_out]
    
    # Chain
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_stream
    mock_firestore.collection.return_value.order_by.return_value.order_by.return_value = mock_query

    # Request with SF Bounds (approx)
    # North: 37.81, South: 37.70, East: -122.35, West: -122.50
    params = {
        'north': 37.81,
        'south': 37.70,
        'east': -122.35,
        'west': -122.50
    }
    
    response = client.get('/api/sightings', query_string=params)
    assert response.status_code == 200
    data = response.get_json()
    
    # Should only have 1 result (the SF one)
    assert len(data['data']) == 1
    assert data['data'][0]['id'] == 'in_sf'

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Dog Finder" in response.data

def test_submit_missing_fields(client):
    response = client.post('/submit', data={})
    assert response.status_code == 400
    assert b"Missing required fields" in response.data
