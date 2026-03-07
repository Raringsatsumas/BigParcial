from app.security import create_access_token, decode_token, verify_password_plain

def test_token_roundtrip():
    token = create_access_token("juan", "user")
    payload_out = decode_token(token)

    assert payload_out["sub"] == "juan"
    assert payload_out["role"] == "user"

def test_verify_password_plain_ok():
    assert verify_password_plain("Admin123!", "Admin123!") is True

def test_verify_password_plain_fail():
    assert verify_password_plain("Admin123!", "otra") is False
