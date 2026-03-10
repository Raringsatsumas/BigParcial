from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from .auth import get_current_user

router = APIRouter(tags=["admin"])


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    return user


def parse_non_negative_price(raw_price):
    if raw_price is None or str(raw_price).strip() == "":
        raise HTTPException(status_code=400, detail="unit_price required")

    try:
        price = float(raw_price)
    except Exception:
        raise HTTPException(status_code=400, detail="unit_price invalid")

    if price < 0:
        raise HTTPException(status_code=400, detail="El precio no puede ser negativo")

    return price


def get_or_create_album_for_artist(db: Session, artist_id: int) -> int:
    row = db.execute(
        text("SELECT AlbumId FROM Album WHERE ArtistId=:aid ORDER BY AlbumId LIMIT 1"),
        {"aid": artist_id},
    ).mappings().first()

    if row:
        return int(row["AlbumId"])

    next_album_id = db.execute(
        text("SELECT COALESCE(MAX(AlbumId), 0) + 1 AS id FROM Album")
    ).mappings().first()["id"]

    db.execute(
        text("INSERT INTO Album (AlbumId, Title, ArtistId) VALUES (:id, :t, :aid)"),
        {"id": int(next_album_id), "t": "Admin Album", "aid": artist_id},
    )
    return int(next_album_id)


@router.post("/admin/tracks")
def create_track(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    """
    Crea un track con name, unit_price, artist_id, genre_id.
    Si llega album_id válido lo usa; si no, toma el primer álbum del artista
    y si no existe, crea uno.
    """
    try:
        name = (payload.get("name") or "").strip()
        artist_id = int(payload.get("artist_id", 0) or 0)
        genre_id = int(payload.get("genre_id", 0) or 0)
        album_id = int(payload.get("album_id", 0) or 0)
        unit_price = parse_non_negative_price(payload.get("unit_price"))

        if not name or artist_id <= 0:
            raise HTTPException(status_code=400, detail="name, unit_price, artist_id required")

        a = db.execute(
            text("SELECT 1 FROM Artist WHERE ArtistId=:aid"),
            {"aid": artist_id},
        ).first()
        if not a:
            raise HTTPException(status_code=404, detail="Artist not found")

        if genre_id:
            g = db.execute(
                text("SELECT 1 FROM Genre WHERE GenreId=:gid"),
                {"gid": genre_id},
            ).first()
            if not g:
                raise HTTPException(status_code=404, detail="Genre not found")

        if album_id > 0:
            al = db.execute(
                text("SELECT 1 FROM Album WHERE AlbumId=:al"),
                {"al": album_id},
            ).first()
            if not al:
                raise HTTPException(status_code=404, detail="Album not found")
        else:
            album_id = get_or_create_album_for_artist(db, artist_id)

        media_row = db.execute(
            text("SELECT MediaTypeId FROM MediaType ORDER BY MediaTypeId LIMIT 1")
        ).mappings().first()
        if not media_row:
            raise HTTPException(status_code=400, detail="No MediaType available")

        media_type_id = int(media_row["MediaTypeId"])
        milliseconds = int(payload.get("milliseconds") or 200000)

        next_track_id = db.execute(
            text("SELECT COALESCE(MAX(TrackId), 0) + 1 AS id FROM Track")
        ).mappings().first()["id"]

        db.execute(
            text("""
                INSERT INTO Track
                    (TrackId, Name, AlbumId, MediaTypeId, GenreId, Milliseconds, UnitPrice)
                VALUES
                    (:tid, :n, :al, :mt, :g, :ms, :up)
            """),
            {
                "tid": int(next_track_id),
                "n": name,
                "al": int(album_id),
                "mt": media_type_id,
                "g": genre_id if genre_id else None,
                "ms": milliseconds,
                "up": unit_price,
            },
        )

        db.commit()
        return {"ok": True, "track_id": int(next_track_id)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Create failed: {str(e)}")


@router.put("/admin/tracks/{track_id}")
def update_track(track_id: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        fields = []
        params = {"tid": track_id}

        if "name" in payload and payload["name"] is not None:
            name = str(payload["name"]).strip()
            if not name:
                raise HTTPException(status_code=400, detail="name required")
            fields.append("Name=:n")
            params["n"] = name

        if "unit_price" in payload and payload["unit_price"] is not None:
            fields.append("UnitPrice=:up")
            params["up"] = parse_non_negative_price(payload["unit_price"])

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update (name/unit_price)")

        res = db.execute(
            text(f"UPDATE Track SET {', '.join(fields)} WHERE TrackId=:tid"),
            params,
        )
        db.commit()

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Track not found")

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.delete("/admin/tracks/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        db.execute(text("DELETE FROM InvoiceLine WHERE TrackId = :tid"), {"tid": track_id})
        db.execute(text("DELETE FROM PlaylistTrack WHERE TrackId = :tid"), {"tid": track_id})

        res = db.execute(text("DELETE FROM Track WHERE TrackId = :tid"), {"tid": track_id})

        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="Track no existe")

        db.commit()
        return {"ok": True, "deleted": track_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
