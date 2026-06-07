import os
import telebot
from telebot import types
import sqlite3
import random
import string
import time
from threading import Lock

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8343465981:AAE4euR3pIQfmWPk2__0uqA4C_Je9bo_9PU"
ADMIN_ID = 8516499380 
BOT_USERNAME = "Gmail_Employee_Pro_bot"   # removed @

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')
DB_NAME = "gmail_employee.db"
db_lock = Lock()

# ==================== DATABASE ENGINE (THREAD SAFE) ====================
def query_db(query, args=(), one=False, commit=False):
    with db_lock:
        try:
            with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                res = cursor.execute(query, args)
                if commit:
                    conn.commit()
                    return res
                rv = res.fetchall()
                return (rv[0] if rv else None) if one else rv
        except Exception as e:
            print(f"DB Error: {e}")
            return None

def init_db():
    query_db('''CREATE TABLE IF NOT EXISTS users (
        uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0, hold REAL DEFAULT 0,
        lang TEXT DEFAULT 'BN', ref_by INTEGER, total_tasks INTEGER DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0, method TEXT DEFAULT 'None', wallet TEXT DEFAULT 'None',
        join_date TEXT, status TEXT DEFAULT 'active'
    )''', commit=True)
    
    query_db('''CREATE TABLE IF NOT EXISTS tasks (
        tid INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, email TEXT, 
        pw TEXT, amount REAL, status TEXT DEFAULT 'active'
    )''', commit=True)
    
    query_db('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY, rate REAL, ref_bonus REAL, min_wd REAL
    )''', commit=True)
    
    if not query_db("SELECT * FROM settings WHERE id=1", one=True):
        query_db("INSERT INTO settings VALUES (1, 25.0, 5.0, 100.0)", commit=True)

init_db()

# ==================== KEYBOARD GENERATOR ====================
def get_main_kb(uid):
    u = query_db("SELECT lang FROM users WHERE uid=?", (uid,), one=True)
    lang = u['lang'] if u else 'BN'
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == 'BN':
        kb.add("тЮХ ржирждрзБржи ржЕрзНржпрж╛ржХрж╛ржЙржирзНржЯ", "ЁЯУВ ржкрзНрж░рзЛржлрж╛ржЗрж▓")
        kb.add("ЁЯТ░ ржмрзНржпрж╛рж▓рзЗржирзНрж╕", "ЁЯСе рж░рзЗржлрж╛рж░рзЗрж▓")
        kb.add("тЪЩя╕П рж╕рзЗржЯрж┐ржВрж╕", "ЁЯТм рж╕рж╛ржкрзЛрж░рзНржЯ")
    else:
        kb.add("тЮХ Register Account", "ЁЯУВ My Profile")
        kb.add("ЁЯТ░ My Balance", "ЁЯСе My Referrals")
        kb.add("тЪЩя╕П Settings", "ЁЯТм Help & Support")
    if uid == ADMIN_ID: 
        kb.add("ЁЯФР Admin Panel")
    return kb

# ==================== START ====================
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    args = m.text.split()

    user = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
    if not user:
        join_date = time.strftime("%d/%m/%Y")
        ref_by = None

        if len(args) > 1:
            try:
                ref_by = int(args[1])
                if ref_by == uid:
                    ref_by = None
            except:
                ref_by = None

        query_db("INSERT INTO users (uid, join_date, ref_by) VALUES (?, ?, ?)", 
                 (uid, join_date, ref_by), commit=True)

    bot.send_message(uid, "ЁЯСЛ Welcome to *Gmail Flux Master*!", reply_markup=get_main_kb(uid))

# --- ЁЯТ░ BALANCE ---
@bot.message_handler(func=lambda m: m.text in ["ЁЯТ░ My Balance", "ЁЯТ░ ржмрзНржпрж╛рж▓рзЗржирзНрж╕"])
def balance_handler(m):
    uid = m.chat.id
    u = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
    if not u:
        return
    text = f"ЁЯТ░ *Account Balance*\n\nЁЯТ╡ Main: рз│{u['balance']}\nтП│ Hold: рз│{u['hold']}\nтЬЕ Completed: {u['completed_tasks']}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("ЁЯТ╕ Withdraw", callback_data="wd_start"),
           types.InlineKeyboardButton("ЁЯФД Refresh", callback_data="bal_refresh"))
    bot.send_message(uid, text, reply_markup=kb)

# --- ЁЯСе REFERRALS ---
@bot.message_handler(func=lambda m: m.text in ["ЁЯСе My Referrals", "ЁЯСе рж░рзЗржлрж╛рж░рзЗрж▓"])
def referral_handler(m):
    uid = m.chat.id
    refs = query_db("SELECT COUNT(*) as total FROM users WHERE ref_by=?", (uid,), one=True)
    total_refs = refs["total"] if refs else 0
    ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    bot.send_message(uid, f"ЁЯСе *Referral Program*\n\nYour Link: {ref_link}\nTotal Referrals: {total_refs}")

# --- ЁЯФР ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "ЁЯФР Admin Panel" and m.chat.id == ADMIN_ID)
def admin_handler(m):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("ЁЯУК Stats", callback_data="adm_stats"),
           types.InlineKeyboardButton("ЁЯУв Broadcast", callback_data="adm_bc"))
    bot.send_message(ADMIN_ID, "ЁЯЫа *Master Admin Dashboard*", reply_markup=kb)

# ==================== CALLBACKS ====================
@bot.callback_query_handler(func=lambda c: True)
def callback_master(c):
    uid = c.message.chat.id
    data = c.data

    if data == "bal_refresh":
        u = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
        if not u:
            return
        new_text = f"ЁЯТ░ *Account Balance*\n\nЁЯТ╡ Main: рз│{u['balance']}\nтП│ Hold: рз│{u['hold']}\nтЬЕ Completed: {u['completed_tasks']}"
        try:
            bot.edit_message_text(new_text, uid, c.message.message_id, reply_markup=c.message.reply_markup)
        except:
            pass
        bot.answer_callback_query(c.id, "Updated!")

    elif data == "wd_start":
        bot.answer_callback_query(c.id, "Withdraw request received!")

    elif data == "adm_stats" and uid == ADMIN_ID:
        users = query_db("SELECT COUNT(*) as total FROM users", one=True)
        total_users = users["total"] if users else 0
        bot.answer_callback_query(c.id, f"Total Users: {total_users}", show_alert=True)

    elif data == "adm_bc" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID, "Enter message to send all:")
        bot.register_next_step_handler(msg, process_broadcast)

# ==================== BROADCAST ====================
def process_broadcast(m):
    users = query_db("SELECT uid FROM users")
    if not users:
        return
    for u in users:
        try:
            bot.send_message(u['uid'], m.text)
        except:
            pass
    bot.send_message(ADMIN_ID, "тЬЕ Broadcast Done!")

# ==================== RUN ====================
if __name__ == "__main__":
    print("All Systems Active...")
    bot.infinity_polling(skip_pending=True)
