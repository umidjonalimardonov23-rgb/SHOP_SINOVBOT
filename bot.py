"""
PRO SHOP BOT — Kengaytirilgan savdo tizimi
===========================================
Imkoniyatlar:
  ✅ Kanal + Bot integratsiyasi
  ✅ Kategoriyalar (Kiyim, Poyabzal, Aksessuarlar...)
  ✅ Ko'p til: O'zbek / Rus / Ingliz
  ✅ To'lov: Click, Payme (havola) + Karta o'tkazmasi
  ✅ Buyurtma holati (yangi → tasdiqlandi → yetkazildi)
  ✅ Admin panel (to'liq boshqaruv menyusi)
  ✅ Mijoz: buyurtmalar tarixi
  ✅ SQLite baza (restart bo'lsa ham saqlanadi)
  ✅ 🔍 Mahsulot qidirish
  ✅ ⭐ Reyting va sharhlar
  ✅ 📦 Yetkazib berish narxi hisoblash
  ✅ 🎁 Promo-kod va chegirmalar
  ✅ 👥 Referal tizim (do'st taklif qilsa bonus)

O'rnatish:
  pip install python-telegram-bot==20.7
"""

import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# ── SOZLAMALAR ───────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "8591487808:AAG3H1BogAXHCgeWYmJUzkt22yAaQsxVgS8")
ADMIN_ID    = 8787603995
CHANNEL_ID  = "@sinov_shop_bot"

CARD_NUMBER = "9860 6067 6080 6673"
CARD_OWNER  = "+998953909477"

CLICK_URL  = "https://my.click.uz/services/pay?service_id=XXXXX&merchant_id=XXXXX"
PAYME_URL  = "https://checkout.paycom.uz/XXXXX"

REFERRAL_BONUS     = 5000  # so'm, do'st taklif qilganda beriladigan bonus
LOW_STOCK_THRESHOLD = 5    # shuncha qolganda adminga ogohlantirish yuboriladi
# ────────────────────────────────────────────────────────────────────────────

DB_PATH = "shop.db"
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ── TILLAR ───────────────────────────────────────────────────────────────────
TEXTS = {
    "uz": {
        "welcome": "👋 Salom, {name}!\n\n🌐 Tilni tanlang:",
        "welcome_back": "👋 Xush kelibsiz, *{name}*! 🎉\n\n👇 Quyidagi menyudan tanlang:",
        "choose_lang": "🌐 Tilni tanlang:",
        "catalog": "📂 Kategoriyalarni tanlang:",
        "no_products": "😔 Bu kategoriyada mahsulot yo'q.",
        "order_name": "👤 Ismingizni kiriting:",
        "order_phone": "📱 Telefon raqamingizni yuboring:",
        "order_address": "🏠 Manzilingizni kiriting:",
        "order_qty": "🔢 Nechta olmoqchisiz?",
        "order_promo": "🎁 Promo-kod bormi? (yo'q bo'lsa /skip yozing):",
        "promo_applied": "✅ Promo-kod qo'llandi! Chegirma: {discount}",
        "promo_invalid": "❌ Noto'g'ri promo-kod. Davom etish uchun /skip yozing.",
        "order_zone": "📦 Yetkazib berish hududini tanlang:",
        "order_pay": "💳 To'lov usulini tanlang:",
        "order_done": "✅ Buyurtma qabul qilindi!\n\n📦 {name}\n💰 {price} so'm × {qty} = {subtotal} so'm\n🎁 Chegirma: -{discount} so'm\n🚚 Yetkazib berish: {delivery} so'm\n💳 Jami: *{total} so'm*\n\nAdmin tez orada bog'lanadi!",
        "my_orders": "📋 Sizning buyurtmalaringiz:",
        "no_orders": "😔 Buyurtmalar yo'q.",
        "pay_card": "💳 Karta orqali to'lash",
        "pay_click": "⚡ Click orqali to'lash",
        "pay_payme": "💚 Payme orqali to'lash",
        "card_info": "💳 Karta raqami: `{card}`\n👤 Egasi: {owner}\n💰 Summa: *{total} so'm*\n\nTo'lovni amalga oshirib, chekni yuboring.",
        "send_receipt": "🧾 Chekni yuboring (surat yoki screenshot):",
        "receipt_sent": "✅ Chek qabul qilindi! Admin tekshiradi.",
        "cancel": "❌ Bekor qilindi.",
        "back": "⬅️ Orqaga",
        "buy": "🛒 Buyurtma berish",
        "status_new": "🆕 Yangi",
        "status_confirmed": "✅ Tasdiqlandi",
        "status_delivered": "🚚 Yetkazildi",
        "status_cancelled": "❌ Bekor",
        "search_ask": "🔍 Qidiruv so'zini kiriting:",
        "search_no": "😔 Hech narsa topilmadi.",
        "search_found": "🔍 Topildi ({count} ta):",
        "rate_ask": "⭐ Buyurtmangizni baholang (1-5):",
        "rate_comment": "💬 Izoh qoldiring (o'tkazib yuborish uchun /skip):",
        "rate_thanks": "✅ Fikringiz uchun rahmat!",
        "referral_info": "👥 Sizning referal havolangiz:\n\n{link}\n\nHar bir do'stingiz uchun {bonus} so'm bonus olasiz!\n\n👤 Taklif qilganlar: {count} kishi\n💰 Jami bonus: {total} so'm",
        "balance_info": "💰 Sizning balans: *{balance} so'm*\n\nBuyurtma berayotganda balansdan foydalanishingiz mumkin.",
        "balance_used": "✅ Balansdan {amount} so'm ishlatildi.",
    },
    "ru": {
        "welcome": "👋 Привет, {name}!\n\nВыберите язык:",
        "welcome_back": "👋 С возвращением, *{name}*! 🎉\n\n👇 Выберите из меню:",
        "choose_lang": "🌐 Выберите язык:",
        "catalog": "📂 Выберите категорию:",
        "no_products": "😔 В этой категории нет товаров.",
        "order_name": "👤 Введите ваше имя:",
        "order_phone": "📱 Отправьте ваш номер телефона:",
        "order_address": "🏠 Введите ваш адрес:",
        "order_qty": "🔢 Сколько штук хотите?",
        "order_promo": "🎁 Есть промокод? (если нет — напишите /skip):",
        "promo_applied": "✅ Промокод применён! Скидка: {discount}",
        "promo_invalid": "❌ Неверный промокод. Напишите /skip для продолжения.",
        "order_zone": "📦 Выберите зону доставки:",
        "order_pay": "💳 Выберите способ оплаты:",
        "order_done": "✅ Заказ принят!\n\n📦 {name}\n💰 {price} сум × {qty} = {subtotal} сум\n🎁 Скидка: -{discount} сум\n🚚 Доставка: {delivery} сум\n💳 Итого: *{total} сум*\n\nАдмин скоро свяжется!",
        "my_orders": "📋 Ваши заказы:",
        "no_orders": "😔 Заказов нет.",
        "pay_card": "💳 Оплата картой",
        "pay_click": "⚡ Оплата Click",
        "pay_payme": "💚 Оплата Payme",
        "card_info": "💳 Номер карты: `{card}`\n👤 Владелец: {owner}\n💰 Сумма: *{total} сум*\n\nПереведите и отправьте чек.",
        "send_receipt": "🧾 Отправьте чек (фото или скриншот):",
        "receipt_sent": "✅ Чек получен! Администратор проверит.",
        "cancel": "❌ Отменено.",
        "back": "⬅️ Назад",
        "buy": "🛒 Заказать",
        "status_new": "🆕 Новый",
        "status_confirmed": "✅ Подтверждён",
        "status_delivered": "🚚 Доставлен",
        "status_cancelled": "❌ Отменён",
        "search_ask": "🔍 Введите поисковый запрос:",
        "search_no": "😔 Ничего не найдено.",
        "search_found": "🔍 Найдено ({count} шт.):",
        "rate_ask": "⭐ Оцените ваш заказ (1-5):",
        "rate_comment": "💬 Оставьте комментарий (/skip — пропустить):",
        "rate_thanks": "✅ Спасибо за отзыв!",
        "referral_info": "👥 Ваша реферальная ссылка:\n\n{link}\n\nЗа каждого друга вы получите {bonus} сум!\n\n👤 Приглашено: {count} чел.\n💰 Всего бонусов: {total} сум",
        "balance_info": "💰 Ваш баланс: *{balance} сум*\n\nМожно использовать при оформлении заказа.",
        "balance_used": "✅ С баланса списано {amount} сум.",
    },
    "en": {
        "welcome": "👋 Hello, {name}!\n\nChoose language:",
        "welcome_back": "👋 Welcome back, *{name}*! 🎉\n\n👇 Choose from the menu:",
        "choose_lang": "🌐 Choose language:",
        "catalog": "📂 Choose a category:",
        "no_products": "😔 No products in this category.",
        "order_name": "👤 Enter your name:",
        "order_phone": "📱 Send your phone number:",
        "order_address": "🏠 Enter your address:",
        "order_qty": "🔢 How many do you want?",
        "order_promo": "🎁 Have a promo code? (type /skip if not):",
        "promo_applied": "✅ Promo code applied! Discount: {discount}",
        "promo_invalid": "❌ Invalid promo code. Type /skip to continue.",
        "order_zone": "📦 Choose delivery zone:",
        "order_pay": "💳 Choose payment method:",
        "order_done": "✅ Order accepted!\n\n📦 {name}\n💰 {price} UZS × {qty} = {subtotal} UZS\n🎁 Discount: -{discount} UZS\n🚚 Delivery: {delivery} UZS\n💳 Total: *{total} UZS*\n\nAdmin will contact you soon!",
        "my_orders": "📋 Your orders:",
        "no_orders": "😔 No orders yet.",
        "pay_card": "💳 Pay by card",
        "pay_click": "⚡ Pay via Click",
        "pay_payme": "💚 Pay via Payme",
        "card_info": "💳 Card number: `{card}`\n👤 Owner: {owner}\n💰 Amount: *{total} UZS*\n\nTransfer and send the receipt.",
        "send_receipt": "🧾 Send receipt (photo or screenshot):",
        "receipt_sent": "✅ Receipt received! Admin will verify.",
        "cancel": "❌ Cancelled.",
        "back": "⬅️ Back",
        "buy": "🛒 Order",
        "status_new": "🆕 New",
        "status_confirmed": "✅ Confirmed",
        "status_delivered": "🚚 Delivered",
        "status_cancelled": "❌ Cancelled",
        "search_ask": "🔍 Enter search query:",
        "search_no": "😔 Nothing found.",
        "search_found": "🔍 Found ({count} items):",
        "rate_ask": "⭐ Rate your order (1-5):",
        "rate_comment": "💬 Leave a comment (/skip to skip):",
        "rate_thanks": "✅ Thank you for your review!",
        "referral_info": "👥 Your referral link:\n\n{link}\n\nEarn {bonus} UZS for each friend!\n\n👤 Referred: {count} people\n💰 Total bonus: {total} UZS",
        "balance_info": "💰 Your balance: *{balance} UZS*\n\nYou can use it when placing an order.",
        "balance_used": "✅ {amount} UZS deducted from balance.",
    }
}

CATEGORIES = {
    "uz": ["👗 Kiyim", "👟 Poyabzal", "💍 Aksessuarlar", "🎒 Sumkalar", "🧴 Kosmetika"],
    "ru": ["👗 Одежда", "👟 Обувь", "💍 Аксессуары", "🎒 Сумки", "🧴 Косметика"],
    "en": ["👗 Clothing", "👟 Footwear", "💍 Accessories", "🎒 Bags", "🧴 Cosmetics"],
}
CAT_KEYS = ["clothing", "footwear", "accessories", "bags", "cosmetics"]

DEFAULT_ZONES = [
    ("Toshkent shahri", "Город Ташкент", "Tashkent city", 10000),
    ("Toshkent viloyati", "Ташкентская область", "Tashkent region", 20000),
    ("Samarqand", "Самарканд", "Samarkand", 30000),
    ("Buxoro", "Бухара", "Bukhara", 30000),
    ("Farg'ona", "Фергана", "Fergana", 25000),
    ("Andijon", "Андижан", "Andijan", 25000),
    ("Namangan", "Наманган", "Namangan", 25000),
    ("Boshqa viloyat", "Другой регион", "Other region", 40000),
]

def t(lang, key, **kwargs):
    text = TEXTS.get(lang, TEXTS["uz"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ── DATABASE ─────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT, photo_id TEXT,
        name_uz TEXT, name_ru TEXT, name_en TEXT,
        price INTEGER, desc_uz TEXT, desc_ru TEXT, desc_en TEXT,
        stock INTEGER DEFAULT 999, active INTEGER DEFAULT 1,
        views INTEGER DEFAULT 0,
        sold_count INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    # Eski DB ga ustun qo'shish (mavjud bo'lsa xato bermaydi)
    try:
        conn.execute("ALTER TABLE products ADD COLUMN views INTEGER DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE products ADD COLUMN sold_count INTEGER DEFAULT 0")
    except:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, lang TEXT,
        product_id INTEGER, product_name TEXT,
        qty INTEGER, price INTEGER, total INTEGER,
        buyer_name TEXT, phone TEXT, address TEXT,
        payment TEXT, status TEXT DEFAULT 'new',
        receipt_file_id TEXT,
        discount INTEGER DEFAULT 0,
        delivery_price INTEGER DEFAULT 0,
        delivery_zone TEXT DEFAULT '',
        promo_code TEXT DEFAULT '',
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'uz',
        username TEXT, full_name TEXT,
        balance INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        discount_type TEXT DEFAULT 'percent',
        discount_value INTEGER DEFAULT 10,
        max_uses INTEGER DEFAULT 100,
        uses_count INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER, user_id INTEGER,
        product_id INTEGER, rating INTEGER,
        comment TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS delivery_zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_uz TEXT, name_ru TEXT, name_en TEXT,
        price INTEGER, active INTEGER DEFAULT 1
    )""")
    # Default yetkazib berish hududlarini qo'shish
    existing = conn.execute("SELECT COUNT(*) FROM delivery_zones").fetchone()[0]
    if existing == 0:
        for z in DEFAULT_ZONES:
            conn.execute(
                "INSERT INTO delivery_zones(name_uz,name_ru,name_en,price) VALUES(?,?,?,?)", z
            )
    conn.commit()
    conn.close()

def db():
    return sqlite3.connect(DB_PATH)

def get_lang(user_id):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return r[0] if r else "uz"

def set_lang(user_id, lang, username="", full_name=""):
    with db() as conn:
        conn.execute("""INSERT INTO users(user_id,lang,username,full_name,created_at)
            VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET lang=?""",
            (user_id, lang, username, full_name, datetime.now().isoformat(), lang))

def get_user(user_id):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def add_balance(user_id, amount):
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))

def use_balance(user_id, amount):
    with db() as conn:
        conn.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id=?", (amount, user_id))

def process_referral(new_user_id, referrer_id):
    with db() as conn:
        already = conn.execute(
            "SELECT referred_by FROM users WHERE user_id=?", (new_user_id,)
        ).fetchone()
        if already and already[0] == 0 and referrer_id != new_user_id:
            conn.execute(
                "UPDATE users SET referred_by=? WHERE user_id=?", (referrer_id, new_user_id)
            )
            conn.execute(
                "UPDATE users SET balance = balance + ?, referral_count = referral_count + 1 WHERE user_id=?",
                (REFERRAL_BONUS, referrer_id)
            )

def get_products(category=None):
    with db() as conn:
        if category:
            return conn.execute(
                "SELECT * FROM products WHERE category=? AND active=1 ORDER BY id DESC", (category,)
            ).fetchall()
        return conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()

def search_products(query):
    q = f"%{query}%"
    with db() as conn:
        return conn.execute(
            """SELECT * FROM products WHERE active=1 AND (
                name_uz LIKE ? OR name_ru LIKE ? OR name_en LIKE ?
                OR desc_uz LIKE ? OR desc_ru LIKE ? OR desc_en LIKE ?
            ) ORDER BY id DESC LIMIT 20""",
            (q, q, q, q, q, q)
        ).fetchall()

def add_product(category, photo_id, name_uz, name_ru, name_en, price, desc_uz, desc_ru, desc_en):
    with db() as conn:
        conn.execute("""INSERT INTO products
            (category,photo_id,name_uz,name_ru,name_en,price,desc_uz,desc_ru,desc_en,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (category, photo_id, name_uz, name_ru, name_en, price, desc_uz, desc_ru, desc_en,
             datetime.now().isoformat()))

def delete_product(pid):
    with db() as conn:
        conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))

def decrease_stock(pid, qty):
    with db() as conn:
        conn.execute(
            "UPDATE products SET stock = MAX(0, stock - ?) WHERE id=?", (qty, pid)
        )
        new_stock = conn.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()[0]
        if new_stock == 0:
            conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    return new_stock

def set_stock(pid, qty):
    with db() as conn:
        conn.execute("UPDATE products SET stock=?, active=? WHERE id=?",
                     (qty, 1 if qty > 0 else 0, pid))

def get_low_stock_products():
    with db() as conn:
        return conn.execute(
            "SELECT id, name_uz, stock FROM products WHERE active=1 AND stock <= ? ORDER BY stock ASC",
            (LOW_STOCK_THRESHOLD,)
        ).fetchall()

def add_order(user_id, username, lang, product_id, product_name, qty, price,
              buyer_name, phone, address, payment,
              discount=0, delivery_price=0, delivery_zone="", promo_code=""):
    subtotal = qty * price
    total = max(0, subtotal - discount) + delivery_price
    with db() as conn:
        cur = conn.execute("""INSERT INTO orders
            (user_id,username,lang,product_id,product_name,qty,price,total,
             buyer_name,phone,address,payment,status,
             discount,delivery_price,delivery_zone,promo_code,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'new',?,?,?,?,?)""",
            (user_id, username, lang, product_id, product_name, qty, price, total,
             buyer_name, phone, address, payment,
             discount, delivery_price, delivery_zone, promo_code,
             datetime.now().isoformat()))
        return cur.lastrowid

def get_orders(user_id=None):
    with db() as conn:
        if user_id:
            return conn.execute(
                "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)
            ).fetchall()
        return conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()

def update_order_status(order_id, status):
    with db() as conn:
        conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))

def update_receipt(order_id, file_id):
    with db() as conn:
        conn.execute("UPDATE orders SET receipt_file_id=? WHERE id=?", (file_id, order_id))

def get_stats():
    with db() as conn:
        total_orders   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        total_revenue  = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelled'").fetchone()[0]
        new_orders     = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
        total_users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_products = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        avg_rating     = conn.execute("SELECT COALESCE(AVG(rating),0) FROM reviews").fetchone()[0]
    return total_orders, total_revenue, new_orders, total_users, total_products, avg_rating

def increment_views(pid):
    with db() as conn:
        conn.execute("UPDATE products SET views = views + 1 WHERE id=?", (pid,))

def increment_sold(pid, qty):
    with db() as conn:
        conn.execute("UPDATE products SET sold_count = sold_count + ? WHERE id=?", (qty, pid))

def get_top_products(limit=10):
    with db() as conn:
        return conn.execute(
            "SELECT id, name_uz, sold_count, views, price FROM products ORDER BY sold_count DESC LIMIT ?",
            (limit,)
        ).fetchall()

def get_stuck_orders(hours=2):
    threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
    with db() as conn:
        return conn.execute(
            "SELECT id, product_name, buyer_name, phone, created_at FROM orders "
            "WHERE status='new' AND created_at < ? ORDER BY id ASC",
            (threshold,)
        ).fetchall()

def get_today_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    with db() as conn:
        orders_today  = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        revenue_today = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ? AND status!='cancelled'",
            (f"{today}%",)
        ).fetchone()[0]
        new_users     = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today}%",)
        ).fetchone()[0]
    return orders_today, revenue_today, new_users

def check_promo(code):
    with db() as conn:
        p = conn.execute(
            "SELECT * FROM promo_codes WHERE code=? AND active=1 AND uses_count < max_uses",
            (code.upper(),)
        ).fetchone()
    return p

def use_promo(code):
    with db() as conn:
        conn.execute("UPDATE promo_codes SET uses_count=uses_count+1 WHERE code=?", (code.upper(),))

def add_promo_code(code, discount_type, discount_value, max_uses):
    with db() as conn:
        try:
            conn.execute(
                "INSERT INTO promo_codes(code,discount_type,discount_value,max_uses,created_at) VALUES(?,?,?,?,?)",
                (code.upper(), discount_type, discount_value, max_uses, datetime.now().isoformat())
            )
            return True
        except:
            return False

def get_promo_codes():
    with db() as conn:
        return conn.execute("SELECT * FROM promo_codes ORDER BY id DESC").fetchall()

def add_review(order_id, user_id, product_id, rating, comment):
    with db() as conn:
        conn.execute(
            "INSERT INTO reviews(order_id,user_id,product_id,rating,comment,created_at) VALUES(?,?,?,?,?,?)",
            (order_id, user_id, product_id, rating, comment, datetime.now().isoformat())
        )

def get_product_reviews(product_id):
    with db() as conn:
        return conn.execute(
            "SELECT rating, comment FROM reviews WHERE product_id=? ORDER BY id DESC LIMIT 5",
            (product_id,)
        ).fetchall()

def get_avg_rating(product_id):
    with db() as conn:
        r = conn.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id=?", (product_id,)
        ).fetchone()
    return r[0] or 0, r[1] or 0

def get_zones(lang):
    col = {"uz": 1, "ru": 2, "en": 3}[lang]
    with db() as conn:
        zones = conn.execute("SELECT id, name_uz, name_ru, name_en, price FROM delivery_zones WHERE active=1").fetchall()
    return [(z[0], z[col], z[4]) for z in zones]

def get_zone_price(zone_id):
    with db() as conn:
        r = conn.execute("SELECT price FROM delivery_zones WHERE id=?", (zone_id,)).fetchone()
    return r[0] if r else 0

def get_zone_name(zone_id, lang):
    col = {"uz": 1, "ru": 2, "en": 3}[lang]
    with db() as conn:
        r = conn.execute("SELECT name_uz, name_ru, name_en FROM delivery_zones WHERE id=?", (zone_id,)).fetchone()
    return r[col - 1] if r else ""

# ── HOLAT KONSTANTALARI ───────────────────────────────────────────────────────
AP_CAT, AP_PHOTO, AP_NAME_UZ, AP_NAME_RU, AP_NAME_EN = range(5)
AP_PRICE, AP_DESC_UZ, AP_DESC_RU, AP_DESC_EN         = range(5, 9)

O_NAME, O_PHONE, O_ADDRESS, O_QTY, O_PROMO, O_ZONE, O_PAY, O_RECEIPT = range(20, 28)

S_QUERY = 30

R_RATING, R_COMMENT = range(40, 42)

ADM_PROMO_CODE, ADM_PROMO_TYPE, ADM_PROMO_VAL, ADM_PROMO_MAX = range(50, 54)
ADM_BROADCAST = 60
ADM_DEL_PROD   = 61
ADM_ZONE_NAME_UZ, ADM_ZONE_NAME_RU, ADM_ZONE_NAME_EN, ADM_ZONE_PRICE = range(62, 66)
ADM_STOCK_PID, ADM_STOCK_QTY = range(67, 69)
ADM_NOTE = 70

# ══════════════════════════════════════════════════════════════════════════════
#  TIL TANLASH
# ══════════════════════════════════════════════════════════════════════════════

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def main_menu_kb(user_id: int, lang: str) -> InlineKeyboardMarkup:
    menu = {
        "uz": [
            ("🛍 Katalog",        "menu_catalog"),
            ("🔍 Qidirish",       "menu_search"),
            ("📦 Buyurtmalarim",  "menu_orders"),
            ("💰 Balansim",       "menu_balance"),
            ("👥 Referal",        "menu_referral"),
            ("🌐 Til o'zgartirish","menu_lang"),
        ],
        "ru": [
            ("🛍 Каталог",        "menu_catalog"),
            ("🔍 Поиск",          "menu_search"),
            ("📦 Мои заказы",     "menu_orders"),
            ("💰 Мой баланс",     "menu_balance"),
            ("👥 Реферал",        "menu_referral"),
            ("🌐 Сменить язык",   "menu_lang"),
        ],
        "en": [
            ("🛍 Catalog",        "menu_catalog"),
            ("🔍 Search",         "menu_search"),
            ("📦 My Orders",      "menu_orders"),
            ("💰 My Balance",     "menu_balance"),
            ("👥 Referral",       "menu_referral"),
            ("🌐 Change Language","menu_lang"),
        ],
    }
    items = menu.get(lang, menu["uz"])
    # 2 ta ustun
    rows = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][0], callback_data=items[i][1])]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(items[i+1][0], callback_data=items[i+1][1]))
        rows.append(row)
    if user_id == ADMIN_ID:
        rows.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin")])
    return InlineKeyboardMarkup(rows)

async def show_main_menu(update, ctx, lang: str, via_query: bool = False):
    user = update.effective_user
    text = t(lang, "welcome_back", name=user.first_name)
    kb   = main_menu_kb(user.id, lang)
    if via_query and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args

    existing = get_user(user.id)

    # Referral link: /start ref_12345
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("_")[1])
            if existing:
                process_referral(user.id, referrer_id)
        except:
            pass

    # Deeplink product: /start product_5
    if args and args[0].startswith("product_"):
        try:
            pid = int(args[0].split("_")[1])
        except:
            pid = None
        if pid:
            ctx.user_data["deeplink_pid"] = pid
            lang = get_lang(user.id)
            await show_product(update, ctx, pid, lang)
            return

    if existing:
        lang = get_lang(user.id)
        await show_main_menu(update, ctx, lang)
        return

    set_lang(user.id, "uz", user.username or "", user.full_name or "")
    await update.message.reply_text(
        t("uz", "welcome", name=user.first_name),
        reply_markup=lang_keyboard()
    )

async def set_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user = query.from_user
    set_lang(user.id, lang, user.username or "", user.full_name or "")

    pid = ctx.user_data.get("deeplink_pid")
    if pid:
        ctx.user_data.pop("deeplink_pid", None)
        await show_product(update, ctx, pid, lang, via_query=True)
        return

    await show_main_menu(update, ctx, lang, via_query=True)

async def change_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(t(lang, "choose_lang"), reply_markup=lang_keyboard())

# ══════════════════════════════════════════════════════════════════════════════
#  KATALOG
# ══════════════════════════════════════════════════════════════════════════════

async def catalog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    cats = CATEGORIES[lang]
    buttons = [[InlineKeyboardButton(name, callback_data=f"cat_{key}")]
               for name, key in zip(cats, CAT_KEYS)]
    buttons.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu_home")])
    kb = InlineKeyboardMarkup(buttons)
    if update.message:
        await update.message.reply_text(t(lang, "catalog"), reply_markup=kb)
    else:
        await update.callback_query.edit_message_text(t(lang, "catalog"), reply_markup=kb)

async def show_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_lang(query.from_user.id)
    cat_key = query.data.split("_", 1)[1]
    products = get_products(cat_key)

    if not products:
        await query.edit_message_text(
            t(lang, "no_products"),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, "back"), callback_data="back_catalog")
            ]])
        )
        return

    name_col = {"uz": 3, "ru": 4, "en": 5}[lang]
    buttons = []
    for p in products:
        avg, cnt = get_avg_rating(p[0])
        stars = f" ⭐{avg:.1f}({cnt})" if cnt > 0 else ""
        buttons.append([InlineKeyboardButton(
            f"{p[name_col]} — {p[6]:,} so'm{stars}", callback_data=f"prod_{p[0]}"
        )])
    buttons.append([InlineKeyboardButton(t(lang, "back"), callback_data="back_catalog")])
    await query.edit_message_text(
        f"📦 {len(products)} ta mahsulot:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_product_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = int(query.data.split("_")[1])
    lang = get_lang(query.from_user.id)
    increment_views(pid)
    await show_product(update, ctx, pid, lang, via_query=True)

async def show_product(update, ctx, pid, lang, via_query=False):
    with db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not p:
        txt = "❌ Mahsulot topilmadi."
        if via_query:
            await update.callback_query.message.reply_text(txt)
        else:
            await update.message.reply_text(txt)
        return

    name_col = {"uz": 3, "ru": 4, "en": 5}[lang]
    desc_col = {"uz": 7, "ru": 8, "en": 9}[lang]
    avg, cnt = get_avg_rating(pid)
    stars_str = f"\n⭐ Reyting: {avg:.1f}/5 ({cnt} ta sharh)" if cnt > 0 else ""
    views_val = p[12] if len(p) > 12 else 0
    sold_val  = p[13] if len(p) > 13 else 0
    views_str = f"\n👁 Ko'rishlar: {views_val:,} | 🛒 Sotilgan: {sold_val:,} dona"

    # Oxirgi sharhlar
    reviews = get_product_reviews(pid)
    reviews_str = ""
    if reviews:
        reviews_str = "\n\n💬 *Sharhlar:*\n"
        for r in reviews[:3]:
            star = "⭐" * r[0]
            comment = f" — {r[1]}" if r[1] else ""
            reviews_str += f"{star}{comment}\n"

    stock = p[11]
    if stock == 0:
        stock_str = "❌ *Tugagan*"
    elif stock <= LOW_STOCK_THRESHOLD:
        stock_str = f"⚠️ Qoldiq: *{stock} dona* (kam qoldi!)"
    else:
        stock_str = f"📦 Qoldiq: *{stock} dona*"

    caption = (
        f"📦 *{p[name_col]}*\n"
        f"💰 Narxi: *{p[6]:,} so'm*\n"
        f"{stock_str}"
        f"{stars_str}"
        f"{views_str}\n\n"
        f"📝 {p[desc_col]}"
        f"{reviews_str}"
    )
    if stock > 0:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, "buy"), callback_data=f"order_{pid}")
        ]])
    else:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Mahsulot tugagan", callback_data="noop")
        ]])
    chat_id = update.callback_query.message.chat_id if via_query else update.message.chat_id
    await ctx.bot.send_photo(chat_id=chat_id, photo=p[2], caption=caption,
                             parse_mode="Markdown", reply_markup=kb)

async def back_catalog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await catalog(update, ctx)

# ══════════════════════════════════════════════════════════════════════════════
#  🔍 QIDIRISH
# ══════════════════════════════════════════════════════════════════════════════

async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(
        t(lang, "search_ask"),
        reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
    )
    return S_QUERY

async def search_start_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Menyu tugmasidan qidiruv boshlash."""
    lang = get_lang(update.effective_user.id)
    if update.callback_query:
        await update.callback_query.message.reply_text(
            t(lang, "search_ask"),
            reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
        )
    return S_QUERY

async def search_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    query = update.message.text.strip()
    products = search_products(query)

    if not products:
        await update.message.reply_text(
            t(lang, "search_no"),
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    name_col = {"uz": 3, "ru": 4, "en": 5}[lang]
    buttons = [[InlineKeyboardButton(
        f"{p[name_col]} — {p[6]:,} so'm", callback_data=f"prod_{p[0]}"
    )] for p in products]
    await update.message.reply_text(
        t(lang, "search_found", count=len(products)),
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════════════════════════
#  BUYURTMA
# ══════════════════════════════════════════════════════════════════════════════

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = int(query.data.split("_")[1])
    lang = get_lang(query.from_user.id)

    with db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not p:
        await query.message.reply_text("❌")
        return ConversationHandler.END

    if p[11] == 0:
        await query.message.reply_text("❌ Kechirasiz, bu mahsulot tugagan!")
        return ConversationHandler.END

    name_col = {"uz": 3, "ru": 4, "en": 5}[lang]
    ctx.user_data.update({
        "o_pid": pid, "o_pname": p[name_col],
        "o_price": p[6], "o_lang": lang,
        "o_stock": p[11],
        "o_discount": 0, "o_delivery": 0,
        "o_zone": "", "o_promo": ""
    })

    await query.message.reply_text(
        t(lang, "order_name"),
        reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
    )
    return O_NAME

async def o_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["o_buyer"] = update.message.text.strip()
    lang = ctx.user_data["o_lang"]
    btn = KeyboardButton(
        "📱 " + ("Raqamni yuborish" if lang=="uz" else "Отправить номер" if lang=="ru" else "Send number"),
        request_contact=True
    )
    await update.message.reply_text(
        t(lang, "order_phone"),
        reply_markup=ReplyKeyboardMarkup([[btn], ["/bekor"]], resize_keyboard=True)
    )
    return O_PHONE

async def o_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["o_phone"] = (
        update.message.contact.phone_number
        if update.message.contact else update.message.text.strip()
    )
    lang = ctx.user_data["o_lang"]
    await update.message.reply_text(
        t(lang, "order_address"),
        reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
    )
    return O_ADDRESS

async def o_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["o_addr"] = update.message.text.strip()
    lang = ctx.user_data["o_lang"]
    await update.message.reply_text(
        t(lang, "order_qty"),
        reply_markup=ReplyKeyboardMarkup([["1","2","3"],["5","10"],["/bekor"]], resize_keyboard=True)
    )
    return O_QTY

async def o_qty(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 1:
        await update.message.reply_text("❌ Raqam kiriting (1 dan ko'p):")
        return O_QTY
    ctx.user_data["o_qty"] = int(txt)
    lang = ctx.user_data["o_lang"]
    await update.message.reply_text(
        t(lang, "order_promo"),
        reply_markup=ReplyKeyboardMarkup([["/skip"], ["/bekor"]], resize_keyboard=True)
    )
    return O_PROMO

async def o_promo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["o_lang"]
    txt = update.message.text.strip()

    if txt.lower() == "/skip":
        return await o_ask_zone(update, ctx)

    promo = check_promo(txt)
    if not promo:
        await update.message.reply_text(t(lang, "promo_invalid"))
        return O_PROMO

    price = ctx.user_data["o_price"]
    qty   = ctx.user_data["o_qty"]
    subtotal = price * qty

    if promo[2] == "percent":
        discount = int(subtotal * promo[3] / 100)
        discount_str = f"{promo[3]}%"
    else:
        discount = min(promo[3], subtotal)
        discount_str = f"{promo[3]:,} so'm"

    ctx.user_data["o_discount"] = discount
    ctx.user_data["o_promo"]    = txt.upper()
    use_promo(txt)
    await update.message.reply_text(t(lang, "promo_applied", discount=discount_str))
    return await o_ask_zone(update, ctx)

async def o_ask_zone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["o_lang"]
    zones = get_zones(lang)
    buttons = [[InlineKeyboardButton(f"{name} — {price:,} so'm", callback_data=f"zone_{zid}")]
               for zid, name, price in zones]
    await update.message.reply_text(
        t(lang, "order_zone"),
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("👇", reply_markup=InlineKeyboardMarkup(buttons))
    return O_ZONE

async def o_zone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = ctx.user_data["o_lang"]
    zone_id = int(query.data.split("_")[1])
    zone_price = get_zone_price(zone_id)
    zone_name  = get_zone_name(zone_id, lang)

    ctx.user_data["o_delivery"] = zone_price
    ctx.user_data["o_zone"]     = zone_name

    subtotal  = ctx.user_data["o_qty"] * ctx.user_data["o_price"]
    discount  = ctx.user_data["o_discount"]
    total     = max(0, subtotal - discount) + zone_price

    # Balans qo'llash
    user = get_user(query.from_user.id)
    balance = user[4] if user else 0
    balance_btn = []
    if balance > 0:
        use_amt = min(balance, total)
        balance_btn = [[InlineKeyboardButton(
            f"💰 Balansdan {use_amt:,} so'm ishlatish", callback_data=f"usebalance_{use_amt}"
        )]]
        ctx.user_data["o_balance_available"] = use_amt

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "pay_card"), callback_data="pay_card")],
        [InlineKeyboardButton(t(lang, "pay_click"), url=f"{CLICK_URL}&amount={total}")],
        [InlineKeyboardButton(t(lang, "pay_payme"), url=f"{PAYME_URL}")],
    ] + balance_btn)

    await query.message.reply_text(
        f"💰 Hisob:\n"
        f"  Mahsulot: {subtotal:,} so'm\n"
        f"  Chegirma: -{discount:,} so'm\n"
        f"  Yetkazib berish ({zone_name}): {zone_price:,} so'm\n"
        f"  ──────────────\n"
        f"  Jami: *{total:,} so'm*",
        parse_mode="Markdown",
        reply_markup=kb
    )
    ctx.user_data["o_total_calc"] = total
    return O_PAY

async def o_use_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    amount = int(query.data.split("_")[1])
    lang   = ctx.user_data["o_lang"]
    ctx.user_data["o_balance_use"] = amount
    ctx.user_data["o_payment"]     = "balance+card"
    await query.message.reply_text(
        t(lang, "balance_used", amount=f"{amount:,}") + f"\n\n" + t(lang, "card_info",
            card=CARD_NUMBER, owner=CARD_OWNER,
            total=f"{max(0, ctx.user_data['o_total_calc'] - amount):,}"),
        parse_mode="Markdown"
    )
    await query.message.reply_text(t(lang, "send_receipt"))
    return O_RECEIPT

async def o_pay_card(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["o_payment"] = "card"
    lang  = ctx.user_data["o_lang"]
    total = ctx.user_data.get("o_total_calc", ctx.user_data["o_qty"] * ctx.user_data["o_price"])
    await query.message.reply_text(
        t(lang, "card_info", card=CARD_NUMBER, owner=CARD_OWNER, total=f"{total:,}"),
        parse_mode="Markdown"
    )
    await query.message.reply_text(t(lang, "send_receipt"))
    return O_RECEIPT

async def o_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Surat yuboring (screenshot yoki foto):")
        return O_RECEIPT
    ctx.user_data["o_receipt"] = update.message.photo[-1].file_id
    return await save_order(update, ctx)

async def o_pay_online(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("To'lov sahifasiga o'ting")
    ctx.user_data["o_payment"] = "online"
    return await save_order_online(update, ctx)

async def save_order_online(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["o_receipt"] = None
    return await save_order(update, ctx)

async def save_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = ctx.user_data
    usr = update.effective_user
    lang = d["o_lang"]

    # Balansdan yechish
    bal_use = d.get("o_balance_use", 0)
    if bal_use > 0:
        use_balance(usr.id, bal_use)

    subtotal = d["o_qty"] * d["o_price"]
    discount = d.get("o_discount", 0) + bal_use
    delivery = d.get("o_delivery", 0)
    total    = max(0, subtotal - d.get("o_discount", 0)) + delivery - bal_use
    total    = max(0, total)

    order_id = add_order(
        usr.id, usr.username or "", lang,
        d["o_pid"], d["o_pname"],
        d["o_qty"], d["o_price"],
        d["o_buyer"], d["o_phone"], d["o_addr"],
        d.get("o_payment", "online"),
        discount=d.get("o_discount", 0),
        delivery_price=delivery,
        delivery_zone=d.get("o_zone", ""),
        promo_code=d.get("o_promo", "")
    )

    if d.get("o_receipt"):
        update_receipt(order_id, d["o_receipt"])

    # Zahirani kamaytirish va sotilganlar sonini oshirish
    new_stock = decrease_stock(d["o_pid"], d["o_qty"])
    increment_sold(d["o_pid"], d["o_qty"])
    stock_alert = ""
    if new_stock == 0:
        stock_alert = f"\n\n🔴 *DIQQAT!* «{d['o_pname']}» mahsuloti *tugadi* va avtomatik yopildi!"
    elif new_stock <= LOW_STOCK_THRESHOLD:
        stock_alert = f"\n\n⚠️ *OGOHLANTIRISH!* «{d['o_pname']}» — qoldiq: *{new_stock} dona*"

    admin_text = (
        f"🔔 *Yangi buyurtma #{order_id}!*\n\n"
        f"📦 {d['o_pname']}\n"
        f"🔢 {d['o_qty']} dona × {d['o_price']:,} = *{subtotal:,} so'm*\n"
        f"🎁 Chegirma: -{d.get('o_discount',0):,} so'm\n"
        f"🚚 Yetkazib berish ({d.get('o_zone','')}): {delivery:,} so'm\n"
        f"💰 Balansdan: -{bal_use:,} so'm\n"
        f"💳 Jami: *{d['o_total_calc']:,} so'm*\n"
        f"💳 To'lov: {d.get('o_payment','online').upper()}\n"
        f"🎁 Promo: {d.get('o_promo','—')}\n\n"
        f"👤 {d['o_buyer']}\n"
        f"📱 {d['o_phone']}\n"
        f"🏠 {d['o_addr']}\n\n"
        f"🆔 @{usr.username or '—'} (ID: {usr.id})"
        f"{stock_alert}"
    )
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Mijoz bilan bog'lanish", url=f"tg://user?id={usr.id}")],
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ostatus_{order_id}_confirmed"),
            InlineKeyboardButton("❌ Bekor", callback_data=f"ostatus_{order_id}_cancelled"),
        ],
        [InlineKeyboardButton("🚚 Yetkazildi", callback_data=f"ostatus_{order_id}_delivered")],
    ])
    await ctx.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=admin_kb)
    if d.get("o_receipt"):
        await ctx.bot.send_photo(ADMIN_ID, d["o_receipt"], caption=f"🧾 #{order_id} buyurtma cheki")

    await update.message.reply_text(
        t(lang, "order_done",
          name=d["o_pname"],
          price=f"{d['o_price']:,}",
          qty=d["o_qty"],
          subtotal=f"{subtotal:,}",
          discount=f"{d.get('o_discount',0)+bal_use:,}",
          delivery=f"{delivery:,}",
          total=f"{d.get('o_total_calc', total):,}"),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — BUYURTMA HOLATI + SHARH SO'RASH
# ══════════════════════════════════════════════════════════════════════════════

STATUS_EMOJI = {
    "confirmed": "✅ Tasdiqlandi",
    "delivered": "🚚 Yetkazildi",
    "cancelled": "❌ Bekor qilindi"
}

async def order_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin buyurtma holatini o'zgartiradi — avval izoh so'raladi."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    _, order_id, status = query.data.split("_", 2)
    ctx.user_data["note_order_id"] = int(order_id)
    ctx.user_data["note_status"]   = status

    label = STATUS_EMOJI.get(status, status)
    await query.message.reply_text(
        f"📝 *{label}* — buyurtma #{order_id}\n\n"
        f"Mijozga qo'shimcha izoh yuboring yoki /skip bosing:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/skip"]], resize_keyboard=True, one_time_keyboard=True)
    )
    return ADM_NOTE

async def order_status_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin yozgan izohni qabul qilib, statusni yangilaydi va mijozga xabar yuboradi."""
    text = update.message.text.strip()
    note = "" if text.lower() in ("/skip", "skip") else text

    order_id = ctx.user_data.pop("note_order_id", None)
    status   = ctx.user_data.pop("note_status", None)
    if not order_id or not status:
        await update.message.reply_text("❌ Xatolik. Qaytadan urinib ko'ring.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    update_order_status(order_id, status)
    label = STATUS_EMOJI.get(status, status)

    await update.message.reply_text(
        f"✅ #{order_id} buyurtma holati: *{label}*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    with db() as conn:
        order = conn.execute(
            "SELECT user_id, lang, product_name, product_id FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()

    if order:
        user_lang  = order[1]
        status_key = f"status_{status}"
        note_line  = f"\n\n💬 *Admin izohi:* {note}" if note else ""
        msg = f"📦 *{order[2]}*\n\n{t(user_lang, status_key)}{note_line}"
        try:
            await ctx.bot.send_message(order[0], msg, parse_mode="Markdown")
        except:
            pass

        if status == "delivered":
            rate_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{'⭐'*i} {i}", callback_data=f"rate_{order_id}_{order[3]}_{i}")
                for i in range(1, 6)
            ]])
            try:
                await ctx.bot.send_message(
                    order[0],
                    t(user_lang, "rate_ask"),
                    reply_markup=rate_kb
                )
            except:
                pass

    return ConversationHandler.END

async def rate_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    order_id, product_id, rating = int(parts[1]), int(parts[2]), int(parts[3])
    lang = get_lang(query.from_user.id)

    ctx.user_data["r_order_id"]   = order_id
    ctx.user_data["r_product_id"] = product_id
    ctx.user_data["r_rating"]     = rating

    await query.edit_message_text(f"{'⭐'*rating} — {rating}/5")
    await query.message.reply_text(
        t(lang, "rate_comment"),
        reply_markup=ReplyKeyboardMarkup([["/skip"]], resize_keyboard=True)
    )
    return R_COMMENT

async def rate_comment_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang    = get_lang(update.effective_user.id)
    comment = "" if update.message.text.strip() == "/skip" else update.message.text.strip()
    add_review(
        ctx.user_data["r_order_id"],
        update.effective_user.id,
        ctx.user_data["r_product_id"],
        ctx.user_data["r_rating"],
        comment
    )
    await update.message.reply_text(
        t(lang, "rate_thanks"),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════════════════════════
#  REFERRAL
# ══════════════════════════════════════════════════════════════════════════════

async def _send_or_edit(update, text, kb, parse_mode="Markdown"):
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=parse_mode)
        except:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=parse_mode)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=parse_mode)

async def referral(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang    = get_lang(user_id)
    bot_info = await ctx.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    user = get_user(user_id)
    ref_count   = user[5] if user else 0
    total_bonus = ref_count * REFERRAL_BONUS
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu_home")]])
    await _send_or_edit(update,
        t(lang, "referral_info",
          link=link, bonus=f"{REFERRAL_BONUS:,}",
          count=ref_count, total=f"{total_bonus:,}"),
        kb
    )

async def balance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang    = get_lang(user_id)
    user    = get_user(user_id)
    balance = user[4] if user else 0
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu_home")]])
    await _send_or_edit(update,
        t(lang, "balance_info", balance=f"{balance:,}"),
        kb
    )

# ══════════════════════════════════════════════════════════════════════════════
#  👤 MIJOZ BUYURTMALARI
# ══════════════════════════════════════════════════════════════════════════════

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang    = get_lang(user_id)
    orders  = get_orders(user_id)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu_home")]])
    if not orders:
        await _send_or_edit(update, t(lang, "no_orders"), kb)
        return
    STATUS_EMOJI = {
        "new":       t(lang, "status_new"),
        "confirmed": t(lang, "status_confirmed"),
        "delivered": t(lang, "status_delivered"),
        "cancelled": t(lang, "status_cancelled"),
    }
    lines = [
        f"🔹 *#{o[0]}* | {o[5]} | {o[8]:,} so'm | {STATUS_EMOJI.get(o[13],'?')}"
        for o in orders
    ]
    await _send_or_edit(update,
        t(lang, "my_orders") + "\n\n" + "\n".join(lines),
        kb
    )

# ══════════════════════════════════════════════════════════════════════════════
#  🛠 ADMIN MENYUSI (to'liq boshqaruv)
# ══════════════════════════════════════════════════════════════════════════════

def admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mahsulot qo'shish",    callback_data="adm_addprod"),
         InlineKeyboardButton("🗑 Mahsulot o'chirish",   callback_data="adm_delprod")],
        [InlineKeyboardButton("🔢 Zahira yangilash",     callback_data="adm_stock"),
         InlineKeyboardButton("⚠️ Kam qolganlar",        callback_data="adm_lowstock")],
        [InlineKeyboardButton("🏆 Top sotilganlar",      callback_data="adm_topsales"),
         InlineKeyboardButton("📊 Statistika",           callback_data="adm_stats")],
        [InlineKeyboardButton("📋 Buyurtmalar",          callback_data="adm_orders"),
         InlineKeyboardButton("📢 Broadcast",            callback_data="adm_broadcast")],
        [InlineKeyboardButton("🎁 Promo qo'shish",       callback_data="adm_addpromo"),
         InlineKeyboardButton("🎫 Promo ro'yxat",        callback_data="adm_promos")],
        [InlineKeyboardButton("📦 Hudud qo'shish",       callback_data="adm_addzone"),
         InlineKeyboardButton("⭐ Sharhlar",             callback_data="adm_reviews")],
        [InlineKeyboardButton("🏠 Bosh menyu",           callback_data="menu_home")],
    ])

async def admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    text = "🛠 *Admin Panel* — barcha boshqaruvlar:"
    kb   = admin_main_kb()
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        query = update.callback_query
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        except:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ══════════════════════════════════════════════════════════════════════════════
#  🏠 ASOSIY MENYU CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data        # menu_catalog / menu_search / menu_orders / ...
    lang   = get_lang(query.from_user.id)

    if action in ("menu_home", "menu_back"):
        await show_main_menu(update, ctx, lang, via_query=True)

    elif action == "menu_catalog":
        await catalog(update, ctx)

    elif action == "menu_orders":
        await my_orders(update, ctx)

    elif action == "menu_balance":
        await balance_cmd(update, ctx)

    elif action == "menu_referral":
        await referral(update, ctx)

    elif action == "menu_lang":
        try:
            await query.edit_message_text(
                t(lang, "choose_lang"), reply_markup=lang_keyboard()
            )
        except:
            await query.message.reply_text(
                t(lang, "choose_lang"), reply_markup=lang_keyboard()
            )

    elif action == "menu_admin":
        if query.from_user.id == ADMIN_ID:
            await admin_menu(update, ctx)
        else:
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)

async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    action = query.data

    if action == "adm_stats":
        tot_o, tot_r, new_o, tot_u, tot_p, avg_r = get_stats()
        await query.message.reply_text(
            f"📊 *Statistika*\n\n"
            f"👥 Foydalanuvchilar: {tot_u}\n"
            f"📦 Mahsulotlar: {tot_p}\n"
            f"🛒 Jami buyurtmalar: {tot_o}\n"
            f"🆕 Yangi buyurtmalar: {new_o}\n"
            f"💰 Jami daromad: {tot_r:,} so'm\n"
            f"⭐ O'rtacha reyting: {avg_r:.1f}/5",
            parse_mode="Markdown"
        )

    elif action == "adm_orders":
        orders = get_orders()
        if not orders:
            await query.message.reply_text("😔 Buyurtmalar yo'q.")
            return
        STATUS_EMOJI = {"new":"🆕","confirmed":"✅","delivered":"🚚","cancelled":"❌"}
        lines = [
            f"{STATUS_EMOJI.get(o[13],'?')} #{o[0]} | {o[5]} | {o[8]:,} so'm | {o[12]}"
            for o in orders
        ]
        await query.message.reply_text(
            "📋 *So'nggi buyurtmalar:*\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )

    elif action == "adm_addprod":
        cats = CATEGORIES["uz"]
        buttons = [[InlineKeyboardButton(name, callback_data=f"acat_{key}")]
                   for name, key in zip(cats, CAT_KEYS)]
        await query.message.reply_text("📂 Kategoriyani tanlang:",
                                       reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "adm_delprod":
        products = get_products()
        if not products:
            await query.message.reply_text("😔 Mahsulotlar yo'q.")
            return
        buttons = [[InlineKeyboardButton(f"🗑 {p[3]} (#{p[0]})", callback_data=f"delp_{p[0]}")]
                   for p in products]
        await query.message.reply_text("Qaysi mahsulotni o'chirish?",
                                       reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "adm_stock":
        products = get_products()
        if not products:
            await query.message.reply_text("😔 Mahsulotlar yo'q.")
            return
        buttons = [[InlineKeyboardButton(
            f"📦 {p[3]} — {p[11]} dona", callback_data=f"setstock_{p[0]}"
        )] for p in products]
        await query.message.reply_text(
            "🔢 Qaysi mahsulot zahirasini yangilash?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif action == "adm_lowstock":
        items = get_low_stock_products()
        if not items:
            await query.message.reply_text("✅ Hamma mahsulot zahirasi yetarli!")
            return
        lines = [f"⚠️ #{p[0]} *{p[1]}* — {p[2]} dona" for p in items]
        await query.message.reply_text(
            "⚠️ *Kam qolgan mahsulotlar:*\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )

    elif action == "adm_topsales":
        tops = get_top_products(10)
        if not tops:
            await query.message.reply_text("😔 Hali sotuv ma'lumoti yo'q.")
            return
        lines = []
        medals = ["🥇","🥈","🥉"]
        for i, p in enumerate(tops):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(
                f"{medal} *{p[1]}*\n"
                f"   🛒 Sotilgan: {p[2]:,} dona | 👁 Ko'rishlar: {p[3]:,} | 💰 {p[4]:,} so'm"
            )
        await query.message.reply_text(
            "🏆 *Eng ko'p sotilgan mahsulotlar:*\n\n" + "\n\n".join(lines),
            parse_mode="Markdown"
        )

    elif action == "adm_promos":
        promos = get_promo_codes()
        if not promos:
            await query.message.reply_text("😔 Promo-kodlar yo'q.")
            return
        lines = [
            f"{'✅' if p[6] else '❌'} *{p[1]}* — {p[3]}{'%' if p[2]=='percent' else ' so'm'} "
            f"({p[5]}/{p[4]} ta ishlatilgan)"
            for p in promos
        ]
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif action == "adm_reviews":
        with db() as conn:
            reviews = conn.execute(
                "SELECT r.rating, r.comment, r.product_id, p.name_uz "
                "FROM reviews r LEFT JOIN products p ON r.product_id=p.id "
                "ORDER BY r.id DESC LIMIT 20"
            ).fetchall()
        if not reviews:
            await query.message.reply_text("😔 Sharhlar yo'q.")
            return
        lines = [f"{'⭐'*r[0]} {r[3]} — {r[1] or '(izohsiz)'}" for r in reviews]
        await query.message.reply_text("\n".join(lines[:15]))

    elif action in ("adm_addpromo", "adm_broadcast", "adm_addzone"):
        ctx.user_data["adm_action"] = action
        if action == "adm_addpromo":
            await query.message.reply_text(
                "🎁 Promo-kod nomini kiriting (masalan: SALE20):",
                reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
            )
            return ADM_PROMO_CODE
        elif action == "adm_broadcast":
            await query.message.reply_text(
                "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
                reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
            )
            return ADM_BROADCAST
        elif action == "adm_addzone":
            await query.message.reply_text(
                "📦 Yangi hudud nomini kiriting (O'zbek tilida):",
                reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
            )
            return ADM_ZONE_NAME_UZ

async def delete_product_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    pid = int(query.data.split("_")[1])
    delete_product(pid)
    await query.message.reply_text(f"✅ Mahsulot #{pid} o'chirildi.")

# ── ADMIN: ZAHIRA YANGILASH ──────────────────────────────────────────────────

async def adm_stock_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    pid = int(query.data.split("_")[1])
    with db() as conn:
        p = conn.execute("SELECT name_uz, stock FROM products WHERE id=?", (pid,)).fetchone()
    if not p:
        await query.message.reply_text("❌ Mahsulot topilmadi.")
        return ConversationHandler.END
    ctx.user_data["stock_pid"] = pid
    await query.message.reply_text(
        f"📦 *{p[0]}*\nHozirgi zahira: *{p[1]} dona*\n\nYangi miqdorni kiriting:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True)
    )
    return ADM_STOCK_QTY

async def adm_stock_qty(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text("❌ Faqat musbat raqam kiriting:")
        return ADM_STOCK_QTY
    pid = ctx.user_data["stock_pid"]
    qty = int(txt)
    set_stock(pid, qty)
    with db() as conn:
        name = conn.execute("SELECT name_uz FROM products WHERE id=?", (pid,)).fetchone()[0]
    status = "✅ faol" if qty > 0 else "❌ yopiq (tugagan)"
    await update.message.reply_text(
        f"✅ *{name}* zahirasi yangilandi!\n"
        f"📦 Yangi miqdor: *{qty} dona*\n"
        f"Holat: {status}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── ADMIN: PROMO-KOD QO'SHISH ─────────────────────────────────────────────────

async def adm_promo_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_promo_code"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "📊 Chegirma turini tanlang:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("% Foiz", callback_data="promotype_percent"),
             InlineKeyboardButton("💰 Summa", callback_data="promotype_amount")]
        ])
    )
    return ADM_PROMO_TYPE

async def adm_promo_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["new_promo_type"] = query.data.split("_")[1]
    label = "foiz (masalan 15)" if ctx.user_data["new_promo_type"] == "percent" else "so'm (masalan 10000)"
    await query.message.reply_text(f"💰 Chegirma miqdorini kiriting ({label}):")
    return ADM_PROMO_VAL

async def adm_promo_val(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text("❌ Faqat raqam:")
        return ADM_PROMO_VAL
    ctx.user_data["new_promo_val"] = int(txt)
    await update.message.reply_text("🔢 Maksimal ishlatilish soni (masalan 100):")
    return ADM_PROMO_MAX

async def adm_promo_max(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text("❌ Faqat raqam:")
        return ADM_PROMO_MAX
    code = ctx.user_data["new_promo_code"]
    ok = add_promo_code(
        code,
        ctx.user_data["new_promo_type"],
        ctx.user_data["new_promo_val"],
        int(txt)
    )
    if ok:
        await update.message.reply_text(
            f"✅ Promo-kod *{code}* muvaffaqiyatli qo'shildi!",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("❌ Bu kod allaqachon mavjud!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ── ADMIN: BROADCAST ──────────────────────────────────────────────────────────

async def adm_broadcast_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    with db() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    sent, failed = 0, 0
    for (uid,) in users:
        try:
            await ctx.bot.send_message(uid, f"📢 {text}")
            sent += 1
        except:
            failed += 1
    await update.message.reply_text(
        f"✅ Yuborildi: {sent} ta\n❌ Xatolik: {failed} ta",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── ADMIN: HUDUD QO'SHISH ────────────────────────────────────────────────────

async def adm_zone_uz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_zone_uz"] = update.message.text.strip()
    await update.message.reply_text("✏️ Hudud nomi (Rus tilida):")
    return ADM_ZONE_NAME_RU

async def adm_zone_ru(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_zone_ru"] = update.message.text.strip()
    await update.message.reply_text("✏️ Hudud nomi (Ingliz tilida):")
    return ADM_ZONE_NAME_EN

async def adm_zone_en(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_zone_en"] = update.message.text.strip()
    await update.message.reply_text("💰 Yetkazib berish narxi (so'mda):")
    return ADM_ZONE_PRICE

async def adm_zone_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text("❌ Faqat raqam:")
        return ADM_ZONE_PRICE
    with db() as conn:
        conn.execute(
            "INSERT INTO delivery_zones(name_uz,name_ru,name_en,price) VALUES(?,?,?,?)",
            (ctx.user_data["new_zone_uz"], ctx.user_data["new_zone_ru"],
             ctx.user_data["new_zone_en"], int(txt))
        )
        conn.commit()
    await update.message.reply_text(
        f"✅ Hudud *{ctx.user_data['new_zone_uz']}* qo'shildi!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — MAHSULOT QO'SHISH
# ══════════════════════════════════════════════════════════════════════════════

async def admin_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return ConversationHandler.END
    cats = CATEGORIES["uz"]
    buttons = [[InlineKeyboardButton(name, callback_data=f"acat_{key}")]
               for name, key in zip(cats, CAT_KEYS)]
    await update.message.reply_text("📂 Kategoriyani tanlang:",
                                    reply_markup=InlineKeyboardMarkup(buttons))
    return AP_CAT

async def ap_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["ap_cat"] = query.data.split("_")[1]
    await query.message.reply_text("🖼 Suratni yuboring:",
                                   reply_markup=ReplyKeyboardMarkup([["/bekor"]], resize_keyboard=True))
    return AP_PHOTO

async def ap_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Surat yuboring.")
        return AP_PHOTO
    ctx.user_data["ap_photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("✏️ Nomi (O'zbek tilida):")
    return AP_NAME_UZ

async def ap_name_uz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ap_name_uz"] = update.message.text.strip()
    await update.message.reply_text("✏️ Nomi (Rus tilida):")
    return AP_NAME_RU

async def ap_name_ru(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ap_name_ru"] = update.message.text.strip()
    await update.message.reply_text("✏️ Nomi (Ingliz tilida):")
    return AP_NAME_EN

async def ap_name_en(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ap_name_en"] = update.message.text.strip()
    await update.message.reply_text("💰 Narxi (so'mda, faqat raqam):")
    return AP_PRICE

async def ap_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip().isdigit():
        await update.message.reply_text("❌ Faqat raqam:")
        return AP_PRICE
    ctx.user_data["ap_price"] = int(update.message.text.strip())
    await update.message.reply_text("📝 Tavsif (O'zbek tilida):")
    return AP_DESC_UZ

async def ap_desc_uz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ap_desc_uz"] = update.message.text.strip()
    await update.message.reply_text("📝 Tavsif (Rus tilida):")
    return AP_DESC_RU

async def ap_desc_ru(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ap_desc_ru"] = update.message.text.strip()
    await update.message.reply_text("📝 Tavsif (Ingliz tilida):")
    return AP_DESC_EN

async def ap_desc_en(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = ctx.user_data
    add_product(
        d["ap_cat"], d["ap_photo"],
        d["ap_name_uz"], d["ap_name_ru"], d["ap_name_en"],
        d["ap_price"],
        d["ap_desc_uz"], d["ap_desc_ru"], d["ap_desc_en"]
    )
    bot_username = (await ctx.bot.get_me()).username
    with db() as conn:
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    caption = (
        f"📦 *{d['ap_name_uz']}*\n"
        f"💰 Narxi: *{d['ap_price']:,} so'm*\n\n"
        f"📝 {d['ap_desc_uz']}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Buyurtma qilish",
                             url=f"https://t.me/{bot_username}?start=product_{pid}")
    ]])
    await ctx.bot.send_photo(chat_id=CHANNEL_ID, photo=d["ap_photo"],
                             caption=caption, parse_mode="Markdown", reply_markup=kb)
    await update.message.reply_text(
        f"✅ Mahsulot qo'shildi va kanalga joylandi! (ID: {pid})",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    tot_o, tot_r, new_o, tot_u, tot_p, avg_r = get_stats()
    await update.message.reply_text(
        f"📊 *Statistika*\n\n"
        f"👥 Foydalanuvchilar: {tot_u}\n"
        f"📦 Mahsulotlar: {tot_p}\n"
        f"🛒 Jami buyurtmalar: {tot_o}\n"
        f"🆕 Yangi buyurtmalar: {new_o}\n"
        f"💰 Jami daromad: {tot_r:,} so'm\n"
        f"⭐ O'rtacha reyting: {avg_r:.1f}/5",
        parse_mode="Markdown"
    )

# ── YORDAMCHI ─────────────────────────────────────────────────────────────────

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(t(lang, "cancel"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ══════════════════════════════════════════════════════════════════════════════
#  ⏰ REJALASHTIRILGAN ISHLAR (SCHEDULED JOBS)
# ══════════════════════════════════════════════════════════════════════════════

async def check_stuck_orders_job(context):
    """Har 30 daqiqada: 2 soatdan ko'p yangi turgan buyurtmalarni tekshiradi"""
    stuck = get_stuck_orders(hours=2)
    if not stuck:
        return
    lines = []
    for o in stuck:
        created = o[4][:16].replace("T", " ")
        lines.append(f"🔴 #{o[0]} | {o[1]} | {o[2]} | {o[3]} | {created}")
    text = (
        f"⏰ *Kutilayotgan buyurtmalar!*\n"
        f"Quyidagi buyurtmalar 2+ soat davomida ko'rib chiqilmagan:\n\n"
        + "\n".join(lines)
    )
    try:
        await context.bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Stuck orders alert error: {e}")

async def daily_report_job(context):
    """Har kuni soat 09:00 da kunlik hisobot yuboradi"""
    orders_today, revenue_today, new_users = get_today_stats()
    tot_o, tot_r, new_o, tot_u, tot_p, avg_r = get_stats()
    low = get_low_stock_products()
    low_str = ""
    if low:
        low_str = "\n\n⚠️ *Kam qolgan mahsulotlar:*\n" + "\n".join(
            [f"  • {p[1]} — {p[2]} dona" for p in low]
        )
    text = (
        f"🌅 *Kunlik hisobot — {datetime.now().strftime('%d.%m.%Y')}*\n\n"
        f"📦 Bugungi buyurtmalar: *{orders_today}*\n"
        f"💰 Bugungi daromad: *{revenue_today:,} so'm*\n"
        f"👥 Yangi mijozlar: *{new_users}*\n\n"
        f"📊 *Umumiy:*\n"
        f"  Jami buyurtmalar: {tot_o}\n"
        f"  Jami daromad: {tot_r:,} so'm\n"
        f"  🆕 Yangi (ko'rib chiqilmagan): {new_o}\n"
        f"  Foydalanuvchilar: {tot_u}\n"
        f"  Faol mahsulotlar: {tot_p}"
        f"{low_str}"
    )
    try:
        await context.bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Daily report error: {e}")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Admin: mahsulot qo'shish
    add_conv = ConversationHandler(
        entry_points=[
            CommandHandler("addproduct", admin_add_start),
            CallbackQueryHandler(ap_cat, pattern=r"^acat_")
        ],
        states={
            AP_CAT:      [CallbackQueryHandler(ap_cat, pattern=r"^acat_")],
            AP_PHOTO:    [MessageHandler(filters.PHOTO, ap_photo)],
            AP_NAME_UZ:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_name_uz)],
            AP_NAME_RU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_name_ru)],
            AP_NAME_EN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_name_en)],
            AP_PRICE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_price)],
            AP_DESC_UZ:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_desc_uz)],
            AP_DESC_RU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_desc_ru)],
            AP_DESC_EN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_desc_en)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Buyurtma
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern=r"^order_\d+$")],
        states={
            O_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, o_name)],
            O_PHONE:   [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), o_phone)],
            O_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, o_address)],
            O_QTY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, o_qty)],
            O_PROMO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, o_promo),
                        CommandHandler("skip", o_promo)],
            O_ZONE:    [CallbackQueryHandler(o_zone, pattern=r"^zone_\d+$")],
            O_PAY:     [
                CallbackQueryHandler(o_pay_card,     pattern="^pay_card$"),
                CallbackQueryHandler(o_pay_online,   pattern="^pay_(click|payme)$"),
                CallbackQueryHandler(o_use_balance,  pattern=r"^usebalance_\d+$"),
            ],
            O_RECEIPT: [MessageHandler(filters.PHOTO, o_receipt)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Qidirish (ham /search komandasi, ham menyu tugmasi orqali)
    search_conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_start),
            CallbackQueryHandler(search_start_cb, pattern="^menu_search$"),
        ],
        states={
            S_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_query)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Sharh
    review_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(rate_product, pattern=r"^rate_\d+_\d+_\d+$")],
        states={
            R_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rate_comment_handler),
                CommandHandler("skip", rate_comment_handler),
            ],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Admin: promo-kod qo'shish
    promo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: adm_promo_code(u, c),
                                           pattern="^adm_addpromo$")],
        states={
            ADM_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_promo_code)],
            ADM_PROMO_TYPE: [CallbackQueryHandler(adm_promo_type, pattern=r"^promotype_")],
            ADM_PROMO_VAL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_promo_val)],
            ADM_PROMO_MAX:  [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_promo_max)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Admin: broadcast
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: adm_broadcast_msg(u, c),
                                           pattern="^adm_broadcast$")],
        states={
            ADM_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_msg)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Admin: hudud qo'shish
    zone_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: adm_zone_uz(u, c),
                                           pattern="^adm_addzone$")],
        states={
            ADM_ZONE_NAME_UZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_zone_uz)],
            ADM_ZONE_NAME_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_zone_ru)],
            ADM_ZONE_NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_zone_en)],
            ADM_ZONE_PRICE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_zone_price)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    # Admin: zahira yangilash
    stock_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_stock_select, pattern=r"^setstock_\d+$")],
        states={
            ADM_STOCK_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_stock_qty)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )

    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("catalog",    catalog))
    app.add_handler(CommandHandler("orders",     my_orders))
    app.add_handler(CommandHandler("stats",      admin_stats))
    app.add_handler(CommandHandler("referral",   referral))
    app.add_handler(CommandHandler("balance",    balance_cmd))
    app.add_handler(CommandHandler("lang",       change_lang))
    app.add_handler(CommandHandler("admin",      admin_menu))

    app.add_handler(add_conv)
    app.add_handler(order_conv)
    app.add_handler(search_conv)
    app.add_handler(review_conv)
    app.add_handler(promo_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(zone_conv)
    app.add_handler(stock_conv)

    # Admin: buyurtma holati + ixtiyoriy izoh
    note_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_status, pattern=r"^ostatus_")],
        states={
            ADM_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_status_note),
                CommandHandler("skip", order_status_note),
            ],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )
    app.add_handler(note_conv)

    app.add_handler(CallbackQueryHandler(set_language,         pattern=r"^lang_"))
    app.add_handler(CallbackQueryHandler(menu_callback,        pattern=r"^menu_"))
    app.add_handler(CallbackQueryHandler(show_category,        pattern=r"^cat_"))
    app.add_handler(CallbackQueryHandler(show_product_callback,pattern=r"^prod_\d+$"))
    app.add_handler(CallbackQueryHandler(back_catalog,         pattern="^back_catalog$"))
    app.add_handler(CallbackQueryHandler(admin_callback,       pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(delete_product_cb,    pattern=r"^delp_\d+$"))
    app.add_handler(CallbackQueryHandler(noop,                 pattern="^noop$"))

    # ⏰ Rejalashtirilgan ishlar (APScheduler o'rnatilgan bo'lsa ishlaydi)
    try:
        from datetime import time as dt_time
        jq = app.job_queue
        if jq is not None:
            jq.run_repeating(check_stuck_orders_job, interval=1800, first=60)
            jq.run_daily(daily_report_job, time=dt_time(hour=4, minute=0))
            print("✅ Job Queue faollashtirildi")
        else:
            print("⚠️  Job Queue mavjud emas — APScheduler o'rnatilmagan")
    except Exception as e:
        print(f"⚠️  Job Queue xatosi: {e}")

    print("✅ PRO Shop Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
