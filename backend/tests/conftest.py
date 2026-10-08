import os
import tempfile

# Must be set before the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SEED_DEMO_DATA"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORD = "Password123!"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin@hospital.example.com")


@pytest.fixture(scope="session")
def doctor(client):
    return _login(client, "doctor@hospital.example.com")


@pytest.fixture(scope="session")
def reception(client):
    return _login(client, "reception@hospital.example.com")


@pytest.fixture(scope="session")
def analyst(client):
    return _login(client, "analyst@hospital.example.com")
