// API Base URL
const API_BASE = "";

// Shared Translations
const TRANSLATIONS = {
    en: {
        app_title: "MyVault",
        portfolio_title: "MyVault Portfolio",
        total_value: "Total Value",
        total_cost: "Total Cost",
        total_profit_loss: "Total Profit/Loss",
        btn_new_asset: "New Asset",
        btn_add_transaction: "New Transaction",
        my_assets: "My Assets",
        col_code: "Code",
        col_name: "Name",
        col_quantity: "Quantity",
        col_avg_cost: "Avg. Cost",
        col_current_price: "Current Price",
        col_total_value: "Total Value",
        col_profit_loss: "Profit/Loss",
        modal_asset_title: "Add New Asset",
        label_code: "Code (e.g. TTE)",
        label_name: "Name (e.g. Technology Fund)",
        label_type: "Type",
        opt_fund: "Fund",
        opt_stock: "Stock",
        btn_save: "Save",
        modal_transaction_title: "Add Transaction",
        label_select_asset: "Select Asset",
        label_quantity: "Quantity",
        label_unit_cost: "Unit Cost",
        btn_add: "Add",
        alert_asset_added: "Asset added successfully!",
        alert_transaction_added: "Transaction added successfully!",
        alert_error: "An error occurred!",
        currency: " TL",
        detail_title: "Asset Detail",
        nav_home: "Home",
        chart_title: "Price History",
        my_position: "My Position",
        loading: "Loading...",
        sidebar_dashboard: "Dashboard",
        sidebar_assets: "Assets",
        sidebar_settings: "Settings"
    },
    tr: {
        app_title: "MyVault",
        portfolio_title: "MyVault Portföy",
        total_value: "Toplam Değer",
        total_cost: "Toplam Maliyet",
        total_profit_loss: "Toplam Kâr/Zarar",
        btn_new_asset: "Yeni Varlık",
        btn_add_transaction: "İşlem Ekle",
        my_assets: "Varlıklarım",
        col_code: "Kod",
        col_name: "Ad",
        col_quantity: "Adet",
        col_avg_cost: "Ort. Maliyet",
        col_current_price: "Güncel Fiyat",
        col_total_value: "Toplam Değer",
        col_profit_loss: "Kâr/Zarar",
        modal_asset_title: "Yeni Varlık Ekle",
        label_code: "Kod (Örn: TTE)",
        label_name: "Ad (Örn: Teknoloji Fonu)",
        label_type: "Tip",
        opt_fund: "Fon",
        opt_stock: "Hisse",
        btn_save: "Kaydet",
        modal_transaction_title: "Alım Ekle",
        label_select_asset: "Varlık Seç",
        label_quantity: "Adet",
        label_unit_cost: "Birim Maliyet",
        btn_add: "Ekle",
        alert_asset_added: "Varlık başarıyla eklendi!",
        alert_transaction_added: "İşlem başarıyla eklendi!",
        alert_error: "Bir hata oluştu!",
        currency: " TL",
        detail_title: "Varlık Detayı",
        nav_home: "Ana Sayfa",
        chart_title: "Fiyat Geçmişi",
        my_position: "Pozisyonum",
        loading: "Yükleniyor...",
        sidebar_dashboard: "Kontrol Paneli",
        sidebar_assets: "Varlıklar",
        sidebar_settings: "Ayarlar"
    }
};

// State
let currentLang = localStorage.getItem('app_lang') || 'en';
let currentTheme = localStorage.getItem('app_theme') || 'light';

// Helper: Format Currency
function formatCurrency(value) {
    const t = TRANSLATIONS[currentLang];
    return `${value.toLocaleString(currentLang === 'tr' ? 'tr-TR' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}${t.currency}`;
}

// Helper: Format Number
function formatNumber(value) {
    return value.toLocaleString(currentLang === 'tr' ? 'tr-TR' : 'en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

// Helper: Update UI Texts
function updatePageTranslations() {
    const t = TRANSLATIONS[currentLang];
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (t[key]) {
            element.textContent = t[key];
        }
    });
}

// Helper: Change Language - Global
window.changeLanguage = function(lang, callback) {
    if (TRANSLATIONS[lang]) {
        currentLang = lang;
        localStorage.setItem('app_lang', lang);
        updatePageTranslations();
        if (callback && typeof callback === 'function') {
            callback();
        }
    }
}

// Helper: Toggle Theme - Global
window.toggleTheme = function() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('app_theme', currentTheme);
    applyTheme();
}

function applyTheme() {
    document.documentElement.setAttribute('data-bs-theme', currentTheme);
    
    // Update Icon
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = currentTheme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    }

    // Update Chart.js if exists
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = currentTheme === 'light' ? '#666' : '#ccc';
        Chart.defaults.borderColor = currentTheme === 'light' ? '#ddd' : '#444';
        
        // Find and update all active charts
        Chart.helpers.each(Chart.instances, function(instance){
            instance.update();
        });
    }
}

// Helper: Toggle Sidebar - Global
window.toggleSidebar = function() {
    document.getElementById('sidebar').classList.toggle('active');
}

// Auto-run on load
document.addEventListener('DOMContentLoaded', () => {
    updatePageTranslations();
    applyTheme();
    
    // Sidebar toggle is safe to keep as event listener
    const sidebarBtn = document.getElementById('sidebarCollapse');
    if (sidebarBtn) sidebarBtn.addEventListener('click', window.toggleSidebar);
});
