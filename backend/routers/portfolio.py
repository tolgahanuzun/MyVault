from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, tuple_
from backend.database import get_db
from backend.models import Portfolio, Asset, PriceHistory, User
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

class PortfolioBase(BaseModel):
    asset_id: int
    quantity: float
    average_cost: float

class TransactionCreate(PortfolioBase):
    user_id: int = 1 # Default user

class PortfolioItemResponse(PortfolioBase):
    id: int
    asset_code: str
    asset_name: str
    current_price: float
    total_value: float
    profit_loss: float
    profit_loss_percent: float
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[PortfolioItemResponse])
async def read_portfolio(user_id: int = 1, db: AsyncSession = Depends(get_db)):
    # 1. Fetch user portfolio
    result = await db.execute(select(Portfolio).filter(Portfolio.user_id == user_id))
    items = result.scalars().all()
    
    if not items:
        return []

    # 2. Get all asset IDs in portfolio
    asset_ids = [item.asset_id for item in items]

    # 3. Batch Fetch Latest Prices (Optimized Query)
    # Subquery to find the max date for each asset
    subquery = select(
        PriceHistory.asset_id,
        func.max(PriceHistory.date).label('max_date')
    ).filter(PriceHistory.asset_id.in_(asset_ids)).group_by(PriceHistory.asset_id).subquery()

    # Join to get the prices
    latest_prices_stmt = select(PriceHistory).join(
        subquery,
        (PriceHistory.asset_id == subquery.c.asset_id) & 
        (PriceHistory.date == subquery.c.max_date)
    )
    latest_prices_result = await db.execute(latest_prices_stmt)
    latest_prices = latest_prices_result.scalars().all()

    # Map prices for O(1) lookup
    price_map = {p.asset_id: p.price for p in latest_prices}
    
    result_list = []
    for item in items:
        # Asset info (Lazy load might not work well in async without explicit options, 
        # so we might need to eager load. However, let's try to rely on simple access 
        # if the session is still active, or better: explicit join)
        
        # To avoid AsyncIO error with lazy loading, let's fetch asset explicitly if not loaded
        # Or better: update the initial query to joinedload(Portfolio.asset)
        # For now, let's assume we need to fetch asset if it's missing or just fetch it.
        # Ideally, we should use: .options(joinedload(Portfolio.asset)) in the first query.
        
        # Let's do a quick fetch for asset if needed, or update the initial query.
        # Updating the initial query is cleaner. 
        # But to match previous logic structure, let's just fetch it here if not present.
        # Actually, for N items, N queries is bad.
        # Let's just fetch asset here for simplicity as N is small.
        # Better: use `await db.get(Asset, item.asset_id)`
        
        asset = await db.get(Asset, item.asset_id)
        
        # Get price from map
        current_price = price_map.get(asset.id, item.average_cost)
        
        total_value = item.quantity * current_price
        cost_basis = item.quantity * item.average_cost
        profit_loss = total_value - cost_basis
        profit_loss_percent = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
        
        result_list.append(PortfolioItemResponse(
            id=item.id,
            asset_id=asset.id,
            quantity=item.quantity,
            average_cost=item.average_cost,
            asset_code=asset.code,
            asset_name=asset.name,
            current_price=current_price,
            total_value=total_value,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent
        ))
        
    return result_list

@router.get("/asset/{asset_id}", response_model=PortfolioItemResponse)
async def read_portfolio_asset(asset_id: int, user_id: int = 1, db: AsyncSession = Depends(get_db)):
    # This endpoint is single item
    result = await db.execute(
        select(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.asset_id == asset_id)
    )
    item = result.scalars().first()
    
    # Check if user owns it or not
    asset = await db.get(Asset, asset_id)
    if not asset:
         raise HTTPException(status_code=404, detail="Asset not found")

    # Get latest price
    last_price_stmt = select(PriceHistory)\
        .filter(PriceHistory.asset_id == asset.id)\
        .order_by(PriceHistory.date.desc())\
        .limit(1)
        
    last_price_result = await db.execute(last_price_stmt)
    last_price_entry = last_price_result.scalars().first()
    
    current_price = last_price_entry.price if last_price_entry else 0

    if not item:
        return PortfolioItemResponse(
            id=0,
            asset_id=asset.id,
            quantity=0,
            average_cost=0,
            asset_code=asset.code,
            asset_name=asset.name,
            current_price=current_price,
            total_value=0,
            profit_loss=0,
            profit_loss_percent=0
        )
    
    # Calculate for owned item
    total_value = item.quantity * current_price
    cost_basis = item.quantity * item.average_cost
    profit_loss = total_value - cost_basis
    profit_loss_percent = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
    
    return PortfolioItemResponse(
        id=item.id,
        asset_id=asset.id,
        quantity=item.quantity,
        average_cost=item.average_cost,
        asset_code=asset.code,
        asset_name=asset.name,
        current_price=current_price,
        total_value=total_value,
        profit_loss=profit_loss,
        profit_loss_percent=profit_loss_percent
    )

@router.post("/transaction")
async def create_transaction(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists, create if not (for convenience)
    user_result = await db.execute(select(User).filter(User.id == transaction.user_id))
    user = user_result.scalars().first()
    
    if not user:
        user = User(id=transaction.user_id, username="default", full_name="Default User")
        db.add(user)
        await db.commit()
    
    # Check if asset exists in portfolio
    portfolio_result = await db.execute(select(Portfolio).filter(
        Portfolio.user_id == transaction.user_id,
        Portfolio.asset_id == transaction.asset_id
    ))
    portfolio_item = portfolio_result.scalars().first()
    
    if portfolio_item:
        # Calculate weighted average cost
        total_quantity = portfolio_item.quantity + transaction.quantity
        total_cost = (portfolio_item.quantity * portfolio_item.average_cost) + (transaction.quantity * transaction.average_cost)
        new_average_cost = total_cost / total_quantity if total_quantity > 0 else 0
        
        portfolio_item.quantity = total_quantity
        portfolio_item.average_cost = new_average_cost
    else:
        portfolio_item = Portfolio(
            user_id=transaction.user_id,
            asset_id=transaction.asset_id,
            quantity=transaction.quantity,
            average_cost=transaction.average_cost
        )
        db.add(portfolio_item)
    
    await db.commit()
    return {"message": "Transaction successful"}
