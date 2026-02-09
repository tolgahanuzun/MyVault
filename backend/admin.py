from fastadmin import SqlAlchemyModelAdmin, register, WidgetType
from backend.models import User, Asset, Portfolio, PriceHistory
from backend.database import engine, SessionLocal
from sqlalchemy import select, update
import bcrypt
import typing as tp
import uuid

# SQLAlchemy session maker (Sync)
# SessionLocal is imported from backend.database to avoid duplication

@register(User, sqlalchemy_sessionmaker=SessionLocal)
class UserAdmin(SqlAlchemyModelAdmin):
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

    def authenticate(self, username: str, password: str) -> uuid.UUID | int | None:
        sessionmaker = self.get_sessionmaker()
        # Senkron session kullanımı
        with sessionmaker() as session:
            query = select(self.model_cls).filter_by(username=username, is_active=True, is_superuser=True)
            result = session.scalars(query)
            user = result.first()
            
            if not user:
                return None
            
            # Şifre kontrolü (Eğer şifre hashli değilse veya user.hash_password boşsa kontrol et)
            if not user.hash_password:
                # Geçici: Şifre alanı boşsa girişe izin verilmeyebilir veya düz metin kontrolü yapılabilir
                # Güvenlik için hash_password olması şart.
                return None

            if not bcrypt.checkpw(password.encode(), user.hash_password.encode()):
                return None
                
            return user.id

    def change_password(self, id: uuid.UUID | int, password: str) -> None:
        sessionmaker = self.get_sessionmaker()
        with sessionmaker() as session:
            hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            # Kullanıcıyı bul ve güncelle
            user = session.get(self.model_cls, id)
            if user:
                user.hash_password = hash_password
                session.commit()

    def orm_save_upload_field(self, obj: tp.Any, field: str, base64: str) -> None:
        sessionmaker = self.get_sessionmaker()
        with sessionmaker() as session:
            # Objeyi session'a merge et veya yeniden sorgula
            current_obj = session.get(self.model_cls, obj.id)
            if current_obj:
                setattr(current_obj, field, base64)
                session.commit()


                

@register(Asset, sqlalchemy_sessionmaker=SessionLocal)
class AssetAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "code", "name", "type")
    search_fields = ("code", "name")
    list_filter = ("type",)

@register(Portfolio, sqlalchemy_sessionmaker=SessionLocal)
class PortfolioAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "user", "asset", "quantity", "average_cost")
    list_filter = ("user", "asset")

@register(PriceHistory, sqlalchemy_sessionmaker=SessionLocal)
class PriceHistoryAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "asset", "date", "price")
    list_filter = ("asset", "date")
