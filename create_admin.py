from backend.database import AsyncSessionLocal
from backend.models import User
import bcrypt
import sys
import getpass
import asyncio
from sqlalchemy import select

# Add project root to path if module not found error occurs
sys.path.append('.')

async def create_superuser(username, password, full_name="Admin User"):
    async with AsyncSessionLocal() as db:
        try:
            # Check if user exists
            result = await db.execute(select(User).filter(User.username == username))
            existing_user = result.scalars().first()
            if existing_user:
                print(f"WARNING: User '{username}' already exists.")
                return

            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Create new user
            new_user = User(
                username=username,
                full_name=full_name,
                hash_password=hashed_password,
                is_superuser=True,
                is_active=True
            )

            db.add(new_user)
            await db.commit()
            print(f"SUCCESS: Superuser '{username}' created.")
            
        except Exception as e:
            print(f"ERROR: {e}")
            await db.rollback()

if __name__ == "__main__":
    print("--- Create Superuser ---")
    try:
        u_name = input("Username: ").strip()
        # Use getpass to hide password input
        pwd = getpass.getpass("Password: ").strip()
        
        if u_name and pwd:
            asyncio.run(create_superuser(u_name, pwd))
        else:
            print("ERROR: Username and password cannot be empty!")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
