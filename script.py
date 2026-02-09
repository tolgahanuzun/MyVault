from backend.database import SessionLocal
from backend.models import User
import bcrypt
import sys
import getpass

# Eğer modül bulunamadı hatası alırsanız, projenin kök dizinini path'e ekler
sys.path.append('.')

def create_superuser(username, password, full_name="Admin User"):
    db = SessionLocal()
    try:
        # Kullanıcı var mı kontrol et
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"UYARI: '{username}' kullanıcı adına sahip bir kullanıcı zaten var.")
            return

        # Şifre hashleme
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Yeni kullanıcı oluştur
        new_user = User(
            username=username,
            full_name=full_name,
            hash_password=hashed_password,
            is_superuser=True,
            is_active=True
        )

        db.add(new_user)
        db.commit()
        print(f"BAŞARILI: Süper kullanıcı '{username}' oluşturuldu.")
        
    except Exception as e:
        print(f"HATA: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("--- Süper Kullanıcı Oluşturma ---")
    try:
        u_name = input("Kullanıcı adı: ").strip()
        # Şifre girilirken ekranda görünmemesi için getpass kullanıyoruz
        pwd = getpass.getpass("Şifre: ").strip()
        
        if u_name and pwd:
            create_superuser(u_name, pwd)
        else:
            print("HATA: Kullanıcı adı ve şifre boş olamaz!")
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")
