from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import Portfolio, Asset, PriceHistory, User
from backend.security import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

class PortfolioBase(BaseModel):
    asset_id: int
    quantity: float
    average_cost: float

class TransactionCreate(PortfolioBase):
    pass 
    # user_id is removed, inferred from token

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
async def read_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch user portfolio
    result = await db.execute(select(Portfolio).filter(Portfolio.user_id == current_user.id))
    items = result.scalars().all()
    
    if not items:
        return []

    # 2. Get all asset IDs in portfolio
    asset_ids = [item.asset_id for item in items]

    # 3. Batch Fetch Latest Prices (Optimized Query)
    subquery = select(
        PriceHistory.asset_id,
        func.max(PriceHistory.date).label('max_date')
    ).filter(PriceHistory.asset_id.in_(asset_ids)).group_by(PriceHistory.asset_id).subquery()

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
async def read_portfolio_asset(
    asset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Portfolio).filter(Portfolio.user_id == current_user.id, Portfolio.asset_id == asset_id)
    )
    item = result.scalars().first()
    
    # Check if asset exists
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
        # User doesn't own this asset yet, return empty/zero state
        # But maybe we want to allow viewing detail even if not owned?
        # The logic below returns a zero-quantity portfolio item which is fine for "Add" context.
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
async def create_transaction(
    transaction: TransactionCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if asset exists in portfolio
    portfolio_result = await db.execute(select(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.asset_id == transaction.asset_id
    ))
    portfolio_item = portfolio_result.scalars().first()
    
    if portfolio_item:
        if transaction.quantity > 0:
            # Buying: Update Weighted Average Cost
            total_quantity = portfolio_item.quantity + transaction.quantity
            total_cost = (portfolio_item.quantity * portfolio_item.average_cost) + (transaction.quantity * transaction.average_cost)
            # Avoid division by zero
            new_average_cost = total_cost / total_quantity if total_quantity > 0 else 0
            
            portfolio_item.quantity = total_quantity
            portfolio_item.average_cost = new_average_cost
        else:
            # Selling: Cost basis doesn't change (FIFO/LIFO ignored), only quantity reduces.
            # transaction.quantity is negative here.
            
            if portfolio_item.quantity + transaction.quantity < 0:
                 raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
            
            portfolio_item.quantity += transaction.quantity
            
            # If quantity becomes 0, we can either keep it or delete it.
            # Deleting it keeps the DB clean.
            if portfolio_item.quantity <= 0:
                await db.delete(portfolio_item)

    else:
        if transaction.quantity < 0:
            raise HTTPException(status_code=400, detail="Cannot sell asset you do not own")

        portfolio_item = Portfolio(
            user_id=current_user.id,
            asset_id=transaction.asset_id,
            quantity=transaction.quantity,
            average_cost=transaction.average_cost
        )
        db.add(portfolio_item)
    
    await db.commit()
    return {"message": "Transaction successful"}
