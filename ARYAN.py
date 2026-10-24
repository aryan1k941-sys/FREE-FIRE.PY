import asyncio
import sqlite3
import random
import logging
import time
import aiohttp
import hmac
import hashlib
import html as html_lib
import json
import urllib.parse
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, Dice, BufferedInputFile
)

# ==============================================================================
# 1. BOT CONFIGURATION & CONSTANTS
# ==============================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Hasan_Modz_Ofc.db')

BOT_TOKEN = "8826960826:AAGACxlp9nIQBaDnpt77Zq2Sm7anjTTDTwE"
BOT_USERNAME = "HASAN_OFFICIAL_PANEL22_BOT"
ADMIN_ID = 8252540513
ADMIN_CONTACT = "@hasan_ob55"

FAMPAY_API_KEY = "fam_fc6b8ab9fea985ff4ff97b91c5739c8dae151e8d"  # Replace with your actual API key
FAMPAY_QR_URL = "https://famgateway.in/api/qr.php"
FAMPAY_VERIFY_URL = "https://famgateway.in/api/verify-order.php"
FAMPAY_STATUS_URL = "https://famgateway.in/api/checkout-status.php"

# Reseller API (automatic key supplier)
# IMPORTANT: this is intentionally the BantiBhaiya endpoint requested for this build.
RESELLER_API_URL = "https://bantibhaiya.to/api/reseller_v1.php"
RESELLER_API_KEY = "YOUR_RRSELLER_API_ADD"

USDT_TO_INR = 90.0
VIP_DISCOUNT_PERCENTAGE = 1.0
VIP_PRICE_INR = 1000.0

WELCOME_STICKER_ID = "CAACAgIAAxkBAAEU-WZmH_..."  # Replace with your sticker ID
SPIN_DELAY_SECONDS = 2.5

FIXED_CATEGORIES = [
    "ANDROID NON ROOT PANEL",
    "ANDROID ROOT PANEL",
    "IPHONE PANEL",
    "PC PANEL"
]

# ==============================================================================
# YOUR PREMIUM EMOJIS – all required emoji IDs (updated with new premium ones)
# ==============================================================================
DEFAULT_EMOJIS = {
    'product_store': '6163205892834598715',
    'profile': '5870695289714643076',
    'sagarproof': '6001517283426439371',
    'sagar': '6195196922379115661',
    'add_balance': '5429651785352501917',
    'history': '6032594876506312598',
    'referral': '5350452584119279096',
    'support': '5472239203590888751',
    'ludo_spin': '5382194935057372936',
    'back': '5409357944619802453',
    'upi': '5807750375033278838',
    'binance': '6161089551994462716',
    'reseller': '5447410659077661506',
    'tutorial': '5427158904729513162',
    'download': '6161336001512874965',
    'telegram': '5456140674028019486',
    'whatsapp': '5251203410396458957',
    'welcome': '5397782960512444700',
    'vip': '5206607081334906820',
    'category_android_non_root': '6161172706856282588',
    'category_android_root': '6161449831031118974',
    'category_iphone': '6161399700172840408',
    'category_pc': '5350554349074391003',
    'grid_id': '5474625972751837256',
    'name': '5215399540814781035',
    'account_level': '6129584162992034014',
    'regular_user': '5904630315946611415',
    'wallet': '6210859306602995217',
    'current_balance': '5316711376876485361',
    'global_stats': '6161437856662298090',
    'total_orders': '6160968017304888311',
    'total_spent': '5197503331215361533',
    'total_referrals': '5938196735200333756',
    'joined_grid': '5433614043006903194',
    'info_icon': '6037421444789440735',
    'check_icon': '6161241250239356403',
    'checkbox_icon': '6161437856662298090',
    'shield_icon': '6086672466132865380',
    'money_icon': '5890848474563352982',
    'redeem_icon': '5377624166436445368',
    'wallet_left': '6210859306602995217',
    'wallet_right': '5305699699204837855',
    'point_down': '6161302621027049305',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def fmt_curr(amount: float) -> str:
    return f"₹{amount:,.2f}"

def safe_float(val, default=0.0):
    """Safely convert a value to float, return default if fails."""
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ==============================================================================
# 2. DATABASE FUNCTIONS
# ==============================================================================
def db_query(query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = True) -> Any:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetchone:
            res = c.fetchone()
        elif fetchall:
            res = c.fetchall()
        else:
            res = None
        if commit: conn.commit()
        return res
    except Exception as e:
        logger.error(f"DB Error: {e} | Query: {query} | Params: {params}")
        if commit: conn.rollback()
        return None
    finally:
        conn.close()

def get_setting(key: str, default: str = "") -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (key,), fetchone=True)
    return val[0] if val and val[0] else default

def set_setting(key: str, value: str) -> None:
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))


def new_user_start_message_enabled() -> bool:
    """Return the admin-controlled New User Notification state."""
    return str(get_setting("new_user_start_message", "ON")).strip().upper() == "ON"

def log_activity(user_id: int, action: str, details: str = "") -> None:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_query(
            "INSERT INTO activity_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, details, timestamp)
        )
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")

def get_emoji(slot: str, default_id: str = None) -> str:
    stored = get_setting(f"emoji_{slot}", "")
    emoji_id = stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">✨</tg-emoji>'
    return "✨"

def get_emoji_icon(slot: str, default_id: str = None) -> str:
    stored = get_setting(f"emoji_{slot}", "")
    emoji_id = stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))
    return emoji_id

# ==============================================================================
# 3. STRING RESOURCES – using placeholders for premium emojis
# ==============================================================================
UI_TEXTS = {
    "start_menu": (
        "{sagar} WELCOME TO HASAN OFFICIAL PANEL STORE 🛍️\n"
        "{product_store} 🔑 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐆𝐚𝐦𝐞 𝐊𝐞𝐲𝐬 & 𝐏𝐚𝐧𝐞𝐥𝐬\n"
        "{profile}  𝐈𝐧𝐬𝐭𝐚𝐧𝐭 𝐀𝐮𝐭𝐨 𝐃𝐞𝐥𝐢𝐯𝐞𝐫𝐲 𝟐𝟒×𝟕\n"
        "{add_balance} 🔒 𝟏𝟎𝟎% 𝐒𝐞𝐜𝐮𝐫𝐞 & 𝐓𝐫𝐮𝐬𝐭𝐞𝐝 𝐒𝐭𝐨𝐫𝐞\n"
        "{history} 💎 𝐁𝐞𝐬𝐭 𝐏𝐫𝐢𝐜𝐞𝐬 𝐆𝐮𝐚𝐫𝐚𝐧𝐭𝐞𝐞𝐝\n"
        "{referral} 🎁 𝐃𝐚𝐢𝐥𝐲 𝐑𝐞𝐰𝐚𝐫𝐝𝐬 & 𝐒𝐩𝐞𝐜𝐢𝐚𝐥 𝐎𝐟𝐟𝐞𝐫𝐬\n"
        "{tutorial} ☎️ 𝟐𝟒/𝟕 𝐋𝐢𝐯𝐞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞\n"
        "{support}🌹 𝐓𝐫𝐮𝐬𝐭𝐞𝐝 𝐛𝐲 𝐇𝐮𝐧𝐝𝐫𝐞𝐝𝐬 𝐨𝐟 𝐔𝐬𝐞𝐫𝐬\n"
        "{sagar} 👤 <b>𝐔𝐬𝐞𝐫 𝐈𝐃:</b> <code>{u[0]}</code>\n"
        "{wallet_left} 💰 <b>𝐘𝐨𝐮𝐫 𝐁𝐚𝐥𝐚𝐧𝐜𝐞:</b> {fmt_curr(u[3])}\n"
    ),
    "download_files": (
        "🗂 <b><u>DOWNLOAD PREMIUM APK & FILES 📊</u></b>\n\n"
        "🌐 All our highly secured, premium, and updated files\n"
        "are securely hosted on our private channel! ⚠️⛔️\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📱 <b>WHAT YOU GET:</b> 📌\n\n"
        "✔️ Latest APK Updates 🔔\n"
        "✔️ 100% Virus Free & Secure ‼️\n"
        "✔️ All Configs & Scripts 🌸\n"
        "✔️ Complete Installation Guides 🔺\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⌨️ Tap the button below to access the Download Channel! 📝"
    ),
    "lucky_dice_result": (
        "{ludo_spin} <b><u>LUCKY DICE RESULT 🔨 💯</u></b>\n\n"
        "🎲 <b>Dice Value:</b> {dice_value}\n\n"
        "💸 <b>You Won:</b> {won_amount}\n"
        "💰 <b>Total Balance:</b> {new_balance}\n\n"
        "Congratulations! Come back after 24 hours."
    ),
    "vip_menu": (
        "🌟 <b><u>VIP MEMBERSHIP CLUB</u></b> 🌟\n\n"
        "Unlock premium benefits and permanent discounts!\n\n"
        "💎 <b>VIP Benefits:</b>\n"
        "• Flat 15% off on ALL products (Stacks with Reseller!)\n"
        "• Priority Support\n"
        "• Exclusive VIP-only giveaways\n\n"
        "💳 <b>VIP Price:</b> ₹299.00 (Lifetime)\n"
        "👤 <b>Your Status:</b> {vip_status}"
    ),
    "add_balance_menu": (
        "{add_balance} <b>ADD BALANCE</b> {info_icon}\n\n"
        "{info_icon} Select your preferred payment method. {ck_icon}\n\n"
        "┣ {upi} UPI — Fast Indian payments {checkbox_icon}\n"
        "┣ {binance} Binance — Crypto payments {checkbox_icon}\n\n"
        "{shield_icon} Payments are verified securely. {check_icon}"
    )
}

def get_ui_text(key: str, **kwargs) -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (f"ui_{key}",), fetchone=True)
    template = val[0] if val and val[0] else UI_TEXTS.get(key, "")

    emoji_map = {
        '{product_store}': get_emoji('product_store'),
        '{sagar}': get_emoji('sagar'),
        '{profile}': get_emoji('profile'),
        '{add_balance}': get_emoji('add_balance'),
        '{history}': get_emoji('history'),
        '{referral}': get_emoji('referral'),
        '{tutorial}': get_emoji('tutorial'),
        '{support}': get_emoji('support'),
        '{ludo_spin}': get_emoji('ludo_spin'),
        '{download}': get_emoji('download'),
        '{telegram}': get_emoji('telegram'),
        '{whatsapp}': get_emoji('whatsapp'),
        '{upi}': get_emoji('upi'),
        '{binance}': get_emoji('binance'),
        '{info_icon}': get_emoji('info_icon'),
        '{check_icon}': get_emoji('check_icon'),
        '{checkbox_icon}': get_emoji('checkbox_icon'),
        '{shield_icon}': get_emoji('shield_icon'),
        '{money_icon}': get_emoji('money_icon'),
        '{redeem_icon}': get_emoji('redeem_icon'),
        '{wallet_left}': get_emoji('wallet_left'),
        '{wallet_right}': get_emoji('wallet_right'),
        '{point_down}': get_emoji('point_down'),
    }
    for placeholder, emoji_tag in emoji_map.items():
        template = template.replace(placeholder, emoji_tag)

    # The DB may contain an older/custom start_menu template that uses
    # {u[0]} and {fmt_curr(u[3])}. str.format() cannot execute a function
    # call inside a field, so resolve these two live profile values first.
    if key == "start_menu" and kwargs.get("u"):
        user_row = kwargs["u"]
        try:
            template = template.replace("{u[0]}", str(user_row[0]))
            template = template.replace("{fmt_curr(u[3])}", fmt_curr(user_row[3]))
        except (IndexError, TypeError):
            logger.warning("Invalid user data while formatting start_menu")

    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError, IndexError) as e:
            logger.warning(f"Missing/invalid formatting value for template {key}: {e}")
    return template

# ==============================================================================
# 4. DATABASE INITIALISATION & MIGRATION
# ==============================================================================
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            phone TEXT, 
            first_name TEXT, 
            username TEXT,
            balance REAL DEFAULT 0.0, 
            account_type TEXT DEFAULT 'Regular', 
            orders_count INTEGER DEFAULT 0, 
            spent REAL DEFAULT 0.0, 
            referrals_count INTEGER DEFAULT 0, 
            referral_earned REAL DEFAULT 0.0, 
            referred_by INTEGER, 
            last_spin TEXT, 
            joined_date TEXT,
            is_reseller INTEGER DEFAULT 0,
            reseller_since TEXT,
            total_saved REAL DEFAULT 0.0,
            is_banned INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            vip_since TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category TEXT, 
            panel_name TEXT DEFAULT '',
            name TEXT, 
            price_inr REAL, 
            reseller_price REAL DEFAULT 0.0,
            stock INTEGER, 
            apk_link TEXT, 
            validity TEXT DEFAULT 'Lifetime', 
            device_limit TEXT DEFAULT '1 Device',
            is_active INTEGER DEFAULT 1,
            maintenance INTEGER DEFAULT 0,
            api_product_id TEXT DEFAULT '',
            api_duration TEXT DEFAULT ''
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_demos (
            product_name_key TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            file_id TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS product_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            product_id INTEGER, 
            key_text TEXT, 
            is_used INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            product_name TEXT, 
            price_paid REAL, 
            delivered_key TEXT, 
            purchase_date TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            message TEXT, 
            status TEXT DEFAULT 'Open',
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY, 
            amount REAL, 
            uses_left INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS redeemed (
            user_id INTEGER, 
            code TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            order_id TEXT PRIMARY KEY, 
            user_id INTEGER, 
            amount_inr REAL, 
            status TEXT, 
            timestamp INTEGER,
            qr_url TEXT,
            upi_id TEXT,
            expires_at INTEGER,
            qr_message_id INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS crypto_txns (
            txid TEXT PRIMARY KEY, 
            user_id INTEGER, 
            amount_usdt REAL, 
            timestamp INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS spin_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            amount REAL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')

    migrations = [
        "ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN vip_since TEXT",
        "ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1",
        "ALTER TABLE products ADD COLUMN maintenance INTEGER DEFAULT 0",
        "ALTER TABLE tickets ADD COLUMN created_at TEXT",
        "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN warnings INTEGER DEFAULT 0",
        "ALTER TABLE products ADD COLUMN panel_name TEXT DEFAULT ''",
        "ALTER TABLE transactions ADD COLUMN qr_url TEXT",
        "ALTER TABLE transactions ADD COLUMN upi_id TEXT",
        "ALTER TABLE transactions ADD COLUMN expires_at INTEGER",
        "ALTER TABLE transactions ADD COLUMN qr_message_id INTEGER",
        "ALTER TABLE products ADD COLUMN api_product_id TEXT DEFAULT ''",
        "ALTER TABLE products ADD COLUMN api_duration TEXT DEFAULT ''"
    ]
    for mig in migrations:
        try: c.execute(mig)
        except sqlite3.OperationalError: pass
    
    c.execute("SELECT COUNT(*) FROM spin_rewards")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO spin_rewards (amount) VALUES (?)", [(0.0,), (1.0,), (2.0,), (5.0,), (10.0,)])

    default_settings = [
        ('spin_status', 'ON'),
        ('daily_spin_limit', '50.0'),
        ('reseller_system_status', 'ON'),
        ('bot_status', 'ON'),
        ('how_to_video', 'None'),
        ('all_files_link', 'None'),
        ('selling_proof_link', 'None'),
        ('fampay_api_key', FAMPAY_API_KEY),
        ('reseller_api_key', RESELLER_API_KEY),
        ('reseller_api_url', RESELLER_API_URL),
        ('fampay_upi_id', ''),
        ('binance_api', ''),
        ('binance_secret', ''),
        ('binance_address', ''),
        ('vip_status', 'OFF'),
        ('reseller_setup_fee', '200.0'),
        ('reseller_min_balance', '500.0'),
        ('migration_done', '0'),
        ('new_user_start_message', 'ON'),
        ('support_telegram', 'https://t.me/YourSupport'),
        ('support_whatsapp', 'https://wa.me/YourNumber'),
        ('ui_start_menu', UI_TEXTS['start_menu']),
        ('ui_download_files', UI_TEXTS['download_files']),
        ('ui_lucky_dice_result', UI_TEXTS['lucky_dice_result']),
        ('ui_vip_menu', UI_TEXTS['vip_menu']),
        ('ui_add_balance_menu', UI_TEXTS['add_balance_menu']),
    ]
    for slot, emoji_id in DEFAULT_EMOJIS.items():
        default_settings.append((f"emoji_{slot}", emoji_id))
    
    for key, val in default_settings:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()

def migrate_categories() -> None:
    done = get_setting("migration_done", "0")
    
    # ALWAYS force update emojis and UI texts regardless of migration status
    logger.info("Forcing emoji and UI text updates...")
    
    # Update all emoji settings
    for slot, emoji_id in DEFAULT_EMOJIS.items():
        set_setting(f"emoji_{slot}", emoji_id)
    
    # Force update UI texts
    set_setting("ui_start_menu", UI_TEXTS['start_menu'])
    set_setting("ui_add_balance_menu", UI_TEXTS['add_balance_menu'])
    set_setting("ui_download_files", UI_TEXTS['download_files'])
    set_setting("ui_lucky_dice_result", UI_TEXTS['lucky_dice_result'])
    set_setting("ui_vip_menu", UI_TEXTS['vip_menu'])
    logger.info("UI texts and emojis updated with new placeholders and IDs.")
    
    # Fix any corrupted price columns (one-time cleanup)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    products = c.execute("SELECT id, price_inr, reseller_price FROM products").fetchall()
    for prod in products:
        pid = prod[0]
        for col in ['price_inr', 'reseller_price']:
            val = prod[1] if col == 'price_inr' else prod[2]
            if val is None or val == "":
                new_val = 0.0
            else:
                try:
                    new_val = float(val)
                except (ValueError, TypeError):
                    new_val = 0.0
            c.execute(f"UPDATE products SET {col}=? WHERE id=?", (new_val, pid))
    conn.commit()
    conn.close()
    logger.info("Fixed any non-numeric price columns.")
    
    if done == "1":
        return
    
    logger.info("Running category migration...")
    
    mapping = {
        "android non root panel": "ANDROID NON ROOT PANEL",
        "android root panel": "ANDROID ROOT PANEL",
        "iphone panel": "IPHONE PANEL",
        "pc panel": "PC PANEL",
    }
    for old, new in mapping.items():
        db_query("UPDATE products SET category = ? WHERE LOWER(category) = ?", (new, old))
    
    db_query("UPDATE products SET category = 'ANDROID NON ROOT PANEL' WHERE LOWER(category) NOT IN (?, ?, ?, ?)",
             ("android non root panel", "android root panel", "iphone panel", "pc panel"))
    
    set_setting("migration_done", "1")
    logger.info("Category migration complete.")

# ==============================================================================
# 5. MIDDLEWARES & SECURITY
# ==============================================================================
async def hacker_loading(message: Message, text: str = "Decrypting Data") -> Message:
    msg = await message.answer(f"⚡ {text}\n[□□□] 0%")
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■□□] 33%", parse_mode='HTML')
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■■□] 66%", parse_mode='HTML')
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■■■] 100%", parse_mode='HTML')
    return msg

class GlobalSecurityMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.last_action_times = {}

    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        now = time.time()
        # Do not throttle inline-button callbacks: rapid keypad taps (especially
        # Confirm) must not be silently discarded. Keep a short debounce for messages.
        if isinstance(event, Message):
            if user_id in self.last_action_times and now - self.last_action_times[user_id] < 0.08:
                return
            self.last_action_times[user_id] = now

        if user_id != ADMIN_ID:
            user_info = db_query("SELECT is_banned FROM users WHERE user_id=?", (user_id,), fetchone=True)
            if user_info and user_info[0] == 1:
                msg = "🚫 <b>ACCESS DENIED</b>\nYou have been banned from using this bot.\nContact support if you think this is a mistake."
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
                return
                
            status_check = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
            status = status_check[0] if status_check else 'ON'
            if status == 'OFF':
                msg = "⚠️ <b>Store Maintenance</b>\n\nThe store is currently offline for updates. Please check back later!"
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer("⚠️ Bot is currently OFF for Maintenance.", show_alert=True)
                return
                
        return await handler(event, data)

dp.message.middleware(GlobalSecurityMiddleware())
dp.callback_query.middleware(GlobalSecurityMiddleware())

# ==============================================================================
# 6. FSM STATES
# ==============================================================================
class UserStates(StatesGroup):
    wait_for_ticket = State()
    wait_for_redeem = State()
    wait_for_crypto_txid = State()
    custom_amount_input = State()

class AdminStates(StatesGroup):
    add_prod_category = State()
    add_prod_panel_name = State()
    add_prod_name = State()
    add_prod_validity = State()
    add_prod_device_limit = State()
    add_prod_price = State()
    add_prod_reseller_price = State()
    add_prod_apk = State()
    add_prod_keys = State()
    add_prod_api_pid = State()
    add_prod_api_duration = State()
    wait_for_product_demo_video = State()
    wait_for_demo_delete_time = State()
    
    edit_prod_field = State()
    wait_for_new_value = State()
    wait_for_add_keys = State()
    wait_for_delete_key = State()
    
    broadcast_msg = State()
    add_coupon_code = State()
    add_coupon_amount = State()
    add_coupon_uses = State()
    
    # Payment gateway setup states
    wait_for_fampay_api = State()
    wait_for_fampay_upi = State()
    wait_for_zapupi_key = State()
    
    # Binance states
    wait_for_binance_api = State()
    wait_for_binance_secret = State()
    wait_for_binance_address = State()
    
    ticket_reply_msg = State()
    reseller_manage_id = State()
    manage_target_user = State()
    wait_for_add_money = State()
    wait_for_minus_money = State()
    wait_for_warning = State()
    
    spin_add_reward = State()
    spin_set_limit = State()
    wait_for_howto_video = State()
    wait_for_all_files_link = State()
    wait_for_selling_proof_link = State()
    
    edit_ui_text = State()
    edit_reseller_price = State()
    wait_for_reseller_setup_fee = State()
    wait_for_reseller_min_balance = State()
    wait_for_reseller_api_key = State()
    wait_for_reseller_api_url = State()
    confirm_ban = State()
    
    wait_for_support_telegram = State()
    wait_for_support_whatsapp = State()
    wait_for_category_emoji = State()
    wait_for_panel_emoji_id = State()
    wait_for_emoji_slot = State()

# ==============================================================================
# 7. KEYBOARDS
# ==============================================================================
def get_category_emoji(category: str) -> str:
    slot_map = {
        "ANDROID NON ROOT PANEL": "category_android_non_root",
        "ANDROID ROOT PANEL": "category_android_root",
        "IPHONE PANEL": "category_iphone",
        "PC PANEL": "category_pc",
    }
    slot = slot_map.get(category)
    if slot:
        return get_emoji_icon(slot, DEFAULT_EMOJIS.get(slot, ""))
    return ""

def get_panel_emoji(panel_name: str) -> str:
    stored = get_setting(f"panel_emoji_{panel_name}", "")
    if stored and stored.isdigit():
        return stored
    return get_emoji_icon("product_store")

def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Verify Contact", request_contact=True)]], 
        resize_keyboard=True, 
        one_time_keyboard=True
    )

def main_menu_kb(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    sys_status = status_check[0] if status_check else 'ON'
    vip_sys_check = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    vip_system = vip_sys_check[0] if vip_sys_check else 'OFF'
    
    is_reseller = False
    if user_id:
        user_check = db_query("SELECT is_reseller FROM users WHERE user_id=?", (user_id,), fetchone=True)
        if user_check:
            is_reseller = bool(user_check[0])

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Buy Key", callback_data="menu_shop",
            icon_custom_emoji_id=get_emoji_icon("product_store"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="My Profile", callback_data="menu_profile",
            icon_custom_emoji_id=get_emoji_icon("profile"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Add Balance", callback_data="menu_add_balance",
            icon_custom_emoji_id=get_emoji_icon("add_balance"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="All History", callback_data="menu_orders",
            icon_custom_emoji_id=get_emoji_icon("history"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Referral", callback_data="menu_referral",
            icon_custom_emoji_id=get_emoji_icon("referral"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="How To Use Bot", callback_data="menu_how_to",
            icon_custom_emoji_id=get_emoji_icon("tutorial"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Support", callback_data="menu_support",
            icon_custom_emoji_id=get_emoji_icon("support"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Ludo Spin", callback_data="menu_spin_landing",
            icon_custom_emoji_id=get_emoji_icon("ludo_spin"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Download Files", callback_data="menu_all_files",
            icon_custom_emoji_id=get_emoji_icon("download"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Selling Proof", callback_data="menu_selling_proof",
            icon_custom_emoji_id=get_emoji_icon("sagarproof"),
            style="success"
        )
    ])
    
    extras_row = []
    if sys_status == 'ON' or is_reseller:
        extras_row.append(InlineKeyboardButton(
            text="Reseller Panel", callback_data="menu_reseller_dash",
            icon_custom_emoji_id=get_emoji_icon("reseller"),
            style="success"
        ))
    if vip_system == 'ON':
        extras_row.append(InlineKeyboardButton(
            text="VIP Club", callback_data="menu_vip_dash",
            style="success"
        ))
    if extras_row:
        kb.inline_keyboard.append(extras_row)
        
    return kb

def back_kb(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="BACK", callback_data=callback,
                icon_custom_emoji_id=get_emoji_icon("back"),
                style="danger"
            )
        ]]
    )

def admin_kb() -> InlineKeyboardMarkup:
    status = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
    status_val = status[0] if status else 'ON'
    vip_status = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    vip_val = vip_status[0] if vip_status else 'OFF'
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Bot Statistics", callback_data="admin_view_stats", style="success")],
        [
            InlineKeyboardButton(text=f"FamPay: {'🟢 ON' if get_setting('gateway_fampay_enabled', 'ON') == 'ON' else '🔴 OFF'}", callback_data="admin_toggle_fampay", style="success" if get_setting('gateway_fampay_enabled', 'ON') == 'ON' else "danger"),
            InlineKeyboardButton(text=f"ZapUPI: {'🟢 ON' if get_setting('gateway_zapupi_enabled', 'ON') == 'ON' else '🔴 OFF'}", callback_data="admin_toggle_zapupi", style="success" if get_setting('gateway_zapupi_enabled', 'ON') == 'ON' else "danger")
        ],
        [InlineKeyboardButton(text="👥 User Control Panel", callback_data="admin_user_control_start", style="success")],
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="admin_add_prod", style="success"),
            InlineKeyboardButton(text="📦 Manage Products", callback_data="admin_manage_prods", style="success")
        ],
        [InlineKeyboardButton(text="🛠 Product Maintenance", callback_data="admin_product_maintenance", style="danger")],
        [InlineKeyboardButton(text="🎬 Set Product Demo", callback_data="admin_set_product_demo", style="success")],
        [
            InlineKeyboardButton(text="👑 Reseller Mgmt", callback_data="admin_reseller_menu", style="success"),
            InlineKeyboardButton(text="🎰 Spin Settings", callback_data="admin_spin_menu", style="success")
        ],
        [
            InlineKeyboardButton(text="🎟 Create Coupon", callback_data="admin_create_coupon", style="success"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast_btn", style="success")
        ],
        [
            InlineKeyboardButton(text="🎫 View Tickets", callback_data="admin_view_tickets", style="success"),
            InlineKeyboardButton(text="📹 Tutorial Video", callback_data="admin_set_video", style="success")
        ],
        [
            InlineKeyboardButton(text="🔗 All Files Link", callback_data="admin_set_all_files", style="success"),
            InlineKeyboardButton(text="🧾 Selling Proof Link", callback_data="admin_set_selling_proof", style="success")
        ],
        [
            InlineKeyboardButton(text="🎨 Edit All Emojis", callback_data="admin_edit_emojis", style="success")
        ],
        [
            InlineKeyboardButton(text="⚙️ FamPay Setup", callback_data="admin_setup_fampay", style="success"),
            InlineKeyboardButton(text="🔐 ZapUPI API Setup", callback_data="admin_setup_zapupi", style="success")
        ],
        [InlineKeyboardButton(text="🪙 Binance Setup", callback_data="admin_setup_binance", style="success")],
        [
            InlineKeyboardButton(text="✏️ Edit UI Texts", callback_data="admin_edit_ui_menu", style="success"),
            InlineKeyboardButton(text="📝 Edit Reseller Price", callback_data="admin_edit_reseller_price", style="success")
        ],
        [
            InlineKeyboardButton(text="💰 Reseller Fee", callback_data="admin_set_reseller_fee", style="success"),
            InlineKeyboardButton(text="💳 Min Balance", callback_data="admin_set_reseller_min", style="success")
        ],
        [
            InlineKeyboardButton(text="🔑 Reseller API Key", callback_data="admin_set_reseller_api_key", style="success"),
            InlineKeyboardButton(text="🌐 Reseller API URL", callback_data="admin_set_reseller_api_url", style="success")
        ],
        [
            InlineKeyboardButton(text="📞 Set Support Links", callback_data="admin_set_support_links", style="success"),
            InlineKeyboardButton(text="🎨 Set Category Emojis", callback_data="admin_set_category_emojis", style="success")
        ],
        [
            InlineKeyboardButton(text="🖼 Set Panel Emojis", callback_data="admin_set_panel_emojis", style="success")
        ],
        [
            InlineKeyboardButton(
                text=f"Bot Status: {status_val} {'🟢' if status_val == 'ON' else '🔴'}",
                callback_data="admin_toggle_bot",
                style="success" if status_val == 'ON' else "danger"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"VIP System: {vip_val} {'🟢' if vip_val == 'ON' else '🔴'}",
                callback_data="admin_toggle_vip_sys",
                style="success" if vip_val == 'ON' else "danger"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🆕 New User Notification: {get_setting('new_user_start_message', 'ON')} {'🟢' if str(get_setting('new_user_start_message', 'ON')).upper() == 'ON' else '🔴'}",
                callback_data="admin_toggle_new_user_notification",
                style="success" if str(get_setting('new_user_start_message', 'ON')).upper() == 'ON' else "danger"
            )
        ]
    ])
    return kb

def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Back to Admin", callback_data="admin_panel_back",
            icon_custom_emoji_id=get_emoji_icon("back"),
            style="danger"
        )
    ]])

# ==============================================================================
# 8. NOTIFICATIONS
# ==============================================================================
async def send_advanced_notification(user_id: int, notif_type: str, amount: float, product: str = None, key: str = None, gateway: str = "FamPay") -> None:
    user_info = db_query("SELECT first_name, phone, username, is_reseller, is_vip FROM users WHERE user_id=?", (user_id,), fetchone=True)
    
    name = user_info[0] if user_info else "Unknown"
    phone = user_info[1] if user_info and user_info[1] else "Not Provided"
    username = f"@{user_info[2]}" if user_info and user_info[2] else "None"
    
    tags = []
    if user_info and user_info[3]: tags.append("👑 Reseller")
    if user_info and user_info[4]: tags.append("🌟 VIP")
    tag_str = " | ".join(tags) if tags else "👤 Regular"
        
    time_now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    
    if notif_type == "ORDER":
        title = "🛒 <b>NEW ORDER PROCESSED!</b> 🛒"
        details = (f"📦 <b>Product:</b> {product}\n🔑 <b>Key:</b> <code>{key}</code>\n💰 <b>Amount Paid:</b> ₹{amount:.2f}\n📅 <b>Time:</b> {time_now}")
    else:
        title = "💰 <b>NEW WALLET DEPOSIT!</b> 💰"
        details = (f"💵 <b>Amount Added:</b> ₹{amount:.2f}\n🧾 <b>Gateway:</b> {gateway}\n🆔 <b>Reference:</b> <code>{product}</code>\n📅 <b>Time:</b> {time_now}")

    msg = f"{title}\n━━━━━━━━━━━━━━━━━━\n👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{user_id}</code>\n📱 <b>Phone:</b> {phone}\n🔗 <b>Username:</b> {username}\n🏷 <b>Status:</b> {tag_str}\n━━━━━━━━━━━━━━━━━━\n{details}"
    try: 
        await bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
    except Exception as e: 
        logger.error(f"Failed to send admin notification: {e}")

# ==============================================================================
# 9. FAMPAY PAYMENT FUNCTIONS
# ==============================================================================

async def generate_fampay_qr(user_id: int, amount: float, upi_id: str = None) -> Dict[str, Any]:
    """Generate a FamGateway QR and return its QR URL + gateway order ID."""
    api_key = get_setting("fampay_api_key", FAMPAY_API_KEY)
    if not api_key or api_key == "YOUR_FAMPAY_API_KEY":
        return {"status": "error", "message": "FamGateway API key not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                FAMPAY_QR_URL,
                params={
                    "api_key": api_key,
                    "amount": f"{float(amount):.2f}",
                    "customer_name": f"Telegram User {user_id}",
                },
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                raw = await resp.text()
                try:
                    result = await resp.json(content_type=None)
                except Exception:
                    logger.error("FamGateway QR returned non-JSON: %s", raw[:1000])
                    return {"status": "error", "message": "Invalid FamGateway QR response"}

                if resp.status != 200:
                    return {
                        "status": "error",
                        "message": result.get("message") or f"FamGateway HTTP {resp.status}",
                    }

                if str(result.get("status", "")).lower() != "success":
                    return {
                        "status": "error",
                        "message": result.get("message") or "FamGateway QR generation failed",
                    }

                data = result.get("data") or {}
                qr_url = data.get("qr_url")
                gateway_order = data.get("order_id")

                if not qr_url:
                    return {"status": "error", "message": "FamGateway did not return a QR URL"}
                if not gateway_order:
                    return {"status": "error", "message": "FamGateway did not return an order ID"}

                # Normalize to the structure already used by SAGAR SHOP.py.
                return {
                    "status": "success",
                    "data": {
                        **data,
                        "qr_url": qr_url,
                        "order_id": gateway_order,
                        "upi_id": data.get("upi_id") or upi_id or get_setting("fampay_upi_id", ""),
                    },
                }
    except Exception as e:
        logger.exception("FamGateway QR generation error")
        return {"status": "error", "message": str(e)}


async def verify_fampay_payment(order_id: str) -> Dict[str, Any]:
    """Verify a FamGateway payment using the authoritative order endpoint,
    then the public checkout-status endpoint as a fallback."""
    api_key = get_setting("fampay_api_key", FAMPAY_API_KEY)
    order_id = str(order_id or "").strip()

    if not api_key or api_key == "YOUR_FAMPAY_API_KEY":
        return {"status": "error", "message": "FamGateway API key not configured"}
    if not order_id:
        return {"status": "error", "message": "Order ID is missing"}

    def is_success(data):
        if not isinstance(data, dict):
            return False
        status = str(data.get("status", "")).strip().lower()
        if status in ("success", "paid", "completed", "confirmed"):
            return True
        d = data.get("data")
        if isinstance(d, dict):
            dstatus = str(d.get("status", "")).strip().lower()
            if dstatus in ("success", "paid", "completed", "confirmed"):
                return True
            if d.get("is_paid") is True or d.get("paid") is True:
                return True
        return data.get("is_paid") is True or data.get("paid") is True

    def normalize(data):
        if not isinstance(data, dict):
            return {}
        d = data.get("data")
        return d if isinstance(d, dict) else data

    async with aiohttp.ClientSession() as session:
        # 1) Authoritative verification with header API-key authentication.
        try:
            async with session.get(
                FAMPAY_VERIFY_URL,
                params={"order_id": order_id, "_": int(time.time() * 1000)},
                headers={"X-Api-Key": api_key, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                raw = await resp.text()
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None
                if resp.status == 200 and is_success(data):
                    payload = normalize(data)
                    returned_order = str(
                        payload.get("order_id") or data.get("order_id") or ""
                    ).strip()
                    if not returned_order or returned_order == order_id:
                        return {"status": "success", "data": payload}
        except Exception as e:
            logger.warning("FamGateway header verification error: %s", e)

        # 2) Same verification endpoint with query-string API key.
        try:
            async with session.get(
                FAMPAY_VERIFY_URL,
                params={
                    "api_key": api_key,
                    "order_id": order_id,
                    "_": int(time.time() * 1000),
                },
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None
                if resp.status == 200 and is_success(data):
                    payload = normalize(data)
                    returned_order = str(
                        payload.get("order_id") or data.get("order_id") or ""
                    ).strip()
                    if not returned_order or returned_order == order_id:
                        return {"status": "success", "data": payload}
        except Exception as e:
            logger.warning("FamGateway query verification error: %s", e)

        # 3) Public checkout-status fallback.
        try:
            async with session.get(
                FAMPAY_STATUS_URL,
                params={"order_id": order_id, "_": int(time.time() * 1000)},
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None
                if resp.status == 200 and is_success(data):
                    payload = normalize(data)
                    returned_order = str(
                        payload.get("order_id") or data.get("order_id") or ""
                    ).strip()
                    if not returned_order or returned_order == order_id:
                        return {"status": "success", "data": payload}
        except Exception as e:
            logger.warning("FamGateway checkout-status verification error: %s", e)

    return {
        "status": "pending",
        "message": "Payment not verified yet. Complete payment and wait for automatic verification.",
    }


async def run_payment_verification(user_id: int, order_id: str, reply_target: Any) -> None:
    """Run payment verification with FamPay."""
    txn = db_query("SELECT amount_inr, status, timestamp, qr_url, upi_id, expires_at FROM transactions WHERE order_id=?", (order_id,), fetchone=True)
    if not txn:
        err = "❌ Invalid or Fake Order ID detected in system!"
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(err, show_alert=True)
        else: await reply_target.answer(err)
        return
    
    if txn[1] == 'paid':
        msg = "✅ This payment has already been securely credited to your wallet."
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    elif txn[1] == 'expired':
        msg = "❌ This order has expired. Please create a new deposit request."
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    
    # Verify with FamGateway; retry briefly so just-settled payments are detected.
    result = await verify_fampay_payment(order_id)
    for _ in range(4):
        if result.get("status") == "success":
            break
        await asyncio.sleep(1)
        result = await verify_fampay_payment(order_id)
    
    if result.get("status") == "success":
        # Keep legacy/deep-link verification safe too: the same atomic credit path
        # used by the background verifier prevents double balance crediting.
        txn_data = result.get("data", {})
        credited = await _credit_verified_transaction(order_id, txn[0], user_id, txn_data, "FamPay")
        if not credited:
            msg = "✅ This payment has already been securely credited to your wallet."
            if isinstance(reply_target, CallbackQuery):
                await reply_target.answer(msg, show_alert=True)
            else:
                await reply_target.answer(msg)
        elif isinstance(reply_target, CallbackQuery):
            try:
                await reply_target.answer("✅ Payment verified automatically.")
            except Exception:
                pass
        return
    elif result.get("status") == "error":
        # Check if transaction failed specifically
        error_msg = result.get("message", "Payment not received yet")
        if "Transaction failed" in error_msg or "not received" in error_msg:
            fail_msg = f"❌ {error_msg}\n\n<i>Please make sure you sent the exact amount to the correct UPI ID.</i>"
            if isinstance(reply_target, CallbackQuery): await reply_target.answer(fail_msg, show_alert=True)
            else: await reply_target.answer(fail_msg)
        else:
            # Still pending - show QR again with status
            pending_msg = f"⏳ <b>Payment Status: PENDING</b>\n\n{error_msg}\n\n<i>Please wait a moment and verify again.</i>"
            if isinstance(reply_target, CallbackQuery): await reply_target.answer(pending_msg, show_alert=True)
            else: await reply_target.answer(pending_msg)
    else:
        err = f"⚠️ Gateway Error: {result.get('message', 'Unknown Error')}"
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(err, show_alert=True)
        else: await reply_target.answer(err)

async def _delete_payment_qr_message(user_id: int, order_id: str = None) -> None:
    """Delete the Telegram QR/payment message after success or expiry."""
    try:
        if order_id:
            row = db_query("SELECT qr_message_id FROM transactions WHERE order_id=? AND user_id=?", (order_id, user_id), fetchone=True)
            message_id = row[0] if row and row[0] else None
        else:
            row = db_query("SELECT qr_message_id FROM transactions WHERE user_id=? AND status='pending' ORDER BY timestamp DESC LIMIT 1", (user_id,), fetchone=True)
            message_id = row[0] if row and row[0] else None
        if message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=int(message_id))
            except Exception:
                pass
        # Backward compatibility with older records that only stored this setting.
        legacy = get_setting(f"qr_msg_{user_id}", "")
        if legacy and (not message_id or str(legacy) != str(message_id)):
            try:
                await bot.delete_message(chat_id=user_id, message_id=int(legacy))
            except Exception:
                pass
        set_setting(f"qr_msg_{user_id}", "")
    except Exception:
        logger.exception("Failed to delete payment QR message for user %s", user_id)


def _claim_paid_transaction(order_id: str) -> bool:
    """Atomically claim a pending order so balance is credited only once."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE transactions SET status='paid' WHERE order_id=? AND status='pending'", (order_id,))
        changed = cur.rowcount == 1
        if changed:
            conn.commit()
        else:
            conn.rollback()
        return changed
    except Exception:
        conn.rollback()
        logger.exception("Atomic payment claim failed for order %s", order_id)
        return False
    finally:
        conn.close()


async def _credit_verified_transaction(order_id: str, fallback_amount: float, user_id: int, txn_data: dict, source: str = "FamPay") -> bool:
    """Credit a verified transaction exactly once, notify admin/user, and remove QR."""
    if not _claim_paid_transaction(order_id):
        return False

    amount_received = safe_float(txn_data.get("amount"), safe_float(fallback_amount, 0.0))
    utr = txn_data.get("utr") or txn_data.get("transaction_id") or "N/A"
    sender_name = txn_data.get("sender_name") or "Unknown"
    payment_time = txn_data.get("payment_time_ist") or datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

    db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount_received, user_id))
    await _delete_payment_qr_message(user_id, order_id)

    pending_product = get_setting(f"pending_product_purchase_{user_id}", "").strip()
    try:
        if pending_product.isdigit():
            await bot.send_message(
                user_id,
                f"🎉 <b>PAYMENT SUCCESSFUL!</b>\n\n"
                f"✅ <b>{fmt_curr(amount_received)}</b> credited. Continuing your product order now...\n"
                f"🧾 UTR: <code>{html_lib.escape(str(utr))}</code>",
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                user_id,
                f"🎉 <b>PAYMENT SUCCESSFUL!</b>\n\n"
                f"✅ <b>{fmt_curr(amount_received)}</b> has been added to your wallet.\n"
                f"🧾 UTR: <code>{html_lib.escape(str(utr))}</code>\n"
                f"👤 Sender: {html_lib.escape(str(sender_name))}\n"
                f"📅 Time: {html_lib.escape(str(payment_time))}",
                reply_markup=main_menu_kb(user_id),
                parse_mode='HTML'
            )
    except Exception:
        pass

    # Resume the exact product checkout that initiated this top-up.
    # A lightweight adapter lets the existing purchase routine use a fresh
    # message, while preserving its normal stock/API/charge checks.
    if pending_product.isdigit():
        set_setting(f"pending_product_purchase_{user_id}", "")
        try:
            class _ResumeMessage:
                def __init__(self, chat_id):
                    self.chat = type("Chat", (), {"id": chat_id})()
                async def edit_text(self, text, **kwargs):
                    return await bot.send_message(user_id, text, **kwargs)
                async def answer(self, text, **kwargs):
                    return await bot.send_message(user_id, text, **kwargs)
            class _ResumeCall:
                def __init__(self, uid, product_id):
                    self.from_user = type("User", (), {"id": uid})()
                    self.data = f"buy_{product_id}"
                    self.message = _ResumeMessage(uid)
                async def answer(self, text="", **kwargs):
                    return None
            await _process_buy(_ResumeCall(user_id, int(pending_product)))
        except Exception:
            logger.exception("Could not resume automatic product purchase for user %s", user_id)
            await bot.send_message(
                user_id,
                "⚠️ Payment received and balance credited, but automatic delivery could not finish. Open Buy Key and tap the same product once; your balance is saved.",
                reply_markup=main_menu_kb(user_id)
            )

    await send_advanced_notification(user_id, "DEPOSIT", amount_received, product=utr, gateway=source)
    log_activity(user_id, "DEPOSIT_AUTO_SUCCESS", f"Amount: {amount_received}, Gateway: {source}, Order: {order_id}, UTR: {utr}")
    return True


async def auto_verify_task() -> None:
    """Fast automatic FamGateway verifier. No Verify Payment button is required."""
    await asyncio.sleep(1)
    while True:
        try:
            api_key = get_setting("fampay_api_key", "")
            zap_key = get_setting("zapupi_zap_key", "").strip()
            if (api_key and api_key != "YOUR_FAMPAY_API_KEY") or zap_key:
                pending_txns = db_query(
                    "SELECT order_id, user_id, amount_inr, timestamp, expires_at FROM transactions WHERE status='pending' ORDER BY timestamp ASC",
                    fetchall=True
                ) or []
                for order_id, user_id, amount, ts, expires_at in pending_txns:
                    # Always ask the gateway first; this avoids expiring a payment that settled near the deadline.
                    is_zapupi = str(order_id).startswith("ZAPUPI")
                    if is_zapupi and zap_key:
                        result = await verify_zapupi_payment(order_id)
                    elif not is_zapupi and api_key and api_key != "YOUR_FAMPAY_API_KEY":
                        result = await verify_fampay_payment(order_id)
                    else:
                        result = {"status": "pending"}
                    if result.get("status") == "success":
                        await _credit_verified_transaction(order_id, amount, user_id, result.get("data") or {}, "ZapUPI Auto" if is_zapupi else "FamPay Auto")
                        continue

                    if expires_at and time.time() > float(expires_at):
                        # Mark expired only if it is still pending, preventing a race with a successful verifier.
                        conn = sqlite3.connect(DB_PATH, timeout=30)
                        try:
                            cur = conn.cursor()
                            cur.execute("UPDATE transactions SET status='expired' WHERE order_id=? AND status='pending'", (order_id,))
                            expired_now = cur.rowcount == 1
                            conn.commit()
                        finally:
                            conn.close()
                        if expired_now:
                            await _delete_payment_qr_message(user_id, order_id)
                            try:
                                minutes = max(1, int(round((float(expires_at) - float(ts)) / 60))) if expires_at else 5
                            except Exception:
                                minutes = 5
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"⏳ <b>QR Code Expired!</b>\nYour {minutes}-minute payment window for order <code>{order_id}</code> has timed out. Please generate a new QR code.",
                                    parse_mode='HTML'
                                )
                            except Exception:
                                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("FamPay fast auto-verifier sweep failed")

        # ~1 second polling gives fast activation while still yielding to the event loop.
        await asyncio.sleep(1)

# ==============================================================================
# 10. ONBOARDING & START
# ==============================================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    try:
        await message.answer_sticker(WELCOME_STICKER_ID)
    except Exception:
        pass

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("v_"):
        order_id = args[1].split("v_", 1)[1]
        msg = await message.answer(
            "🔄 <b>Verifying your payment securely...</b>\n<i>Connecting to gateway...</i>",
            parse_mode='HTML'
        )
        await run_payment_verification(message.from_user.id, order_id, msg)
        return

    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].split("_", 1)[1])
        except Exception:
            referred_by = None

    user_id = message.from_user.id
    current_username = message.from_user.username or ""
    existing = db_query(
        "SELECT phone, first_name, username FROM users WHERE user_id=?",
        (user_id,),
        fetchone=True
    )

    is_new_user = not existing
    phone_verified = bool(existing and existing[0])

    if is_new_user:
        db_query(
            "INSERT OR IGNORE INTO users "
            "(user_id, first_name, username, referred_by, joined_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                message.from_user.first_name or "",
                current_username,
                referred_by,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        log_activity(user_id, "ACCOUNT_CREATED")

        # New-user notification is sent directly from /start, independently
        # of contact verification, so a later handler error cannot suppress it.
        if new_user_start_message_enabled():
            username = f"@{current_username}" if current_username else "Not set"
            joined_at = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            admin_msg = (
                "🆕 <b>NEW USER STARTED THE BOT</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {html_lib.escape(message.from_user.first_name or 'User')}\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🔗 <b>Username:</b> {html_lib.escape(username)}\n"
                "📱 <b>Phone:</b> Not verified yet\n"
                f"📅 <b>Joined:</b> {joined_at}"
            )
            try:
                await bot.send_message(ADMIN_ID, admin_msg, parse_mode='HTML')
                log_activity(user_id, "NEW_USER_ADMIN_NOTIFICATION_SENT")
            except Exception:
                logger.exception("New user notification failed for user %s", user_id)
    else:
        db_query(
            "UPDATE users SET first_name=?, username=? WHERE user_id=?",
            (message.from_user.first_name or "", current_username, user_id)
        )
        log_activity(user_id, "CMD_START")

    if not phone_verified:
        await message.answer(
            "<b>🛡 VERIFICATION REQUIRED</b>\n\n"
            "To safeguard your orders and account, we need to verify your contact.\n"
            "👇 <b>Tap the button below once:</b>",
            parse_mode='HTML',
            reply_markup=contact_kb()
        )
        return

    await send_main_menu(message)


@dp.message(F.contact)
async def handle_contact(message: Message):
    contact = message.contact
    user_id = message.from_user.id

    # Accept only the user's own Telegram contact.
    if contact.user_id is not None and contact.user_id != user_id:
        await message.answer(
            "❌ <b>Security Alert:</b> Please share your OWN contact using the button.",
            parse_mode='HTML',
            reply_markup=contact_kb()
        )
        return

    phone = (contact.phone_number or "").strip()
    if not phone:
        await message.answer(
            "❌ Phone number was not received. Please tap <b>📱 Verify Contact</b> again.",
            parse_mode='HTML',
            reply_markup=contact_kb()
        )
        return

    existing = db_query(
        "SELECT phone, referred_by FROM users WHERE user_id=?",
        (user_id,),
        fetchone=True
    )

    # Ensure the user row exists before saving verification.
    if not existing:
        db_query(
            "INSERT OR IGNORE INTO users "
            "(user_id, first_name, username, joined_date) VALUES (?, ?, ?, ?)",
            (
                user_id,
                message.from_user.first_name or "",
                message.from_user.username or "",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        existing = db_query(
            "SELECT phone, referred_by FROM users WHERE user_id=?",
            (user_id,),
            fetchone=True
        )

    was_missing = not existing or not existing[0]
    referrer_id = existing[1] if existing and len(existing) > 1 else None

    # Save the phone BEFORE showing the main menu. This prevents /start from
    # asking for contact verification again.
    db_query(
        "UPDATE users SET phone=?, first_name=?, username=? WHERE user_id=?",
        (
            phone,
            message.from_user.first_name or "",
            message.from_user.username or "",
            user_id
        )
    )

    # IMPORTANT: Notify admin immediately when a NEW user shares their contact.
    # The notification reads the phone directly from the saved DB value, so
    # admin sees the actual number instead of "Not verified yet".
    if was_missing and new_user_start_message_enabled():
        try:
            admin_name = html_lib.escape(message.from_user.first_name or "User")
            admin_username = (
                f"@{html_lib.escape(message.from_user.username)}"
                if message.from_user.username else "Not set"
            )
            contact_time = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            contact_notification = (
                "📱 <b>NEW USER CONTACT VERIFIED</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {admin_name}\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🔗 <b>Username:</b> {admin_username}\n"
                f"📞 <b>Phone Number:</b> <code>{html_lib.escape(phone)}</code>\n"
                "✅ <b>Status:</b> Contact shared successfully\n"
                f"📅 <b>Time:</b> {contact_time}"
            )
            await bot.send_message(
                ADMIN_ID,
                contact_notification,
                parse_mode='HTML'
            )
            log_activity(
                user_id,
                "NEW_USER_CONTACT_ADMIN_NOTIFICATION_SENT",
                f"Phone: {phone}"
            )
        except Exception:
            logger.exception(
                "New-user contact notification failed for user %s",
                user_id
            )

    if referrer_id and was_missing and referrer_id != user_id:
        db_query(
            "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id=?",
            (referrer_id,)
        )
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 <b>Referral Success!</b>\n"
                f"User <b>{html_lib.escape(message.from_user.first_name or 'User')}</b> "
                "joined using your link!",
                parse_mode='HTML'
            )
        except Exception:
            pass

    log_activity(user_id, "CONTACT_VERIFIED", f"Phone: {phone}")

    try:
        await message.answer(
            "✅ <b>Contact verification successful!</b>\n\n"
            "Welcome to HASAN OFFICIAL PANEL STORE Your account is now verified.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
    except Exception:
        pass

    await send_main_menu(message)


async def send_main_menu(ctx: Any, user_id: Optional[int] = None):
    # Callback message.from_user is the bot, not the person who pressed the button.
    # Accept the real Telegram user ID explicitly for callback-driven menu returns.
    user_id = user_id if user_id is not None else ctx.from_user.id
    u = db_query(
        "SELECT user_id, first_name, account_type, balance, orders_count, spent, "
        "referrals_count, joined_date, is_reseller, reseller_since, total_saved, is_vip "
        "FROM users WHERE user_id=?",
        (user_id,),
        fetchone=True
    )

    if not u:
        u = (
            user_id, ctx.from_user.first_name or "", "Regular", 0.0,
            0, 0.0, 0, "", 0, "", 0.0, 0
        )

    text = get_ui_text("start_menu", u=u)
    kb = main_menu_kb(user_id)

    if isinstance(ctx, Message):
        await ctx.answer(text, reply_markup=kb, parse_mode='HTML')
    else:
        await ctx.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    # Photo captions cannot be converted to the text-based start menu reliably.
    # Remove the old payment/cancel post, then send a fresh main menu message.
    await state.clear()
    log_activity(call.from_user.id, "RETURN_MAIN_MENU")
    try:
        await call.message.delete()
    except Exception:
        pass
    await send_main_menu(call.message, user_id=call.from_user.id)
    try:
        await call.answer()
    except Exception:
        pass

# ==============================================================================
# 11. ADD BALANCE
# ==============================================================================
@dp.callback_query(F.data == "menu_add_balance")
async def select_gateway_menu(call: CallbackQuery):
    log_activity(call.from_user.id, "VIEW_ADD_BALANCE")
    text = get_ui_text("add_balance_menu")
    gateway_rows = []
    fampay_on = get_setting("gateway_fampay_enabled", "ON") == "ON" and bool(get_setting("fampay_api_key", "")) and get_setting("fampay_api_key", "") != "YOUR_FAMPAY_API_KEY"
    zapupi_on = get_setting("gateway_zapupi_enabled", "ON") == "ON" and bool(get_setting("zapupi_zap_key", "").strip())
    if fampay_on:
        gateway_rows.append([InlineKeyboardButton(text="UPI PAY (FamPay)", callback_data="gateway_inr", icon_custom_emoji_id=get_emoji_icon("upi"), style="primary")])
    if zapupi_on:
        gateway_rows.append([InlineKeyboardButton(text="ZAPUPI PAY", callback_data="gateway_zapupi", style="success")])
    if not gateway_rows:
        gateway_rows.append([InlineKeyboardButton(text="⚠️ Payment Gateway Not Configured", callback_data="menu_add_balance", style="danger")])
    # Custom amount is gateway-specific and is available inside the ZapUPI menu,
    # not on the main Add Balance screen.
    gateway_rows.extend([
        [InlineKeyboardButton(text="BINANCE PAY", callback_data="gateway_crypto", icon_custom_emoji_id=get_emoji_icon("binance"), style="primary")],
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=gateway_rows)
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

# ==============================================================================
# 12. FAMPAY UPI PAYMENT FLOW
# ==============================================================================
@dp.callback_query(F.data == "gateway_inr")
async def add_balance_inr(call: CallbackQuery):
    if get_setting("gateway_fampay_enabled", "ON") != "ON":
        return await call.answer("FamPay gateway is OFF.", show_alert=True)
    text = f"💵 <b>— FAMPAY UPI DEPOSIT —</b> 💵\n\nSelect amount to deposit:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹50", callback_data="pay_50", style="primary"), InlineKeyboardButton(text="₹100", callback_data="pay_100", style="primary")],
        [InlineKeyboardButton(text="₹200", callback_data="pay_200", style="primary"), InlineKeyboardButton(text="₹500", callback_data="pay_500", style="primary")],
        [InlineKeyboardButton(text="₹1000", callback_data="pay_1000", style="primary"), InlineKeyboardButton(text="₹2000", callback_data="pay_2000", style="primary")],
        [InlineKeyboardButton(text="✏️ Custom Amount", callback_data="custom_deposit_keypad", style="primary")],
        [InlineKeyboardButton(text="Back", callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "gateway_zapupi")
async def zapupi_amount_menu(call: CallbackQuery):
    if get_setting("gateway_zapupi_enabled", "ON") != "ON":
        return await call.answer("ZapUPI gateway is OFF.", show_alert=True)
    if not get_setting("zapupi_zap_key", "").strip():
        return await call.answer("ZapUPI API Key admin ne abhi set nahi ki hai.", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹50", callback_data="zap_pay_50", style="primary"), InlineKeyboardButton(text="₹100", callback_data="zap_pay_100", style="primary")],
        [InlineKeyboardButton(text="₹200", callback_data="zap_pay_200", style="primary"), InlineKeyboardButton(text="₹500", callback_data="zap_pay_500", style="primary")],
        [InlineKeyboardButton(text="₹1000", callback_data="zap_pay_1000", style="primary"), InlineKeyboardButton(text="₹2000", callback_data="zap_pay_2000", style="primary")],
        [InlineKeyboardButton(text="✏️ CUSTOM AMOUNT", callback_data="custom_zapupi_keypad", style="success")],
        [InlineKeyboardButton(text="❌ CANCEL / BACK", callback_data="menu_add_balance", style="danger")]
    ])
    await call.message.edit_text("🏦 <b>ZAPUPI DEPOSIT</b>\n\nPayment amount select karein:", reply_markup=kb, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("zap_pay_"))
async def zapupi_pay_amount(call: CallbackQuery):
    try:
        amount = float(call.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        return await call.answer("Invalid amount.", show_alert=True)
    await call.message.edit_text("⏳ <b>ZapUPI payment link generate ho raha hai...</b>", parse_mode="HTML")
    await generate_zapupi_order(call.from_user.id, amount, call.message)
    await call.answer()

async def generate_zapupi_order(user_id: int, amount: float, message_obj: Message) -> None:
    """Create a ZapUPI order and show the payment link; auto-verifier credits only confirmed payments."""
    key = get_setting("zapupi_zap_key", "").strip()
    if not key:
        return await message_obj.edit_text("⚠️ Admin ko Admin Panel → ZapUPI API Setup mein Zap Key set karni hogi.", reply_markup=back_kb("gateway_zapupi"), parse_mode="HTML")
    order_id = f"ZAPUPI{user_id}{int(time.time())}"
    payload = {"zap_key": key, "amount": str(round(float(amount), 2)), "order_id": order_id, "remark": f"Wallet Deposit | UID {user_id}"}
    base = get_setting("webhook_base_url", "").strip()
    if base:
        payload.update({"success_url": base.rstrip('/') + "/zapupi/success", "failed_url": base.rstrip('/') + "/zapupi/failed", "timeout_url": base.rstrip('/') + "/zapupi/timeout", "webhook_url": base.rstrip('/') + "/zapupi/webhook"})
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://pay.zapupi.com/api/create-order", json=payload) as resp:
                raw = await resp.text()
                try: data = json.loads(raw)
                except Exception: data = {}
        set_setting("zapupi_debug_last_create", raw[:1500])
        payment_url = data.get("payment_url") if isinstance(data, dict) else None
        if not isinstance(data, dict) or str(data.get("status", "")).lower() != "success" or not payment_url:
            err = data.get("message", "ZapUPI ne valid payment link return nahi kiya.") if isinstance(data, dict) else "Invalid ZapUPI response"
            return await message_obj.edit_text(f"❌ <b>ZapUPI order create nahi hua.</b>\n\n<code>{html_lib.escape(str(err))}</code>", reply_markup=back_kb("gateway_zapupi"), parse_mode="HTML")
        expires_at = int(time.time()) + 300
        db_query("INSERT OR REPLACE INTO transactions (order_id,user_id,amount_inr,status,timestamp,qr_url,upi_id,expires_at) VALUES (?,?,?,'pending',?,?,?,?)", (order_id, user_id, float(amount), int(time.time()), payment_url, "ZapUPI", expires_at))
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Pay Now — ZapUPI", url=payment_url, style="success")],
            [InlineKeyboardButton(text="❌ Cancel Payment", callback_data=f"cancel_payment_{order_id}", style="danger")]
        ])
        caption = (f"🏦 <b>ZAPUPI PAYMENT</b>\n\n💰 <b>Amount:</b> {fmt_curr(amount)}\n🧾 <b>Order ID:</b> <code>{order_id}</code>\n⏳ <b>Expires:</b> 5 minutes\n\nPay using the button above. Payment is checked automatically; balance is added only after ZapUPI confirms success.")
        await message_obj.delete()
        sent = await bot.send_message(user_id, caption, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        db_query("UPDATE transactions SET qr_message_id=? WHERE order_id=? AND user_id=?", (sent.message_id, order_id, user_id))
        set_setting(f"qr_msg_{user_id}", str(sent.message_id))
        log_activity(user_id, "GENERATE_ZAPUPI_ORDER", f"Amount: {amount}, Order ID: {order_id}")
    except Exception as e:
        logger.exception("ZapUPI order creation failed")
        try: await message_obj.edit_text(f"❌ <b>ZapUPI error:</b>\n<code>{html_lib.escape(str(e))}</code>", reply_markup=back_kb("gateway_zapupi"), parse_mode="HTML")
        except Exception: pass

async def verify_zapupi_payment(order_id: str) -> Dict[str, Any]:
    key = get_setting("zapupi_zap_key", "").strip()
    if not key or not order_id:
        return {"status": "pending", "message": "ZapUPI key/order missing"}
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://pay.zapupi.com/api/order-status", json={"zap_key": key, "order_id": order_id}) as resp:
                raw = await resp.text()
                try: data = json.loads(raw)
                except Exception: data = {}
        set_setting("zapupi_debug_last_check", raw[:1500])
        if isinstance(data, dict) and str(data.get("status", "")).lower() == "success":
            d = data.get("data") or {}
            if isinstance(d, dict) and (str(d.get("status", "")).lower() in ("success", "paid", "completed", "successful") or d.get("paid") is True):
                return {"status": "success", "data": d}
        return {"status": "pending", "message": "Payment not verified yet"}
    except Exception as e:
        set_setting("zapupi_debug_last_check", f"[REQUEST FAILED] {e}")
        return {"status": "pending", "message": str(e)}

@dp.callback_query(F.data.in_({"custom_deposit_keypad", "custom_zapupi_keypad", "custom_any_gateway_keypad"}))
async def show_custom_keypad(call: CallbackQuery, state: FSMContext):
    gateway = "choose" if call.data == "custom_any_gateway_keypad" else ("zapupi" if call.data == "custom_zapupi_keypad" else "fampay")
    await state.set_state(UserStates.custom_amount_input)
    await state.update_data(amount_str="0", payment_gateway=gateway)
    cancel_target = "gateway_zapupi" if gateway == "zapupi" else ("menu_add_balance" if gateway == "choose" else "gateway_inr")
    await show_keypad(call.message, cancel_callback=cancel_target)

async def show_keypad(message: Message, amount_str: str = "0", cancel_callback: str = "gateway_inr"):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="      1      ", callback_data="kp_1", style="primary"), InlineKeyboardButton(text="      2      ", callback_data="kp_2", style="primary"), InlineKeyboardButton(text="      3      ", callback_data="kp_3", style="primary")],
        [InlineKeyboardButton(text="      4      ", callback_data="kp_4", style="primary"), InlineKeyboardButton(text="      5      ", callback_data="kp_5", style="primary"), InlineKeyboardButton(text="      6      ", callback_data="kp_6", style="primary")],
        [InlineKeyboardButton(text="      7      ", callback_data="kp_7", style="primary"), InlineKeyboardButton(text="      8      ", callback_data="kp_8", style="primary"), InlineKeyboardButton(text="      9      ", callback_data="kp_9", style="primary")],
        [InlineKeyboardButton(text="    ⌫    ", callback_data="kp_backspace", style="danger"), InlineKeyboardButton(text="      0      ", callback_data="kp_0", style="primary"), InlineKeyboardButton(text="    C    ", callback_data="kp_clear", style="danger")],
        [InlineKeyboardButton(text=f"✅ Confirm (₹{amount_str})", callback_data="kp_confirm", style="success")],
        [InlineKeyboardButton(text="↩️ Cancel", callback_data=cancel_callback, icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    text = f"💵 <b>Enter Amount (₹):</b>\n\nCurrent: ₹{amount_str}"
    await message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("kp_"), UserStates.custom_amount_input)
async def keypad_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_str = data.get("amount_str", "0")
    action = call.data[len("kp_"):]
    if action == "confirm":
        if amount_str == "0":
            await call.answer("Amount cannot be zero.", show_alert=True)
            return
        try:
            amount = float(amount_str)
            if amount < 1:
                await call.answer("Minimum deposit is ₹1.", show_alert=True)
                return
            gateway = data.get("payment_gateway", "fampay")
            try:
                await call.answer("Processing amount…")
            except Exception:
                pass
            await state.clear()
            if gateway == "choose":
                try: await call.message.delete()
                except Exception: pass
                await start_wallet_payment_gateway_choice(call.from_user.id, amount)
            elif gateway == "zapupi":
                await call.message.edit_text("⏳ <b>Generating ZapUPI payment link...</b>", parse_mode="HTML")
                await generate_zapupi_order(call.from_user.id, amount, call.message)
            else:
                await call.message.edit_text("⏳ <b>Generating Secure QR Code...</b>", parse_mode="HTML")
                await generate_fampay_order(call.from_user.id, amount, call.message)
        except ValueError:
            await call.answer("Invalid amount.", show_alert=True)
        return
    if action == "backspace":
        if len(amount_str) > 1: amount_str = amount_str[:-1]
        else: amount_str = "0"
    elif action == "clear":
        amount_str = "0"
    else:
        if amount_str == "0": amount_str = action
        else: amount_str += action
        if len(amount_str) > 6: amount_str = amount_str[:6]
    await state.update_data(amount_str=amount_str)
    gateway = data.get("payment_gateway", "fampay")
    cancel_target = "gateway_zapupi" if gateway == "zapupi" else ("menu_add_balance" if gateway == "choose" else "gateway_inr")
    await show_keypad(call.message, amount_str, cancel_callback=cancel_target)
    await call.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_fampay_payment_callback(call: CallbackQuery):
    inr_amount = float(call.data.split("_")[1])
    await call.message.edit_text("⏳ <b>Generating Secure QR Code via FamGateway...</b>", parse_mode='HTML')
    await generate_fampay_order(call.from_user.id, inr_amount, call.message)

async def generate_fampay_order(user_id: int, inr_amount: float, message_obj: Message) -> None:
    """Generate FamPay QR and show the QR image directly with Verify/Cancel buttons."""
    api_key = get_setting("fampay_api_key", "")
    if not api_key or api_key == "YOUR_FAMPAY_API_KEY":
        return await message_obj.edit_text(
            "⚠️ FamGateway is currently offline.\nAdmin needs to set the FamGateway API Key.",
            reply_markup=back_kb("gateway_inr"),
            parse_mode="HTML"
        )

    # Admin must configure the receiving UPI ID after saving the API key.
    upi_id = get_setting("fampay_upi_id", "")
    if not upi_id:
        return await message_obj.edit_text(
            "⚠️ UPI ID is not configured.\nAdmin needs to set the UPI ID in FamPay Setup.",
            reply_markup=back_kb("gateway_inr"),
            parse_mode="HTML"
        )

    current_time = int(time.time())
    default_order_id = f"FAMPAY{user_id}{current_time}"

    # FamGateway QR flow from cord.py:
    # https://famgateway.in/api/qr.php?api_key=...&amount=...
    result = await generate_fampay_qr(user_id, inr_amount, upi_id)

    if result.get("status") != "success":
        error_msg = result.get("message", "Unknown error")
        return await message_obj.edit_text(
            f"❌ <b>QR Generation Failed:</b>\n{error_msg}",
            reply_markup=back_kb("gateway_inr"),
            parse_mode="HTML"
        )

    data = result.get("data") or {}
    qr_url = data.get("qr_url")
    order_id = data.get("order_id") or default_order_id
    upi_id = data.get("upi_id") or upi_id
    # Fixed 5-minute payment window for this bot.
    expires_at_str = "5 Minutes"
    created_at = data.get("created_at_ist") or datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    if not qr_url:
        return await message_obj.edit_text(
            "❌ <b>QR Generation Failed:</b>\nFamPay response me QR image URL nahi mila.",
            reply_markup=back_kb("gateway_inr"),
            parse_mode="HTML"
        )

    # Always start a fresh 5-minute local payment window from QR creation.
    expires_timestamp = int(time.time() + 300)

    # Save the transaction as pending.
    db_query(
        "INSERT OR REPLACE INTO transactions "
        "(order_id, user_id, amount_inr, status, timestamp, qr_url, upi_id, expires_at) "
        "VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)",
        (order_id, user_id, inr_amount, current_time, qr_url, upi_id, expires_timestamp)
    )

    # IMPORTANT: show the QR image itself, not a "View QR Code" link.
    # This follows the QR presentation used in SAGAR_MODS_SHOP.
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Cancel Payment",
                callback_data=f"cancel_payment_{order_id}",
                style="danger"
            )
        ]
    ])

    caption = (
        f"💳 <b>PAYMENT QR CODE</b>\n\n"
        f"💵 <b>Amount:</b> {fmt_curr(inr_amount)}\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
        f"🏦 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"⏳ <b>Expires:</b> {expires_at_str}\n\n"
        f"📱 Scan this QR with your UPI app and pay the exact amount.\n"
        f"⚡ Payment is verified automatically after successful payment.\n\n"
        f"🔒 Your balance will be credited automatically after verification."
    )

    log_activity(
        user_id,
        "GENERATE_INVOICE_FAMPAY",
        f"Amount: {inr_amount}, Order ID: {order_id}"
    )

    # Delete the temporary "Generating..." message and send the QR as a photo.
    try:
        await message_obj.delete()
    except Exception:
        pass

    try:
        sent_qr = await bot.send_photo(
            chat_id=user_id,
            photo=qr_url,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
        # Store QR message id so Cancel/Verify can cleanly remove it.
        try:
            qr_message_id = sent_qr.message_id
            db_query("UPDATE transactions SET qr_message_id=? WHERE order_id=? AND user_id=?", (qr_message_id, order_id, user_id))
            set_setting(f"qr_msg_{user_id}", str(qr_message_id))
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to send FamPay QR photo: {e}")
        # Fallback: keep the QR URL accessible if Telegram cannot fetch the image.
        await bot.send_message(
            chat_id=user_id,
            text=caption + f"\n\n🖼 <a href=\"{qr_url}\">Open QR Code</a>",
            reply_markup=kb,
            parse_mode="HTML"
        )

@dp.callback_query(F.data.startswith("verify_"))
async def manual_verify_callback(call: CallbackQuery):
    order_id = call.data.split("_", 1)[1]
    await run_payment_verification(call.from_user.id, order_id, call)


@dp.callback_query(F.data.startswith("cancel_payment_"))
async def cancel_payment_callback(call: CallbackQuery):
    """Cancel a pending payment, delete its QR, and show clean cancellation options."""
    order_id = call.data[len("cancel_payment_"):]
    user_id = call.from_user.id
    txn = db_query(
        "SELECT status FROM transactions WHERE order_id=? AND user_id=?",
        (order_id, user_id), fetchone=True
    )
    if not txn:
        return await call.answer("❌ Payment order not found.", show_alert=True)
    if txn[0] == "paid":
        return await call.answer("⚠️ This payment is already completed.", show_alert=True)

    db_query("UPDATE transactions SET status='cancelled' WHERE order_id=? AND user_id=?", (order_id, user_id))
    log_activity(user_id, "PAYMENT_CANCELLED", f"Order: {order_id}")
    # Delete the QR/photo itself so it cannot remain above the cancellation message.
    try:
        await call.message.delete()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Add Balance Again", callback_data=f"retry_deposit_{order_id}", style="success")],
        [InlineKeyboardButton(text="↩️ Back to Menu", callback_data="back_main", style="primary")]
    ])
    try:
        await bot.send_message(user_id, "❌ <b>Payment Cancelled</b>", reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("❌ Payment cancelled.")

# ==============================================================================
# 13. BINANCE CRYPTO PAYMENT
# ==============================================================================
async def start_wallet_payment_gateway_choice(user_id: int, amount: float):
    fampay_on = get_setting("gateway_fampay_enabled", "ON") == "ON" and bool(get_setting("fampay_api_key", "")) and get_setting("fampay_api_key", "") != "YOUR_FAMPAY_API_KEY"
    zapupi_on = get_setting("gateway_zapupi_enabled", "ON") == "ON" and bool(get_setting("zapupi_zap_key", "").strip())
    if fampay_on and not zapupi_on:
        msg = await bot.send_message(user_id, f"⏳ Generating FamPay QR for {fmt_curr(amount)}...")
        return await generate_fampay_order(user_id, amount, msg)
    if zapupi_on and not fampay_on:
        msg = await bot.send_message(user_id, f"⏳ Generating ZapUPI payment for {fmt_curr(amount)}...")
        return await generate_zapupi_order(user_id, amount, msg)
    if not fampay_on and not zapupi_on:
        return await bot.send_message(user_id, "❌ Payment gateways are OFF or not configured. Contact admin.")
    set_setting(f"pending_wallet_gateway_amount_{user_id}", str(round(float(amount), 2)))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 FamPay", callback_data="walletpay_fampay", style="primary")],
        [InlineKeyboardButton(text="🏦 ZapUPI", callback_data="walletpay_zapupi", style="success")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_add_balance", style="danger")]
    ])
    await bot.send_message(user_id, f"💰 <b>Amount:</b> {fmt_curr(amount)}\n\nChoose payment gateway:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.in_({"walletpay_fampay", "walletpay_zapupi"}))
async def wallet_custom_gateway_choice(call: CallbackQuery):
    user_id = call.from_user.id
    amount = safe_float(get_setting(f"pending_wallet_gateway_amount_{user_id}", "0"))
    if amount <= 0:
        return await call.answer("Amount request expired. Please try again.", show_alert=True)
    gateway = "fampay" if call.data == "walletpay_fampay" else "zapupi"
    enabled = get_setting(f"gateway_{gateway}_enabled", "ON") == "ON"
    configured = (bool(get_setting("fampay_api_key", "")) and get_setting("fampay_api_key", "") != "YOUR_FAMPAY_API_KEY") if gateway == "fampay" else bool(get_setting("zapupi_zap_key", "").strip())
    if not enabled or not configured:
        return await call.answer("This gateway is OFF or not configured.", show_alert=True)
    set_setting(f"pending_wallet_gateway_amount_{user_id}", "")
    await call.answer()
    try: await call.message.delete()
    except Exception: pass
    msg = await bot.send_message(user_id, f"⏳ Generating {('FamPay QR' if gateway == 'fampay' else 'ZapUPI payment')} for {fmt_curr(amount)}...")
    if gateway == "fampay": await generate_fampay_order(user_id, amount, msg)
    else: await generate_zapupi_order(user_id, amount, msg)

async def start_product_payment_gateway_choice(user_id: int, amount: float):
    """Use only enabled gateways; ask user only when both gateways are available."""
    fampay_on = get_setting("gateway_fampay_enabled", "ON") == "ON" and bool(get_setting("fampay_api_key", "")) and get_setting("fampay_api_key", "") != "YOUR_FAMPAY_API_KEY"
    zapupi_on = get_setting("gateway_zapupi_enabled", "ON") == "ON" and bool(get_setting("zapupi_zap_key", "").strip())
    if fampay_on and not zapupi_on:
        msg = await bot.send_message(user_id, f"⏳ Generating FamPay QR for {fmt_curr(amount)}...")
        return await generate_fampay_order(user_id, amount, msg)
    if zapupi_on and not fampay_on:
        msg = await bot.send_message(user_id, f"⏳ Generating ZapUPI payment for {fmt_curr(amount)}...")
        return await generate_zapupi_order(user_id, amount, msg)
    if not fampay_on and not zapupi_on:
        return await bot.send_message(user_id, "❌ Admin ne FamPay aur ZapUPI dono gateways OFF kiye hue hain ya API setup nahi hai.")
    set_setting(f"pending_gateway_amount_{user_id}", str(round(float(amount), 2)))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay with FamPay", callback_data="shortpay_fampay", style="primary")],
        [InlineKeyboardButton(text="🏦 Pay with ZapUPI", callback_data="shortpay_zapupi", style="success")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main", style="danger")]
    ])
    await bot.send_message(user_id, f"🛒 <b>PRODUCT PAYMENT</b>\n\n💰 Exact amount required: <b>{fmt_curr(amount)}</b>\n\nChoose your payment gateway:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.in_({"shortpay_fampay", "shortpay_zapupi"}))
async def product_shortfall_gateway_choice(call: CallbackQuery):
    user_id = call.from_user.id
    amount = safe_float(get_setting(f"pending_gateway_amount_{user_id}", "0"))
    if amount <= 0:
        return await call.answer("Payment request expired. Please tap Buy again.", show_alert=True)
    gateway = "fampay" if call.data == "shortpay_fampay" else "zapupi"
    enabled = get_setting(f"gateway_{gateway}_enabled", "ON") == "ON"
    configured = bool(get_setting("fampay_api_key", "")) and get_setting("fampay_api_key", "") != "YOUR_FAMPAY_API_KEY" if gateway == "fampay" else bool(get_setting("zapupi_zap_key", "").strip())
    if not enabled or not configured:
        return await call.answer("This gateway is currently OFF or not configured.", show_alert=True)
    set_setting(f"pending_gateway_amount_{user_id}", "")
    await call.answer()
    try: await call.message.delete()
    except Exception: pass
    msg = await bot.send_message(user_id, f"⏳ Generating {('FamPay QR' if gateway == 'fampay' else 'ZapUPI payment')} for {fmt_curr(amount)}...")
    if gateway == "fampay":
        await generate_fampay_order(user_id, amount, msg)
    else:
        await generate_zapupi_order(user_id, amount, msg)

@dp.callback_query(F.data.startswith("buytopup_"))
async def buy_product_topup(call: CallbackQuery):
    """Create a UPI QR for the exact wallet shortfall before product purchase."""
    try:
        prod_id = int(call.data.split("_", 1)[1])
    except (ValueError, IndexError):
        return await call.answer("Invalid product.", show_alert=True)
    prod = db_query("SELECT price_inr, reseller_price, name, panel_name FROM products WHERE id=?", (prod_id,), fetchone=True)
    user = db_query("SELECT balance, is_reseller, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if not prod or not user:
        return await call.answer("Product/user not found.", show_alert=True)
    base = safe_float(prod[1]) if user[1] else safe_float(prod[0])
    price = base - (base * VIP_DISCOUNT_PERCENTAGE / 100) if user[2] else base
    amount = round(max(0.0, price - safe_float(user[0])), 2)
    if amount <= 0:
        await call.answer("Your balance is enough now. Tap Buy again.", show_alert=True)
        return
    await call.answer()
    # Remove the old confirm-order post; the QR/payment message replaces it.
    try:
        await call.message.delete()
    except Exception:
        pass
    # Remember the product the user was trying to buy, so verified payment
    # can continue that purchase instead of dropping the user at Start Menu.
    set_setting(f"pending_product_purchase_{call.from_user.id}", str(prod_id))
    await start_product_payment_gateway_choice(call.from_user.id, amount)

@dp.callback_query(F.data.startswith("retry_deposit_"))
async def retry_cancelled_deposit(call: CallbackQuery):
    order_id = call.data[len("retry_deposit_"):]
    txn = db_query("SELECT amount_inr, status FROM transactions WHERE order_id=? AND user_id=?", (order_id, call.from_user.id), fetchone=True)
    if not txn:
        return await call.answer("Payment order not found.", show_alert=True)
    amount = safe_float(txn[0])
    await call.answer()
    try:
        await call.message.delete()
    except Exception:
        pass
    await start_product_payment_gateway_choice(call.from_user.id, amount)

@dp.callback_query(F.data == "gateway_crypto")
async def add_balance_crypto(call: CallbackQuery, state: FSMContext):
    address_check = db_query("SELECT value FROM settings WHERE key='binance_address'", fetchone=True)
    if not address_check or not address_check[0]:
        return await call.message.edit_text("⚠️ Binance Gateway is currently offline. Admin has not set a deposit address.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    deposit_address = address_check[0]
    msg = (f"🪙 <b>— BINANCE USDT DEPOSIT —</b> 🪙\n\n💵 <b>Exchange Rate:</b> 1 USDT = ₹{USDT_TO_INR}\n⚠️ <b>Network:</b> Please send via <b>TRC20</b> or <b>BEP20</b>.\n\n👇 <b>Send your USDT to this exact address:</b>\n<code>{deposit_address}</code>\n\n━━━━━━━━━━━━━━━━━━\n✅ <b>After sending the USDT, reply to this message with your exact TxID (Transaction Hash) to instantly claim your balance.</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
    await call.message.edit_text(msg, reply_markup=kb, parse_mode='HTML')
    await state.set_state(UserStates.wait_for_crypto_txid)

@dp.message(UserStates.wait_for_crypto_txid)
async def process_crypto_txid(m: Message, state: FSMContext):
    txid = m.text.strip()
    user_id = m.from_user.id
    if len(txid) < 10: return await m.answer("❌ That doesn't look like a valid TxID. Please try again.")
    if db_query("SELECT txid FROM crypto_txns WHERE txid=?", (txid,), fetchone=True):
        return await m.answer("⚠️ This Transaction ID has already been claimed in the system!", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    api_key_check = db_query("SELECT value FROM settings WHERE key='binance_api'", fetchone=True)
    secret_key_check = db_query("SELECT value FROM settings WHERE key='binance_secret'", fetchone=True)
    if not api_key_check or not secret_key_check:
        return await m.answer("⚠️ Binance API is missing on the server. Contact Support.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    await m.answer("🔄 <b>Verifying your TxID with Binance Blockchain...</b>\n<i>This may take up to 30 seconds...</i>", parse_mode='HTML')
    api_key = api_key_check[0]; secret_key = secret_key_check[0]
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': api_key}
    url = f"https://api.binance.com/sapi/v1/capital/deposit/hisrec?{query_string}&signature={signature}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    try: history = await resp.json(content_type=None)
                    except: history = []
                    found = False
                    for deposit in history:
                        if deposit.get("txId") == txid and deposit.get("status") == 1:
                            found = True
                            usdt_amount = float(deposit.get("amount"))
                            inr_amount = usdt_amount * USDT_TO_INR
                            db_query("INSERT INTO crypto_txns (txid, user_id, amount_usdt, timestamp) VALUES (?, ?, ?, ?)", (txid, user_id, usdt_amount, int(time.time())))
                            db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (inr_amount, user_id))
                            await m.answer(f"🎉 <b>CRYPTO DEPOSIT SUCCESSFUL!</b>\n\n✅ We safely received <b>{usdt_amount} USDT</b>.\n💰 <b>{fmt_curr(inr_amount)}</b> has been added to your balance!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
                            await send_advanced_notification(user_id, "DEPOSIT", inr_amount, product=txid, gateway="Binance Crypto")
                            log_activity(user_id, "CRYPTO_DEPOSIT", f"TxID: {txid}, Amount: {inr_amount}")
                            await state.clear()
                            break
                    if not found: await m.answer("❌ <b>TxID Not Found or Still Pending!</b>\nMake sure the transaction is fully confirmed. Try again in 5 mins.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
                else: await m.answer(f"⚠️ <b>Binance Server Error:</b> HTTP {resp.status}.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
        except Exception as e: await m.answer(f"⚠️ <b>Connection Error:</b> {str(e)}", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')

# ==============================================================================
# 14. SHOP – with uppercase categories and new point_down emoji
# ==============================================================================
@dp.callback_query(F.data == "menu_shop")
async def view_shop_panels(call: CallbackQuery):
    log_activity(call.from_user.id, "VIEW_SHOP")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b><u>SELECT PRODUCT PANEL</u></b>\n━━━━━━━━━━━━━━━━━━\n\n{get_emoji('point_down')} <b>Choose a panel to view its packages:</b>"
    for cat in FIXED_CATEGORIES:
        count = db_query("SELECT COUNT(*) FROM products WHERE category LIKE ? AND is_active=1", (cat + '%',), fetchone=True)[0]
        emoji_id = get_category_emoji(cat)
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat[:30]}", icon_custom_emoji_id=emoji_id, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("cat_"))
async def view_panel_names(call: CallbackQuery):
    category = call.data.split("cat_", 1)[1]
    panel_names = db_query("""SELECT MIN(TRIM(panel_name)) AS panel_name, MAX(COALESCE(maintenance,0)) AS maintenance
                              FROM products
                              WHERE category LIKE ? AND is_active=1 AND TRIM(COALESCE(panel_name,'')) != ''
                              GROUP BY LOWER(TRIM(panel_name))
                              ORDER BY MIN(TRIM(panel_name)) COLLATE NOCASE""", (category + '%',), fetchall=True)
    if not panel_names:
        prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit, maintenance FROM products WHERE category LIKE ? AND is_active=1", (category + '%',), fetchall=True)
        if not prods: return await call.answer("❌ No products available in this category yet.", show_alert=True)
        await show_products_for_panel(call, prods, category)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b><u>{category.upper()} PANELS</u></b>\n━━━━━━━━━━━━━━━━━━\n\n{get_emoji('point_down')} <b>Choose a panel name:</b>"
    for pn in panel_names:
        panel = str(pn[0] or '').strip()
        panel_maintenance = bool(pn[1]) if len(pn) > 1 else False
        emoji_id = get_panel_emoji(panel) or get_emoji_icon("product_store")
        # Show maintained panels in red; the maintenance state applies to every duration under this panel.
        label = f"🔴 {panel} — MAINTENANCE" if panel_maintenance else panel
        kb.inline_keyboard.append([InlineKeyboardButton(text=label[:64], callback_data=f"pnl_{category[:30]}_{panel[:30]}", icon_custom_emoji_id=emoji_id, style="danger" if panel_maintenance else "primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK TO PANELS", callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("pnl_"))
async def view_products_for_panel(call: CallbackQuery):
    parts = call.data.split("pnl_", 1)[1].split("_", 1)
    if len(parts) != 2: return await call.answer("Invalid selection.", show_alert=True)
    category, panel_name = parts[0], parts[1]
    # Do not open a panel while its maintenance flag is enabled.
    panel_state = db_query(
        "SELECT MAX(COALESCE(maintenance,0)) FROM products WHERE category LIKE ? AND LOWER(TRIM(COALESCE(panel_name,''))) LIKE LOWER(TRIM(?)) AND is_active=1",
        (category + '%', panel_name + '%'), fetchone=True
    )
    if panel_state and bool(panel_state[0]):
        return await call.answer("🛠 This product is currently under maintenance. Please wait for the maintenance update.", show_alert=True)
    prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit, maintenance FROM products WHERE category LIKE ? AND panel_name LIKE ? AND is_active=1", (category + '%', panel_name + '%'), fetchall=True)
    if not prods: return await call.answer("No products found for this panel.", show_alert=True)
    # Resolve panel-level maintenance so all durations/products under the panel are treated consistently.
    panel_state = db_query("SELECT MAX(COALESCE(maintenance,0)) FROM products WHERE category LIKE ? AND LOWER(TRIM(COALESCE(panel_name,''))) LIKE LOWER(TRIM(?)) AND is_active=1", (category + '%', panel_name + '%'), fetchone=True)
    if panel_state and bool(panel_state[0]):
        prods = [tuple(list(p[:7]) + [1]) for p in prods]
    await show_products_for_panel(call, prods, f"{category} - {panel_name}")

async def show_products_for_panel(call: CallbackQuery, prods: List[Tuple], header: str):
    user = db_query("SELECT is_reseller, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    is_reseller = bool(user[0]) if user else False
    is_vip = bool(user[1]) if user else False
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b><u>{header.upper()} PACKAGES</u></b>\n━━━━━━━━━━━━━━━━━━\n\n"
    # Same package name is shown only once (case-insensitive), even if duplicated in DB.
    seen_names = set()
    demo_button = None
    for p in prods:
        prod_id, package_name, normal_price, stock, reseller_price, validity, device = p[:7]
        maintenance = bool(p[7]) if len(p) > 7 else False
        normalized_name = str(package_name or '').strip().casefold()
        if normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        normal_price = safe_float(normal_price)
        reseller_price = safe_float(reseller_price)
        base_price = reseller_price if is_reseller else normal_price
        display_price = base_price - (base_price * (VIP_DISCOUNT_PERCENTAGE / 100)) if is_vip else base_price
        stock_status = "🛠 UNDER MAINTENANCE" if maintenance else ("✅ In Stock" if stock > 0 else "❌ Out of Stock")
        text += f"{get_emoji('product_store')} ⏱ <b>Validity: {html_lib.escape(str(package_name))}</b>\n"
        if is_reseller or is_vip:
            text += f"💰 Regular Price: <s>{fmt_curr(normal_price)}</s>\n"
            if is_reseller and not is_vip: text += f"👑 <b>Reseller Price: {fmt_curr(display_price)}</b>\n"
            elif is_vip and not is_reseller: text += f"🌟 <b>VIP Price: {fmt_curr(display_price)}</b>\n"
            else: text += f"👑🌟 <b>Super Price: {fmt_curr(display_price)}</b>\n"
        else:
            text += f"💰 Price: {fmt_curr(normal_price)}\n"
        text += f"📱 Limit: {html_lib.escape(str(device))} | 📦 {stock_status}\n\n"
        # Keep a single panel-level Watch Demo button, regardless of how many durations
        # are configured. It is appended after all duration buttons, immediately above Back.
        panel_demo_name = str(header.rsplit(' - ', 1)[-1] if ' - ' in header else header).strip()
        demo_key = panel_demo_name.casefold()
        demo_row = db_query("SELECT file_id FROM product_demos WHERE product_name_key=?", (demo_key,), fetchone=True)
        if demo_row and demo_row[0] and demo_button is None:
            demo_button = InlineKeyboardButton(
                text=f"▶️ Watch Demo — {panel_demo_name}"[:64],
                callback_data=f"watch_demo_{prod_id}",
                style="primary"
            )
        if maintenance:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"🔴 {package_name} — UNDER MAINTENANCE", callback_data=f"product_maintenance_info_{prod_id}", style="danger")])
        elif stock > 0:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"🟢 Buy {package_name} - {fmt_curr(display_price)}", callback_data=f"buy_{prod_id}", icon_custom_emoji_id=get_emoji_icon("product_store"), style="success")])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {package_name} (Out of Stock)", callback_data="ignore_stock_click", style="danger")])
    text += f"{get_emoji('point_down')} <b>Select package below to instantly purchase:</b>"
    if demo_button is not None:
        kb.inline_keyboard.append([demo_button])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK TO PANELS", callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("product_maintenance_info_"))
async def product_maintenance_info(call: CallbackQuery):
    prod_id = int(call.data.rsplit("_", 1)[1])
    row = db_query("SELECT name FROM products WHERE id=?", (prod_id,), fetchone=True)
    name = html_lib.escape(str(row[0])) if row else "Product"
    await call.answer(f"🛠 {name} is under maintenance. Please try again later.", show_alert=True)

@dp.callback_query(F.data == "ignore_stock_click")
async def ignore_stock_click(call: CallbackQuery):
    await call.answer("⚠️ This duration is completely Out of Stock! Admins have been notified to refill.", show_alert=True)

# ==============================================================================
# RESELLER API - AUTOMATIC KEY DELIVERY
# ==============================================================================
USER_BUY_LOCKS: Dict[int, asyncio.Lock] = {}


def get_reseller_api_url() -> str:
    """Return the admin-configured reseller API endpoint."""
    url = get_setting("reseller_api_url", RESELLER_API_URL).strip()
    return url or RESELLER_API_URL


def get_reseller_api_key() -> str:
    return get_setting("reseller_api_key", RESELLER_API_KEY).strip()


async def reseller_api_request(action: str, **fields) -> Tuple[bool, Any]:
    """Call the reseller API and return (ok, response)."""
    api_key = get_reseller_api_key()
    if not api_key or api_key == "YOUR_RRSELLER_API_ADD":
        return False, "Reseller API key is not configured."

    payload = {"api_key": api_key, "action": action}
    payload.update({k: v for k, v in fields.items() if v not in (None, "")})
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                get_reseller_api_url(),
                data=payload,
                headers={"X-API-Key": api_key, "Accept": "application/json"},
            ) as resp:
                raw = await resp.text()
                try:
                    data = json.loads(raw)
                except (ValueError, TypeError):
                    return False, f"Invalid API response (HTTP {resp.status}): {raw[:300]}"
                return True, data
    except asyncio.TimeoutError:
        return False, "TIMEOUT"
    except aiohttp.ClientError as exc:
        return False, f"Connection error: {exc}"


async def reseller_buy(api_product_id: str, duration: str = "", quantity: int = 1) -> Tuple[bool, str]:
    """Purchase one automatic key from the configured reseller API."""
    ok, data = await reseller_api_request(
        "buy",
        product_id=str(api_product_id),
        duration=duration,
        quantity=quantity,
    )
    if not ok:
        return False, str(data)
    if isinstance(data, dict) and str(data.get("status", "")).lower() == "success":
        key = data.get("key")
        if not key:
            keys = data.get("keys")
            if isinstance(keys, list) and keys:
                key = keys[0]
        if key:
            return True, str(key)
        logger.error("Reseller API reported success without a key: %s", data)
        return False, "API returned success but no key. Check supplier orders."
    if isinstance(data, dict):
        return False, str(data.get("message") or data.get("error") or "Request failed")
    return False, "Request failed"


@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: CallbackQuery):
    """One purchase at a time per user; API purchase happens before wallet debit."""
    lock = USER_BUY_LOCKS.setdefault(call.from_user.id, asyncio.Lock())
    if lock.locked():
        return await call.answer("⏳ Your previous purchase is still processing...", show_alert=True)
    async with lock:
        await _process_buy(call)


async def _process_buy(call: CallbackQuery):
    prod_id = int(call.data.split("_", 1)[1])
    prod = db_query(
        "SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name, api_product_id, api_duration, maintenance FROM products WHERE id=?",
        (prod_id,), fetchone=True
    )
    user = db_query(
        "SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?",
        (call.from_user.id,), fetchone=True
    )
    if not prod or not user:
        return await call.answer("❌ Critical Error: Item not found in DB!", show_alert=True)

    if len(prod) > 11 and bool(prod[11]):
        return await call.answer("🛠 This product is under maintenance. Please try again later.", show_alert=True)

    normal_price = safe_float(prod[1])
    reseller_price = safe_float(prod[7])
    is_reseller = bool(user[2])
    is_vip = bool(user[4])
    base_price = reseller_price if is_reseller else normal_price
    final_price = base_price - (base_price * (VIP_DISCOUNT_PERCENTAGE / 100)) if is_vip else base_price
    savings = normal_price - final_price

    if user[0] < final_price:
        shortfall = round(final_price - safe_float(user[0]), 2)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Pay {fmt_curr(shortfall)} via UPI", callback_data=f"buytopup_{prod_id}", style="success")],
            [InlineKeyboardButton(text="↩️ Back to Shop", callback_data="menu_shop", style="danger")]
        ])
        summary = (
            "💎 <b>CONFIRM YOUR ORDER</b> 💎\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Product:</b> {html_lib.escape(str(prod[8] or prod[0]))}\n"
            f"⏳ <b>Duration:</b> {html_lib.escape(str(prod[4]))}\n"
            f"💰 <b>Price:</b> {fmt_curr(final_price)}\n"
            f"👛 <b>Wallet Balance:</b> {fmt_curr(safe_float(user[0]))}\n"
            f"➕ <b>Amount to Pay:</b> {fmt_curr(shortfall)}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ Your balance is short. Pay only the exact remaining amount using UPI."
        )
        await call.answer()
        return await call.message.edit_text(summary, reply_markup=kb, parse_mode="HTML")

    # If linked, obtain the key first. A failed supplier request never charges the user.
    api_pid = (prod[9] or "").strip()
    api_duration = (prod[10] or "").strip()
    api_delivered = ""
    if api_pid:
        await call.answer("⏳ Generating your key, please wait...")
        ok, result = await reseller_buy(api_pid, api_duration, 1)
        if not ok:
            log_activity(call.from_user.id, "API_BUY_FAILED", f"prod={prod_id} api_pid={api_pid} err={result}")
            if result == "TIMEOUT":
                msg = "⚠️ Supplier took too long to respond. You were NOT charged. Please try again in a minute."
            else:
                msg = f"❌ Could not generate key right now. You were NOT charged.\nReason: {html_lib.escape(result)}\nContact: {ADMIN_CONTACT}"
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ <b>API BUY FAILED</b>\nProduct #{prod_id} | User <code>{call.from_user.id}</code>\n<code>{html_lib.escape(str(result))}</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return await call.message.answer(msg, parse_mode="HTML")
        api_delivered = result

    # Charge only after API key delivery succeeds (or for a local-key product).
    db_query(
        "UPDATE users SET balance=?, spent=spent+?, orders_count=orders_count+1, total_saved=total_saved+? WHERE user_id=?",
        (user[0] - final_price, final_price, savings, call.from_user.id),
    )

    delivered_key = api_delivered
    if not delivered_key:
        if prod[2] > 0:
            key_data = db_query(
                "SELECT id, key_text FROM product_keys WHERE product_id=? AND is_used=0 LIMIT 1",
                (prod_id,), fetchone=True
            )
            if key_data:
                delivered_key = key_data[1]
                db_query("UPDATE product_keys SET is_used=1 WHERE id=?", (key_data[0],))
                db_query("UPDATE products SET stock=stock-1 WHERE id=?", (prod_id,))
            else:
                delivered_key = "OUT_OF_STOCK_CONTACT_ADMIN_CODE_01"
        else:
            delivered_key = "OUT_OF_STOCK_CONTACT_ADMIN_CODE_02"

    if user[1]:
        commission = final_price * 0.15
        db_query(
            "UPDATE users SET balance=balance+?, referral_earned=referral_earned+? WHERE user_id=?",
            (commission, commission, user[1]),
        )
        try:
            await bot.send_message(
                user[1],
                f"🎁 <b>Referral Bonus Added!</b>\nYour friend made a successful purchase. You earned {fmt_curr(commission)} directly to your wallet!",
                parse_mode="HTML",
            )
        except Exception:
            pass

    product_full_name = f"{prod[6]} - {prod[8]} ({prod[0]})"
    db_query(
        "INSERT INTO orders (user_id, product_name, price_paid, delivered_key, purchase_date) VALUES (?, ?, ?, ?, ?)",
        (call.from_user.id, product_full_name, final_price, delivered_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    log_activity(call.from_user.id, "PURCHASE_SUCCESS", f"Product: {product_full_name}, Paid: {final_price}")
    await send_advanced_notification(call.from_user.id, "ORDER", final_price, product=product_full_name, key=delivered_key)

    msg = (
        f"✅ <b>PURCHASE SUCCESSFUL!</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Panel:</b> {prod[6]}\n📁 <b>Panel Name:</b> {prod[8]}\n"
        f"⏱ <b>Package:</b> {prod[0]}\n💰 <b>Amount Deducted:</b> {fmt_curr(final_price)}\n"
        f"📱 <b>Device Limit:</b> {prod[5]}\n━━━━━━━━━━━━━━━━━━\n"
    )
    if prod[3] and prod[3].startswith("http"):
        msg += f"📥 <b>APK Link:</b> <a href='{prod[3]}'>Click Here to Download</a>\n\n"
    if "OUT_OF_STOCK" in delivered_key:
        msg += f"⚠️ <b>CRITICAL INVENTORY ALERT</b>\nYour money was deducted, but the key vault was empty. Contact Admin immediately with this message: {ADMIN_CONTACT}\n"
    else:
        msg += f"🔑 <b>Your Exclusive Key:</b>\n<code>{html_lib.escape(delivered_key)}</code>\n\n<i>For any issues or guide, tap Support or contact: {ADMIN_CONTACT}</i>"
    await call.message.edit_text(msg, reply_markup=back_kb("menu_shop"), disable_web_page_preview=True, parse_mode="HTML")


@dp.callback_query(F.data == "menu_vip_dash")
async def vip_dashboard(call: CallbackQuery):
    u = db_query("SELECT balance, is_vip, vip_since FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    is_vip = bool(u[1])
    status_str = "🟢 Active (Lifetime)" if is_vip else "🔴 Not Subscribed"
    text = get_ui_text("vip_menu", vip_status=status_str)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if is_vip:
        text += f"\n📅 <b>Member Since:</b> {u[2]}\n\nEnjoy your permanent 15% discount!"
    else:
        text += f"\n\n💳 <b>Your Current Balance:</b> {fmt_curr(u[0])}\n"
        if u[0] >= VIP_PRICE_INR: kb.inline_keyboard.append([InlineKeyboardButton(text=f"✅ Purchase VIP for {fmt_curr(VIP_PRICE_INR)}", callback_data="execute_vip_upgrade", style="success")])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Need {fmt_curr(VIP_PRICE_INR)} to Upgrade", callback_data="ignore_stock_click", style="danger")])
            kb.inline_keyboard.append([InlineKeyboardButton(text="💳 Add Balance Now", callback_data="menu_add_balance", style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "execute_vip_upgrade")
async def execute_vip_upgrade(call: CallbackQuery):
    u = db_query("SELECT balance, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if u[1]: return await call.answer("⚠️ You are already a VIP Member!", show_alert=True)
    if u[0] < VIP_PRICE_INR: return await call.answer(f"❌ Your balance dropped below {VIP_PRICE_INR}.", show_alert=True)
    new_balance = u[0] - VIP_PRICE_INR
    now_date = datetime.now().strftime("%Y-%m-%d")
    db_query("UPDATE users SET balance=?, is_vip=1, vip_since=? WHERE user_id=?", (new_balance, now_date, call.from_user.id))
    log_activity(call.from_user.id, "UPGRADED_VIP")
    try: await bot.send_message(ADMIN_ID, f"🌟 <b>NEW VIP UPGRADE</b>\n👤 User ID: <code>{call.from_user.id}</code>", parse_mode='HTML')
    except: pass
    await call.answer("🎉 Upgrade Successful! You are now a VIP Member.", show_alert=True)
    await vip_dashboard(call)

@dp.callback_query(F.data == "menu_reseller_dash")
async def reseller_dashboard(call: CallbackQuery):
    u = db_query("SELECT balance, is_reseller, reseller_since, total_saved FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    system_status = status_check[0] if status_check else "ON"
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    if u[1]: 
        text = (f"{get_emoji('shield_icon')} <b><u>— RESELLER DASHBOARD —</u></b> {get_emoji('shield_icon')}\n\n🟢 <b>Status:</b> Active\n📅 <b>Since:</b> {u[2]}\n{get_emoji('money_icon')} <b>Total Saved:</b> {fmt_curr(u[3])}\n\n🎉 You are enjoying exclusive wholesale prices on all products!")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
        await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
        return
    if system_status == "OFF": return await call.answer("⚠️ Wholesale / Reseller registrations are currently closed by Admin.", show_alert=True)
    text = (f"⚡ <b><u>— BECOME A RESELLER —</u></b> ⚡\n\nUpgrade your account to access wholesale <b>Reseller Prices</b>!\n\n📋 <b>Requirements to Upgrade:</b>\n1️⃣ Must have a minimum balance of <b>{fmt_curr(min_balance)}</b>.\n2️⃣ A one-time setup fee of <b>{fmt_curr(setup_fee)}</b> will be deducted.\n\n💳 <b>Your Current Balance:</b> {fmt_curr(u[0])}\n")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if u[0] >= min_balance: kb.inline_keyboard.append([InlineKeyboardButton(text=f"✅ Pay {fmt_curr(setup_fee)} & Become Reseller", callback_data="execute_reseller_upgrade", style="success")])
    else:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Insufficient Balance (Need {fmt_curr(min_balance)})", callback_data="ignore_stock_click", style="danger")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="💳 Add Balance", callback_data="menu_add_balance", style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "execute_reseller_upgrade")
async def execute_reseller_upgrade(call: CallbackQuery):
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    u = db_query("SELECT balance, is_reseller FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if u[1]: return await call.answer("⚠️ You are already a Reseller!", show_alert=True)
    if u[0] < min_balance: return await call.answer(f"❌ Your balance dropped below {fmt_curr(min_balance)}. Please top up.", show_alert=True)
    new_balance = u[0] - setup_fee
    db_query("UPDATE users SET balance=?, is_reseller=1, reseller_since=?, account_type='Reseller' WHERE user_id=?", (new_balance, datetime.now().strftime("%Y-%m-%d"), call.from_user.id))
    log_activity(call.from_user.id, "UPGRADED_RESELLER")
    try: await bot.send_message(ADMIN_ID, f"👑 <b>NEW RESELLER UPGRADE</b>\n👤 User ID: <code>{call.from_user.id}</code>", parse_mode='HTML')
    except: pass
    await call.answer("🎉 Upgrade Successful! Welcome to the Reseller tier.", show_alert=True)
    await reseller_dashboard(call)

@dp.callback_query(F.data == "menu_orders")
async def my_orders(call: CallbackQuery):
    orders = db_query("SELECT product_name, delivered_key, purchase_date, price_paid FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (call.from_user.id,), fetchall=True)
    if not orders: return await call.message.edit_text("🧾 You haven't made any purchases yet. Your vault is empty.", reply_markup=back_kb(), parse_mode='HTML')
    text = "🧾 <b><u>— YOUR RECENT ORDERS (LAST 10) —</u></b> 🧾\n\n"
    for o in orders: text += f"📦 <b>{o[0]}</b> ({fmt_curr(o[3])})\n🔑 <code>{o[1]}</code>\n📅 <i>{o[2]}</i>\n━━━━━━━━━━━━━━━━\n"
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "menu_profile")
async def show_profile(call: CallbackQuery):
    u = db_query("SELECT user_id, first_name, account_type, balance, orders_count, spent, referrals_count, joined_date, is_reseller, reseller_since, total_saved, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    acc_type_display = []
    if u[8]: acc_type_display.append(f"{get_emoji('reseller')} Reseller")
    if u[11]: acc_type_display.append(f"{get_emoji('vip')} VIP")
    type_str = " | ".join(acc_type_display) if acc_type_display else f"{get_emoji('regular_user')} Regular User"
    text = (
        f"{get_emoji('grid_id')} <b><u>— YOUR SECURE PROFILE —</u></b> {get_emoji('grid_id')}\n\n"
        f"{get_emoji('grid_id')} <b>Grid ID:</b> <code>{u[0]}</code>\n"
        f"{get_emoji('name')} <b>Name:</b> {u[1]}\n"
        f"{get_emoji('account_level')} <b>Account Level:</b> {type_str}\n\n"
        f"{get_emoji('wallet_left')} <b>— Wallet —</b> {get_emoji('wallet_right')}\n"
        f"{get_emoji('wallet_left')} <b>Current Balance:</b> {fmt_curr(u[3])} {get_emoji('wallet_right')}\n\n"
        f"{get_emoji('global_stats')} <b>— Global Statistics —</b>\n"
        f"{get_emoji('total_orders')} <b>Total Orders:</b> {u[4]}\n"
        f"{get_emoji('total_spent')} <b>Total Spent:</b> {fmt_curr(u[5])}\n"
        f"{get_emoji('total_referrals')} <b>Total Referrals:</b> {u[6]}\n\n"
    )
    if u[8]:
        text += f"{get_emoji('shield_icon')} <b>— RESELLER METRICS —</b> {get_emoji('shield_icon')}\n{get_emoji('money_icon')} <b>Total Saved via Reseller:</b> {fmt_curr(u[10])}\n\n"
    text += f"{get_emoji('joined_grid')} <b>Joined Grid:</b> {u[7]}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Redeem Promo Code",
            callback_data="redeem_coupon",
            icon_custom_emoji_id=get_emoji_icon('redeem_icon'),
            style="success"
        )],
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "redeem_coupon")
async def redeem_coupon_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🎟 <b>Please enter your VIP / Promo redeem code below:</b>", reply_markup=back_kb("menu_profile"), parse_mode='HTML')
    await state.set_state(UserStates.wait_for_redeem)

@dp.message(UserStates.wait_for_redeem)
async def process_redeem(m: Message, state: FSMContext):
    code = m.text.strip().upper()
    user_id = m.from_user.id
    if db_query("SELECT * FROM redeemed WHERE user_id=? AND code=?", (user_id, code), fetchone=True):
        await m.answer("❌ Anti-Fraud Alert: You already redeemed this unique code!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
        await state.clear()
        return
    coupon = db_query("SELECT amount, uses_left FROM coupons WHERE code=?", (code,), fetchone=True)
    if not coupon: await m.answer("❌ Invalid or Expired Code!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    elif coupon[1] <= 0: await m.answer("❌ This code's usage limit has been fully claimed by other users.", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    else:
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (coupon[0], user_id))
        db_query("UPDATE coupons SET uses_left = uses_left - 1 WHERE code=?", (code,))
        db_query("INSERT INTO redeemed (user_id, code) VALUES (?, ?)", (user_id, code))
        log_activity(user_id, "PROMO_REDEEMED", f"Code: {code}, Amount: {coupon[0]}")
        await m.answer(f"🎉 <b>Success!</b>\nSafely added {fmt_curr(coupon[0])} to your balance!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
        try:
            user_info = db_query("SELECT first_name FROM users WHERE user_id=?", (user_id,), fetchone=True)
            uname = user_info[0] if user_info else "Unknown User"
            await bot.send_message(ADMIN_ID, f"🎟 <b>PROMO CODE REDEEMED!</b>\n👤 User: {uname} (<code>{user_id}</code>)\n🔖 Code: <b>{code}</b>\n💵 Amount: {fmt_curr(coupon[0])}", parse_mode='HTML')
        except Exception: pass
    await state.clear()

@dp.callback_query(F.data == "menu_referral")
async def show_referral(call: CallbackQuery):
    u = db_query("SELECT referrals_count, referral_earned FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{call.from_user.id}"
    text = (f"{get_emoji('referral')} <b><u>AFFILIATE PROGRAM</u></b> {get_emoji('referral')}\n\n✅ <b>Status:</b> ACTIVE\n💰 Earn <b>15% flat commission</b> on every successful purchase made by your referred friends!\n\n📊 <b>YOUR STATS:</b>\n👥 Total Invited: {u[0]}\n💵 Life-time Earned: {fmt_curr(u[1])}\n\n🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>\n\n<i>Simply copy and share this link to start earning!</i>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

# ==============================================================================
# 16. LUDO / DICE SPIN
# ==============================================================================
@dp.callback_query(F.data == "menu_spin_landing")
async def lucky_spin_landing(call: CallbackQuery):
    status_check = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    spin_status = status_check[0] if status_check else "ON"
    if spin_status == "OFF": return await call.answer("⚠️ Lucky Ludo Spin is currently disabled by Admin.", show_alert=True)
    await call.message.edit_text(f"{get_emoji('ludo_spin')} <b><u>— LUDO SPIN —</u></b> {get_emoji('ludo_spin')}\n\nTest your luck! You can spin once every 24 hours.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Spin Dice Now!", callback_data="execute_spin", style="success")], 
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ]), parse_mode='HTML')

@dp.callback_query(F.data == "execute_spin")
async def execute_spin(call: CallbackQuery):
    status_check = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    if status_check and status_check[0] == "OFF": return await call.answer("⚠️ Lucky Spin is disabled.", show_alert=True)
    u = db_query("SELECT last_spin, balance, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    now = datetime.now()
    if u[0] and now < datetime.strptime(u[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        return await call.message.edit_text("❌ <b>Cooldown Active!</b>\nYou already played today. Come back tomorrow.", reply_markup=back_kb(), parse_mode='HTML')
    await call.message.delete()
    dice_msg = await bot.send_dice(chat_id=call.message.chat.id, emoji="🎲")
    await asyncio.sleep(SPIN_DELAY_SECONDS) 
    dice_val = dice_msg.dice.value
    limit_check = db_query("SELECT value FROM settings WHERE key='daily_spin_limit'", fetchone=True)
    limit = safe_float(limit_check[0]) if limit_check else 50.0
    rewards_db = db_query("SELECT amount FROM spin_rewards WHERE amount <= ?", (limit,), fetchall=True)
    rewards_list = [r[0] for r in rewards_db] if rewards_db else [0.0]
    reward = random.choice(rewards_list)
    if bool(u[2]) and reward > 0: reward = reward * 2.0
    new_bal = u[1] + reward
    db_query("UPDATE users SET balance=?, last_spin=? WHERE user_id=?", (new_bal, now.strftime("%Y-%m-%d %H:%M:%S"), call.from_user.id))
    log_activity(call.from_user.id, "PLAYED_SPIN", f"Reward: {reward}, Dice: {dice_val}")
    msg = get_ui_text("lucky_dice_result", dice_value=dice_val, won_amount=fmt_curr(reward), new_balance=fmt_curr(new_bal))
    if bool(u[2]) and reward > 0: msg += "\n\n<i>🌟 VIP Bonus: 2x Multiplier Applied!</i>"
    await dice_msg.reply(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📚 BACK TO MENU", callback_data="back_main", style="success")]]), parse_mode='HTML')

# ==============================================================================
# 17. TUTORIALS & SUPPORT
# ==============================================================================
@dp.callback_query(F.data == "menu_how_to")
async def tutorial_system(call: CallbackQuery):
    video_link_query = db_query("SELECT value FROM settings WHERE key='how_to_video'", fetchone=True)
    video_link = video_link_query[0] if video_link_query and video_link_query[0] != 'None' else None
    text = (f"{get_emoji('tutorial')} <b><u>— TUTORIALS & GUIDE —</u></b> {get_emoji('tutorial')}\n\n1️⃣ Add funds via <b>Add Balance</b>\n2️⃣ Navigate to <b>Buy Key</b>\n3️⃣ Choose your desired Panel and Package validity.\n4️⃣ The Key and Installation APK link will be instantly provided.")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if video_link: kb.inline_keyboard.append([InlineKeyboardButton(text="Watch Full Video Tutorial", url=video_link, icon_custom_emoji_id=get_emoji_icon("tutorial"), style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "menu_support")
async def support_center(call: CallbackQuery):
    telegram_link = get_setting("support_telegram", "https://t.me/YourSupport")
    whatsapp_link = get_setting("support_whatsapp", "https://wa.me/YourNumber")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Contact on Telegram", url=telegram_link, icon_custom_emoji_id=get_emoji_icon("telegram"), style="primary")],
        [InlineKeyboardButton(text="Contact on WhatsApp", url=whatsapp_link, icon_custom_emoji_id=get_emoji_icon("whatsapp"), style="primary")],
        [InlineKeyboardButton(text="🎫 Open New Ticket", callback_data="open_ticket", style="success"), InlineKeyboardButton(text="📋 My Open Tickets", callback_data="my_tickets", style="success")], 
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(f"{get_emoji('telegram')}{get_emoji('whatsapp')} <b><u>— PREMIUM SUPPORT CENTER —</u></b>\n\nContact us via Telegram or WhatsApp for instant help, or open a support ticket for admin assistance.", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "my_tickets")
async def view_my_tickets(call: CallbackQuery):
    tickets = db_query("SELECT id, message, status, created_at FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 5", (call.from_user.id,), fetchall=True)
    if not tickets: return await call.message.edit_text("📋 You do not have any active or previous support tickets.", reply_markup=back_kb("menu_support"), parse_mode='HTML')
    text = "📋 <b><u>— Your Recent Tickets —</u></b> 📋\n\n"
    for t in tickets:
        status_icon = "🟢" if t[2] == 'Open' else "🔴"
        text += f"🎫 <b>Ticket #{t[0]}</b> | Status: {status_icon} <b>{t[2]}</b>\n📅 <i>{t[3]}</i>\n📝 <i>{t[1][:80]}...</i>\n\n"
    await call.message.edit_text(text, reply_markup=back_kb("menu_support"), parse_mode='HTML')

@dp.callback_query(F.data == "open_ticket")
async def open_ticket_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 <b>Please type your issue/message below in detail:</b>", reply_markup=back_kb("menu_support"), parse_mode='HTML')
    await state.set_state(UserStates.wait_for_ticket)

@dp.message(UserStates.wait_for_ticket)
async def process_ticket(m: Message, state: FSMContext):
    db_query("INSERT INTO tickets (user_id, message, created_at) VALUES (?, ?, ?)", (m.from_user.id, m.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    await m.answer("✅ <b>Ticket Submitted Successfully!</b> Admins will reply soon.", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    try: await bot.send_message(ADMIN_ID, f"🚨 <b>NEW SUPPORT TICKET</b>\nFrom: <code>{m.from_user.id}</code>\nMsg: {m.text}", parse_mode='HTML')
    except: pass
    log_activity(m.from_user.id, "OPENED_TICKET")
    await state.clear()

# ==============================================================================
# 18. ADMIN PANEL
# ==============================================================================
@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    await message.answer("⚙️ <b>Advanced Admin Terminal</b>\n<i>Authorized Access Granted.</i>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_panel_back")
async def back_to_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ <b>Advanced Admin Terminal</b>\n<i>Authorized Access Granted.</i>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_toggle_vip_sys")
async def toggle_vip_sys(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    current = res[0] if res else 'OFF'
    new_status = 'ON' if current == 'OFF' else 'OFF'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('vip_status', ?)", (new_status,))
    await call.message.edit_reply_markup(reply_markup=admin_kb())

@dp.callback_query(F.data == "admin_user_control_start")
async def admin_user_control_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Download Full User List", callback_data="admin_download_userlist", style="success")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("💻 <b>User Control Terminal</b>\n\n✏️ Enter the <b>User ID</b> or <b>@Username</b> you want to investigate or manage:\n\n👇 <b>OR</b> download the full user CSV format list:", reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.manage_target_user)

@dp.callback_query(F.data == "admin_download_userlist")
async def admin_download_userlist(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    users = db_query("SELECT username, user_id, phone, balance, orders_count, is_vip, is_reseller FROM users", fetchall=True)
    if not users: return await call.answer("❌ No users found in the database.", show_alert=True)
    file_content = "FULL DATABASE DUMP\n" + "="*100 + "\n"
    for u in users:
        uname = u[0] if u[0] else "No_Username"
        uid = u[1]
        phone = u[2] if u[2] else "No_Phone"
        bal = u[3]
        orders = u[4]
        vip_status = "YES" if u[5] else "NO"
        res_status = "YES" if u[6] else "NO"
        file_content += f"UID: {uid} | UNAME: {uname} | PHONE: {phone} | BAL: ₹{bal:.2f} | BUY: {orders} | VIP: {vip_status} | RES: {res_status}\n"
    doc = BufferedInputFile(file_content.encode('utf-8'), filename=f"DB_{datetime.now().strftime('%Y%m%d')}.txt")
    await call.message.answer_document(document=doc, caption="📋 <b>Database export complete.</b>", parse_mode='HTML')
    await call.answer()

@dp.message(AdminStates.manage_target_user)
async def process_user_lookup(m: Message, state: FSMContext):
    target = m.text.strip()
    if target.startswith('@'): target = target[1:]
    loader_msg = await hacker_loading(m, "Querying User Database")
    user_q = db_query("SELECT user_id, first_name, username, balance, is_reseller, orders_count, spent, joined_date, is_banned, warnings, is_vip FROM users WHERE user_id=? OR username=? COLLATE NOCASE", (target, target), fetchone=True)
    if not user_q: return await loader_msg.edit_text("❌ Target not found in the grid. Check ID/Username syntax.", reply_markup=admin_back_kb(), parse_mode='HTML')
    u_id, u_name, u_user, bal, is_res, orders, spent, joined, is_banned, warnings, is_vip = user_q
    await state.update_data(target_u_id=u_id)
    status_emoji = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
    tags = []
    if is_res: tags.append("👑 Reseller")
    if is_vip: tags.append("🌟 VIP")
    type_str = " | ".join(tags) if tags else "👤 Regular"
    text = (f"🛡 <b><u>USER CONTROL TERMINAL</u></b> 🛡\n━━━━━━━━━━━━━━━━━━\n📛 <b>Name:</b> {u_name} (@{u_user})\n🆔 <b>ID:</b> <code>{u_id}</code>\n📊 <b>Status:</b> {status_emoji}\n🔰 <b>Type:</b> {type_str}\n⚠️ <b>Warnings Issued:</b> {warnings}\n━━━━━━━━━━━━━━━━━━\n💰 <b>Wallet Balance:</b> {fmt_curr(bal)}\n📦 <b>Orders:</b> {orders} | 💸 <b>Total Spent:</b> {fmt_curr(spent)}\n📅 <b>Joined:</b> {joined}")
    ban_btn_text = "Unban ✅" if is_banned else "Ban 🚫"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add Funds ➕", callback_data=f"usrctrl_add_{u_id}", style="success"), InlineKeyboardButton(text="Minus Funds ➖", callback_data=f"usrctrl_min_{u_id}", style="danger")],
        [InlineKeyboardButton(text=ban_btn_text, callback_data=f"usrctrl_ban_{u_id}", style="danger"), InlineKeyboardButton(text="Warn User ⚠️", callback_data=f"usrctrl_warn_{u_id}", style="danger")],
        [InlineKeyboardButton(text="Give VIP 🌟" if not is_vip else "Remove VIP 🚫", callback_data=f"usrctrl_vip_{u_id}", style="success")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await loader_msg.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("usrctrl_"))
async def handle_user_actions(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    action = call.data.split("_")[1]
    u_id = int(call.data.split("_")[2])
    await state.update_data(target_u_id=u_id)
    if action == "ban":
        current_status = db_query("SELECT is_banned FROM users WHERE user_id=?", (u_id,), fetchone=True)[0]
        if current_status == 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Yes, Ban", callback_data=f"confirm_ban_{u_id}", style="danger"), InlineKeyboardButton(text="❌ Cancel", callback_data="admin_user_control_start", style="danger")]
            ])
            await call.message.edit_text(f"⚠️ Are you sure you want to <b>BAN</b> user <code>{u_id}</code>?", reply_markup=kb, parse_mode='HTML')
            await state.set_state(AdminStates.confirm_ban)
        else:
            db_query("UPDATE users SET is_banned=0 WHERE user_id=?", (u_id,))
            await call.answer("✅ User unbanned successfully!", show_alert=True)
            m = call.message; m.text = str(u_id); await process_user_lookup(m, state)
    elif action == "vip":
        current_status = db_query("SELECT is_vip FROM users WHERE user_id=?", (u_id,), fetchone=True)[0]
        if current_status == 1:
            db_query("UPDATE users SET is_vip=0 WHERE user_id=?", (u_id,))
            await call.answer("✅ VIP Removed!", show_alert=True)
        else:
            db_query("UPDATE users SET is_vip=1, vip_since=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d"), u_id))
            await call.answer("✅ VIP Granted!", show_alert=True)
        m = call.message; m.text = str(u_id); await process_user_lookup(m, state)
    elif action == "add":
        await call.message.edit_text("💰 Enter the amount to <b>ADD</b> to this user's wallet:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_add_money)
    elif action == "min":
        await call.message.edit_text("💸 Enter the amount to <b>DEDUCT</b> from this user's wallet:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_minus_money)
    elif action == "warn":
        await call.message.edit_text("⚠️ Type the strict warning message you want to send directly to this user:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_warning)

@dp.callback_query(F.data.startswith("confirm_ban_"))
async def confirm_ban(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    u_id = int(call.data.split("_")[2])
    db_query("UPDATE users SET is_banned=1 WHERE user_id=?", (u_id,))
    await call.answer("🔴 User has been banned!", show_alert=True)
    await state.clear()
    m = call.message; m.text = str(u_id); await process_user_lookup(m, state)

@dp.message(AdminStates.wait_for_add_money)
async def exec_add_money(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        data = await state.get_data()
        u_id = data['target_u_id']
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
        await m.answer(f"✅ Successfully added {fmt_curr(amt)} to target <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
        try: await bot.send_message(u_id, f"💰 <b>Wallet Top-up!</b>\nAdmin has manually added {fmt_curr(amt)} to your wallet.", parse_mode='HTML')
        except: pass
        await state.clear()
    except ValueError: await m.answer("❌ Critical Error: Input must be a valid number.")

@dp.message(AdminStates.wait_for_minus_money)
async def exec_minus_money(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        data = await state.get_data()
        u_id = data['target_u_id']
        db_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (amt, u_id))
        await m.answer(f"✅ Successfully deducted {fmt_curr(amt)} from target <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Critical Error: Input must be a valid number.")

@dp.message(AdminStates.wait_for_warning)
async def exec_warn_user(m: Message, state: FSMContext):
    data = await state.get_data()
    u_id = data['target_u_id']
    warn_text = m.text
    db_query("UPDATE users SET warnings = warnings + 1 WHERE user_id=?", (u_id,))
    await m.answer(f"✅ Official warning dispatched to <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
    try: await bot.send_message(u_id, f"⚠️ <b>OFFICIAL WARNING FROM SYSTEM ADMIN:</b>\n\n{warn_text}\n\n<i>Subsequent infractions may lead to an automated grid ban.</i>", parse_mode='HTML')
    except: pass
    await state.clear()

# ==============================================================================
# 19. ADMIN STATISTICS
# ==============================================================================
@dp.callback_query(F.data == "admin_view_stats")
async def admin_dashboard_stats(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    t_users = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    t_resellers = db_query("SELECT COUNT(*) FROM users WHERE is_reseller=1", fetchone=True)[0]
    t_vip = db_query("SELECT COUNT(*) FROM users WHERE is_vip=1", fetchone=True)[0]
    t_prods = db_query("SELECT COUNT(*) FROM products", fetchone=True)[0]
    t_keys = db_query("SELECT COUNT(*) FROM product_keys WHERE is_used=0", fetchone=True)[0]
    t_rev = db_query("SELECT SUM(spent) FROM users", fetchone=True)[0] or 0.0
    today_str = datetime.now().strftime("%Y-%m-%d")
    t_spins = db_query("SELECT COUNT(*) FROM users WHERE last_spin LIKE ?", (f"{today_str}%",), fetchone=True)[0]
    msg = (f"📊 <b><u>GRID INTELLIGENCE DASHBOARD</u></b> 📊\n━━━━━━━━━━━━━━━━━━\n👥 <b>Total Grid Users:</b> {t_users}\n👑 <b>Wholesale Resellers:</b> {t_resellers}\n🌟 <b>Elite VIP Members:</b> {t_vip}\n━━━━━━━━━━━━━━━━━━\n📦 <b>Active Products:</b> {t_prods}\n🔑 <b>Unused Keys in Vault:</b> {t_keys}\n💰 <b>Total Gross Revenue:</b> {fmt_curr(t_rev)}\n🎰 <b>Ludo Spins Today:</b> {t_spins}\n━━━━━━━━━━━━━━━━━━")
    await call.message.edit_text(msg, reply_markup=admin_back_kb(), parse_mode='HTML')

# ==============================================================================
# =============================================================================
# PRODUCT MAINTENANCE — imported concept from SAGAR_MODS_API.zip
# =============================================================================
@dp.callback_query(F.data == "admin_product_maintenance")
async def admin_product_maintenance_list(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    # Maintenance is managed per PANEL NAME (the same name configured in Set Panel Emojis),
    # not per duration/package row. Each panel name is shown exactly once.
    rows = db_query("""SELECT panel_name, MIN(id), MAX(maintenance)
                      FROM products
                      WHERE is_active=1 AND TRIM(COALESCE(panel_name,'')) != ''
                      GROUP BY LOWER(TRIM(panel_name))
                      ORDER BY panel_name COLLATE NOCASE""", fetchall=True) or []
    if not rows:
        return await call.message.edit_text("📦 No products found.", reply_markup=admin_back_kb(), parse_mode="HTML")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for panel, prod_id, maintenance in rows:
        panel = str(panel or '').strip()
        icon_id = get_panel_emoji(panel) or get_emoji_icon("product_store")
        status = "🔴" if maintenance else "🟢"
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f"{status} {panel[:60]}",
            callback_data=f"admin_maint_product_{prod_id}",
            icon_custom_emoji_id=icon_id,
            style="danger" if maintenance else "success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel_back", style="danger")])
    await call.message.edit_text(
        "🛠 <b>PRODUCT MAINTENANCE CONTROL</b>\n\nEach panel name from <b>Set Panel Emojis</b> is shown only once. Clicking a panel toggles maintenance for every product/duration under that same panel name and blocks purchases while ON.",
        reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("admin_maint_product_"))
async def admin_maint_product_detail(call: CallbackQuery):
    # Toggle all duration/product rows under the selected panel name; no timing/details page.
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    try:
        prod_id = int(call.data.rsplit("_", 1)[1])
    except ValueError:
        return await call.answer("Invalid product.", show_alert=True)
    row = db_query("SELECT panel_name FROM products WHERE id=?", (prod_id,), fetchone=True)
    if not row:
        return await call.answer("Product not found.", show_alert=True)
    panel = str(row[0] or '').strip()
    state_row = db_query("SELECT MAX(maintenance) FROM products WHERE LOWER(TRIM(COALESCE(panel_name,'')))=LOWER(TRIM(?))", (panel,), fetchone=True)
    new_state = 0 if (state_row and bool(state_row[0])) else 1
    db_query("UPDATE products SET maintenance=? WHERE LOWER(TRIM(COALESCE(panel_name,'')))=LOWER(TRIM(?))", (new_state, panel))
    await call.answer("🔴 Panel set to MAINTENANCE" if new_state else "🟢 Panel set AVAILABLE", show_alert=False)
    await admin_product_maintenance_list(call)

# 20. ADMIN PRODUCT MANAGEMENT
# ==============================================================================
@dp.callback_query(F.data == "admin_add_prod")
async def add_prod_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in FIXED_CATEGORIES:
        emoji_id = get_category_emoji(cat)
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"addprod_cat_{cat}", icon_custom_emoji_id=emoji_id, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("<b>Step 1:</b> Choose the <b>Category</b> for this product:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("addprod_cat_"))
async def add_prod_category_selected(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    category = call.data.split("addprod_cat_", 1)[1]
    await state.update_data(cat=category)
    await call.message.edit_text(f"<b>Step 2:</b> Enter <b>PANEL NAME</b>\n(e.g., 'MST PANEL', 'DRIP PANEL'):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.add_prod_panel_name)

@dp.message(AdminStates.add_prod_panel_name)
async def add_prod_panel_name(m: Message, state: FSMContext):
    await state.update_data(panel_name=m.text)
    await m.answer("<b>Step 3:</b> Enter <b>PACKAGE DURATION/DATE NAME</b>\n(e.g., '7 Days', '1 Month'):", parse_mode='HTML')
    await state.set_state(AdminStates.add_prod_name)

@dp.message(AdminStates.add_prod_name)
async def add_prod_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("⏳ Enter Time Validity String (e.g., '24 Hours'):", parse_mode='HTML')
    await state.set_state(AdminStates.add_prod_validity)

@dp.message(AdminStates.add_prod_validity)
async def add_prod_validity(m: Message, state: FSMContext):
    await state.update_data(validity=m.text)
    await m.answer("📱 Enter strict Device Enforcement Limit (e.g., '1 Device HWID'):", parse_mode='HTML')
    await state.set_state(AdminStates.add_prod_device_limit)

@dp.message(AdminStates.add_prod_device_limit)
async def add_prod_device_limit(m: Message, state: FSMContext):
    await state.update_data(device_limit=m.text)
    await m.answer("💰 Enter standard **User Price** in Rupees (₹) (e.g., 500):", parse_mode='HTML')
    await state.set_state(AdminStates.add_prod_price)

@dp.message(AdminStates.add_prod_price)
async def add_prod_price(m: Message, state: FSMContext):
    try:
        await state.update_data(price=float(m.text))
        await m.answer("👑 Enter wholesale **Reseller Price** in Rupees (₹) (e.g., 300):", parse_mode='HTML')
        await state.set_state(AdminStates.add_prod_reseller_price)
    except ValueError: await m.answer("❌ Invalid input datatype! Must be numerical.")

@dp.message(AdminStates.add_prod_reseller_price)
async def add_prod_reseller_price(m: Message, state: FSMContext):
    try:
        await state.update_data(reseller_price=float(m.text))
        await m.answer("🔗 Enter direct APK/Payload Download Link (or type 'none' to omit):", parse_mode='HTML')
        await state.set_state(AdminStates.add_prod_apk)
    except ValueError: await m.answer("❌ Invalid input datatype! Must be numerical.")

@dp.message(AdminStates.add_prod_apk)
async def add_prod_apk(m: Message, state: FSMContext):
    await state.update_data(apk="" if (m.text or "").strip().lower() == 'none' else (m.text or "").strip())
    await m.answer(
        "🔌 <b>API TARGET / PID</b>\n\n"
        "Send the <b>API Target Product ID (PID)</b> from the reseller API for automatic key generation.\n"
        "Example: <code>151</code>\n\n"
        "If this product should use manual keys, type <code>none</code>.",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.add_prod_api_pid)

@dp.message(AdminStates.add_prod_api_pid)
async def add_prod_api_pid(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    if txt.lower() in ("none", "no", "skip", ""):
        await state.update_data(api_pid="", api_duration="")
        await m.answer(
            "📥 <b>Manual Key Mode</b>\n\nPaste all license <b>Keys</b>, one key per line:",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.add_prod_keys)
        return
    await state.update_data(api_pid=txt)
    await m.answer(
        "⏱ Send the API <b>duration</b> exactly as supported by the API.\n"
        "Example: <code>1 Day</code>, <code>7 Days</code>, <code>1 Month</code>.\n\n"
        "Type <code>none</code> if the API PID does not need a duration.",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.add_prod_api_duration)

@dp.message(AdminStates.add_prod_api_duration)
async def add_prod_api_duration(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    duration = "" if txt.lower() in ("none", "no", "skip", "") else txt
    data = await state.get_data()
    db_query(
        "INSERT INTO products (category, panel_name, name, price_inr, reseller_price, stock, apk_link, validity, device_limit, api_product_id, api_duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data['cat'], data['panel_name'], data['name'], data['price'], data['reseller_price'], 999, data['apk'], data['validity'], data['device_limit'], data['api_pid'], duration)
    )
    await m.answer(
        f"✅ <b>Product Added with AUTO API KEY!</b>\n\n"
        f"📦 <b>Category:</b> {html_lib.escape(str(data['cat']))}\n"
        f"🧩 <b>Panel:</b> {html_lib.escape(str(data['panel_name']))}\n"
        f"📌 <b>Product:</b> {html_lib.escape(str(data['name']))}\n"
        f"💰 <b>User Price:</b> {fmt_curr(data['price'])}\n"
        f"👑 <b>Reseller Price:</b> {fmt_curr(data['reseller_price'])}\n"
        f"🔌 <b>API Target/PID:</b> <code>{html_lib.escape(data['api_pid'])}</code>"
        f"{' | ' + html_lib.escape(duration) if duration else ''}\n"
        "⚡ <b>Keys will be generated automatically on purchase.</b>",
        reply_markup=admin_kb(), parse_mode='HTML'
    )
    await state.clear()

@dp.message(AdminStates.add_prod_keys)
async def add_prod_keys(m: Message, state: FSMContext):
    keys = [k.strip() for k in m.text.strip().split('\n') if k.strip()]
    data = await state.get_data()
    stock = len(keys)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (category, panel_name, name, price_inr, reseller_price, stock, apk_link, validity, device_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (data['cat'], data['panel_name'], data['name'], data['price'], data['reseller_price'], stock, data['apk'], data['validity'], data['device_limit']))
    prod_id = c.lastrowid
    for k in keys: c.execute("INSERT INTO product_keys (product_id, key_text) VALUES (?, ?)", (prod_id, k))
    conn.commit()
    conn.close()
    await m.answer(f"✅ <b>Data Deployment Successful!</b>\n\n📦 Panel '{data['cat']}' -> Panel Name '{data['panel_name']}' -> Package '{data['name']}'\n🔒 Vault Stock: {stock} Keys injected.\n💰 User Price: {fmt_curr(data['price'])} | 👑 Reseller: {fmt_curr(data['reseller_price'])}", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_manage_prods")
async def admin_manage_prods(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    prods = db_query("SELECT id, name, category, panel_name, stock, is_active FROM products ORDER BY category, panel_name", fetchall=True)
    if not prods: return await call.message.edit_text("📦 Store Database is completely empty.", reply_markup=admin_back_kb(), parse_mode='HTML')
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in prods:
        status_dot = "🟢" if p[5] else "🔴"
        panel_name = p[3] if p[3] is not None else ""
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{status_dot} [{p[2]}] {panel_name} - {p[1]} (Stock: {p[4]})", callback_data=f"admin_view_p_{p[0]}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("📦 <b>Database Editor: Select Node to modify</b>", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("admin_view_p_"))
async def admin_view_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    try:
        p_id = int(call.data.split("_")[3])
        prod = db_query("SELECT * FROM products WHERE id=?", (p_id,), fetchone=True)
        if not prod: return await call.answer("❌ Architecture fault: Node lost!", show_alert=True)
        panel_name = prod[2] if prod[2] is not None else ""
        price_inr = safe_float(prod[4])
        reseller_price = safe_float(prod[5])
        text = (f"📦 <b><u>NODE DEEP DIVE DETAILS</u></b>\n━━━━━━━━━━━━━━━━━━\n<b>ID:</b> <code>{prod[0]}</code>\n<b>Panel Group:</b> {prod[1]}\n<b>Panel Name:</b> {panel_name}\n<b>Package Date/Time:</b> {prod[3]}\n<b>Standard Price:</b> {fmt_curr(price_inr)}\n👑 <b>Wholesale Price:</b> {fmt_curr(reseller_price)}\n<b>Vault Stock:</b> {prod[6]}\n<b>Payload Link:</b> {prod[7] if prod[7] else 'None'}\n<b>Time Config:</b> {prod[8]}\n<b>HWID Limit:</b> {prod[9]}\n<b>Visibility:</b> {'Active' if prod[10] else 'Hidden'}\n<b>API PID:</b> {html_lib.escape(str(prod[11] or 'Not set'))}\n<b>API Days/Duration:</b> {html_lib.escape(str(prod[12] or 'Not set'))}\n━━━━━━━━━━━━━━━━━━")
        toggle_btn_text = "Hide Product 👁‍🗨" if prod[10] else "Unhide Product 👁"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Edit Panel Group 🏷️", callback_data=f"edit_p_{p_id}_cat", style="primary"), InlineKeyboardButton(text="Edit Panel Name 🏷️", callback_data=f"edit_p_{p_id}_panel_name", style="primary")],
            [InlineKeyboardButton(text="Edit Package Name ✏️", callback_data=f"edit_p_{p_id}_name", style="primary")],
            [InlineKeyboardButton(text="Edit Price 💰", callback_data=f"edit_p_{p_id}_price", style="primary"), InlineKeyboardButton(text="Edit R-Price 👑", callback_data=f"edit_p_{p_id}_rprice", style="primary")],
            [InlineKeyboardButton(text="Edit Validity ⏳", callback_data=f"edit_p_{p_id}_validity", style="primary"), InlineKeyboardButton(text="Edit Device 📱", callback_data=f"edit_p_{p_id}_device", style="primary")],
            [InlineKeyboardButton(text="Edit APK Link 🔗", callback_data=f"edit_p_{p_id}_apk", style="primary"), InlineKeyboardButton(text="Add Keys ➕", callback_data=f"edit_p_{p_id}_keys", style="success")],
            [InlineKeyboardButton(text="Edit API PID 🔌", callback_data=f"edit_p_{p_id}_api_pid", style="primary"), InlineKeyboardButton(text="Edit API Days ⏳", callback_data=f"edit_p_{p_id}_api_duration", style="primary")],
            [InlineKeyboardButton(text="Delete Key 🗑", callback_data=f"delkey_p_{p_id}", style="danger"), InlineKeyboardButton(text=toggle_btn_text, callback_data=f"toggle_p_{p_id}", style="primary")],
            [InlineKeyboardButton(text="Nuke Full Node 🗑", callback_data=f"delete_p_{p_id}", style="danger"), InlineKeyboardButton(text="BACK", callback_data="admin_manage_prods", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
        ])
        await call.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in admin_view_product: {e}")
        await call.message.edit_text(f"❌ Error loading product: {str(e)}", reply_markup=admin_back_kb(), parse_mode='HTML')

@dp.callback_query(F.data.startswith("toggle_p_"))
async def admin_toggle_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    p_id = int(call.data.split("_")[2])
    current = db_query("SELECT is_active FROM products WHERE id=?", (p_id,), fetchone=True)[0]
    new_val = 0 if current == 1 else 1
    db_query("UPDATE products SET is_active=? WHERE id=?", (new_val, p_id))
    await call.answer("Visibility updated successfully!", show_alert=True)
    await admin_view_product(call)

# ==============================================================================
# FIX: Edit product field – correctly handle different data types and multi-word fields
# ==============================================================================
@dp.callback_query(F.data.startswith("edit_p_"))
async def start_edit_product(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    # Use split with maxsplit=3 to keep field name intact (may contain underscores)
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        return await call.answer("Invalid callback data.", show_alert=True)
    p_id = int(parts[2])
    field = parts[3]
    await state.update_data(edit_p_id=p_id, edit_field=field)
    if field == 'keys':
        await call.message.edit_text("📥 <b>Vault Injection</b>\nPaste the <b>NEW KEYS</b> to append to the stock (1 key per line):", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_add_keys)
    else:
        field_name_map = {'cat': 'New Panel Group/Category Name', 'panel_name': 'New Panel Name', 'name': 'New Package/Date Name', 'price': 'New Standard Price in ₹', 'rprice': 'New Reseller Price in ₹', 'validity': 'New Time Validity String', 'device': 'New HWID Limit String', 'apk': 'New Payload Link (or type "none")', 'api_pid': 'New API Target / PID (type none to unlink)', 'api_duration': 'New API Days / Duration (type none to clear)'}
        await call.message.edit_text(f"✏️ Input the required data for: <b>{field_name_map.get(field, field)}</b>", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_new_value)

@dp.message(AdminStates.wait_for_new_value)
async def process_edit_value(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['edit_p_id']; field = data['edit_field']; new_val = m.text.strip()
    
    # Convert price fields to float, others remain strings
    if field in ['price', 'rprice']:
        try:
            new_val = float(new_val)
        except ValueError:
            return await m.answer("❌ Invalid number format. Please enter a valid price (e.g., 500).")
    elif field in ['apk', 'api_pid', 'api_duration']:
        new_val = "" if new_val.lower() in ('none', 'no', 'skip') else new_val
    # For panel_name, cat, name, validity, device – keep as string
    
    db_col_map = {'cat': 'category', 'panel_name': 'panel_name', 'name': 'name', 'price': 'price_inr', 'rprice': 'reseller_price', 'validity': 'validity', 'device': 'device_limit', 'apk': 'apk_link', 'api_pid': 'api_product_id', 'api_duration': 'api_duration'}
    db_query(f"UPDATE products SET {db_col_map[field]}=? WHERE id=?", (new_val, p_id))
    await m.answer("✅ <b>Node updated gracefully!</b>", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.message(AdminStates.wait_for_add_keys)
async def process_add_keys(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['edit_p_id']
    keys = [k.strip() for k in m.text.strip().split('\n') if k.strip()]
    if len(keys) == 0: return await m.answer("❌ Protocol breach: Zero valid keys found.", reply_markup=admin_kb(), parse_mode='HTML')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for k in keys: c.execute("INSERT INTO product_keys (product_id, key_text) VALUES (?, ?)", (p_id, k))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(keys), p_id))
    conn.commit(); conn.close()
    await m.answer(f"✅ <b>Vault Secure!</b> {len(keys)} new keys appended and encrypted.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data.startswith("delete_p_"))
async def admin_delete_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    p_id = int(call.data.split("_")[2])
    db_query("DELETE FROM products WHERE id=?", (p_id,))
    db_query("DELETE FROM product_keys WHERE product_id=?", (p_id,))
    await call.answer("☢️ Nuclear wipe successful! Node and vault deleted.", show_alert=True)
    await admin_manage_prods(call)

@dp.callback_query(F.data.startswith("delkey_p_"))
async def admin_delete_key_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    p_id = int(call.data.split("_")[2])
    await state.update_data(del_p_id=p_id)
    await call.message.edit_text("🗑 Send the <b>exact string match</b> of the key you wish to purge from the vault:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_delete_key)

@dp.message(AdminStates.wait_for_delete_key)
async def process_delete_key(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['del_p_id']
    key_to_delete = m.text.strip()
    key_data = db_query("SELECT id, is_used FROM product_keys WHERE product_id=? AND key_text=?", (p_id, key_to_delete), fetchone=True)
    if not key_data: return await m.answer("❌ Key not found. Check logs and try again.", reply_markup=admin_back_kb(), parse_mode='HTML')
    if key_data[1] == 1: return await m.answer("⚠️ Action Blocked: This key has already been dispatched to a user.", reply_markup=admin_back_kb(), parse_mode='HTML')
    db_query("DELETE FROM product_keys WHERE id=?", (key_data[0],))
    db_query("UPDATE products SET stock = stock - 1 WHERE id=?", (p_id,))
    await m.answer(f"✅ Key <code>{key_to_delete}</code> securely purged from vault.\n📦 Database indices updated.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# 21. ADMIN TICKETS, BROADCAST, COUPONS
# ==============================================================================
@dp.callback_query(F.data == "admin_view_tickets")
async def admin_view_tickets(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    tickets = db_query("SELECT id, user_id, message, created_at FROM tickets WHERE status='Open' LIMIT 1", fetchall=True)
    if not tickets: return await call.answer("✅ Zero pending issues. Grid is clean!", show_alert=True)
    t = tickets[0]
    text = (f"🎫 <b><u>ACTIVE TICKET #{t[0]}</u></b>\n👤 <b>Origin UID:</b> <code>{t[1]}</code>\n📅 <b>Timestamp:</b> {t[3]}\n\n📝 <b>Payload:</b>\n{t[2]}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Formulate Reply", callback_data=f"reply_ticket_{t[0]}_{t[1]}", style="primary")],
        [InlineKeyboardButton(text="❌ Force Close Ticket", callback_data=f"close_ticket_{t[0]}", style="danger")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket(call: CallbackQuery):
    ticket_id = call.data.split("_")[2]
    db_query("UPDATE tickets SET status='Closed' WHERE id=?", (ticket_id,))
    await call.answer("✅ Status set to Closed.", show_alert=True)
    await admin_view_tickets(call) 

@dp.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket_start(call: CallbackQuery, state: FSMContext):
    data = call.data.split("_")
    ticket_id, user_id = data[2], data[3]
    await state.update_data(ticket_id=ticket_id, user_id=user_id)
    await call.message.edit_text(f"💬 Formulating reply for node <code>{user_id}</code>.\n\nType your message payload:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.ticket_reply_msg)

@dp.message(AdminStates.ticket_reply_msg)
async def send_ticket_reply(m: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.send_message(data['user_id'], f"📞 <b>Admin Reply (Ref #{data['ticket_id']}):</b>\n\n{m.text}", parse_mode='HTML')
        db_query("UPDATE tickets SET status='Closed' WHERE id=?", (data['ticket_id'],))
        await m.answer("✅ Payload delivered and connection closed successfully.", reply_markup=admin_kb(), parse_mode='HTML')
    except Exception as e: await m.answer(f"❌ Transmission Error: {e}", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast_btn")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📢 <b>Mass Broadcast Protocol</b>\n\nSend the rich message payload you wish to transmit globally across the grid:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.broadcast_msg)

@dp.message(AdminStates.broadcast_msg)
async def admin_broadcast_send(message: Message, state: FSMContext):
    users = db_query("SELECT user_id FROM users", fetchall=True)
    sent, failed = 0, 0
    m = await message.answer("⏳ Broadcast protocol initiated... Do not interrupt.", parse_mode='HTML')
    for u in users:
        try:
            await message.send_copy(chat_id=u[0])
            sent += 1
        except Exception: failed += 1
        await asyncio.sleep(0.06) 
    await m.edit_text(f"✅ <b>Global Broadcast Complete!</b>\n\n🟢 Nodes reached: {sent}\n🔴 Nodes failed/blocked: {failed}", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_create_coupon")
async def admin_create_coupon_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🎟 Enter a highly secure alphanumeric sequence for the Promo Code:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.add_coupon_code)

@dp.message(AdminStates.add_coupon_code)
async def admin_coupon_code(m: Message, state: FSMContext):
    await state.update_data(code=m.text.strip().upper())
    await m.answer("💰 Enter the monetary reward payload in <b>RUPEES (₹)</b>:", parse_mode='HTML')
    await state.set_state(AdminStates.add_coupon_amount)

@dp.message(AdminStates.add_coupon_amount)
async def admin_coupon_amount(m: Message, state: FSMContext):
    try:
        await state.update_data(amount=float(m.text)) 
        await m.answer("👥 Enter the exact maximum threshold uses for this code:", parse_mode='HTML')
        await state.set_state(AdminStates.add_coupon_uses)
    except ValueError: await m.answer("❌ Non-numerical data detected. Aborting.")

@dp.message(AdminStates.add_coupon_uses)
async def admin_coupon_uses(m: Message, state: FSMContext):
    try:
        uses = int(m.text)
        data = await state.get_data()
        db_query("INSERT OR REPLACE INTO coupons (code, amount, uses_left) VALUES (?, ?, ?)", (data['code'], data['amount'], uses))
        await m.answer(f"✅ Protocol <b>{data['code']}</b> encoded!\nReward Vector: {fmt_curr(data['amount'])}\nThreshold Limit: {uses} executions.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Non-numerical data detected. Aborting.")

# ==============================================================================
# 22. ADMIN RESELLER & SPIN SETTINGS
# ==============================================================================
@dp.callback_query(F.data == "admin_reseller_menu")
async def admin_reseller_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    sys_status = status_check[0] if status_check else "ON"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Grant Reseller Rights", callback_data="reseller_make", style="success"), InlineKeyboardButton(text="➖ Revoke Reseller", callback_data="reseller_remove", style="danger")],
        [InlineKeyboardButton(text="📋 Audit Active Resellers", callback_data="reseller_view", style="primary")],
        [InlineKeyboardButton(text=f"{'🟢' if sys_status == 'ON' else '🔴'} Auto-Upgrade System: {sys_status}", callback_data="admin_toggle_reseller_sys", style="success" if sys_status == 'ON' else "danger")], 
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("👑 <b>Wholesale Reseller Protocols</b>\nSelect administrative action:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "admin_toggle_reseller_sys")
async def toggle_reseller_sys(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('reseller_system_status', ?)", (new_status,))
    await admin_reseller_menu(call)

@dp.callback_query(F.data.in_(["reseller_make", "reseller_remove"]))
async def reseller_prompt_id(call: CallbackQuery, state: FSMContext):
    action = call.data
    await state.update_data(reseller_action=action)
    await call.message.edit_text("👤 Identify target node. Input <b>User ID</b> or <b>@username</b>:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.reseller_manage_id)

@dp.message(AdminStates.reseller_manage_id)
async def process_reseller_manage(m: Message, state: FSMContext):
    data = await state.get_data()
    target = m.text.strip()
    if target.startswith('@'): target = target[1:]
    user_q = db_query("SELECT user_id, first_name FROM users WHERE user_id=? OR username=? COLLATE NOCASE", (target, target), fetchone=True)
    if not user_q: return await m.answer("❌ Target completely ghosted. Not in database.", reply_markup=admin_back_kb(), parse_mode='HTML')
    u_id, u_name = user_q[0], user_q[1]
    if data['reseller_action'] == "reseller_make":
        db_query("UPDATE users SET is_reseller=1, reseller_since=?, account_type='Reseller' WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d"), u_id))
        await m.answer(f"✅ Credentials upgraded. <b>{u_name}</b> (<code>{u_id}</code>) has reseller rights.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        db_query("UPDATE users SET is_reseller=0, account_type='Regular' WHERE user_id=?", (u_id,))
        await m.answer(f"✅ Credentials revoked. <b>{u_name}</b> (<code>{u_id}</code>) is back to regular user.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "reseller_view")
async def reseller_view(call: CallbackQuery):
    resellers = db_query("SELECT user_id, first_name, username FROM users WHERE is_reseller=1", fetchall=True)
    if not resellers: return await call.message.edit_text("📋 Zero active resellers found.", reply_markup=admin_back_kb(), parse_mode='HTML')
    text = "👑 <b><u>ACTIVE RESELLER AUDIT LOG</u></b> 👑\n━━━━━━━━━━━━━━━━━━\n"
    for r in resellers:
        uname = f"(@{r[2]})" if r[2] else ""
        text += f"👤 {r[1]} {uname}\n🆔 <code>{r[0]}</code>\n\n"
    await call.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_spin_menu")
async def admin_spin_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    status = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    limit = db_query("SELECT value FROM settings WHERE key='daily_spin_limit'", fetchone=True)
    status_val = status[0] if status else 'ON'
    limit_val = limit[0] if limit else '50.0'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Append Reward Logic", callback_data="spin_add", style="success"), InlineKeyboardButton(text="❌ Drop Reward Logic", callback_data="spin_del", style="danger")],
        [InlineKeyboardButton(text="📋 Audit Configs", callback_data="spin_view", style="primary"), InlineKeyboardButton(text="⚙️ Throttle Limits", callback_data="spin_limit", style="primary")],
        [InlineKeyboardButton(text=f"{'🟢' if status_val == 'ON' else '🔴'} Master Toggle: {status_val}", callback_data="spin_toggle", style="success" if status_val == 'ON' else "danger")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(f"🎰 <b>Advanced Ludo/Spin Algorithms</b>\nCurrent Threshold: ₹{limit_val}", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "spin_toggle")
async def spin_toggle(call: CallbackQuery):
    res = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('spin_status', ?)", (new_status,))
    await admin_spin_menu(call)

@dp.callback_query(F.data == "admin_toggle_new_user_notification")
async def admin_toggle_new_user_notification(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    current = new_user_start_message_enabled()
    set_setting("new_user_start_message", "OFF" if current else "ON")
    await call.answer("New User Notification " + ("OFF" if current else "ON"))
    try:
        await call.message.edit_reply_markup(reply_markup=admin_kb())
    except Exception:
        await call.message.edit_text("⚙️ <b>Admin Control</b>", reply_markup=admin_kb(), parse_mode='HTML')


@dp.callback_query(F.data == "admin_toggle_bot")
async def toggle_bot(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (new_status,))
    await call.message.edit_reply_markup(reply_markup=admin_kb())

@dp.callback_query(F.data == "spin_add")
async def spin_add_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🎰 Inject new decimal logic limit (e.g. 15.50):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.spin_add_reward)

@dp.message(AdminStates.spin_add_reward)
async def spin_add_exec(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        db_query("INSERT INTO spin_rewards (amount) VALUES (?)", (amt,))
        await m.answer(f"✅ Algorithm updated. New vector {fmt_curr(amt)} injected.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Math parsing error.")

@dp.callback_query(F.data == "spin_view")
async def spin_view(call: CallbackQuery):
    rewards = db_query("SELECT amount FROM spin_rewards ORDER BY amount ASC", fetchall=True)
    text = "🎰 <b>Live Ludo Constants</b>\n\n"
    for r in rewards: text += f"🎁 {fmt_curr(r[0])}\n"
    await call.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "menu_all_files")
async def menu_all_files(call: CallbackQuery):
    """Show an intermediate Download Files page; do not open the admin URL directly from the main menu."""
    link = (get_setting("all_files_link", "None") or "None").strip()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if link.lower() != "none" and (link.startswith("http://") or link.startswith("https://")):
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="📥 Open Download Files",
                icon_custom_emoji_id=get_emoji_icon("download"),
                url=link,
                style="success"
            )
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="⚠️ Files Not Configured",
                callback_data="download_files_not_configured",
                style="danger"
            )
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")
    ])
    text = (
        "📥 <b>DOWNLOAD FILES</b>\n\n"
        "Access the available files from the button below.\n"
        "Your files link is managed by the admin. 📦"
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "download_files_not_configured")
async def download_files_not_configured(call: CallbackQuery):
    await call.answer("⚠️ Download Files link is not configured yet.", show_alert=True)


@dp.callback_query(F.data == "menu_selling_proof")
async def menu_selling_proof(call: CallbackQuery):
    """Show an intermediate Selling Proof page; the admin-controlled URL opens only from the inner button."""
    link = (get_setting("selling_proof_link", "None") or "None").strip()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if link.lower() != "none" and (link.startswith("http://") or link.startswith("https://")):
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="🧾 Verify / View Selling Proof",
                icon_custom_emoji_id=get_emoji_icon("sagarproof"),
                url=link,
                style="success"
            )
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="⚠️ Proof Not Configured",
                callback_data="selling_proof_not_configured",
                style="danger"
            )
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")
    ])
    text = (
        "🧾 <b>SELLING PROOF</b>\n\n"
        "Check the available selling proof using the button below.\n"
        "The proof link is controlled by the admin. ✅"
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "selling_proof_not_configured")
async def selling_proof_not_configured(call: CallbackQuery):
    await call.answer("⚠️ Selling Proof link is not configured yet.", show_alert=True)


@dp.callback_query(F.data == "admin_set_product_demo")
async def admin_set_product_demo_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    # Use the same identity that the user-side Watch Demo handler uses:
    # panel_name when present, otherwise the product name. Do not filter by
    # is_active, because admins must also be able to configure demos for
    # currently hidden/inactive products. Group case-insensitively so each
    # identical name appears exactly once.
    rows = db_query("SELECT COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),'')) AS demo_name FROM products WHERE COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),'')) IS NOT NULL GROUP BY LOWER(TRIM(COALESCE(NULLIF(panel_name,''), NULLIF(name,'')))) ORDER BY MIN(COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),''))) COLLATE NOCASE", fetchall=True) or []
    if not rows:
        return await call.answer("No products found in the products database. Add products first.", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    demo_name_map = {}
    for row in rows:
        name = str(row[0]).strip()
        key = name.casefold()
        token = str(abs(hash(key)) % 10**10)
        demo_name_map[token] = name
        existing = db_query("SELECT file_id FROM product_demos WHERE product_name_key=?", (key,), fetchone=True)
        prefix = "✅" if existing else "🎬"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{prefix} {name}"[:64], callback_data="setdemo_" + token, style="success")])
    # Demo settings are stored in the existing settings table, so they survive restarts.
    auto_delete = get_setting("demo_auto_delete", "ON").upper() == "ON"
    delay_seconds = max(1, int(safe_float(get_setting("demo_delete_after_seconds", "60"), 60)))
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=f"Auto-Delete: {'ON 🟢' if auto_delete else 'OFF 🔴'}", callback_data="demo_toggle_auto_delete", style="success" if auto_delete else "danger"),
        InlineKeyboardButton(text=f"Delete After: {format_demo_delay(delay_seconds)}", callback_data="demo_set_delete_time", style="success")
    ])
    # Persist callback hash-to-name mapping in FSM data for this admin session.
    await state.update_data(demo_name_map=demo_name_map)
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel_back", style="danger")])
    await call.message.edit_text("🎬 <b>SET PRODUCT DEMO</b>\n\nChoose a product name to upload or replace its demo video. Same-name entries share one demo video.\n\n🗑 Auto-delete controls whether the sent demo message is removed. Set a custom delay in seconds, minutes, or hours.", reply_markup=kb, parse_mode="HTML")
    await call.answer()

def format_demo_delay(seconds: int) -> str:
    seconds = max(1, int(seconds))
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


@dp.callback_query(F.data.in_({"demo_toggle_auto_delete", "demo_set_delete_time"}))
async def admin_demo_settings(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    if call.data == "demo_toggle_auto_delete":
        current = get_setting("demo_auto_delete", "ON").upper()
        new_value = "OFF" if current == "ON" else "ON"
        set_setting("demo_auto_delete", new_value)
        await call.answer(f"Auto-delete {new_value}.")
        # Re-render the existing product selection menu.
        rows = db_query("SELECT COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),'')) AS demo_name FROM products WHERE COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),'')) IS NOT NULL GROUP BY LOWER(TRIM(COALESCE(NULLIF(panel_name,''), NULLIF(name,'')))) ORDER BY MIN(COALESCE(NULLIF(TRIM(panel_name),''), NULLIF(TRIM(name),''))) COLLATE NOCASE", fetchall=True) or []
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        demo_name_map = {}
        for row in rows:
            name = str(row[0]).strip()
            key = name.casefold()
            token = str(abs(hash(key)) % 10**10)
            demo_name_map[token] = name
            existing = db_query("SELECT file_id FROM product_demos WHERE product_name_key=?", (key,), fetchone=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{'✅' if existing else '🎬'} {name}"[:64], callback_data="setdemo_" + token, style="success")])
        await state.update_data(demo_name_map=demo_name_map)
        auto_delete = get_setting("demo_auto_delete", "ON").upper() == "ON"
        delay_seconds = max(1, int(safe_float(get_setting("demo_delete_after_seconds", "60"), 60)))
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"Auto-Delete: {'ON 🟢' if auto_delete else 'OFF 🔴'}", callback_data="demo_toggle_auto_delete", style="success" if auto_delete else "danger"),
            InlineKeyboardButton(text=f"Delete After: {format_demo_delay(delay_seconds)}", callback_data="demo_set_delete_time", style="success")
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back to Admin", callback_data="admin_panel_back", style="danger")])
        await call.message.edit_reply_markup(reply_markup=kb)
        return
    await state.set_state(AdminStates.wait_for_demo_delete_time)
    await call.message.answer(
        "⏱ <b>Set demo auto-delete delay</b>\nSend a time such as <code>30s</code>, <code>5m</code>, <code>1h</code>, or <code>2 hours</code>. A plain number means minutes. Maximum: 30 days.",
        parse_mode="HTML",
        reply_markup=admin_back_kb()
    )
    await call.answer()


@dp.message(AdminStates.wait_for_demo_delete_time)
async def admin_save_demo_delete_time(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    raw = (m.text or "").strip().lower()
    match = re.fullmatch(r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)?", raw)
    if not match:
        return await m.answer("❌ Invalid time. Examples: <code>30s</code>, <code>5m</code>, <code>1h</code>, or <code>2 hours</code>.", parse_mode="HTML")
    amount = int(match.group(1))
    unit = match.group(2) or "m"
    multiplier = 1 if unit.startswith("s") else (3600 if unit.startswith("h") else 60)
    seconds = amount * multiplier
    if seconds < 1 or seconds > 30 * 24 * 3600:
        return await m.answer("❌ Delay must be between 1 second and 30 days.")
    set_setting("demo_delete_after_seconds", str(seconds))
    await state.clear()
    await m.answer(f"✅ Demo auto-delete delay saved: <b>{format_demo_delay(seconds)}</b>.", parse_mode="HTML", reply_markup=admin_kb())


@dp.callback_query(F.data.startswith("setdemo_"))
async def admin_choose_demo_product(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    data = await state.get_data()
    name = (data.get("demo_name_map") or {}).get(call.data.split("setdemo_", 1)[1])
    if not name:
        return await call.answer("Please reopen Set Product Demo and choose again.", show_alert=True)
    await state.update_data(demo_selected_name=name)
    await state.set_state(AdminStates.wait_for_product_demo_video)
    await call.message.answer(f"🎬 Send the demo video for <b>{html_lib.escape(name)}</b>.\nSend a video, or type <code>none</code> to remove its demo.", parse_mode="HTML")
    await call.answer()

@dp.message(AdminStates.wait_for_product_demo_video)
async def admin_save_product_demo(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    name = str(data.get("demo_selected_name") or "").strip()
    if not name:
        await state.clear()
        return await m.answer("Product selection expired. Open Set Product Demo again.")
    key = name.casefold()
    if (m.text or "").strip().casefold() == "none":
        db_query("DELETE FROM product_demos WHERE product_name_key=?", (key,))
        await m.answer(f"✅ Demo removed for <b>{html_lib.escape(name)}</b>.", parse_mode="HTML", reply_markup=admin_kb())
    elif m.video:
        db_query("INSERT OR REPLACE INTO product_demos (product_name_key, display_name, file_id, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (key, name, m.video.file_id))
        await m.answer(f"✅ Demo saved for <b>{html_lib.escape(name)}</b>. Auto-delete: {html_lib.escape(get_setting('demo_auto_delete', 'ON'))}; delay: {format_demo_delay(max(1, int(safe_float(get_setting('demo_delete_after_seconds', '60'), 60))))}.", parse_mode="HTML", reply_markup=admin_kb())
    else:
        return await m.answer("Please send a video file, or type <code>none</code> to remove it.", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("watch_demo_"))
async def user_watch_product_demo(call: CallbackQuery):
    try:
        prod_id = int(call.data.rsplit("_", 1)[1])
    except ValueError:
        return await call.answer("Invalid product.", show_alert=True)
    row = db_query("SELECT name, category, panel_name, maintenance FROM products WHERE id=?", (prod_id,), fetchone=True)
    if not row:
        return await call.answer("Product not found.", show_alert=True)
    name, category, panel_name, maintenance = row
    panel_state = db_query("SELECT MAX(COALESCE(maintenance,0)) FROM products WHERE category LIKE ? AND LOWER(TRIM(COALESCE(panel_name,'')))=LOWER(TRIM(?)) AND is_active=1", (str(category or '') + '%', str(panel_name or '')), fetchone=True)
    if maintenance or (panel_state and panel_state[0]):
        return await call.answer("🛠 This product is currently under maintenance. Please wait for the maintenance update.", show_alert=True)
    key = str(panel_name or name or '').strip().casefold()
    demo = db_query("SELECT file_id, display_name FROM product_demos WHERE product_name_key=?", (key,), fetchone=True)
    if not demo:
        return await call.answer("Demo video is not set for this product yet.", show_alert=True)
    auto_delete = get_setting("demo_auto_delete", "ON").upper() == "ON"
    delay_seconds = max(1, int(safe_float(get_setting("demo_delete_after_seconds", "60"), 60)))
    if auto_delete:
        await call.answer(f"🎬 Demo sent. It will be deleted after {format_demo_delay(delay_seconds)}.")
    else:
        await call.answer("🎬 Demo sent. Auto-delete is OFF.")
    try:
        caption = f"🎬 <b>{html_lib.escape(str(demo[1]))} — Demo</b>"
        if auto_delete:
            caption += f"\n⏳ This video message will be deleted after {format_demo_delay(delay_seconds)}."
        sent = await bot.send_video(call.from_user.id, demo[0], caption=caption, parse_mode="HTML")
        if auto_delete:
            async def delete_demo_message(chat_id: int, message_id: int, delay: int):
                await asyncio.sleep(delay)
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            asyncio.create_task(delete_demo_message(sent.chat.id, sent.message_id, delay_seconds))
    except Exception as exc:
        logger.exception("Could not send product demo: %s", exc)
        await call.message.answer("Unable to send demo right now. Please contact admin.")

@dp.callback_query(F.data == "admin_set_video")
async def admin_set_video_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📹 Input direct streaming / YouTube Link for Tutorial system:\n<i>(Or type 'None' to clear registry):</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_howto_video)

@dp.message(AdminStates.wait_for_howto_video)
async def exec_set_video(m: Message, state: FSMContext):
    link = m.text.strip()
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('how_to_video', ?)", (link,))
    await m.answer("✅ Routing complete. Video linked.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_all_files")
async def admin_set_all_files_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🔗 Input the direct Channel / Cloud URL for 'Download Files' button:\n<i>(Or type 'None' to format data):</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_all_files_link)

@dp.message(AdminStates.wait_for_all_files_link)
async def exec_set_all_files(m: Message, state: FSMContext):
    link = m.text.strip()
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('all_files_link', ?)", (link,))
    await m.answer("✅ Global resource variable updated.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_selling_proof")
async def admin_set_selling_proof_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    current = get_setting("selling_proof_link", "None")
    await call.message.edit_text(
        "🧾 <b>SELLING PROOF LINK</b>\n\n"
        f"Current Link: <code>{current}</code>\n\n"
        "Send the new Selling Proof URL below.\n"
        "Type <code>None</code> to disable/remove it.",
        reply_markup=admin_back_kb(),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.wait_for_selling_proof_link)


@dp.message(AdminStates.wait_for_selling_proof_link)
async def exec_set_selling_proof(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    link = (m.text or "").strip()

    if link.lower() == "none":
        link = "None"
    elif not (link.startswith("http://") or link.startswith("https://")):
        await m.answer(
            "❌ Invalid URL!\nPlease send a valid link starting with http:// or https://",
            reply_markup=admin_back_kb(),
            parse_mode='HTML'
        )
        return

    set_setting("selling_proof_link", link)
    await state.clear()
    await m.answer(
        "✅ <b>Selling Proof link updated successfully!</b>\n\n"
        f"🔗 Link: <code>{link}</code>",
        reply_markup=admin_kb(),
        parse_mode='HTML'
    )


@dp.callback_query(F.data == "admin_edit_emojis")
async def admin_edit_emojis(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    rows = db_query("SELECT key, value FROM settings WHERE key LIKE 'emoji_%' ORDER BY key", fetchall=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for row in rows:
        key = row[0]
        slot = key.replace("emoji_", "")
        current_id = row[1] if row[1] else "Not set"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{slot} (ID: {current_id})", callback_data=f"edit_emoji_{slot}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🎨 <b>Edit All Emojis</b>\nChoose an emoji slot to change its ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_emoji_"))
async def admin_edit_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    slot = call.data.split("edit_emoji_", 1)[1]
    await state.update_data(emoji_slot=slot)
    current = get_setting(f"emoji_{slot}", "Not set")
    await call.message.edit_text(f"✏️ Enter new emoji ID for <b>{slot}</b>:\nCurrent: {current}\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_emoji_slot)

@dp.message(AdminStates.wait_for_emoji_slot)
async def save_emoji_slot(m: Message, state: FSMContext):
    data = await state.get_data()
    slot = data['emoji_slot']
    new_id = m.text.strip()
    if new_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"emoji_{slot}",))
        await m.answer(f"✅ Reset emoji for '{slot}' to default.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not new_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"emoji_{slot}", new_id)
        await m.answer(f"✅ Emoji for '{slot}' updated to ID {new_id}.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_edit_ui_menu")
async def admin_edit_ui_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Start Menu Text", callback_data="edit_ui_start", style="primary")],
        [InlineKeyboardButton(text="Edit Download Files Text", callback_data="edit_ui_download", style="primary")],
        [InlineKeyboardButton(text="Edit VIP Menu Text", callback_data="edit_ui_vip", style="primary")],
        [InlineKeyboardButton(text="Edit Lucky Dice Text", callback_data="edit_ui_dice", style="primary")],
        [InlineKeyboardButton(text="Edit Add Balance Text", callback_data="edit_ui_add_balance", style="primary")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("✏️ <b>Edit User Interface Texts</b>\nSelect which text you want to modify:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_ui_"))
async def admin_edit_ui_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    ui_key = call.data.split("_")[2]
    await state.update_data(ui_key=ui_key)
    current_text = get_ui_text(ui_key)
    await call.message.edit_text(f"📝 Send the new text for <b>{ui_key.upper()}</b> menu.\n\nCurrent text:\n{current_text}", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.edit_ui_text)

@dp.message(AdminStates.edit_ui_text)
async def admin_save_ui_text(m: Message, state: FSMContext):
    data = await state.get_data()
    ui_key = data['ui_key']
    new_text = m.text
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"ui_{ui_key}", new_text))
    await m.answer(f"✅ UI text <b>{ui_key}</b> updated successfully!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_edit_reseller_price")
async def admin_edit_reseller_price_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    prods = db_query("SELECT id, name, category, panel_name, reseller_price FROM products ORDER BY category, panel_name", fetchall=True)
    if not prods: return await call.message.edit_text("No products to edit.", reply_markup=admin_back_kb(), parse_mode='HTML')
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in prods:
        panel_name = p[3] if p[3] is not None else ""
        r_price = safe_float(p[4])
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p[2]} - {panel_name} - {p[1]} (₹{r_price:.2f})", callback_data=f"edit_reseller_{p[0]}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("👑 <b>Edit Reseller Price per Product</b>\nSelect a product to change its wholesale price:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_reseller_"))
async def admin_edit_reseller_price_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    prod_id = int(call.data.split("_")[2])
    await state.update_data(edit_reseller_prod_id=prod_id)
    await call.message.edit_text("💰 Enter the new <b>Reseller Price</b> in Rupees (₹) for this product:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.edit_reseller_price)

@dp.message(AdminStates.edit_reseller_price)
async def admin_save_reseller_price(m: Message, state: FSMContext):
    try:
        new_price = float(m.text)
        data = await state.get_data()
        prod_id = data['edit_reseller_prod_id']
        db_query("UPDATE products SET reseller_price=? WHERE id=?", (new_price, prod_id))
        await m.answer(f"✅ Reseller price updated to {fmt_curr(new_price)} for product ID {prod_id}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid price.")

@dp.callback_query(F.data == "admin_set_reseller_fee")
async def admin_set_reseller_fee(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("💰 Enter the new <b>Reseller Setup Fee</b> in Rupees (₹):\nCurrent: " + get_setting("reseller_setup_fee", "200.0"), reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_reseller_setup_fee)

@dp.message(AdminStates.wait_for_reseller_setup_fee)
async def admin_save_reseller_fee(m: Message, state: FSMContext):
    try:
        fee = float(m.text)
        set_setting("reseller_setup_fee", str(fee))
        await m.answer(f"✅ Reseller setup fee updated to {fmt_curr(fee)}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid amount.")

@dp.callback_query(F.data == "admin_set_reseller_api_url")
async def admin_set_reseller_api_url(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    current = get_reseller_api_url()
    await call.message.edit_text(
        "🌐 <b>RESELLER API URL CONTROL</b>\n\n"
        f"Current URL: <code>{html_lib.escape(current)}</code>\n\n"
        "Send the new reseller API URL.\n"
        "Example: <code>https://bantibhaiya.to/api/reseller_v1.php</code>\n\n"
        "Type <code>/cancel</code> to cancel.",
        reply_markup=admin_back_kb(), parse_mode='HTML'
    )
    await state.set_state(AdminStates.wait_for_reseller_api_url)

@dp.message(AdminStates.wait_for_reseller_api_url)
async def admin_save_reseller_api_url(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    url = (m.text or "").strip()
    if url.lower() == "/cancel":
        await state.clear()
        return await m.answer("❌ Reseller API URL setup cancelled.", reply_markup=admin_kb(), parse_mode='HTML')
    if not (url.startswith("http://") or url.startswith("https://")):
        return await m.answer("❌ Invalid URL. Please send a URL starting with http:// or https://", reply_markup=admin_back_kb(), parse_mode='HTML')
    set_setting("reseller_api_url", url)
    await state.clear()
    await m.answer(
        "✅ <b>Reseller API URL Saved!</b>\n\n"
        f"🌐 Endpoint: <code>{html_lib.escape(url)}</code>",
        reply_markup=admin_kb(), parse_mode='HTML'
    )


@dp.callback_query(F.data == "admin_set_reseller_api_key")
async def admin_set_reseller_api_key(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    current = get_setting("reseller_api_key", "")
    masked = (current[:4] + "..." + current[-4:]) if len(current) > 10 else ("Not set" if not current else "••••••")
    await call.message.edit_text(
        "🔑 <b>RESELLER API KEY</b>\n\n"
        f"Current Key: <code>{html_lib.escape(masked)}</code>\n\n"
        "Send your new Reseller API Key below.\n"
        "The key will be saved securely in the bot database.\n"
        "Type <code>/cancel</code> to cancel.",
        reply_markup=admin_back_kb(),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.wait_for_reseller_api_key)


@dp.message(AdminStates.wait_for_reseller_api_key)
async def admin_save_reseller_api_key(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    key = (m.text or "").strip()
    if key.lower() == "/cancel":
        await state.clear()
        return await m.answer("❌ Reseller API key setup cancelled.", reply_markup=admin_kb(), parse_mode='HTML')
    if not key or key == "YOUR_RRSELLER_API_ADD":
        return await m.answer("❌ Invalid API key. Please send the actual Reseller API key.", reply_markup=admin_back_kb(), parse_mode='HTML')
    set_setting("reseller_api_key", key)
    await state.clear()
    try:
        await m.delete()
    except Exception:
        pass
    masked = (key[:4] + "..." + key[-4:]) if len(key) > 10 else "••••••"
    await m.answer(
        "✅ <b>Reseller API Key Saved!</b>\n\n"
        f"🔑 Key: <code>{html_lib.escape(masked)}</code>\n"
        f"🌐 Endpoint: <code>{html_lib.escape(get_reseller_api_url())}</code>\n\n"
        "You no longer need to edit the .py file to change the API key.",
        reply_markup=admin_kb(),
        parse_mode='HTML'
    )


@dp.callback_query(F.data == "admin_set_reseller_min")
async def admin_set_reseller_min(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("💳 Enter the new <b>Minimum Balance</b> required to become reseller (₹):\nCurrent: " + get_setting("reseller_min_balance", "500.0"), reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_reseller_min_balance)

@dp.message(AdminStates.wait_for_reseller_min_balance)
async def admin_save_reseller_min(m: Message, state: FSMContext):
    try:
        min_bal = float(m.text)
        set_setting("reseller_min_balance", str(min_bal))
        await m.answer(f"✅ Minimum reseller balance updated to {fmt_curr(min_bal)}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid amount.")

@dp.callback_query(F.data == "admin_set_support_links")
async def admin_set_support_links(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Set Telegram Link", callback_data="admin_set_telegram", style="primary")],
        [InlineKeyboardButton(text="📱 Set WhatsApp Link", callback_data="admin_set_whatsapp", style="primary")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("📌 <b>Support Contact Links</b>\nSet the URLs for Telegram and WhatsApp support:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "admin_set_telegram")
async def admin_set_telegram(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("✈️ Enter the Telegram contact URL (e.g., https://t.me/YourSupport):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_support_telegram)

@dp.message(AdminStates.wait_for_support_telegram)
async def save_telegram_link(m: Message, state: FSMContext):
    link = m.text.strip()
    set_setting("support_telegram", link)
    await m.answer("✅ Telegram support link updated!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_whatsapp")
async def admin_set_whatsapp(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📱 Enter the WhatsApp contact URL (e.g., https://wa.me/1234567890):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_support_whatsapp)

@dp.message(AdminStates.wait_for_support_whatsapp)
async def save_whatsapp_link(m: Message, state: FSMContext):
    link = m.text.strip()
    set_setting("support_whatsapp", link)
    await m.answer("✅ WhatsApp support link updated!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_category_emojis")
async def admin_set_category_emojis(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in FIXED_CATEGORIES:
        current = get_setting(f"cat_emoji_{cat}", "Not set")
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{cat} (ID: {current})", callback_data=f"set_cat_emoji_{cat}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🎨 <b>Set Category Emojis</b>\nChoose a category to set its custom emoji ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("set_cat_emoji_"))
async def admin_set_category_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    category = call.data.split("set_cat_emoji_", 1)[1]
    await state.update_data(cat_emoji_category=category)
    await call.message.edit_text(f"🎨 Enter the emoji ID for <b>{category}</b>:\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_category_emoji)

@dp.message(AdminStates.wait_for_category_emoji)
async def save_category_emoji(m: Message, state: FSMContext):
    data = await state.get_data()
    category = data['cat_emoji_category']
    emoji_id = m.text.strip()
    if emoji_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"cat_emoji_{category}",))
        await m.answer(f"✅ Reset emoji for {category} to default.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not emoji_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"cat_emoji_{category}", emoji_id)
        await m.answer(f"✅ Emoji set for {category} successfully!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_panel_emojis")
async def admin_set_panel_emojis(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    panels = db_query("SELECT DISTINCT panel_name FROM products WHERE panel_name != '' ORDER BY panel_name", fetchall=True)
    if not panels:
        await call.message.edit_text("No panel names found in products.", reply_markup=admin_back_kb(), parse_mode='HTML')
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in panels:
        panel = p[0]
        current = get_setting(f"panel_emoji_{panel}", "Not set")
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{panel} (ID: {current})", callback_data=f"set_panel_emoji_{panel}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🖼 <b>Set Panel Emojis</b>\nChoose a panel name to set its custom emoji ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("set_panel_emoji_"))
async def admin_set_panel_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    panel_name = call.data.split("set_panel_emoji_", 1)[1]
    await state.update_data(panel_emoji_name=panel_name)
    await call.message.edit_text(f"🎨 Enter the emoji ID for panel <b>{panel_name}</b>:\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_panel_emoji_id)

@dp.message(AdminStates.wait_for_panel_emoji_id)
async def save_panel_emoji(m: Message, state: FSMContext):
    data = await state.get_data()
    panel_name = data['panel_emoji_name']
    emoji_id = m.text.strip()
    if emoji_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"panel_emoji_{panel_name}",))
        await m.answer(f"✅ Reset emoji for panel '{panel_name}'.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not emoji_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"panel_emoji_{panel_name}", emoji_id)
        await m.answer(f"✅ Emoji set for panel '{panel_name}'!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# Payment gateway ON/OFF controls (admin only)
@dp.callback_query(F.data.in_({"admin_toggle_fampay", "admin_toggle_zapupi"}))
async def admin_toggle_payment_gateway(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    gateway = "fampay" if call.data == "admin_toggle_fampay" else "zapupi"
    key = f"gateway_{gateway}_enabled"
    current = get_setting(key, "ON")
    new_value = "OFF" if current == "ON" else "ON"
    set_setting(key, new_value)
    label = "FamPay" if gateway == "fampay" else "ZapUPI"
    await call.answer(f"{label} {new_value}")
    try:
        await call.message.edit_reply_markup(reply_markup=admin_kb())
    except Exception:
        await call.message.answer(f"{label} gateway is now {new_value}.", reply_markup=admin_kb())

# 23. ADMIN FAMPAY SETUP
# ==============================================================================
@dp.callback_query(F.data == "admin_setup_fampay")
async def setup_fampay_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    current_api = get_setting("fampay_api_key", "Not set")
    current_upi = get_setting("fampay_upi_id", "Not set")
    await call.message.edit_text(
        f"⚙️ <b>FAMPAY SECURITY DEPLOYMENT</b>\n\n"
        f"🔑 Current API Key: {current_api[:8] if current_api != 'Not set' else 'Not set'}... (hidden)\n"
        f"🏦 Current UPI ID: {current_upi}\n\n"
        f"Send new <b>FamPay API Key</b>:\n<i>(Type /cancel to abort)</i>",
        reply_markup=admin_back_kb(), parse_mode='HTML'
    )
    await state.set_state(AdminStates.wait_for_fampay_api)

@dp.message(AdminStates.wait_for_fampay_api)
async def setup_fampay_api(m: Message, state: FSMContext):
    if m.text == '/cancel':
        await state.clear()
        return await m.answer("Sequence killed.", reply_markup=admin_kb(), parse_mode='HTML')
    api_key = m.text.strip()
    set_setting("fampay_api_key", api_key)
    await m.answer("🔑 FamPay API Key saved!\n\nNow enter the <b>UPI ID</b> to receive payments (e.g., example@okhdfcbank):", parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_fampay_upi)

@dp.message(AdminStates.wait_for_fampay_upi)
async def setup_fampay_upi(m: Message, state: FSMContext):
    upi_id = m.text.strip()
    if '@' not in upi_id:
        return await m.answer("❌ Invalid UPI ID! Must contain '@'. Example: example@okhdfcbank", parse_mode='HTML')
    set_setting("fampay_upi_id", upi_id)
    await m.answer(f"✅ <b>FamPay Gateway configured successfully!</b>\n\n🏦 UPI ID: {upi_id}\n🔑 API Key: Saved\n\nGateway is now ready for payments.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# ADMIN ZAPUPI API SETUP
# ==============================================================================
@dp.callback_query(F.data == "admin_setup_zapupi")
async def setup_zapupi_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Admin only.", show_alert=True)
    current = get_setting("zapupi_zap_key", "").strip()
    masked = (current[:6] + "••••••••") if current else "NOT SET"
    await call.message.edit_text(
        "🔐 <b>ZAPUPI API SETTINGS</b>\n\n"
        f"Current Zap Key: <code>{html_lib.escape(masked)}</code>\n\n"
        "pay.zapupi.com gateway ka <b>Zap Key</b> bhejein.\n"
        "Key database mein save hogi; code edit karne ki zaroorat nahi.\n\n"
        "/cancel — cancel setup",
        reply_markup=admin_back_kb(), parse_mode="HTML"
    )
    await state.set_state(AdminStates.wait_for_zapupi_key)
    await call.answer()

@dp.message(AdminStates.wait_for_zapupi_key)
async def setup_zapupi_key(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    raw = (m.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        return await m.answer("❌ ZapUPI setup cancelled.", reply_markup=admin_kb())
    if len(raw) < 6 or raw.startswith("/"):
        return await m.answer("❌ Valid ZapUPI Zap Key bhejein, ya /cancel type karein.")
    set_setting("zapupi_zap_key", raw)
    await state.clear()
    await m.answer("✅ <b>ZapUPI API Key saved!</b>\n\n🏦 ZapUPI payment option ab Add Balance menu mein available hoga.", reply_markup=admin_kb(), parse_mode="HTML")

# ==============================================================================
# 24. ADMIN BINANCE SETUP
# ==============================================================================
@dp.callback_query(F.data == "admin_setup_binance")
async def setup_binance_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🪙 <b>CRYPTO NODE INIT: Step 1/3</b>\nInput Master <b>Binance API Key</b>:\n<i>(Type /cancel to halt protocol)</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_api)

@dp.message(AdminStates.wait_for_binance_api)
async def setup_binance_api(m: Message, state: FSMContext):
    if m.text == '/cancel':
        await state.clear()
        return await m.answer("Sequence aborted.", reply_markup=admin_kb(), parse_mode='HTML')
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_api', ?)", (m.text.strip(),))
    await m.answer("🪙 <b>CRYPTO NODE INIT: Step 2/3</b>\nNow inject the highly secure <b>Binance Secret Key</b>:", parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_secret)

@dp.message(AdminStates.wait_for_binance_secret)
async def setup_binance_secret(m: Message, state: FSMContext):
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_secret', ?)", (m.text.strip(),))
    await m.answer("🪙 <b>CRYPTO NODE INIT: Step 3/3</b>\nFinal variable: Set the public <b>USDT Deposit Address (TRC20/BEP20)</b>\nUsers will broadcast to this ledger:", parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_address)

@dp.message(AdminStates.wait_for_binance_address)
async def setup_binance_address(m: Message, state: FSMContext):
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_address', ?)", (m.text.strip(),))
    await m.answer("✅ <b>Blockchain node synchronized.</b> Crypto gateway is fully armed.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()


# ==============================================================================
# RESELLER API ADMIN COMMANDS
# ==============================================================================
@dp.message(Command("linkapi"))
async def cmd_linkapi(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 3:
        return await m.answer(
            "Usage:\n<code>/linkapi BOT_PRODUCT_ID API_PID [DURATION]</code>\n"
            "Example: <code>/linkapi 5 151 1 Day</code>\n"
            "Unlink: <code>/linkapi 5 off</code>", parse_mode="HTML")
    try:
        p_id = int(parts[1])
    except ValueError:
        return await m.answer("❌ BOT_PRODUCT_ID must be a number.")
    if not db_query("SELECT id FROM products WHERE id=?", (p_id,), fetchone=True):
        return await m.answer("❌ Product not found in bot.")
    if parts[2].lower() == "off":
        db_query("UPDATE products SET api_product_id='', api_duration='' WHERE id=?", (p_id,))
        return await m.answer(f"✅ Product #{p_id} unlinked from reseller API. Local keys will be used again.")
    api_pid = parts[2].strip()
    duration = parts[3].strip() if len(parts) > 3 else ""
    db_query("UPDATE products SET api_product_id=?, api_duration=?, stock=999 WHERE id=?", (api_pid, duration, p_id))
    await m.answer(
        f"✅ <b>API linked!</b>\nProduct: <code>{p_id}</code>\nAPI PID: <code>{html_lib.escape(api_pid)}</code>"
        f"{'\nDuration: <code>' + html_lib.escape(duration) + '</code>' if duration else ''}\n\n"
        "Keys will now be generated automatically on purchase.", parse_mode="HTML")


@dp.message(Command("setresellerapi"))
async def cmd_setresellerapi(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return await m.answer("Usage: <code>/setresellerapi YOUR_API_KEY</code>", parse_mode="HTML")
    key = parts[1].strip()
    set_setting("reseller_api_key", key)
    try:
        await m.delete()
    except Exception:
        pass
    await m.answer("✅ Reseller API key saved securely.\n🌐 Endpoint: <code>https://bantibhaiya.to/api/reseller_v1.php</code>", parse_mode="HTML")


@dp.message(Command("apibalance"))
async def cmd_apibalance(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    ok, data = await reseller_api_request("balance")
    if not ok:
        return await m.answer(f"❌ {html_lib.escape(str(data))}", parse_mode="HTML")
    await m.answer(f"💰 <b>Supplier wallet</b>\n<code>{html_lib.escape(json.dumps(data, indent=2, ensure_ascii=False)[:3500])}</code>", parse_mode="HTML")


@dp.message(Command("apiproducts"))
async def cmd_apiproducts(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    ok, data = await reseller_api_request("products")
    if not ok:
        return await m.answer(f"❌ {html_lib.escape(str(data))}", parse_mode="HTML")
    raw = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    await m.answer_document(BufferedInputFile(raw, filename="api_products.json"), caption="Reseller API products (PIDs & stock)")

# ==============================================================================
# 25. BOOTSTRAPPING & MAIN
# ==============================================================================
async def main() -> None:
    init_db()
    logger.info("Initializing DB structure...")
    migrate_categories()
    asyncio.create_task(auto_verify_task())
    logger.info("FamPay FAST Auto-Verifier Daemon Running in Background (1s polling).")
    logger.info("🚀 CORE SYSTEM IS FULLY OPERATIONAL...")
    try:
        await dp.start_polling(bot)
    except Exception as err:
        logger.error(f"Critical System Failure in Polling: {err}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("System shutting down gracefully. Goodbye.")