import requests
import time

def test_chat():
    base_url = "http://localhost:5000/api"
    # Login
    res = requests.post(f"{base_url}/auth/login", json={"username": "testuser", "password": "password"})
    if res.status_code != 200:
        # Register instead
        requests.post(f"{base_url}/auth/register", json={"username": "testuser", "email": "test@test.com", "password": "password"})
        res = requests.post(f"{base_url}/auth/login", json={"username": "testuser", "password": "password"})
        
    token = res.json()["data"]["access_token"]
    
    # Test Chat
    chat_res = requests.post(
        f"{base_url}/chat/",
        json={"message": "hello", "history": []},
        headers={"Authorization": f"Bearer {token}"}
    )
    print("STATUS:", chat_res.status_code)
    print("JSON:", chat_res.text)

test_chat()
