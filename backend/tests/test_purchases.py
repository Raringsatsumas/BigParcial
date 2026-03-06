from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.routers.auth import get_current_user


class FakeMappings:
    def __init__(self, first=None, all_rows=None):
        self._first = first
        self._all_rows = all_rows or []

    def first(self):
        return self._first

    def all(self):
        return self._all_rows


class FakeResult:
    def __init__(self, first=None, all_rows=None):
        self._first = first
        self._all_rows = all_rows or []

    def mappings(self):
        return FakeMappings(first=self._first, all_rows=self._all_rows)

    def first(self):
        return self._first


class DuplicatePurchaseDB:
    def execute(self, stmt, params=None):
        sql = str(stmt)

        if "SELECT TrackId, UnitPrice FROM Track" in sql:
            return FakeResult(first={"TrackId": 1, "UnitPrice": 0.99})

        if "FROM app_purchase" in sql and "LIMIT 1" in sql:
            return FakeResult(first={"exists": 1})

        raise AssertionError(f"SQL no esperada: {sql}")

    def commit(self):
        pass

    def rollback(self):
        pass


def override_user():
    return {
        "id": 1,
        "username": "juan",
        "role": "user",
        "chinook_customer_id": 1,
    }


def override_db():
    return DuplicatePurchaseDB()


def test_create_purchase_returns_409_if_already_bought():
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    r = client.post("/v1/purchases", json={"track_id": 1, "quantity": 1})

    assert r.status_code == 409
    assert "Ya compraste" in r.json()["detail"]

    app.dependency_overrides = {}
