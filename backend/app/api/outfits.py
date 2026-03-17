"""
Outfit API endpoints.
"""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.outfit_service import OutfitService
from app.schemas import OutfitResponse, PaginatedResponse

router = APIRouter(prefix="/outfits", tags=["Outfits"])


@router.get("/search", response_model=PaginatedResponse)
def search_outfits(
    q: str = Query(..., min_length=1, description="Vibe/style search (e.g., 'date-night', 'casual', 'retro')"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    service = OutfitService(db)
    outfits, total = service.search_by_vibe(
        vibe=q,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        items=[OutfitResponse.model_validate(o) for o in outfits],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("", response_model=PaginatedResponse)
def list_outfits(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    service = OutfitService(db)
    outfits, total = service.get_all(page=page, per_page=per_page)
    return PaginatedResponse(
        items=[OutfitResponse.model_validate(o) for o in outfits],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/{outfit_id}", response_model=OutfitResponse)
def get_outfit(outfit_id: UUID, db: Session = Depends(get_db)):
    service = OutfitService(db)
    outfit = service.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitResponse.model_validate(outfit)
