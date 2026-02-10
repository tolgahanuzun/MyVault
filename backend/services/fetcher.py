from tefas import Crawler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import cast, Date, func, select
from backend.models import Asset, PriceHistory, AssetType
from datetime import datetime, date, timedelta, time
import logging

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_fund_prices(db: AsyncSession):
    """
    Fetches latest prices for all funds in the database from TEFAS and saves them.
    Optimized to minimize DB queries and prevent hourly duplicates.
    """
    tefas = Crawler()
    
    # 1. Get all assets of type FUND
    result = await db.execute(select(Asset).filter(Asset.type == AssetType.FUND.value))
    funds = result.scalars().all()
    
    if not funds:
        logger.info("No funds found to track.")
        return

    # Create a map of Code -> ID for quick lookup
    fund_map = {fund.code: fund.id for fund in funds}
    fund_codes = list(fund_map.keys())
    
    # 2. Fetch data from TEFAS (Last 3 days to be safe)
    start_dt = date.today() - timedelta(days=2)
    
    try:
        # Fetching bulk data
        # Note: Crawler fetch is synchronous
        result = tefas.fetch(start=start_dt.strftime("%Y-%m-%d"), 
                             columns=["code", "date", "price"])
        
        if result is None or result.empty:
            logger.warning("Could not fetch data from TEFAS.")
            return

        # 3. Filter only our funds
        result = result[result['code'].isin(fund_codes)]
        
        if result.empty:
            logger.info("No data found for tracked funds in the last few days.")
            return

        # 4. Prepare data for DAILY check (Optimized)
        
        # We need to know if we already have price for (asset_id, date)
        # Fetch existing records from start_dt onwards
        
        existing_records_query = select(PriceHistory.asset_id, PriceHistory.date).filter(
            PriceHistory.asset_id.in_(fund_map.values()),
            PriceHistory.date >= start_dt
        )
        existing_records_result = await db.execute(existing_records_query)
        existing_records = existing_records_result.all()
        
        # Build a set of (asset_id, date_string) for O(1) lookup
        # We use date() part only to ensure one price per day per asset
        existing_keys = set()
        for rec in existing_records:
            asset_id = rec[0]
            rec_date = rec[1] 
            if rec_date:
                existing_keys.add((asset_id, rec_date.date()))
        
        new_records = []
        
        for index, row in result.iterrows():
            code = row['code']
            asset_id = fund_map.get(code)
            
            # TEFAS returns a Timestamp, convert to date/datetime
            # row['date'] from tefas crawler is usually a datetime object (pandas timestamp)
            tefas_date = row['date']
            
            # Ensure we have a date object for comparison
            if hasattr(tefas_date, 'date'):
                price_date_obj = tefas_date.date()
            else:
                price_date_obj = tefas_date # Fallback if already date
            
            # Key for daily check
            current_key = (asset_id, price_date_obj)
            
            if current_key not in existing_keys:
                price_val = float(row['price'])
                
                new_records.append(PriceHistory(
                    asset_id=asset_id,
                    date=tefas_date, # Save the full datetime from TEFAS
                    price=price_val
                ))
                # Add to set to prevent duplicates within the same batch
                existing_keys.add(current_key)
        
        # 5. Bulk Insert
        if new_records:
            db.add_all(new_records)
            await db.commit()
            logger.info(f"Added {len(new_records)} new price records.")
        else:
            logger.info(f"No new price records found.")
            
    except Exception as e:
        logger.error(f"Data fetch error: {e}")
        await db.rollback()
