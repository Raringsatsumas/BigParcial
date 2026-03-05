from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..db import get_db
from .auth import require_admin

router = APIRouter(tags=["admin"])

@router.post("/admin/tracks")
def create_track(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    name = (payload.get("name") or "").strip()
    album_id = int(payload.get("album_id", 0))
    media_type_id = int(payload.get("media_type_id", 0))
    milliseconds = int(payload.get("milliseconds", 0))
    unit_price = payload.get("unit_price")

    if not name or album_id <= 0 or media_type_id <= 0 or milliseconds <= 0 or unit_price is None:
        raise HTTPException(400, "name, album_id, media_type_id, milliseconds, unit_price required")

    db.execute(
        text("""
          INSERT INTO Track (Name, AlbumId, MediaTypeId, Milliseconds, UnitPrice)
          VALUES (:n,:aid,:mid,:ms,:up)
        """),
        {"n": name, "aid": album_id, "mid": media_type_id, "ms": milliseconds, "up": unit_price},
    )
    track_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]
    db.commit()
    return {"ok": True, "track_id": track_id}

@router.put("/admin/tracks/{track_id}")
def update_track(track_id: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    fields = []
    params = {"tid": track_id}

    if "name" in payload:
        fields.append("Name=:n")
        params["n"] = payload["name"]
    if "unit_price" in payload:
        fields.append("UnitPrice=:up")
        params["up"] = payload["unit_price"]
    if "milliseconds" in payload:
        fields.append("Milliseconds=:ms")
        params["ms"] = payload["milliseconds"]

    if not fields:
        raise HTTPException(400, "No fields to update")

    res = db.execute(text(f"UPDATE Track SET {', '.join(fields)} WHERE TrackId=:tid"), params)
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(404, "Track not found")
    return {"ok": True}

@router.delete("/admin/tracks/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        res = db.execute(text("DELETE FROM Track WHERE TrackId=:tid"), {"tid": track_id})
        db.commit()
        if res.rowcount == 0:
            raise HTTPException(404, "Track not found")
        return {"ok": True}
    except Exception:
        db.rollback()
        raise HTTPException(409, "Cannot delete track (has references).")
