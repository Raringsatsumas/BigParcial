from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from .auth import get_current_user  # debe existir en tu proyecto


router = APIRouter(tags=["purchases"])


# -----------------------------
# Pydantic models
# -----------------------------
class PurchaseCreate(BaseModel):
    track_id: int = Field(..., gt=0)
    quantity: int = Field(1, ge=1, le=99)


class PurchaseItem(BaseModel):
    InvoiceId: int
    InvoiceDate: str
    TrackId: int
    TrackName: str
    AlbumTitle: Optional[str] = None
    ArtistName: Optional[str] = None
    GenreName: Optional[str] = None
    UnitPrice: float
    Quantity: int
    LineTotal: float


# -----------------------------
# Helpers
# -----------------------------
def _next_id(db: Session, table: str, col: str) -> int:
    row = db.execute(
        text(f"SELECT IFNULL(MAX({col}), 0) + 1 AS next_id FROM {table}")
    ).mappings().first()
    return int(row["next_id"])


def _get_customer_id(user: Dict[str, Any]) -> int:
    # soporta varios nombres por si tu auth devuelve diferente
    cid = user.get("chinook_customer_id") or user.get("customer_id")
    if not cid:
        raise HTTPException(
            status_code=400,
            detail="Usuario autenticado sin chinook_customer_id/customer_id asociado.",
        )
    return int(cid)


# -----------------------------
# Endpoints
# -----------------------------
@router.get("/purchases", response_model=Dict[str, List[PurchaseItem]])
def list_purchases(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Lista compras del usuario (por CustomerId de Chinook).
    IMPORTANTE: incluye TrackId para que el front pueda bloquear 'comprar' si ya la tiene.
    """
    customer_id = _get_customer_id(user)

    rows = db.execute(
        text(
            """
            SELECT
              i.InvoiceId,
              DATE_FORMAT(i.InvoiceDate, '%Y-%m-%d %H:%i:%s') AS InvoiceDate,
              t.TrackId,
              t.Name AS TrackName,
              al.Title AS AlbumTitle,
              ar.Name AS ArtistName,
              g.Name AS GenreName,
              il.UnitPrice,
              il.Quantity,
              (il.UnitPrice * il.Quantity) AS LineTotal
            FROM Invoice i
            JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId
            JOIN Track t ON t.TrackId = il.TrackId
            JOIN Album al ON al.AlbumId = t.AlbumId
            JOIN Artist ar ON ar.ArtistId = al.ArtistId
            LEFT JOIN Genre g ON g.GenreId = t.GenreId
            WHERE i.CustomerId = :cid
            ORDER BY i.InvoiceDate DESC, i.InvoiceId DESC
            LIMIT 300
            """
        ),
        {"cid": customer_id},
    ).mappings().all()

    # asegurar floats (a veces viene Decimal)
    out = []
    for r in rows:
        out.append(
            {
                "InvoiceId": int(r["InvoiceId"]),
                "InvoiceDate": r["InvoiceDate"],
                "TrackId": int(r["TrackId"]),
                "TrackName": r["TrackName"],
                "AlbumTitle": r.get("AlbumTitle"),
                "ArtistName": r.get("ArtistName"),
                "GenreName": r.get("GenreName"),
                "UnitPrice": float(r["UnitPrice"]),
                "Quantity": int(r["Quantity"]),
                "LineTotal": float(r["LineTotal"]),
            }
        )

    return {"items": out}


@router.post("/purchases")
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Crea una compra:
    - valida track
    - NO permite comprar/descargar el mismo track más de una vez (409)
    - inserta Invoice + InvoiceLine (usando MAX()+1 para evitar problemas de PK)
    """
    customer_id = _get_customer_id(user)
    track_id = payload.track_id
    quantity = payload.quantity

    # 1) validar track y obtener precio
    track = db.execute(
        text("SELECT TrackId, UnitPrice FROM Track WHERE TrackId = :tid"),
        {"tid": track_id},
    ).mappings().first()
    if not track:
        raise HTTPException(404, "Track no existe")

    unit_price = float(track["UnitPrice"])
    line_total = float(unit_price * quantity)

    # 2) bloquear recompra (no descarga más de una vez)
    already = db.execute(
        text(
            """
            SELECT 1
            FROM InvoiceLine il
            JOIN Invoice i ON i.InvoiceId = il.InvoiceId
            WHERE i.CustomerId = :cid AND il.TrackId = :tid
            LIMIT 1
            """
        ),
        {"cid": customer_id, "tid": track_id},
    ).first()
    if already:
        raise HTTPException(
            status_code=409,
            detail="Ya compraste esta canción. No puedes comprar/descargarla otra vez.",
        )

    # 3) obtener info de facturación (opcional, pero queda bonito)
    cust = db.execute(
        text(
            """
            SELECT Address, City, State, Country, PostalCode
            FROM Customer
            WHERE CustomerId = :cid
            """
        ),
        {"cid": customer_id},
    ).mappings().first()
    if not cust:
        raise HTTPException(404, "CustomerId no existe en Chinook")

    invoice_id = _next_id(db, "Invoice", "InvoiceId")
    invoice_line_id = _next_id(db, "InvoiceLine", "InvoiceLineId")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 4) insertar Invoice
        db.execute(
            text(
                """
                INSERT INTO Invoice
                  (InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState,
                   BillingCountry, BillingPostalCode, Total)
                VALUES
                  (:iid, :cid, :dt, :addr, :city, :st, :cty, :pc, :tot)
                """
            ),
            {
                "iid": invoice_id,
                "cid": customer_id,
                "dt": now,
                "addr": cust.get("Address"),
                "city": cust.get("City"),
                "st": cust.get("State"),
                "cty": cust.get("Country"),
                "pc": cust.get("PostalCode"),
                "tot": line_total,
            },
        )

        # 5) insertar InvoiceLine
        db.execute(
            text(
                """
                INSERT INTO InvoiceLine
                  (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)
                VALUES
                  (:ilid, :iid, :tid, :up, :qty)
                """
            ),
            {
                "ilid": invoice_line_id,
                "iid": invoice_id,
                "tid": track_id,
                "up": unit_price,
                "qty": quantity,
            },
        )

        db.commit()

        return {
            "ok": True,
            "invoice_id": invoice_id,
            "invoice_line_id": invoice_line_id,
            "track_id": track_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": line_total,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Purchase failed: {str(e)}")
