from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from backend.database import get_db
from backend.models import Portfolio, Asset, PriceHistory, User, Order, OrderType
from backend.security import get_current_user
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

class PortfolioBase(BaseModel):
    asset_id: int
    quantity: float
    average_cost: float

class OrderCreate(BaseModel):
    asset_id: int
    type: OrderType
    quantity: float
    price: float
    executed_at: datetime | None = None

class OrderResponse(BaseModel):
    id: int
    type: str
    quantity: float
    price: float
    executed_at: datetime
    profit_snapshot: float | None
    cost_snapshot: float | None
    
    class Config:
        from_attributes = True

class PortfolioHistoryItem(BaseModel):
    date: str
    total_value: float
    total_cost: float
    total_profit: float

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

@router.get("/history", response_model=List[PortfolioHistoryItem])
async def read_portfolio_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch user portfolio
    result = await db.execute(select(Portfolio).filter(Portfolio.user_id == current_user.id))
    items = result.scalars().all()
    
    if not items:
        return []

    # Map asset quantities for simulation
    portfolio_map = {item.asset_id: {"quantity": item.quantity, "avg_cost": item.average_cost} for item in items}
    asset_ids = list(portfolio_map.keys())

    # 2. Get history prices for these assets
    # We select all history first, then process in Python to avoid SQLite date casting issues
    history_stmt = select(
        PriceHistory.date,
        PriceHistory.asset_id,
        PriceHistory.price
    ).filter(
        PriceHistory.asset_id.in_(asset_ids)
    ).order_by(PriceHistory.date)
    
    history_result = await db.execute(history_stmt)
    history_rows = history_result.all()
    
    # 3. Aggregate in Python with forward-fill
    date_asset_price_map = {}
    all_dates = set()
    
    for row in history_rows:
        # row.date might be string or datetime depending on SQLite driver config
        # Safe handling
        raw_date = row.date
        if isinstance(raw_date, str):
            try:
                dt = datetime.fromisoformat(raw_date)
                day = dt.date()
            except:
                 # Fallback if format is different
                 day = datetime.now().date() # Should not happen ideally
        else:
            day = raw_date.date()
            
        if day not in date_asset_price_map:
            date_asset_price_map[day] = {}
        # If multiple entries for same day, last one wins (due to order_by)
        date_asset_price_map[day][row.asset_id] = row.price
        all_dates.add(day)
        
    sorted_dates = sorted(list(all_dates))
    
    response = []
    last_known_prices = {} # asset_id -> price
    
    for day in sorted_dates:
        # Update prices for today
        if day in date_asset_price_map:
            for asset_id, price in date_asset_price_map[day].items():
                last_known_prices[asset_id] = price
        
        # Calculate totals
        daily_value = 0.0
        daily_cost = 0.0
        
        for asset_id, item_data in portfolio_map.items():
            # Only include assets we have a price for (or have seen a price for)
            if asset_id in last_known_prices:
                qty = item_data["quantity"]
                cost = item_data["avg_cost"]
                price = last_known_prices[asset_id]
                
                daily_value += qty * price
                daily_cost += qty * cost
        
        # Only add to response if we have some value (optional)
        profit = daily_value - daily_cost
        
        response.append(PortfolioHistoryItem(
            date=day.strftime("%Y-%m-%d"),
            total_value=daily_value,
            total_cost=daily_cost,
            total_profit=profit
        ))
        
    return response

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

@router.post("/add_asset/{asset_id}")
async def add_asset_to_portfolio(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if exists
    result = await db.execute(select(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.asset_id == asset_id
    ))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Asset already in portfolio")
        
    # Check if asset valid
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    new_item = Portfolio(
        user_id=current_user.id,
        asset_id=asset_id,
        quantity=0,
        average_cost=0
    )
    db.add(new_item)
    await db.commit()
    return {"message": "Asset added to portfolio"}

@router.post("/order")
async def create_order(
    order_data: OrderCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch Portfolio
    result = await db.execute(select(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.asset_id == order_data.asset_id
    ))
    portfolio_item = result.scalars().first()
    
    if not portfolio_item:
        raise HTTPException(status_code=400, detail="Asset not found in portfolio. Please add it first.")
    
    # 2. Logic
    if order_data.executed_at is None:
        order_data.executed_at = datetime.utcnow()

    # Create Order object
    new_order = Order(
        portfolio_id=portfolio_item.id,
        type=order_data.type,
        quantity=order_data.quantity,
        price=order_data.price,
        executed_at=order_data.executed_at,
        cost_snapshot=portfolio_item.average_cost
    )

    if order_data.type == OrderType.BUY:
        # Buy Logic
        # New Avg Cost = ((Old Qty * Old Cost) + (New Qty * New Price)) / Total Qty
        total_cost_basis = (portfolio_item.quantity * portfolio_item.average_cost) + (order_data.quantity * order_data.price)
        total_quantity = portfolio_item.quantity + order_data.quantity
        
        portfolio_item.average_cost = total_cost_basis / total_quantity if total_quantity > 0 else 0
        portfolio_item.quantity = total_quantity
        
    elif order_data.type == OrderType.SELL:
        # Sell Logic
        if portfolio_item.quantity < order_data.quantity:
             raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
             
        # Realized Profit = (Sell Price - Avg Cost) * Sell Qty
        # Use current avg cost for profit calc
        realized_profit = (order_data.price - portfolio_item.average_cost) * order_data.quantity
        new_order.profit_snapshot = realized_profit
        
        portfolio_item.quantity -= order_data.quantity
        # Avg Cost remains same for weighted average method on Sell
            
    db.add(new_order)
    await db.commit()
    return {"message": "Order processed successfully"}

@router.get("/orders/{asset_id}", response_model=List[OrderResponse])
async def get_asset_orders(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find portfolio
    result = await db.execute(select(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.asset_id == asset_id
    ))
    portfolio_item = result.scalars().first()
    
    if not portfolio_item:
         return []
         
    # Fetch orders
    orders_result = await db.execute(
        select(Order).filter(Order.portfolio_id == portfolio_item.id).order_by(Order.executed_at.desc())
    )
    return orders_result.scalars().all()
