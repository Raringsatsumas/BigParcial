from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from ..db import get_db
from .auth import get_current_user

router = APIRouter(tags=["purchases"])

@router.get("/purchases")
def my_purchases(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("""
            SELECT
              p.id, p.purchased_at, p.quantity, p.total,
              t.TrackId, t.Name AS TrackName,
              ar.Name AS ArtistName,
              g.Name AS GenreName
            FROM app_purchase p
            JOIN Track t ON t.TrackId = p.track_id
            JOIN Album al ON al.AlbumId = t.AlbumId
            JOIN Artist ar ON ar.ArtistId = al.ArtistId
            LEFT JOIN Genre g ON g.GenreId = t.GenreId
            WHERE p.user_id = :uid
            ORDER BY p.purchased_at DESC
        """),
        {"uid": user["id"]},
    ).mappings().all()
    return {"items": list(rows)}

@router.post("/purchases")
def buy(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    track_id = int(payload.get("track_id", 0))
    quantity = int(payload.get("quantity", 1))
    if track_id <= 0 or quantity <= 0:
        raise HTTPException(400, "track_id and quantity required")

    track = db.execute(
        text("SELECT TrackId, UnitPrice FROM Track WHERE TrackId=:tid"),
        {"tid": track_id},
    ).mappings().first()
    if not track:
        raise HTTPException(404, "Track not found")

    unit_price = float(track["UnitPrice"])
    total = unit_price * quantity
    invoice_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    invoice_id = None
    try:
        db.execute(
            text("INSERT INTO Invoice (CustomerId, InvoiceDate, Total) VALUES (:cid,:dt,:tot)"),
            {"cid": user["chinook_customer_id"] or 1, "dt": invoice_date, "tot": total},
        )
        invoice_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]

        db.execute(
            text("""
              INSERT INTO InvoiceLine (InvoiceId, TrackId, UnitPrice, Quantity)
              VALUES (:iid,:tid,:up,:q)
            """),
            {"iid": invoice_id, "tid": track_id, "up": unit_price, "q": quantity},
        )
    except Exception:
        invoice_id = None

    db.execute(
        text("""
          INSERT INTO app_purchase (user_id, invoice_id, track_id, unit_price, quantity, total)
          VALUES (:uid,:iid,:tid,:up,:q,:tot)
        """),
        {"uid": user["id"], "iid": invoice_id, "tid": track_id, "up": unit_price, "q": quantity, "tot": total},
    )
    db.commit()
    return {"ok": True, "invoice_id": invoice_id, "total": total}
