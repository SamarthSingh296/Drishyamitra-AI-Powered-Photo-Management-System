import requests
base_url = "http://localhost:5000/api"
r2 = requests.post(f"{base_url}/auth/login", json={"username": "testuserx", "password": "password"})
token = r2.json().get("data", {}).get("access_token")
chat_res = requests.post(f"{base_url}/chat/", json={"message": "hello", "history": []}, headers={"Authorization": f"Bearer {token}"})
print(chat_res.json())
