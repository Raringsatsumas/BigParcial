from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..db import get_db
from .auth import require_admin

router = APIRouter(tags=["admin"])

def get_or_create_album_for_artist(db: Session, artist_id: int) -> int:
    # usa el primer album del artista; si no tiene, crea uno
    row = db.execute(
        text("SELECT AlbumId FROM Album WHERE ArtistId=:aid ORDER BY AlbumId LIMIT 1"),
        {"aid": artist_id},
    ).mappings().first()

    if row:
        return int(row["AlbumId"])

    db.execute(
        text("INSERT INTO Album (Title, ArtistId) VALUES (:t, :aid)"),
        {"t": "Admin Album", "aid": artist_id},
    )
    album_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]
    return int(album_id)


@router.post("/admin/tracks")
def create_track(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    """
    Crea un track con name, unit_price, artist_id, genre_id.
    Internamente decide AlbumId según el artista.
    """
    name = (payload.get("name") or "").strip()
    unit_price = payload.get("unit_price")
    artist_id = int(payload.get("artist_id", 0))
    genre_id = int(payload.get("genre_id", 0))

    if not name or unit_price is None or artist_id <= 0:
        raise HTTPException(400, "name, unit_price, artist_id required")

    # valida artista
    a = db.execute(text("SELECT 1 FROM Artist WHERE ArtistId=:aid"), {"aid": artist_id}).first()
    if not a:
        raise HTTPException(404, "Artist not found")

    # valida género si viene
    if genre_id:
        g = db.execute(text("SELECT 1 FROM Genre WHERE GenreId=:gid"), {"gid": genre_id}).first()
        if not g:
            raise HTTPException(404, "Genre not found")

    album_id = get_or_create_album_for_artist(db, artist_id)

    # defaults para Chinook
    media_type_id = 1          # normalmente existe
    milliseconds = 200000      # default

    db.execute(
        text("""
          INSERT INTO Track (Name, AlbumId, MediaTypeId, GenreId, Milliseconds, UnitPrice)
          VALUES (:n,:al,:mt,:g,:ms,:up)
        """),
        {"n": name, "al": album_id, "mt": media_type_id, "g": (genre_id if genre_id else None), "ms": milliseconds, "up": unit_price},
    )
    track_id = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()["id"]
    db.commit()
    return {"ok": True, "track_id": track_id}


@router.put("/admin/tracks/{track_id}")
def update_track(track_id: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    fields = []
    params = {"tid": track_id}

    if "name" in payload and payload["name"] is not None:
        fields.append("Name=:n")
        params["n"] = payload["name"]
    if "unit_price" in payload and payload["unit_price"] is not None:
        fields.append("UnitPrice=:up")
        params["up"] = payload["unit_price"]

    if not fields:
        raise HTTPException(400, "No fields to update (name/unit_price)")

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
        # si tiene referencias (InvoiceLine, PlaylistTrack, etc.)
        raise HTTPException(409, "Cannot delete track (has references).")
