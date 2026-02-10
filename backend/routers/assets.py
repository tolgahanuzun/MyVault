from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Asset, AssetType, PriceHistory
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import date, datetime

router = APIRouter(
    prefix="/assets",
    tags=["assets"]
)

class AssetBase(BaseModel):
    code: str
    name: str
    type: AssetType

    # Pydantic v2 validator (field_validator)
    # Convert incoming code to uppercase regardless of input
    @field_validator('code')
    @classmethod
    def upper_case_code(cls, v: str) -> str:
        return v.upper()

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    
    class Config:
        from_attributes = True # orm_mode for pydantic v2

class PricePoint(BaseModel):
    date: datetime # Changed date -> datetime
    price: float

class AssetDetailResponse(AssetResponse):
    history: List[PricePoint] = []

@router.get("/", response_model=List[AssetResponse])
async def read_assets(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).offset(skip).limit(limit))
    assets = result.scalars().all()
    return assets

@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def read_asset_detail(asset_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # History sorted by date
    history_result = await db.execute(
        select(PriceHistory)
        .filter(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date.asc())
    )
    history = history_result.scalars().all()
    
    return {
        "id": asset.id,
        "code": asset.code,
        "name": asset.name,
        "type": asset.type,
        "history": history
    }

@router.post("/", response_model=AssetResponse)
async def create_asset(asset: AssetCreate, db: AsyncSession = Depends(get_db)):
    # Code already uppercased by validator
    result = await db.execute(select(Asset).filter(Asset.code == asset.code))
    db_asset = result.scalars().first()
    
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset already exists")
    
    new_asset = Asset(code=asset.code, name=asset.name, type=asset.type)
    db.add(new_asset)
    await db.commit()
    await db.refresh(new_asset)
    return new_asset
