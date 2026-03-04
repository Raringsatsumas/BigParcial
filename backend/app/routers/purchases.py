from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from ..db import get_db
from ..schemas import PurchaseRequest

router = APIRouter(tags=["purchases"])

@router.post("/purchases")
def create_purchase(req: PurchaseRequest, db: Session = Depends(get_db)):
    # validar customer
    cust = db.execute(
        text("SELECT CustomerId FROM Customer WHERE CustomerId = :cid"),
        {"cid": req.customer_id}
    ).mappings().first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    # validar track y precio
    track = db.execute(
        text("SELECT TrackId, UnitPrice FROM Track WHERE TrackId = :tid"),
        {"tid": req.track_id}
    ).mappings().first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    unit_price = float(track["UnitPrice"])
    total = unit_price * req.quantity

    invoice_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        db.execute(
            text("""
                INSERT INTO Invoice
                    (CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState,
                     BillingCountry, BillingPostalCode, Total)
                VALUES
                    (:CustomerId, :InvoiceDate, :BillingAddress, :BillingCity, :BillingState,
                     :BillingCountry, :BillingPostalCode, :Total)
            """),
            {
                "CustomerId": req.customer_id,
                "InvoiceDate": invoice_date,
                "BillingAddress": getattr(req.billing, "address", None),
                "BillingCity": getattr(req.billing, "city", None),
                "BillingState": getattr(req.billing, "state", None),
                "BillingCountry": getattr(req.billing, "country", None),
                "BillingPostalCode": getattr(req.billing, "postal_code", None),
                "Total": total,
            }
        )

        invoice_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]

        db.execute(
            text("""
                INSERT INTO InvoiceLine (InvoiceId, TrackId, UnitPrice, Quantity)
                VALUES (:InvoiceId, :TrackId, :UnitPrice, :Quantity)
            """),
            {
                "InvoiceId": invoice_id,
                "TrackId": req.track_id,
                "UnitPrice": unit_price,
                "Quantity": req.quantity
            }
        )

        db.commit()
        return {"invoice_id": int(invoice_id), "total": total}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Purchase failed: {str(e)}")
