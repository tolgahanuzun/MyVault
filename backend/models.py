from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Enum, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime
import enum

class AssetType(str, enum.Enum):
    FUND = "FUND"
    STOCK = "STOCK"

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

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) # TTE, THYAO
    name = Column(String)
    type = Column(String) # FUND or STOCK
    
    price_history = relationship("PriceHistory", back_populates="asset")
    portfolios = relationship("Portfolio", back_populates="asset")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    quantity = Column(Float) # Quantity
    average_cost = Column(Float) # Average Cost (Per unit)
    
    user = relationship("User", back_populates="portfolios")
    asset = relationship("Asset", back_populates="portfolios")

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

    # An asset can have only one price for the same date.
    # Note: With DateTime, uniqueness is down to the second. 
    # Logic in fetcher.py handles daily checks.
    __table_args__ = (
        UniqueConstraint('asset_id', 'date', name='uix_price_asset_date'),
    )
