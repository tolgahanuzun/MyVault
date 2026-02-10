# MyVault - Borsa & Fon Takip Uygulaması

Hisse ve fon portföylerini takip etmek için basit, hafif bir web uygulaması.

[🇺🇸 English README](README.md)

## Ekran Görüntüleri

| Ana Sayfa (Dashboard) | Yönetim Paneli (Admin) |
|:---:|:---:|
| <img src="img/index.png" alt="Ana Sayfa" width="400"/> | <img src="img/admin.png" alt="Admin Paneli" width="400"/> |

## Teknoloji Altyapısı

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, APScheduler
- **Admin Panel:** FastAdmin
- **Database Migration:** Alembic
- **Frontend:** HTML, CSS (Bootstrap), Vanilla JavaScript
- **Veri Kaynağı:** TEFAS (crawler ile)

## Temel Özellikler

- **Varlık Yönetimi:** Gelişmiş FastAdmin paneli ile fon/hisse yönetimi.
- **Portföy Takibi:** Adet, maliyet ve güncel değer takibi.
- **Otomatik Veri:** Günlük TEFAS veri çekme işlemleri (Background job).
- **Grafikler:** Chart.js ile tarihsel fiyat grafikleri.
- **Çoklu Dil:** İngilizce ve Türkçe desteği (Frontend & Admin).
- **Güvenlik:** Admin paneli için güvenli giriş sistemi.

## Kurulum

1. **Klonla ve Hazırla:**
   ```bash
   git clone https://github.com/tolgahanuzun/MyVault
   cd MyVault
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Veritabanı ve Kullanıcı Oluşturma:**
   ```bash
   # Veritabanı tablolarını oluştur/güncelle
   alembic upgrade head
   
   # Admin kullanıcısı oluştur
   python script.py
   ```
   *Not: Varsayılan veritabanı `local.db` dosyasıdır. Değiştirmek için `.env` dosyasında `DATABASE_URL` tanımlayabilirsiniz.*

3. **Çalıştır:**
   ```bash
   uvicorn backend.main:app --reload
   ```

4. **Erişim:**
   - Uygulama: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Admin: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) (Oluşturduğunuz kullanıcı ile giriş yapın)

## Yapılacaklar Listesi (Todo)

- [x] Admin Paneli Entegrasyonu (FastAdmin)
- [x] Modern UI (Sidebar & Dark Mode)
- [x] Veritabanı Migrasyon Sistemi (Alembic)
- [x] Admin Kullanıcı Yönetimi & Güvenlik
- [ ] Mobil Uygulama (React Native/Flutter)
- [ ] Telegram Bot Bildirimleri
- [ ] Son Kullanıcı Girişi (JWT Auth - Frontend)
- [ ] Yabancı Hisse & Kripto Desteği
- [ ] Veri Dışa Aktarma (CSV/Excel)
