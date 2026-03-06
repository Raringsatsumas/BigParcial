from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..db import get_db
from ..security import verify_password_plain, create_access_token, decode_token

router = APIRouter(tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

def get_user_by_username(db: Session, username: str):
    return db.execute(
        text("SELECT id, username, email, password_hash, role, chinook_customer_id FROM app_user WHERE username=:u"),
        {"u": username},
    ).mappings().first()

@router.post("/auth/register")
def register(payload: dict, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not username or not email or len(password) < 4:
        raise HTTPException(400, "username/email required and password >= 4")

    exists = db.execute(
        text("SELECT 1 FROM app_user WHERE username=:u OR email=:e"),
        {"u": username, "e": email},
    ).first()
    if exists:
        raise HTTPException(409, "username/email already exists")

    # crea customer en Chinook para facturas (simple)
    try:
        db.execute(
            text("INSERT INTO Customer (FirstName, LastName, Email, SupportRepId) VALUES (:fn,'User',:em,1)"),
            {"fn": username, "em": email},
        )
        cust_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]
    except Exception:
        cust_id = 1

    db.execute(
        text("""
          INSERT INTO app_user (username, email, password_hash, role, chinook_customer_id)
          VALUES (:u,:e,:p,'user',:cid)
        """),
        {"u": username, "e": email, "p": password, "cid": cust_id},  # 👈 texto plano
    )
    db.commit()
    return {"ok": True, "username": username, "role": "user"}

@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form.username)
    if not user or not verify_password_plain(form.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user["username"], role=user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "username": user["username"]}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin role required")
    return user
