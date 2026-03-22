
import os
from dotenv import load_dotenv
load_dotenv()

# Mock these if missing locally to verify code logic at least, 
# but ideally we want to test with real ones if possible.
# app/__init__.py doesn't require them to crash, but init_oauth does use them.

try:
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    
    print("App created successfully.")
    
    with app.test_client() as client:
        print("Attempting to access /login...")
        response = client.get('/login')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 500:
            print("Got 500 Error!")
        elif response.status_code == 302:
            print(f"Success! Redirecting to: {response.location}")
        else:
            print(f"Unexpected status: {response.status_code}")
            print(response.data)
            
except Exception as e:
    print(f"CRASHED: {e}")
    import traceback
    traceback.print_exc()
