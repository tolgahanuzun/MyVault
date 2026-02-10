from fastadmin import SqlAlchemyModelAdmin, register, WidgetType, action
from backend.models import User, Asset, Portfolio, PriceHistory
from backend.database import AsyncSessionLocal
from backend.services.fetcher import fetch_fund_prices
from sqlalchemy import select, update
import bcrypt
import typing as tp
import uuid

# SQLAlchemy session maker (Async for FastAdmin)
# AsyncSessionLocal is imported from backend.database

class BaseAdmin(SqlAlchemyModelAdmin):
    actions = ("delete_selected_action",)

    @action(description="Seçilenleri Sil")
    async def delete_selected_action(self, objs: list[tp.Any]) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            for obj in objs:
                pk = getattr(obj, "id", None)
                if pk is not None:
                    db_obj = await session.get(self.model_cls, pk)
                    if db_obj:
                        await session.delete(db_obj)
            await session.commit()

@register(User, sqlalchemy_sessionmaker=AsyncSessionLocal)
class UserAdmin(BaseAdmin):
    exclude = ("hash_password",)
    list_display = ("id", "username", "full_name", "is_superuser", "is_active")
    list_display_links = ("id", "username")
    search_fields = ("username", "full_name")
    list_filter = ("is_superuser", "is_active")
    
    formfield_overrides = {
        "username": (WidgetType.Input, {"required": True}),
        "hash_password": (WidgetType.PasswordInput, {"passwordModalForm": True}),
        "avatar_url": (WidgetType.Upload, {"required": False}),
    }

    async def authenticate(self, username: str, password: str) -> uuid.UUID | int | None:
        sessionmaker = self.get_sessionmaker()
        # Async session usage
        async with sessionmaker() as session:
            query = select(self.model_cls).filter_by(username=username, is_active=True, is_superuser=True)
            result = await session.scalars(query)
            user = result.first()
            
            if not user:
                return None
            
            # Password check (Check if password is not hashed or user.hash_password is empty)
            if not user.hash_password:
                # Temporary: If password field is empty, login might be denied or plain text check can be done
                # hash_password is required for security.
                return None

            if not bcrypt.checkpw(password.encode(), user.hash_password.encode()):
                return None
                
            return user.id

    async def change_password(self, id: uuid.UUID | int, password: str) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            # Find user and update
            user = await session.get(self.model_cls, id)
            if user:
                user.hash_password = hash_password
                await session.commit()

    async def orm_save_upload_field(self, obj: tp.Any, field: str, base64: str) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            # Merge object to session or requery
            current_obj = await session.get(self.model_cls, obj.id)
            if current_obj:
                setattr(current_obj, field, base64)
                await session.commit()

@register(Asset, sqlalchemy_sessionmaker=AsyncSessionLocal)
class AssetAdmin(BaseAdmin):
    list_display = ("id", "code", "name", "type")
    search_fields = ("code", "name")
    list_filter = ("type",)
    actions = ("fetch_prices_action", "delete_selected_action")

    @action(description="Tüm Fon Fiyatlarını Güncelle (TEFAS)")
    async def fetch_prices_action(self, objs: list[Asset]) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            await fetch_fund_prices(session)

@register(Portfolio, sqlalchemy_sessionmaker=AsyncSessionLocal)
class PortfolioAdmin(BaseAdmin):
    list_display = ("id", "user", "asset", "quantity", "average_cost")
    list_filter = ("user", "asset")

@register(PriceHistory, sqlalchemy_sessionmaker=AsyncSessionLocal)
class PriceHistoryAdmin(BaseAdmin):
    list_display = ("id", "asset", "date", "price")
    list_filter = ("asset", "date")
