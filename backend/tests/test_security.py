from app.security import create_access_token, decode_token, verify_password_plain

def test_token_roundtrip():
    payload_in = {
        "sub": "juan",
        "id": 10,
        "role": "user",
        "chinook_customer_id": 99,
    }

    token = create_access_token(payload_in["sub"], payload_in["role"])
    payload_out = decode_token(token)

    assert payload_out["sub"] == "juan"
    assert payload_out["id"] == 10
    assert payload_out["role"] == "user"
    assert payload_out["chinook_customer_id"] == 99

def test_verify_password_plain_ok():
    assert verify_password_plain("Admin123!", "Admin123!") is True

def test_verify_password_plain_fail():
    assert verify_password_plain("Admin123!", "otra") is False
