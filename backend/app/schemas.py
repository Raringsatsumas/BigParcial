from pydantic import BaseModel, Field
from typing import Optional, List

class TrackOut(BaseModel):
    TrackId: int
    TrackName: str
    UnitPrice: float
    AlbumTitle: Optional[str] = None
    ArtistName: Optional[str] = None
    GenreName: Optional[str] = None

class ArtistOut(BaseModel):
    ArtistId: int
    ArtistName: str
    Albums: int
    Tracks: int

class GenreOut(BaseModel):
    GenreId: int
    GenreName: str
    Tracks: int

class BillingInfo(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class PurchaseRequest(BaseModel):
    customer_id: int = Field(..., ge=1)
    track_id: int = Field(..., ge=1)
    quantity: int = Field(1, ge=1, le=100)
    billing: Optional[BillingInfo] = None

class PurchaseResponse(BaseModel):
    invoice_id: int
    total: float
