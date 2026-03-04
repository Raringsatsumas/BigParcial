from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from ..db import get_db

router = APIRouter(tags=["catalog"])

def clamp_limit_offset(limit: int, offset: int):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    return limit, offset

@router.get("/tracks")
def list_tracks(
    query: Optional[str] = None,
    genre_id: Optional[int] = None,
    artist_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit, offset = clamp_limit_offset(limit, offset)

    where = []
    params = {}

    if query and query.strip():
        where.append("t.Name LIKE :q")
        params["q"] = f"%{query.strip()}%"

    if genre_id:
        where.append("t.GenreId = :genre_id")
        params["genre_id"] = int(genre_id)

    if artist_id:
        where.append("ar.ArtistId = :artist_id")
        params["artist_id"] = int(artist_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = text(f"""
        SELECT
            t.TrackId, t.Name AS TrackName, t.UnitPrice,
            al.Title AS AlbumTitle,
            ar.Name AS ArtistName,
            g.Name AS GenreName
        FROM Track t
        JOIN Album al ON al.AlbumId = t.AlbumId
        JOIN Artist ar ON ar.ArtistId = al.ArtistId
        LEFT JOIN Genre g ON g.GenreId = t.GenreId
        {where_sql}
        ORDER BY t.Name
        LIMIT {limit} OFFSET {offset}
    """)

    rows = db.execute(sql, params).mappings().all()
    return {"items": list(rows), "count": len(rows), "limit": limit, "offset": offset}

@router.get("/tracks/{track_id}")
def track_detail(track_id: int, db: Session = Depends(get_db)):
    sql = text("""
        SELECT
            t.TrackId, t.Name AS TrackName, t.UnitPrice,
            t.Milliseconds, t.Composer,
            al.Title AS AlbumTitle,
            ar.Name AS ArtistName,
            g.Name AS GenreName
        FROM Track t
        JOIN Album al ON al.AlbumId = t.AlbumId
        JOIN Artist ar ON ar.ArtistId = al.ArtistId
        LEFT JOIN Genre g ON g.GenreId = t.GenreId
        WHERE t.TrackId = :tid
    """)
    row = db.execute(sql, {"tid": int(track_id)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")
    return row

@router.get("/artists")
def list_artists(query: Optional[str] = None, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit, offset = clamp_limit_offset(limit, offset)

    where_sql = ""
    params = {}
    if query and query.strip():
        where_sql = "WHERE ar.Name LIKE :q"
        params["q"] = f"%{query.strip()}%"

    sql = text(f"""
        SELECT
            ar.ArtistId, ar.Name AS ArtistName,
            COUNT(DISTINCT al.AlbumId) AS Albums,
            COUNT(t.TrackId) AS Tracks
        FROM Artist ar
        LEFT JOIN Album al ON al.ArtistId = ar.ArtistId
        LEFT JOIN Track t ON t.AlbumId = al.AlbumId
        {where_sql}
        GROUP BY ar.ArtistId, ar.Name
        ORDER BY ar.Name
        LIMIT {limit} OFFSET {offset}
    """)

    rows = db.execute(sql, params).mappings().all()
    return {"items": list(rows), "count": len(rows), "limit": limit, "offset": offset}

@router.get("/genres")
def list_genres(query: Optional[str] = None, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit, offset = clamp_limit_offset(limit, offset)

    where_sql = ""
    params = {}
    if query and query.strip():
        where_sql = "WHERE g.Name LIKE :q"
        params["q"] = f"%{query.strip()}%"

    sql = text(f"""
        SELECT
            g.GenreId, g.Name AS GenreName,
            COUNT(t.TrackId) AS Tracks
        FROM Genre g
        LEFT JOIN Track t ON t.GenreId = g.GenreId
        {where_sql}
        GROUP BY g.GenreId, g.Name
        ORDER BY g.Name
        LIMIT {limit} OFFSET {offset}
    """)

    rows = db.execute(sql, params).mappings().all()
    return {"items": list(rows), "count": len(rows), "limit": limit, "offset": offset}
