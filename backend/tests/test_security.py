from app.security import create_access_token, decode_token, verify_password_plain

def test_token_roundtrip():
    token = create_access_token({
        "sub": "juan",
        "id": 10,
        "role": "user",
        "chinook_customer_id": 99
    })

    payload = decode_token(token)

    assert payload["sub"] == "juan"
    assert payload["id"] == 10
    assert payload["role"] == "user"
    assert payload["chinook_customer_id"] == 99

def test_verify_password_plain_ok():
    assert verify_password_plain("Admin123!", "Admin123!") is True

def test_verify_password_plain_fail():
    assert verify_password_plain("Admin123!", "otra") is False
