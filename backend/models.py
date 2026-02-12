from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Enum, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime
import enum

class AssetType(str, enum.Enum):
    FUND = "FUND"
    STOCK = "STOCK"

class OrderType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    
    # FastAdmin authentication fields
    hash_password = Column(String, nullable=True) # Nullable for existing users
    is_superuser = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(Text, nullable=True)

    portfolios = relationship("Portfolio", back_populates="user")

    def __str__(self):
        return f"ID:{self.id}: {self.username} - {self.full_name}"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) # TTE, THYAO
    name = Column(String)
    type = Column(String) # FUND or STOCK
    
    price_history = relationship("PriceHistory", back_populates="asset")
    portfolios = relationship("Portfolio", back_populates="asset")

    def __str__(self):
        return f"ID:{self.id}: {self.code} - {self.name} - {self.type}"

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    quantity = Column(Float) # Quantity
    average_cost = Column(Float) # Average Cost (Per unit)
    
    user = relationship("User", back_populates="portfolios")
    asset = relationship("Asset", back_populates="portfolios")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")

    def __str__(self):
        return f"ID:{self.id}: {self.quantity} - {self.average_cost}"
    # A user can only hold one record for an asset in their portfolio (Quantity increases)
    __table_args__ = (
        UniqueConstraint('user_id', 'asset_id', name='uix_portfolio_user_asset'),
    )

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    date = Column(DateTime, index=True)
    price = Column(Float)
    
    asset = relationship("Asset", back_populates="price_history")

    def __str__(self):
        return f"ID:{self.id}: {self.price}"

    # An asset can have only one price for the same date.
    # Note: With DateTime, uniqueness is down to the second. 
    # Logic in fetcher.py handles daily checks.
    __table_args__ = (
        UniqueConstraint('asset_id', 'date', name='uix_price_asset_date'),
    )

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    type = Column(String) # BUY or SELL (stored as string but uses OrderType enum in logic)
    quantity = Column(Float) # Transaction quantity (always positive)
    price = Column(Float) # Transaction price
    executed_at = Column(DateTime, default=datetime.utcnow)
    profit_snapshot = Column(Float, nullable=True) # Realized profit for SELL orders
    cost_snapshot = Column(Float) # Average cost at the time of order (before update for BUY, at time of SELL)

    portfolio = relationship("Portfolio", back_populates="orders")

    def __str__(self):
        return f"ID:{self.id}: {self.type} - {self.quantity} @ {self.price}"
