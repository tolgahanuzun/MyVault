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
    start_dt = date.today() - timedelta(days=3)
    
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

        # 4. Prepare data for hourly check
        
        # Get current time info
        now = datetime.now()
        current_hour_str = now.strftime('%Y-%m-%d %H') # '2026-02-09 11'
        
        # We need to know if there is ANY record for (asset_id) in THIS HOUR.
        # Let's query records for TODAY only.
        
        today_start = datetime.combine(now.date(), time.min)
        
        existing_records_query = select(PriceHistory.asset_id, PriceHistory.date).filter(
            PriceHistory.asset_id.in_(fund_map.values()),
            PriceHistory.date >= today_start # Greater than today 00:00
        )
        existing_records_result = await db.execute(existing_records_query)
        existing_records = existing_records_result.all()
        
        # Build a set of (asset_id, 'YYYY-MM-DD HH')
        # We process Python datetime objects here, which is safer than DB strftime.
        existing_hourly_keys = set()
        for rec in existing_records:
            asset_id = rec[0]
            rec_date = rec[1] # datetime object
            if rec_date:
                key = (asset_id, rec_date.strftime('%Y-%m-%d %H'))
                existing_hourly_keys.add(key)
        
        new_records = []
        
        for index, row in result.iterrows():
            code = row['code']
            asset_id = fund_map.get(code)
            
            # Key for current hour check
            current_key = (asset_id, current_hour_str)
            
            if current_key not in existing_hourly_keys:
                price_val = float(row['price'])
                
                new_records.append(PriceHistory(
                    asset_id=asset_id,
                    date=now, # Save with full precision
                    price=price_val
                ))
                # Add to set to prevent duplicates within the same batch
                existing_hourly_keys.add(current_key)
        
        # 5. Bulk Insert
        if new_records:
            db.add_all(new_records)
            await db.commit()
            logger.info(f"Added {len(new_records)} new price records (Hourly check passed).")
        else:
            logger.info(f"No new price records. All assets already have data for {current_hour_str}.")
            
    except Exception as e:
        logger.error(f"Data fetch error: {e}")
        await db.rollback()
