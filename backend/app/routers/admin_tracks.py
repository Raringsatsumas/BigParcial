from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from .auth import get_current_user

router = APIRouter(prefix="/admin/tracks", tags=["admin-tracks"])


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    return user


@router.post("")
def create_track(
    payload: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        name = (payload.get("name") or "").strip()
        unit_price = payload.get("unit_price")
        genre_id = payload.get("genre_id")
        media_type_id = payload.get("media_type_id") or 1
        composer = payload.get("composer")
        milliseconds = int(payload.get("milliseconds") or 1)
        bytes_value = int(payload.get("bytes") or 1)

        album_id = payload.get("album_id")
        album_mode = payload.get("album_mode") or payload.get("album_source")
        artist_id = payload.get("artist_id")
        new_album_title = (
            payload.get("new_album_title")
            or payload.get("album_title")
            or payload.get("new_album_name")
            or ""
        ).strip()

        if not name:
            raise HTTPException(status_code=400, detail="Nombre requerido")

        if unit_price is None or str(unit_price).strip() == "":
            raise HTTPException(status_code=400, detail="Precio requerido")

        # Si no viene album_id, intentamos crear uno nuevo si mandan artista + título
        if not album_id:
            if album_mode == "new" or new_album_title:
                if not artist_id:
                    raise HTTPException(status_code=400, detail="Artista requerido para crear álbum")
                if not new_album_title:
                    raise HTTPException(status_code=400, detail="Título de álbum requerido")

                next_album_row = db.execute(
                    text("SELECT COALESCE(MAX(AlbumId), 0) + 1 AS next_id FROM Album")
                ).mappings().first()
                next_album_id = int(next_album_row["next_id"])

                db.execute(
                    text("""
                        INSERT INTO Album (AlbumId, Title, ArtistId)
                        VALUES (:album_id, :title, :artist_id)
                    """),
                    {
                        "album_id": next_album_id,
                        "title": new_album_title,
                        "artist_id": int(artist_id),
                    },
                )
                album_id = next_album_id
            else:
                raise HTTPException(status_code=400, detail="Álbum requerido")

        next_track_row = db.execute(
            text("SELECT COALESCE(MAX(TrackId), 0) + 1 AS next_id FROM Track")
        ).mappings().first()
        next_track_id = int(next_track_row["next_id"])

        db.execute(
            text("""
                INSERT INTO Track
                    (TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice)
                VALUES
                    (:track_id, :name, :album_id, :media_type_id, :genre_id, :composer, :milliseconds, :bytes_value, :unit_price)
            """),
            {
                "track_id": next_track_id,
                "name": name,
                "album_id": int(album_id),
                "media_type_id": int(media_type_id),
                "genre_id": int(genre_id) if genre_id not in (None, "", 0, "0") else None,
                "composer": composer,
                "milliseconds": milliseconds,
                "bytes_value": bytes_value,
                "unit_price": float(unit_price),
            },
        )

        db.commit()
        return {"ok": True, "track_id": next_track_id, "album_id": int(album_id)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando track: {str(e)}")


@router.put("/{track_id}")
def update_track(
    track_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        exists = db.execute(
            text("SELECT TrackId FROM Track WHERE TrackId = :track_id"),
            {"track_id": track_id},
        ).mappings().first()

        if not exists:
            raise HTTPException(status_code=404, detail="Track no encontrado")

        fields = []
        params = {"track_id": track_id}

        if "name" in payload:
            fields.append("Name = :name")
            params["name"] = (payload.get("name") or "").strip()

        if "unit_price" in payload:
            fields.append("UnitPrice = :unit_price")
            params["unit_price"] = float(payload.get("unit_price"))

        if "genre_id" in payload:
            fields.append("GenreId = :genre_id")
            genre_id = payload.get("genre_id")
            params["genre_id"] = int(genre_id) if genre_id not in (None, "", 0, "0") else None

        if "album_id" in payload:
            fields.append("AlbumId = :album_id")
            params["album_id"] = int(payload.get("album_id"))

        if "media_type_id" in payload:
            fields.append("MediaTypeId = :media_type_id")
            params["media_type_id"] = int(payload.get("media_type_id"))

        if not fields:
            return {"ok": True, "updated": False}

        sql = f"UPDATE Track SET {', '.join(fields)} WHERE TrackId = :track_id"
        db.execute(text(sql), params)
        db.commit()

        return {"ok": True, "updated": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando track: {str(e)}")


@router.delete("/{track_id}")
def delete_track(
    track_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        # Borra referencias para no romper FK
        db.execute(
            text("DELETE FROM InvoiceLine WHERE TrackId = :track_id"),
            {"track_id": track_id},
        )
        db.execute(
            text("DELETE FROM PlaylistTrack WHERE TrackId = :track_id"),
            {"track_id": track_id},
        )

        result = db.execute(
            text("DELETE FROM Track WHERE TrackId = :track_id"),
            {"track_id": track_id},
        )

        if result.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="Track no encontrado")

        db.commit()
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando track: {str(e)}")
