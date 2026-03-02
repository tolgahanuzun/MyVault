from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import cast, Date, func, select
from backend.models import Asset, PriceHistory, AssetType
from datetime import datetime, date, timedelta
import logging
import requests
import time
import random
from backend.config import settings

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_fund_prices(db: AsyncSession):
    """
    Fetches latest prices for all funds in the database from our internal API and saves them.
    Iterates through all tracked funds and fetches the price individually.
    Implements ordering by last update time (oldest first) and retry mechanism.
    """
    
    # 1. Get all assets of type FUND, ordered by last price update date ascending (nulls first)
    # We want funds that haven't been updated recently to be processed first.
    
    # Subquery to find the max date for each asset
    subquery = (
        select(PriceHistory.asset_id, func.max(PriceHistory.date).label("last_update"))
        .group_by(PriceHistory.asset_id)
        .subquery()
    )

    # Main query joining Asset with the subquery
    query = (
        select(Asset, subquery.c.last_update)
        .outerjoin(subquery, Asset.id == subquery.c.asset_id)
        .filter(Asset.type == AssetType.FUND.value)
        .order_by(subquery.c.last_update.asc().nullsfirst())
    )
    
    result = await db.execute(query)
    funds_data = result.all()
    
    if not funds_data:
        logger.info("No funds found to track.")
        return

    today = date.today()
    one_hour_ago = datetime.now() - timedelta(hours=1)
    new_records_count = 0

    # Initialize Session
    session = requests.Session()
    if settings.API_TOKEN:
        session.headers.update({'Authorization': f'Token {settings.API_TOKEN}'})

    for row in funds_data:
        fund = row[0]
        last_update = row[1]
        
        # Check if updated in last 1 hour
        if last_update:
            # last_update might be datetime or string depending on DB driver
            if isinstance(last_update, str):
                 try:
                     last_update_dt = datetime.fromisoformat(last_update)
                 except:
                     last_update_dt = None
            else:
                 last_update_dt = last_update
                 
            if last_update_dt and last_update_dt > one_hour_ago:
                logger.info(f"Skipping {fund.code}, updated recently at {last_update_dt}")
                continue

        retry_count = 0
        max_retries = 3
        price = None
        
        while retry_count < max_retries:
            try:
                # Add small delay to be gentle on our own API
                time.sleep(0.1)
                
                # Fetch price from API
                price = fetch_fund_price_from_api(fund.code, session)
                
                if price is not None:
                    break # Success
                
                retry_count += 1
                logger.warning(f"Attempt {retry_count}/{max_retries} failed for {fund.code}. Retrying...")
                time.sleep(1) # Wait before retry
                
            except Exception as e:
                logger.error(f"Error processing fund {fund.code} (Attempt {retry_count + 1}): {e}")
                retry_count += 1
                time.sleep(1)
        
        if price is None:
            logger.error(f"Failed to fetch price for {fund.code} after {max_retries} attempts. Skipping.")
            continue

        if price == 0:
            logger.warning(f"Fetched price is 0 for {fund.code}. Skipping update.")
            continue

        try:
            # Check existence
            existing_query = select(PriceHistory).filter(
                PriceHistory.asset_id == fund.id,
                cast(PriceHistory.date, Date) == today
            )
            existing_result = await db.execute(existing_query)
            existing_record = existing_result.scalars().first()
            
            if existing_record:
                # Update existing record if needed
                if existing_record.price != price:
                    existing_record.price = price
                    existing_record.date = datetime.now()
                    logger.info(f"Updated price for {fund.code}: {price}")
            else:
                # Create new record
                new_record = PriceHistory(
                    asset_id=fund.id,
                    date=datetime.now(),
                    price=price
                )
                db.add(new_record)
                new_records_count += 1
                logger.info(f"New price for {fund.code}: {price}")
        except Exception as e:
             logger.error(f"Database error for {fund.code}: {e}")

    try:
        await db.commit()
        if new_records_count > 0:
            logger.info(f"Successfully added {new_records_count} new price records.")
    except Exception as e:
        logger.error(f"Database commit error: {e}")
        await db.rollback()

def fetch_fund_price_from_api(fund_code: str, session: requests.Session = None) -> float | None:
    """
    Fetches the latest price of a specific fund from our internal API.
    Target URL: {API_BASE_URL}/api/v1/myvault/funds/{fund_code}/
    """
    base_url = settings.API_BASE_URL.rstrip('/')
    url = f"{base_url}/api/v1/myvault/funds/{fund_code.upper()}/"
    
    try:
        req_obj = session if session else requests
        
        response = req_obj.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Expected format: {"code": "AFT", "price": 12.3456, "source": "...", "timestamp": "..."}
        if "price" in data:
            return float(data["price"])
        else:
            logger.warning(f"API response missing 'price' field for {fund_code}: {data}")
            return None

    except Exception as e:
        logger.error(f"Error fetching price for {fund_code} from API: {e}")
        return None
