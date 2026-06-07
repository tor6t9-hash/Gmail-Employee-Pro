import telebot
from telebot import types
import sqlite3
import threading
import random
import string
from datetime import datetime
import time

# ==================== কনফিগারেশন ====================
BOT_TOKEN = "8343465981:AAGiMVZwCcmzvARDt4UFRBF7Gno_4YN865E" 
ADMIN_ID = 8516499380  
CHANNEL_ID = "@Gmail_Employee_News"
CHANNEL_LINK = "https://t.me/Gmail_Employee_News"
SUPPORT_USERNAME = "@gmail_employee_pro_support" 
DB_NAME = "earning_bot.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
db_lock = threading.Lock()

# ==================== ভাষা ডিকশনারি ====================
STRINGS = {
    'EN': {
        'start': "👋 <b>Welcome {name}!</b>\nStart earning by completing simple tasks.",
        'reg': "➕ Register Account", 'prof': "📂 My Profile", 'bal': "💰 My Balance",
        'ref': "👥 My Referral", 'set': "⚙️ Settings", 'sup': "💬 Support", 'with': "💸 Withdraw",
        'profile_info': "👤 <b>Profile:</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Joined: {date}\n📊 Tasks: {done} Done",
        'balance_info': "💰 <b>Your Balance:</b>\n\n💵 Current: {bal} BDT\n⏳ On Hold: {hold} BDT",
        'refer_info': "👥 <b>Referral Program:</b>\n\n🔗 Link: <code>https://t.me/{bot_user}?start={uid}</code>\n🎁 Bonus: 2.5 BDT per approved task of your referral.",
        'force_msg': "👋 Hey, <b>{name}</b> welcome!\n🔴 Join our channel to use the bot.",
        'set_msg': "⚙️ <b>Settings:</b>\nSelect your preferred language below.",
        'off_msg': "⚠️ <b>Sorry!</b> Currently Gmail tasks are temporarily closed by Admin."
    },
    'BN': {
        'start': "👋 <b>স্বাগতম {name}!</b>\nসহজ কিছু কাজ সম্পন্ন করে আয় করা শুরু করুন।",
        'reg': "➕ Register Account", 'prof': "📂 প্রোফাইল", 'bal': "💰 ব্যালেন্স",
        'ref': "👥 রেফারেল", 'set': "⚙️ সেটিংস", 'sup': "💬 সাপোর্ট", 'with': "💸 টাকা তুলুন",
        'profile_info': "👤 <b>প্রোফাইল:</b>\n\n🆔 আইডি: <code>{uid}</code>\n📅 জয়েন: {date}\n📊 কাজ: {done}টি সম্পন্ন",
        'balance_info': "💰 <b>আপনার ব্যালেন্স:</b>\n\n💵 মূল ব্যালেন্স: {bal} টাকা\n⏳ পেন্ডিং: {hold} টাকা",
        'refer_info': "👥 <b>রেফারেল প্রোগ্রাম:</b>\n\n🔗 লিংক: <code>https://t.me/{bot_user}?start={uid}</code>\n🎁 বোনাস: আপনার রেফার করা ইউজারের প্রতি টাস্ক অ্যাপ্রুভ হলে পাবেন ২.৫ টাকা।",
        'force_msg': "👋 Hey, <b>{name}</b> আপনাকে স্বাগতম!\n🔴 সমস্ত আপডেট পেতে আমাদের চ্যানেলে জয়েন করুন।",
        'set_msg': "⚙️ <b>সেটিংস:</b>\nনিচ থেকে আপনার পছন্দের ভাষা নির্বাচন করুন।",
        'off_msg': "⚠️ <b>দুঃখিত!</b> বর্তমানে অ্যাডমিন কর্তৃক জিমেইল এর কাজ সাম্যিকভাবে বন্ধ রাখা হয়েছে।"
    }
}

# ==================== ডাটাবেস ফাংশন ====================
def query_db(query, args=(), one=False, commit=False):
    with db_lock:
        try:
            with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                res = cursor.execute(query, args)
                if commit: conn.commit()
                rv = res.fetchall()
                return (rv[0] if rv else None) if one else rv
        except Exception as e:
            print(f"Database Error: {e}")
            return None

def init_db():
    query_db('''CREATE TABLE IF NOT EXISTS users (
        uid INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, 
        hold REAL DEFAULT 0, done_tasks INTEGER DEFAULT 0, 
        join_date TEXT, lang TEXT DEFAULT 'BN', status TEXT DEFAULT 'Active',
        referred_by INTEGER DEFAULT 0, last_submit INTEGER DEFAULT 0
    )''', commit=True)
    query_db('''CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY, min_withdraw REAL DEFAULT 50.0, 
        ref_bonus REAL DEFAULT 5.0, task_reward REAL DEFAULT 25.0,
        bot_status TEXT DEFAULT 'ON'
    )''', commit=True)
    query_db('''CREATE TABLE IF NOT EXISTS withdraws (
        wid INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, amount REAL, number TEXT, status TEXT DEFAULT 'Pending'
    )''', commit=True)
    query_db('''CREATE TABLE IF NOT EXISTS tasks (
        tid INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, details TEXT, status TEXT DEFAULT 'Pending', reward_amt REAL DEFAULT 0
    )''', commit=True)
    if not query_db("SELECT * FROM config", one=True):
        query_db("INSERT INTO config (id, min_withdraw, ref_bonus, task_reward, bot_status) VALUES (1, 50.0, 5.0, 25.0, 'ON')", commit=True)

init_db()

# ==================== হেল্পার ফাংশন ====================
def generate_random_data():
    letters = string.ascii_lowercase
    numbers = string.digits
    email_user = ''.join(random.choice(letters) for i in range(7)) + ''.join(random.choice(numbers) for i in range(3))
    password = ''.join(random.choice(letters + numbers) for i in range(10))
    return email_user, password

def is_subscribed(uid):
    try:
        if uid == ADMIN_ID: return True
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def force_join_kb():
    kb = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("💎 Join Channel", url=CHANNEL_LINK)
    btn2 = types.InlineKeyboardButton("✅ Joined", callback_data="check_joined")
    kb.add(btn1, btn2) 
    return kb

def main_kb(uid):
    user = query_db("SELECT lang FROM users WHERE uid=?", (uid,), one=True)
    lang = user['lang'] if user else 'BN'
    L = STRINGS[lang]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(L['reg'], L['prof'], L['bal'], L['ref'], L['with'], L['set'], L['sup'])
    if uid == ADMIN_ID: kb.add("🔐 Admin Panel")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("📊 ড্যাশবোর্ড", "👥 সব ইউজার")
    kb.add("📋 পেন্ডিং টাস্ক", "💰 পেন্ডিং উত্তোলন")
    kb.add("⚙️ সেটিংস", "📢 ব্রডকাস্ট", "🔙 প্রধান মেনু")
    return kb

def admin_settings_inline():
    conf = query_db("SELECT * FROM config WHERE id=1", one=True)
    status_emoji = "🟢 ON" if conf['bot_status'] == 'ON' else "🔴 OFF"
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(f"জিমেইল কাজ: {status_emoji}", callback_data="toggle_bot"),
        types.InlineKeyboardButton(f"💰 টাস্ক রিওয়ার্ড ({conf['task_reward']}৳)", callback_data="change_task_reward"),
        types.InlineKeyboardButton(f"🎁 রেফার বোনাস ({conf['ref_bonus']}৳)", callback_data="change_ref_bonus"),
        types.InlineKeyboardButton(f"💸 সর্বনিম্ন উত্তোলন ({conf['min_withdraw']}৳)", callback_data="change_min_withdraw")
    )
    return kb

# ==================== হ্যান্ডলারস ====================
@bot.message_handler(commands=['start'])
def start(m):
    bot.clear_step_handler_by_chat_id(m.chat.id) 
    uid, uname = m.chat.id, m.from_user.first_name
    user = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
    if not user:
        join_date = datetime.now().strftime("%d-%m-%Y")
        ref_id = 0
        if len(m.text.split()) > 1:
            try:
                ref_id = int(m.text.split()[1])
                if ref_id == uid: ref_id = 0
            except: ref_id = 0
        query_db("INSERT INTO users (uid, username, join_date, referred_by) VALUES (?, ?, ?, ?)", (uid, uname, join_date, ref_id), commit=True)
        user = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
    
    if not is_subscribed(uid):
        return bot.send_message(uid, STRINGS[user['lang']]['force_msg'].format(name=uname), reply_markup=force_join_kb())
    
    bot.send_message(uid, STRINGS[user['lang']]['start'].format(name=uname), reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: True)
def router(m):
    uid = m.chat.id
    user = query_db("SELECT * FROM users WHERE uid=?", (uid,), one=True)
    if not user: return
    if user['status'] == 'Banned': return bot.send_message(uid, "🚫 আপনি ব্যান হয়েছেন।")

    all_buttons = []
    for lang in STRINGS:
        all_buttons.extend(STRINGS[lang].values())
    if m.text in all_buttons or m.text == "🔐 Admin Panel":
        bot.clear_step_handler_by_chat_id(uid)

    if not is_subscribed(uid):
        return bot.send_message(uid, STRINGS[user['lang']]['force_msg'].format(name=m.from_user.first_name), reply_markup=force_join_kb())

    if uid == ADMIN_ID:
        if m.text == "🔐 Admin Panel":
            return bot.send_message(uid, "🔐 <b>অ্যাডমিন প্যানেল</b>", reply_markup=admin_kb())
        elif m.text == "📊 ড্যাশবোর্ড":
            u_count = query_db("SELECT COUNT(*) as c FROM users", one=True)['c']
            t_count = query_db("SELECT COUNT(*) as c FROM tasks WHERE status='Pending'", one=True)['c']
            return bot.send_message(uid, f"📊 <b>রিপোর্ট:</b>\n\nইউজার: {u_count} জন\nপেন্ডিং টাস্ক: {t_count}টি")
        elif m.text == "👥 সব ইউজার":
            msg = bot.send_message(uid, "🔍 ইউজারের 🆔 (ID) দিন:")
            return bot.register_next_step_handler(msg, manage_user_step)
        elif m.text == "📋 পেন্ডিং টাস্ক":
            tasks = query_db("SELECT * FROM tasks WHERE status='Pending'")
            if not tasks: return bot.send_message(uid, "📭 কোনো পেন্ডিং টাস্ক নেই।")
            for t in tasks:
                kb = types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("✅ Approve", callback_data=f"t_app_{t['tid']}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"t_rej_{t['tid']}")
                )
                bot.send_message(uid, f"📝 <b>ID: {t['tid']}</b>\n👤 ইউজার: <code>{t['uid']}</code>\n\n{t['details']}\n\n⚠️ <i>Approve করার আগে ডেটা যাচাই করুন।</i>", reply_markup=kb)
            return
        elif m.text == "💰 পেন্ডিং উত্তোলন":
            ws = query_db("SELECT * FROM withdraws WHERE status='Pending'")
            if not ws: return bot.send_message(uid, "📭 কোনো পেন্ডিং উত্তোলন নেই।")
            for w in ws:
                kb = types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("✅ Paid", callback_data=f"pay_done_{w['wid']}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_fail_{w['wid']}")
                )
                bot.send_message(uid, f"💳 <b>উইথড্র #{w['wid']}</b>\n👤 ইউজার: <code>{w['uid']}</code>\n💰 টাকা: {w['amount']}\n📱 নম্বর: <code>{w['number']}</code>", reply_markup=kb)
            return
        elif m.text == "⚙️ সেটিংস":
            return bot.send_message(uid, "⚙️ <b>অ্যাডমিন সেটিংস:</b>", reply_markup=admin_settings_inline())
        elif m.text == "📢 ব্রডকাস্ট":
            msg = bot.send_message(uid, "📝 সব ইউজারের জন্য মেসেজটি লিখুন:")
            return bot.register_next_step_handler(msg, process_broadcast)
        elif m.text == "🔙 প্রধান মেনু":
            return bot.send_message(uid, "🏠 প্রধান মেনু", reply_markup=main_kb(uid))

    L = STRINGS[user['lang']]
    if m.text == L['reg']:
        conf = query_db("SELECT * FROM config WHERE id=1", one=True)
        if conf['bot_status'] == 'OFF': return bot.send_message(uid, L['off_msg'])
        
        email_prefix, password = generate_random_data()
        msg_text = (
            f"<b>একটি জিমেইল অ্যাকাউন্ট নিবন্ধন করুন এবং {conf['task_reward']}৳ পান।</b>\n\n"
            f"📧 Email: <code>{email_prefix}</code>@gmail.com\n"
            f"🔑 Password: <code>{password}</code>\n\n"
            f"🔒 নির্দিষ্ট ডেটা ব্যবহার করতে ভুলবেন না।"
        )
        kb = types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("📤 সাবমিট করুন", callback_data=f"submit_task|{email_prefix}@gmail.com|{password}"),
            types.InlineKeyboardButton("❌ ক্যানсел করুন", callback_data="cancel_task")
        )
        bot.send_message(uid, msg_text, reply_markup=kb)

    elif m.text == L['prof']:
        bot.send_message(uid, L['profile_info'].format(uid=uid, date=user['join_date'], done=user['done_tasks']))
    elif m.text == L['bal']:
        bot.send_message(uid, L['balance_info'].format(bal=user['balance'], hold=user['hold']))
    elif m.text == L['ref']:
        bot_user = bot.get_me().username
        bot.send_message(uid, L['refer_info'].format(bot_user=bot_user, uid=uid))
    elif m.text == L['with']:
        min_w = query_db("SELECT min_withdraw FROM config", one=True)['min_withdraw']
        if user['balance'] < min_w: return bot.send_message(uid, f"❌ নূন্যতম {min_w} টাকা প্রয়োজন।")
        msg = bot.send_message(uid, "📱 আপনার ১১ অক্ষরের বিকাশ নম্বরটি দিন:")
        bot.register_next_step_handler(msg, withdraw_step_1)
    elif m.text == L['set']:
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_EN"), types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_BN"))
        bot.send_message(uid, L['set_msg'], reply_markup=kb)
    elif m.text == L['sup']:
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💬 সরাসরি যোগাযোগ করুন", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}"))
        bot.send_message(uid, f"📩 সাপোর্ট টিমের সাথে যোগাযোগ করুন।", reply_markup=kb)

# ==================== উইথড্র লজিক ====================
def withdraw_step_1(m):
    all_buttons = []
    for lang in STRINGS:
        all_buttons.extend(STRINGS[lang].values())
    if m.text in all_buttons:
        return router(m)

    num = m.text.strip()
    if len(num) != 11 or not num.isdigit():
        msg = bot.send_message(m.chat.id, "❌ সঠিক ১১ অক্ষরের নম্বর দিন:")
        return bot.register_next_step_handler(msg, withdraw_step_1)
    msg = bot.send_message(m.chat.id, "💰 কত টাকা উত্তোলন করতে চান?")
    bot.register_next_step_handler(msg, withdraw_step_2, num)

def withdraw_step_2(m, num):
    all_buttons = []
    for lang in STRINGS:
        all_buttons.extend(STRINGS[lang].values())
    if m.text in all_buttons:
        return router(m)

    try:
        amt = float(m.text)
        user = query_db("SELECT balance FROM users WHERE uid=?", (m.chat.id,), one=True)
        if amt > user['balance']: return bot.send_message(m.chat.id, "❌ পর্যাপ্ত ব্যালেন্স নেই।")
        query_db("INSERT INTO withdraws (uid, amount, number) VALUES (?, ?, ?)", (m.chat.id, amt, num), commit=True)
        query_db("UPDATE users SET balance = balance - ? WHERE uid = ?", (amt, m.chat.id), commit=True)
        bot.send_message(m.chat.id, "✅ উত্তোলনের অনুরোধ সফল হয়েছে। অ্যাডমিন চেক করে টাকা পাঠিয়ে দিবে।")
    except: bot.send_message(m.chat.id, "❌ ভুল ইনপুট।")

# ==================== কলব্যাক হ্যান্ডলার ====================
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = c.message.chat.id
    
    if uid == ADMIN_ID:
        if c.data == "toggle_bot":
            conf = query_db("SELECT bot_status FROM config WHERE id=1", one=True)
            new_status = 'OFF' if conf['bot_status'] == 'ON' else 'ON'
            query_db("UPDATE config SET bot_status=? WHERE id=1", (new_status,), commit=True)
            bot.answer_callback_query(c.id, f"স্ট্যাটাস: {new_status}")
            bot.edit_message_reply_markup(uid, c.message.id, reply_markup=admin_settings_inline())

        elif c.data == "change_task_reward":
            msg = bot.send_message(uid, "🔢 নতুন টাস্ক রিওয়ার্ড (টাকা) লিখুন:")
            bot.register_next_step_handler(msg, lambda m: update_config_field(m, 'task_reward'))
            bot.answer_callback_query(c.id)

        elif c.data == "change_ref_bonus":
            msg = bot.send_message(uid, "🔢 নতুন রেফার বোনাস (টাকা) লিখুন:")
            bot.register_next_step_handler(msg, lambda m: update_config_field(m, 'ref_bonus'))
            bot.answer_callback_query(c.id)

        elif c.data == "change_min_withdraw":
            msg = bot.send_message(uid, "🔢 নতুন সর্বনিম্ন উত্তোলন লিমিট লিখুন:")
            bot.register_next_step_handler(msg, lambda m: update_config_field(m, 'min_withdraw'))
            bot.answer_callback_query(c.id)

        elif c.data.startswith("u_add_"):
            target_uid = c.data.split("_")[2]
            msg = bot.send_message(uid, f"💰 ইউজার {target_uid}-কে কত টাকা দিতে চান?")
            bot.register_next_step_handler(msg, lambda m: process_manual_add(m, target_uid))
            bot.answer_callback_query(c.id)

        elif c.data.startswith("u_ban_"):
            target_uid = c.data.split("_")[2]
            user = query_db("SELECT status FROM users WHERE uid=?", (target_uid,), one=True)
            new_status = 'Banned' if user['status'] == 'Active' else 'Active'
            query_db("UPDATE users SET status=? WHERE uid=?", (new_status, target_uid), commit=True)
            bot.answer_callback_query(c.id, f"ইউজার এখন {new_status}", show_alert=True)
            bot.send_message(uid, f"✅ ইউজার 🆔 {target_uid} এখন {new_status}।")

        elif c.data.startswith("t_app_"):
            tid = c.data.split("_")[2]
            task = query_db("SELECT * FROM tasks WHERE tid=?", (tid,), one=True)
            if task and task['status'] == 'Pending':
                query_db("UPDATE users SET balance = balance + ?, hold = hold - ?, done_tasks = done_tasks + 1 WHERE uid = ?", (task['reward_amt'], task['reward_amt'], task['uid']), commit=True)
                query_db("UPDATE tasks SET status='Approved' WHERE tid=?", (tid,), commit=True)
                user_data = query_db("SELECT referred_by FROM users WHERE uid=?", (task['uid'],), one=True)
                if user_data and user_data['referred_by'] != 0:
                    query_db("UPDATE users SET balance = balance + 2.5 WHERE uid = ?", (user_data['referred_by'],), commit=True)
                bot.edit_message_text(f"✅ টাস্ক #{tid} অনুমোদিত।", uid, c.message.id)
                bot.send_message(task['uid'], f"✅ আপনার টাস্ক অনুমোদিত হয়েছে! {task['reward_amt']}৳ মূল ব্যালেন্সে যোগ হয়েছে।")
            bot.answer_callback_query(c.id)
            
        elif c.data.startswith("t_rej_"):
            tid = c.data.split("_")[2]
            task = query_db("SELECT * FROM tasks WHERE tid=?", (tid,), one=True)
            if task and task['status'] == 'Pending':
                query_db("UPDATE users SET hold = hold - ? WHERE uid = ?", (task['reward_amt'], task['uid']), commit=True)
                query_db("UPDATE tasks SET status='Rejected' WHERE tid=?", (tid,), commit=True)
                bot.edit_message_text(f"❌ টাস্ক #{tid} রিজেক্ট করা হয়েছে।", uid, c.message.id)
                bot.send_message(task['uid'], "❌ দুঃখিত, আপনার জিমেইল টাস্কটি রিজেক্ট করা হয়েছে।")
            bot.answer_callback_query(c.id)

        elif c.data.startswith("pay_done_"):
            wid = c.data.split("_")[2]
            w_info = query_db("SELECT * FROM withdraws WHERE wid=?", (wid,), one=True)
            if w_info and w_info['status'] == 'Pending':
                query_db("UPDATE withdraws SET status='Paid' WHERE wid=?", (wid,), commit=True)
                bot.edit_message_text(f"✅ উইথড্র #{wid} পেইড করা হয়েছে।", uid, c.message.id)
                bot.send_message(w_info['uid'], f"✅ অভিনন্দন! আপনার {w_info['amount']}৳ উইথড্র সফলভাবে বিকাশ করা হয়েছে।")
            bot.answer_callback_query(c.id, "পেইড সফল!")

        elif c.data.startswith("pay_fail_"):
            wid = c.data.split("_")[2]
            w_info = query_db("SELECT * FROM withdraws WHERE wid=?", (wid,), one=True)
            if w_info and w_info['status'] == 'Pending':
                query_db("UPDATE users SET balance = balance + ? WHERE uid = ?", (w_info['amount'], w_info['uid']), commit=True)
                query_db("UPDATE withdraws SET status='Rejected' WHERE wid=?", (wid,), commit=True)
                bot.edit_message_text(f"❌ উইথড্র #{wid} রিজেক্ট করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।", uid, c.message.id)
                bot.send_message(w_info['uid'], f"❌ আপনার {w_info['amount']}৳ উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে। টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে।")
            bot.answer_callback_query(c.id)

    if c.data.startswith("submit_task"):
        user_info = query_db("SELECT last_submit FROM users WHERE uid=?", (uid,), one=True)
        current_ts = int(time.time())
        last_sub = user_info['last_submit'] or 0
        rem_time = 30 - (current_ts - last_sub)
        
        if rem_time > 0:
            return bot.answer_callback_query(c.id, f"⏳ দয়া করে {int(rem_time)} সেকেন্ড অপেক্ষা করুন।", show_alert=True)
        
        parts = c.data.split("|")
        conf = query_db("SELECT task_reward FROM config WHERE id=1", one=True)
        bot.edit_message_text(f"🔍 <b>Verifying...</b>\n<code>{parts[1]}</code>", uid, c.message.id)
        time.sleep(1.5)
        
        admin_details = f"📧 Email: <code>{parts[1]}</code>\n🔑 Pwd: <code>{parts[2]}</code>"
        
        query_db("UPDATE users SET hold = hold + ?, last_submit = ? WHERE uid = ?", (conf['task_reward'], current_ts, uid), commit=True)
        query_db("INSERT INTO tasks (uid, details, reward_amt) VALUES (?, ?, ?)", (uid, admin_details, conf['task_reward']), commit=True)
        bot.edit_message_text("✅ <b>সাবমিট সফল!</b> টাকা পেন্ডিং ব্যালেন্সে যোগ হয়েছে।", uid, c.message.id)
        bot.send_message(ADMIN_ID, f"🔔 <b>নতুন টাস্ক!</b> ইউজার: <code>{uid}</code>")

    elif c.data.startswith("lang_"):
        new_lang = c.data.split("_")[1]
        query_db("UPDATE users SET lang=? WHERE uid=?", (new_lang, uid), commit=True)
        bot.answer_callback_query(c.id, f"ভাষা: {new_lang}")
        bot.send_message(uid, "✅ সেটিংস আপডেট হয়েছে!", reply_markup=main_kb(uid))

    elif c.data == "check_joined":
        if is_subscribed(uid): bot.send_message(uid, "✅ জয়েন করেছেন!", reply_markup=main_kb(uid))
        else: bot.answer_callback_query(c.id, "❌ জয়েন করেননি!", show_alert=True)

    elif c.data == "cancel_task":
        bot.delete_message(uid, c.message.id)

# ==================== অ্যাডমিন ফাংশনসমূহ ====================
def manage_user_step(m):
    user = query_db("SELECT * FROM users WHERE uid=?", (m.text,), one=True)
    if not user: return bot.send_message(ADMIN_ID, "❌ ইউজার পাওয়া যায়নি।")
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("➕ টাকা যোগ", callback_data=f"u_add_{m.text}"),
        types.InlineKeyboardButton("🚫 ব্যান/আনব্যান", callback_data=f"u_ban_{m.text}")
    )
    bot.send_message(ADMIN_ID, f"👤 ইউজার: <code>{m.text}</code>\nব্যালেন্স: {user['balance']}৳\nপেন্ডিং: {user['hold']}৳", reply_markup=kb)

def update_config_field(m, field):
    try:
        val = float(m.text)
        query_db(f"UPDATE config SET {field}=? WHERE id=1", (val,), commit=True)
        bot.send_message(ADMIN_ID, f"✅ সফলভাবে {field} আপডেট হয়েছে!")
    except: bot.send_message(ADMIN_ID, "❌ শুধুমাত্র সংখ্যা দিন।")

def process_manual_add(m, target_uid):
    try:
        amt = float(m.text)
        query_db("UPDATE users SET balance = balance + ? WHERE uid = ?", (amt, target_uid), commit=True)
        bot.send_message(ADMIN_ID, "✅ টাকা যোগ করা হয়েছে।")
        bot.send_message(target_uid, f"🎁 অ্যাডমিন আপনার ব্যালেন্সে {amt}৳ যোগ করেছে।")
    except: bot.send_message(ADMIN_ID, "❌ ভুল ইনপুট।")

def process_broadcast(m):
    users = query_db("SELECT uid FROM users")
    for u in users:
        try: bot.copy_message(u['uid'], m.chat.id, m.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ ব্রডকাস্ট সম্পন্ন!")

# ==================== Render ফ্রি হোস্ট ফিক্স ====================
if __name__ == "__main__":
    import os
    print("Bot is running...")
    
    # একটি ফেক ওয়েব সার্ভার ব্যাকগ্রাউন্ডে চালু করা যেন Render পোর্ট এরর না দেয়
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is alive!")
            
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    
    # আপনার বটের মেইন পোলিং রান করা
    bot.infinity_polling()
