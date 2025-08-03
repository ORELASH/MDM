"""
Simple API test to check FastAPI functionality
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI(title="RedshiftManager API Test")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working"}


@app.get("/")
async def root():
    return {"message": "RedshiftManager API Test"}


if __name__ == "__main__":
    # Test with client
    client = TestClient(app)

    print("🔧 בדיקת API פשוט...")

    # Test health endpoint
    response = client.get("/health")
    print(f"✅ Health: {response.status_code} - {response.json()}")

    # Test root endpoint
    response = client.get("/")
    print(f"✅ Root: {response.status_code} - {response.json()}")

    print("✅ API פשוט עובד בהצלחה")
