import asyncio
import logging
import random
import aiomysql
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject 
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated, BotCommand
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ================= الإعدادات الأساسية والثابتة =================
BOT_TOKEN = "8799520306:AAF1bMMTftn21TCE8DvB5CgTEeUAVyez5_s"
SUPER_ADMIN_ID = 8309566360 
LOG_CHANNEL_ID = -1003753128410 # غرفة العمليات والأرشيف

DB_HOST = "srv1814.hstgr.io"
DB_USER = "u315866850_4zCBQ"
DB_PASS = "NNt0JBRMRs"  
DB_NAME = "u315866850_FnwSO"  

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ================= حالات النظام (FSM) =================
class OrderFollowers(StatesGroup):
    waiting_for_link = State()
    waiting_for_quantity = State()

class BuyPoints(StatesGroup):
    waiting_for_receipt = State()
    pending_item_id = State()

class WithdrawMIQ(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_amount = State()

class TransferPoints(StatesGroup):
    waiting_for_id = State()
    waiting_for_amount = State()

class PromoCode(StatesGroup):
    waiting_for_code = State()

class BuyAds(StatesGroup):
    waiting_for_details = State()

class StakePoints(StatesGroup):
    waiting_for_amount = State()

class AnswerNews(StatesGroup):
    waiting_for_answer = State()

class ExchangeCurrency(StatesGroup):
    waiting_for_amount = State()
    exchange_type = State()

class AdminBroadcast(StatesGroup):
    waiting_for_message = State()

# ================= دوال قاعدة البيانات المركزية =================

async def get_setting(pool, key, default_value):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT setting_value FROM settings WHERE setting_key = %s", (key,))
            res = await cur.fetchone()
            if res: return res['setting_value']
            await cur.execute("INSERT IGNORE INTO settings (setting_key, setting_value) VALUES (%s, %s)", (key, str(default_value)))
            return str(default_value)

async def log_action(pool, user_id, action_type, details):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO action_logs (user_id, action_type, details) VALUES (%s, %s, %s)", (user_id, action_type, details))

async def place_smm_order(pool, link, quantity):
    api_url = await get_setting(pool, 'smm_api_url', 'https://smmalos.com/api/v2')
    api_key = await get_setting(pool, 'smm_api_key', 'YOUR_API_KEY_HERE')
    service_id = await get_setting(pool, 'smm_service_id', '123')

    if api_key == "YOUR_API_KEY_HERE" or not api_url:
        logging.warning("SMM API is not configured in the Dashboard yet.")
        return None 

    async with aiohttp.ClientSession() as session:
        payload = {"key": api_key, "action": "add", "service": int(service_id), "link": link, "quantity": quantity}
        try:
            async with session.post(api_url, data=payload) as resp:
                result = await resp.json()
                if "order" in result: return result["order"] 
                return None
        except Exception as e:
            logging.error(f"SMM API Error: {e}")
            return None

async def create_db_pool():
    pool = await aiomysql.create_pool(host=DB_HOST, port=3306, user=DB_USER, password=DB_PASS, db=DB_NAME, autocommit=True)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE users SET role = 'owner' WHERE id = %s", (SUPER_ADMIN_ID,))
    return pool

async def get_or_create_user(pool, user_id, username, inviter_id=None):
    is_new = False
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            if not user:
                is_new = True
                if inviter_id:
                    await cur.execute("INSERT INTO users (id, username, invited_by) VALUES (%s, %s, %s)", (user_id, username, inviter_id))
                    invite_reward = int(await get_setting(pool, 'invite_reward_pts', 15))
                    await cur.execute("UPDATE users SET points = points + %s, invites_count = invites_count + 1 WHERE id = %s", (invite_reward, inviter_id))
                    await log_action(pool, inviter_id, "referral_bonus", f"Invited user {user_id}. Got {invite_reward} pts.")
                else:
                    await cur.execute("INSERT INTO users (id, username) VALUES (%s, %s)", (user_id, username))
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return await cur.fetchone(), is_new

def extract_username(link):
    link = link.strip()
    if "t.me/" in link: return "@" + link.split("t.me/")[1].replace("/", "").split("?")[0]
    if link.startswith("@"): return link
    return None

# ================= القوائم والأزرار =================

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton(text="📘 ✦ دليل استخدام منصة المليون ✦ 📘", callback_data="bot_guide")],
        [
            InlineKeyboardButton(text="💎 تجميع النقاط", callback_data="earn_points"), 
            InlineKeyboardButton(text="🚀 طلب متابعين", callback_data="order_followers")
        ],
        [
            InlineKeyboardButton(text="🛒 المتجر الإمبراطوري", callback_data="point_store"), 
            InlineKeyboardButton(text="💸 تحويل نقاط", callback_data="transfer_points")
        ],
        [
            InlineKeyboardButton(text="⛏️ منجم المليون (العب لتربح)", callback_data="play_mine_game"), 
            InlineKeyboardButton(text="🏦 بنك المليون", callback_data="bank_staking")
        ],
        [
            InlineKeyboardButton(text="⚖️ بورصة التوقعات", callback_data="predict_market"), 
            InlineKeyboardButton(text="⚡ صندوق الحظ", callback_data="flash_drop")
        ],
        [
            InlineKeyboardButton(text="💱 صرافة المليون", callback_data="exchange_menu"),
            InlineKeyboardButton(text="📥 سحب أرباح (MIQ)", callback_data="withdraw_miq")
        ],
        [
            InlineKeyboardButton(text="🏆 المتصدرين", callback_data="leaderboard"), 
            InlineKeyboardButton(text="⚔️ حرب المحافظات", callback_data="province_war")
        ],
        [
            InlineKeyboardButton(text="📰 اقرأ لتربح", callback_data="read_to_earn"), 
            InlineKeyboardButton(text="🎁 المكافأة اليومية", callback_data="daily_reward")
        ],
        [
            InlineKeyboardButton(text="🎟️ استرداد كود", callback_data="redeem_promo"), 
            InlineKeyboardButton(text="🔗 رابط الدعوة", callback_data="referral_link")
        ],
        [InlineKeyboardButton(text="👤 حسابي", callback_data="my_account")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton(text="📊 إحصائيات النظام", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 إرسال إذاعة للمستخدمين", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🌐 الانتقال للداشبورد (Web)", callback_data="admin_web_info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_provinces_keyboard():
    provs = ["بغداد", "البصرة", "نينوى", "أربيل", "النجف", "كربلاء", "بابل", "ذي قار", "ميسان", "واسط", "الديوانية", "المثنى", "كركوك", "صلاح الدين", "الأنبار", "ديالى", "السليمانية", "حلبجة"]
    kb = []
    for i in range(0, len(provs), 3):
        row = [InlineKeyboardButton(text=p, callback_data=f"prov_{p}") for p in provs[i:i+3]]
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ================= 🔒 نظام الاشتراك الإجباري الديناميكي =================

async def get_missing_force_subs(pool, user_id):
    missing_channels = []
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT channel_username FROM force_subs")
            channels = await cur.fetchall()
    for ch in channels:
        channel_uname = ch['channel_username']
        try:
            member = await bot.get_chat_member(chat_id=channel_uname, user_id=user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                missing_channels.append(channel_uname)
        except TelegramBadRequest: pass 
    return missing_channels

def get_dynamic_force_sub_menu(missing_channels):
    keyboard = []
    for ch in missing_channels:
        clean_link = ch.replace("@", "")
        keyboard.append([InlineKeyboardButton(text=f"📰 اشترك في {ch}", url=f"https://t.me/{clean_link}")])
    keyboard.append([InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data="check_force_sub")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================= 📘 الدليل التوضيحي =================

@dp.callback_query(F.data == "bot_guide")
async def bot_guide_handler(callback: CallbackQuery, pool):
    guide_text = await get_setting(pool, 'bot_guide_text', "مرحباً بك في منصة المليون.")
    formatted_text = f"📘 <b>دليل استخدام منصة المليون</b> 📘\n━━━━━━━━━━━━━━━━━━\n{guide_text}"
    keyboard = [[InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]]
    await callback.message.edit_text(formatted_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ================= نظام الدخول وبدء البوت =================

@dp.message(Command("admin"))
async def command_admin_handler(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    await message.answer("👑 <b>لوحة تحكم الإدارة السريعة</b>", reply_markup=get_admin_menu())

@dp.message(CommandStart())
async def command_start_handler(message: Message, command: CommandObject, pool, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    name = message.from_user.first_name or "صديقي"
    
    missing_subs = await get_missing_force_subs(pool, user_id)
    if missing_subs:
        text = "🛑 <b>يجب الاشتراك في القنوات التالية أولاً لتفعيل حسابك وإدارة رصيدك:</b>"
        return await message.answer(text, reply_markup=get_dynamic_force_sub_menu(missing_subs))

    inviter_id = None
    if command.args and command.args.isdigit():
        inviter_id = int(command.args)
        if inviter_id == user_id: inviter_id = None 
            
    user_data, is_new = await get_or_create_user(pool, user_id, message.from_user.username, inviter_id)
    
    if is_new:
        await log_action(pool, user_id, "user_joined", "New user registered via start command")
        try:
            await bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"👤 <b>مستخدم جديد انضم!</b>\nالاسم: {name}\nالآيدي: <code>{user_id}</code>\nاليوزر: @{message.from_user.username}")
        except Exception: pass

    if not user_data.get('province'):
        text = f"📍 <b>مرحباً بك يا {name}!</b>\n━━━━━━━━━━━━━━━━━━\nقبل أن تبدأ، يرجى اختيار محافظتك لتمثيلها في <b>(حرب المحافظات ⚔️)</b>:"
        return await message.answer(text, reply_markup=get_provinces_keyboard())

    welcome_text = f"👋 <b>أهلاً بك يا {name}</b>\n━━━━━━━━━━━━━━━━━━\n💼 <b>رصيد النقاط:</b> <code>{user_data['points']}</code>\n🪙 <b>رصيد MIQ:</b> <code>{int(user_data['miq_balance'])}</code>\n"
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.callback_query(F.data == "check_force_sub")
async def check_force_sub_handler(callback: CallbackQuery, pool):
    name = callback.from_user.first_name or "صديقي"
    missing_subs = await get_missing_force_subs(pool, callback.from_user.id)
    
    if not missing_subs:
        await callback.answer("✅ تم التحقق من الاشتراك بنجاح!", show_alert=True)
        user_data, _ = await get_or_create_user(pool, callback.from_user.id, callback.from_user.username)
        
        if not user_data.get('province'):
            text = f"📍 <b>مرحباً بك يا {name}!</b>\n━━━━━━━━━━━━━━━━━━\nاختر محافظتك لدعمها في <b>(حرب المحافظات ⚔️)</b>:"
            return await callback.message.edit_text(text, reply_markup=get_provinces_keyboard())
            
        welcome_text = f"👋 <b>أهلاً بك يا {name}</b>\n━━━━━━━━━━━━━━━━━━\n💼 <b>النقاط:</b> <code>{user_data['points']}</code>\n🪙 <b>عملة MIQ:</b> <code>{int(user_data['miq_balance'])}</code>\n"
        await callback.message.edit_text(welcome_text, reply_markup=get_main_menu())
    else:
        await callback.answer("❌ أنت لم تشترك في جميع القنوات بعد!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=get_dynamic_force_sub_menu(missing_subs))

# ================= حرب المحافظات =================

@dp.callback_query(F.data.startswith("prov_"))
async def set_province_handler(callback: CallbackQuery, pool):
    province = callback.data.split("_")[1]
    name = callback.from_user.first_name or "صديقي"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE users SET province = %s WHERE id = %s", (province, callback.from_user.id))
    text = f"✅ <b>أهلاً بك يا {name} كمقاتل من أبناء {province}!</b>\nاجمع النقاط لرفع اسم محافظتك عالياً ⚔️🇮🇶"
    await callback.message.edit_text(text, reply_markup=get_main_menu())

@dp.callback_query(F.data == "province_war")
async def province_war_handler(callback: CallbackQuery, pool):
    await callback.answer()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT province, SUM(points) as total FROM users WHERE province IS NOT NULL GROUP BY province ORDER BY total DESC LIMIT 10")
            provs = await cur.fetchall()
            
    text = "⚔️ <b>حرب المحافظات - صدارة الترتيب</b> ⚔️\n━━━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉", "🎖", "🎖", "🎖", "🎖", "🎖", "🎖", "🎖"]
    if not provs:
        text += "<i>لم تبدأ المعركة بعد. كن الأول ومثل محافظتك!</i>\n"
    else:
        for i, p in enumerate(provs):
            text += f"{medals[i]} <b>{p['province']}:</b> {int(p['total'])} نقطة\n"
    text += "\n💡 <i>انشر رابط الدعوة لأبناء محافظتك لتتصدروا الترتيب العام!</i>"
    keyboard = [[InlineKeyboardButton(text="🔙 العودة للقائمة", callback_data="back_to_main")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ================= التبادل وتجميع النقاط =================

@dp.callback_query(F.data == "earn_points")
async def earn_points_handler(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    earn_reward = int(await get_setting(pool, 'earn_reward_pts', 10))
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT id, target_link FROM orders 
                WHERE status = 'pending' AND quantity > 0 AND user_id != %s 
                AND target_link NOT IN (SELECT channel_username FROM completed_tasks WHERE user_id = %s) 
                LIMIT 1
            """, (user_id, user_id))
            order = await cur.fetchone()
            
    if not order:
        return await callback.answer("✅ لا توجد طلبات تبادل حالياً من المستخدمين. عد لاحقاً!", show_alert=True)
        
    clean_link = order['target_link'].replace('@', '')
    keyboard = [
        [InlineKeyboardButton(text="👉 اضغط هنا للاشتراك 👈", url=f"https://t.me/{clean_link}")], 
        [InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data=f"check_sub_{order['id']}")], 
        [InlineKeyboardButton(text="🔙 العودة للقائمة", callback_data="back_to_main")]
    ]
    await callback.message.edit_text(
        f"📣 <b>مهمة تبادل جديدة!</b>\n💎 <b>المكافأة: {earn_reward} نقاط</b>\nاشترك في القناة أدناه ثم اضغط تحقق لاستلام المكافأة.", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(F.data.startswith("check_sub_"))
async def check_subscription_handler(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    order_id = int(callback.data.split("_")[2]) 
    earn_reward = int(await get_setting(pool, 'earn_reward_pts', 10))
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT target_link, quantity FROM orders WHERE id = %s AND status = 'pending'", (order_id,))
            order = await cur.fetchone()
            
            if not order:
                return await callback.answer("❌ الطلب انتهى أو تم إنجازه بالكامل من قبل المستخدمين.", show_alert=True)
                
            channel_username = order['target_link']
            await cur.execute("SELECT * FROM completed_tasks WHERE user_id = %s AND channel_username = %s", (user_id, channel_username))
            if await cur.fetchone():
                return await callback.answer("❌ لقد استلمت المكافأة عن هذه القناة مسبقاً!", show_alert=True)
                
            try:
                member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
                if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                    await cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (earn_reward, user_id))
                    await cur.execute("INSERT IGNORE INTO completed_tasks (user_id, channel_username) VALUES (%s, %s)", (user_id, channel_username))
                    await cur.execute("UPDATE orders SET quantity = quantity - 1 WHERE id = %s", (order_id,))
                    await cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s AND quantity <= 0", (order_id,))
                    await log_action(pool, user_id, "earn_points", f"Subscribed to {channel_username}. Got {earn_reward} pts.")
                    await callback.answer(f"🎉 تمت إضافة {earn_reward} نقاط إلى رصيدك بنجاح.", show_alert=True)
                    await earn_points_handler(callback, pool=pool) 
                else:
                    await callback.answer("❌ أنت لم تشترك في القناة. اشترك أولاً ثم حاول التحقق.", show_alert=True)
            except TelegramBadRequest:
                await callback.answer("⚠️ خطأ في الوصول للقناة. قد يكون صاحب القناة أزال البوت من الإشراف.", show_alert=True)

@dp.chat_member()
async def penalty_system_handler(event: ChatMemberUpdated, pool):
    if event.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
        user_id = event.from_user.id
        chat_username = f"@{event.chat.username}" if event.chat.username else None
        if not chat_username: return
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM completed_tasks WHERE user_id = %s AND channel_username = %s", (user_id, chat_username))
                if await cur.fetchone():
                    await cur.execute("UPDATE users SET points = points - 20 WHERE id = %s", (user_id,))
                    await log_action(pool, user_id, "penalty_leave", f"Left channel {chat_username}. Deducted 20 pts.")
                    try:
                        await bot.send_message(chat_id=user_id, text=f"🚨 <b>تحذير هام!</b>\nلقد قمت بمغادرة القناة {chat_username}.\nتم خصم <b>20 نقطة</b> من رصيدك كعقوبة للمغادرة.")
                    except Exception: pass

# ================= طلب متابعين =================

@dp.callback_query(F.data == "order_followers")
async def order_followers_handler(callback: CallbackQuery, state: FSMContext, pool):
    user_data, _ = await get_or_create_user(pool, callback.from_user.id, callback.from_user.username)
    cost_per_follower = int(await get_setting(pool, 'follower_order_cost', 10))
    min_order = 10 * cost_per_follower
    
    if user_data['points'] < min_order:
        return await callback.answer(f"❌ رصيدك لا يكفي لطلب متابعين. الحد الأدنى للطلب يتطلب {min_order} نقطة.", show_alert=True)
        
    await state.set_state(OrderFollowers.waiting_for_link)
    keyboard = [[InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_order")]]
    await callback.message.edit_text(
        f"📝 <b>أرسل معرف قناتك (مثال: @Channel):</b>\n\n⚠️ <i>ملاحظة 1: يجب أن ترفع البوت كـ (مشرف) في قناتك.</i>\n⚠️ <i>ملاحظة 2: تكلفة المتابع الواحد هي {cost_per_follower} نقاط تخصم من رصيدك.</i>", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.message(OrderFollowers.waiting_for_link)
async def process_order_link(message: Message, state: FSMContext):
    username = extract_username(message.text)
    if not username: return await message.answer("❌ المعرف غير صالح. يرجى إرسال معرف يبدأ بـ @.")
        
    try:
        bot_member = await bot.get_chat_member(chat_id=username, user_id=bot.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            return await message.answer("❌ البوت ليس مشرفاً في قناتك. ارفع البوت مشرف أولاً ثم أرسل المعرف مرة أخرى.")
    except TelegramBadRequest:
        return await message.answer("❌ البوت لا يمكنه الوصول للقناة. تأكد من أن القناة عامة وأن البوت مشرف فيها.")
        
    await state.update_data(target_link=username)
    await state.set_state(OrderFollowers.waiting_for_quantity)
    await message.answer("🔢 <b>أرسل العدد المطلوب من المتابعين (أرقام فقط):</b>")

@dp.message(OrderFollowers.waiting_for_quantity)
async def process_order_quantity(message: Message, state: FSMContext, pool):
    if not message.text.isdigit(): return await message.answer("❌ يرجى إرسال أرقام فقط.")
    quantity = int(message.text)
    user_id = message.from_user.id
    cost_per_follower = int(await get_setting(pool, 'follower_order_cost', 10))
    total_cost = quantity * cost_per_follower
    
    if quantity < 10: return await message.answer("❌ الحد الأدنى للطلب هو 10 متابعين.")
    user_data, _ = await get_or_create_user(pool, user_id, message.from_user.username)
    
    if user_data['points'] < total_cost:
        return await message.answer(f"❌ رصيدك لا يكفي. تكلفة هذا الطلب هي {total_cost} نقطة، ورصيدك هو {user_data['points']}.")
        
    data = await state.get_data()
    channel_link = data['target_link']
    smm_order_id = await place_smm_order(pool, channel_link, quantity)
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE users SET points = points - %s WHERE id = %s", (total_cost, user_id))
            await cur.execute("INSERT INTO orders (user_id, target_link, quantity, original_quantity, status, source) VALUES (%s, %s, %s, %s, 'pending', 'exchange')", (user_id, channel_link, quantity, quantity))
            await log_action(pool, user_id, "order_followers", f"Ordered {quantity} for {channel_link}. Cost: {total_cost}")
            
    try: await bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🚀 <b>طلب تبادل جديد!</b>\nالعميل: <code>{user_id}</code>\nالقناة: {channel_link}\nالعدد: {quantity} متابع")
    except Exception: pass

    await state.clear()
    await message.answer("✅ <b>تم استلام طلبك بنجاح!</b>\nتم إدراج قناتك في قسم (تجميع النقاط) وسيبدأ الأعضاء بالانضمام إليها.", reply_markup=get_main_menu())

# ================= ⛏️ لعبة منجم المليون و سحب الـ MIQ =================

@dp.callback_query(F.data == "play_mine_game")
async def play_mine_game_handler(callback: CallbackQuery, pool):
    cost = int(await get_setting(pool, 'mine_game_cost', 100))
    reward_type = await get_setting(pool, 'mine_reward_type', 'miq')
    r_min = int(await get_setting(pool, 'mine_reward_min', 1))
    r_max = int(await get_setting(pool, 'mine_reward_max', 5))

    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT points, last_mine_time FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            
            # --- القفل الزمني الذكي (4 ساعات) ---
            if user['last_mine_time']:
                time_passed = datetime.now() - user['last_mine_time']
                if time_passed < timedelta(hours=4):
                    remaining = timedelta(hours=4) - time_passed
                    hours, remainder = divmod(remaining.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    return await callback.answer(f"⏳ المنجم قيد التجديد! الموارد غير جاهزة.\nعد بعد {hours} ساعة و {minutes} دقيقة.", show_alert=True)
            # -----------------------------------

            if user['points'] < cost:
                return await callback.answer(f"❌ رصيدك لا يكفي. تحتاج {cost} نقطة لشراء فأس التنقيب.", show_alert=True)

            reward = random.randint(r_min, r_max)

            if reward_type == 'miq':
                await cur.execute("UPDATE users SET points = points - %s, miq_balance = miq_balance + %s, last_mine_time = CURRENT_TIMESTAMP WHERE id = %s", (cost, reward, user_id))
                currency_name = "MIQ 🪙"
            else:
                await cur.execute("UPDATE users SET points = points - %s + %s, last_mine_time = CURRENT_TIMESTAMP WHERE id = %s", (cost, reward, user_id))
                currency_name = "نقطة 💎"

            await log_action(pool, user_id, "mine_game", f"Played mine game. Cost: {cost}. Won: {reward} {reward_type}")

    await callback.message.edit_text(
        f"⛏️ <b>لعبة منجم المليون</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"💸 <b>ثمن فأس التنقيب:</b> {cost} نقطة (تم الخصم)\n"
        f"🎉 <b>النتيجة:</b> لقد بحثت في المنجم ووجدت <b>{reward} {currency_name}</b>!\n\n"
        f"⏱️ <i>المنجم يحتاج الآن إلى 4 ساعات لتجديد موارده...</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 العودة للقائمة", callback_data="back_to_main")]
        ])
    )

@dp.callback_query(F.data == "withdraw_miq")
async def withdraw_miq_start(callback: CallbackQuery, state: FSMContext, pool):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT miq_balance FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()

    if user['miq_balance'] < 50:
        return await callback.answer("❌ الحد الأدنى للسحب هو 50 عملة MIQ.", show_alert=True)

    await state.update_data(max_miq=user['miq_balance'])
    await state.set_state(WithdrawMIQ.waiting_for_wallet)

    keyboard = [[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]
    await callback.message.edit_text(
        f"📥 <b>سحب أرباح (MIQ) إلى المحفظة</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"رصيدك القابل للسحب: <b>{int(user['miq_balance'])} MIQ</b>\n\n"
        f"📝 <b>أرسل الآن عنوان محفظتك (Tonkeeper Address):</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.message(WithdrawMIQ.waiting_for_wallet)
async def process_withdraw_wallet(message: Message, state: FSMContext):
    wallet = message.text.strip()
    if len(wallet) < 10:
        return await message.answer("❌ عنوان المحفظة قصير جداً وغير صالح، يرجى التأكد.")
    await state.update_data(wallet_address=wallet)
    await state.set_state(WithdrawMIQ.waiting_for_amount)
    await message.answer("🔢 <b>أرسل الكمية التي تريد سحبها (أرقام فقط):</b>")

@dp.message(WithdrawMIQ.waiting_for_amount)
async def process_withdraw_amount(message: Message, state: FSMContext, pool):
    if not message.text.isdigit():
        return await message.answer("❌ يرجى إرسال أرقام فقط.")
    
    amount = int(message.text)
    data = await state.get_data()
    max_miq = data['max_miq']

    if amount < 50:
        return await message.answer("❌ الحد الأدنى للسحب هو 50 MIQ.")
    if amount > max_miq:
        return await message.answer(f"❌ رصيدك لا يكفي. أقصى مبلغ يمكنك سحبه هو {int(max_miq)} MIQ.")

    user_id = message.from_user.id
    wallet = data['wallet_address']

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE users SET miq_balance = miq_balance - %s WHERE id = %s", (amount, user_id))
            await cur.execute("INSERT INTO withdraw_requests (user_id, wallet_address, amount) VALUES (%s, %s, %s)", (user_id, wallet, amount))
            await log_action(pool, user_id, "withdraw_miq", f"Requested withdrawal of {amount} MIQ to {wallet}")

    await state.clear()
    await message.answer("✅ <b>تم استلام طلب السحب بنجاح!</b>\nسيتم مراجعة الطلب وتحويل العملات إلى محفظتك قريباً.", reply_markup=get_main_menu())

# ================= باقي الأقسام (صندوق الحظ، البورصة، الأخبار، المتجر، الخ) =================

@dp.callback_query(F.data == "flash_drop")
async def flash_drop_handler(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM flash_drops WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
            drop = await cur.fetchone()
            if not drop: return await callback.answer("❌ لا توجد صناديق حظ مفتوحة حالياً.", show_alert=True)
            
            await cur.execute("SELECT * FROM user_flash_drops WHERE user_id = %s AND drop_id = %s", (user_id, drop['id']))
            if await cur.fetchone(): return await callback.answer("✅ لقد استلمت جائزتك من هذا الصندوق مسبقاً!", show_alert=True)
            
            if drop['current_winners'] < drop['max_winners']:
                await cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (drop['reward'], user_id))
                await cur.execute("INSERT INTO user_flash_drops (user_id, drop_id) VALUES (%s, %s)", (user_id, drop['id']))
                await cur.execute("UPDATE flash_drops SET current_winners = current_winners + 1 WHERE id = %s", (drop['id'],))
                if drop['current_winners'] + 1 >= drop['max_winners']: await cur.execute("UPDATE flash_drops SET is_active = FALSE WHERE id = %s", (drop['id'],))
                await log_action(pool, user_id, "flash_drop_win", f"Won {drop['reward']} points from drop {drop['id']}")
                await callback.answer(f"🎉 وااااو! لحقت على الصندوق وربحت {drop['reward']} نقطة!", show_alert=True)
                await back_to_main_handler(callback, pool=pool)
            else:
                await cur.execute("UPDATE flash_drops SET is_active = FALSE WHERE id = %s", (drop['id'],))
                await callback.answer("⏳ للاسف! انتهى الصندوق وتم توزيع كل الجوائز.", show_alert=True)

@dp.callback_query(F.data == "predict_market")
async def predict_market_handler(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM predictions WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            pred = await cur.fetchone()
            if not pred: return await callback.answer("❌ لا توجد بورصة توقعات نشطة حالياً.", show_alert=True)
            
            await cur.execute("SELECT * FROM user_predictions WHERE user_id = %s AND predict_id = %s", (user_id, pred['id']))
            if await cur.fetchone(): return await callback.answer("✅ لقد قمت بتسجيل توقعك والمراهنة مسبقاً!", show_alert=True)
            
            text = f"⚖️ <b>بورصة توقعات المليون</b>\n━━━━━━━━━━━━━━━━━━\n❓ <b>{pred['question']}</b>\n\n💰 <b>الرهان للدخول:</b> {pred['bet_amount']} نقطة"
            keyboard = [[InlineKeyboardButton(text=f"1️⃣ {pred['opt1']}", callback_data=f"vote_{pred['id']}_1")], [InlineKeyboardButton(text=f"2️⃣ {pred['opt2']}", callback_data=f"vote_{pred['id']}_2")]]
            if pred.get('opt3'): keyboard.append([InlineKeyboardButton(text=f"3️⃣ {pred['opt3']}", callback_data=f"vote_{pred['id']}_3")])
            if pred.get('opt4'): keyboard.append([InlineKeyboardButton(text=f"4️⃣ {pred['opt4']}", callback_data=f"vote_{pred['id']}_4")])
            keyboard.append([InlineKeyboardButton(text="🔙 العودة للقائمة", callback_data="back_to_main")])
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("vote_"))
async def process_prediction_vote(callback: CallbackQuery, pool):
    data = callback.data.split("_")
    pred_id, opt, user_id = int(data[1]), int(data[2]), callback.from_user.id
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            await cur.execute("SELECT bet_amount FROM predictions WHERE id = %s AND status = 'active'", (pred_id,))
            pred = await cur.fetchone()
            
            if not pred: return await callback.answer("❌ عذراً، تم إغلاق التصويت.", show_alert=True)
            if user['points'] < pred['bet_amount']: return await callback.answer(f"❌ رصيدك لا يكفي للرهان. تحتاج {pred['bet_amount']} نقطة.", show_alert=True)
            
            await cur.execute("UPDATE users SET points = points - %s WHERE id = %s", (pred['bet_amount'], user_id))
            await cur.execute("INSERT INTO user_predictions (user_id, predict_id, chosen_option) VALUES (%s, %s, %s)", (user_id, pred_id, opt))
            await log_action(pool, user_id, "prediction_vote", f"Voted option {opt} for prediction {pred_id}")
            
    await callback.answer("✅ تم تسجيل توقعك وخصم الرهان. بالتوفيق!", show_alert=True)
    await back_to_main_handler(callback, pool=pool)

@dp.callback_query(F.data == "read_to_earn")
async def read_to_earn_start(callback: CallbackQuery, state: FSMContext, pool):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM read_to_earn WHERE active = TRUE ORDER BY id DESC LIMIT 1")
            task = await cur.fetchone()
            if not task: return await callback.answer("❌ لا توجد مهام إخبارية حالياً.", show_alert=True)
            
            await cur.execute("SELECT * FROM completed_news WHERE user_id = %s AND news_id = %s", (user_id, task['id']))
            if await cur.fetchone(): return await callback.answer("✅ لقد قمت بالإجابة على خبر اليوم مسبقاً!", show_alert=True)
            
    await state.update_data(task=task)
    await state.set_state(AnswerNews.waiting_for_answer)
    reward_name = "عملة MIQ" if task['reward_type'] == 'miq' else "نقطة"
    text = f"📰 <b>اقرأ لتربح ({task['reward']} {reward_name})</b>\n━━━━━━━━━━━━━━━━━━\n🔗 <b>رابط الخبر:</b>\n{task['url']}\n\n❓ <b>السؤال:</b> {task['question']}\n\n✍️ <i>أرسل إجابتك الآن في رسالة هنا:</i>"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]))

@dp.message(AnswerNews.waiting_for_answer)
async def check_news_answer(message: Message, state: FSMContext, pool):
    task = (await state.get_data())['task']
    if message.text.strip() == task['answer'].strip():
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT current_winners, max_winners FROM read_to_earn WHERE id = %s AND active = TRUE", (task['id'],))
                check = await cur.fetchone()
                if not check or check['current_winners'] >= check['max_winners']:
                    await cur.execute("UPDATE read_to_earn SET active = FALSE WHERE id = %s", (task['id'],))
                    return await message.answer("⏳ للاسف! اكتمل العدد المطلوب للإجابات الصحيحة.", reply_markup=get_main_menu())

                if task['reward_type'] == 'miq': await cur.execute("UPDATE users SET miq_balance = miq_balance + %s WHERE id = %s", (task['reward'], message.from_user.id))
                else: await cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (task['reward'], message.from_user.id))
                await cur.execute("INSERT INTO completed_news (user_id, news_id) VALUES (%s, %s)", (message.from_user.id, task['id']))
                await cur.execute("UPDATE read_to_earn SET current_winners = current_winners + 1 WHERE id = %s", (task['id'],))
        currency_name = "عملة MIQ" if task['reward_type'] == 'miq' else "نقطة"
        await message.answer(f"🎉 <b>إجابة صحيحة!</b>\nتمت إضافة <b>{task['reward']} {currency_name}</b> لرصيدك.", reply_markup=get_main_menu())
    else:
        await message.answer("❌ <b>إجابة خاطئة!</b> حاول مرة أخرى.")
    await state.clear()

@dp.callback_query(F.data == "bank_staking")
async def bank_staking_menu(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    interest_percent = float(await get_setting(pool, 'bank_interest_percent', 5.0))
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM staking WHERE user_id = %s", (user_id,))
            stake = await cur.fetchone()
            await cur.execute("SELECT points, miq_balance FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()

    if stake:
        days_passed = (datetime.now() - stake['last_claim']).days
        daily_reward = int(stake['amount'] * (interest_percent / 100.0))
        reward = days_passed * daily_reward
        curr_name = "MIQ" if stake['currency'] == 'miq' else "نقطة"
        text = f"🏦 <b>بنك المليون</b>\n💰 <b>الوديعة المجمدة:</b> {stake['amount']} {curr_name}\n⏳ <b>الأرباح الجاهزة:</b> {reward} {curr_name}\n<i>(فائدة يومية {interest_percent}%)</i>"
        keyboard = [[InlineKeyboardButton(text="💵 استلام الأرباح", callback_data="claim_staking_reward")], [InlineKeyboardButton(text="🔓 كسر الوديعة", callback_data="withdraw_staking")], [InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]
    else:
        text = f"🏦 <b>بنك المليون</b>\nجمد رصيدك لمدة شهر واحصل على فائدة ({interest_percent}%).\n\n💼 <b>رصيدك المتاح:</b>\n{user['points']} نقطة (أدنى: 10k)\n{int(user['miq_balance'])} MIQ (أدنى: 1k)"
        keyboard = [[InlineKeyboardButton(text="🔒 استثمار نقاط", callback_data="deposit_pts")], [InlineKeyboardButton(text="🔒 استثمار MIQ", callback_data="deposit_miq")], [InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("deposit_"))
async def deposit_start(callback: CallbackQuery, state: FSMContext):
    currency_type = "points" if "pts" in callback.data else "miq"
    await state.update_data(curr=currency_type)
    await state.set_state(StakePoints.waiting_for_amount)
    currency_name = "نقاط" if currency_type == "points" else "MIQ"
    await callback.message.edit_text(f"🔢 <b>أرسل المبلغ الذي تريد تجميده كـ {currency_name}:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]))

@dp.message(StakePoints.waiting_for_amount)
async def process_staking_amount(message: Message, state: FSMContext, pool):
    if not message.text.isdigit(): return await message.answer("❌ أرقام فقط.")
    amount, user_id, currency = int(message.text), message.from_user.id, (await state.get_data())['curr']
    min_required = 10000 if currency == 'points' else 1000
    
    if amount < min_required: return await message.answer(f"❌ الحد الأدنى للوديعة هو {min_required}.")
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            col = "points" if currency == 'points' else "miq_balance"
            await cur.execute(f"SELECT {col} as balance FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            if user['balance'] < amount: return await message.answer("❌ رصيدك لا يكفي.", reply_markup=get_main_menu())
            
            await cur.execute(f"UPDATE users SET {col} = {col} - %s WHERE id = %s", (amount, user_id))
            await cur.execute("INSERT INTO staking (user_id, currency, amount) VALUES (%s, %s, %s)", (user_id, currency, amount))
    await state.clear()
    await message.answer(f"✅ <b>تم تجميد الوديعة بنجاح!</b> بدأ العداد.", reply_markup=get_main_menu())

@dp.callback_query(F.data == "claim_staking_reward")
async def claim_staking_reward(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    interest_percent = float(await get_setting(pool, 'bank_interest_percent', 5.0))
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM staking WHERE user_id = %s", (user_id,))
            stake = await cur.fetchone()
            if not stake: return await callback.answer("❌ ليس لديك وديعة نشطة.", show_alert=True)
            
            days_passed = (datetime.now() - stake['last_claim']).days
            reward = days_passed * int(stake['amount'] * (interest_percent / 100.0))
            if reward <= 0: return await callback.answer("❌ لم تتراكم أرباح بعد (تحتسب كل 24 ساعة).", show_alert=True)
            
            col = "points" if stake['currency'] == 'points' else "miq_balance"
            await cur.execute(f"UPDATE users SET {col} = {col} + %s WHERE id = %s", (reward, user_id))
            await cur.execute("UPDATE staking SET last_claim = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
    await callback.answer(f"🎉 استلمت {reward} كأرباح من وديعتك!", show_alert=True)
    await bank_staking_menu(callback, pool)

@dp.callback_query(F.data == "withdraw_staking")
async def withdraw_staking(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    interest_percent = float(await get_setting(pool, 'bank_interest_percent', 5.0))
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM staking WHERE user_id = %s", (user_id,))
            stake = await cur.fetchone()
            if not stake: return
            
            days_total = (datetime.now() - stake['start_time']).days
            penalty = 0
            if days_total < 30:
                penalty = (days_total * int(stake['amount'] * (interest_percent / 100.0))) * 2 
            final_return = max(0, stake['amount'] - penalty)
            col = "points" if stake['currency'] == 'points' else "miq_balance"
            
            await cur.execute(f"UPDATE users SET {col} = {col} + %s WHERE id = %s", (final_return, user_id))
            await cur.execute("DELETE FROM staking WHERE user_id = %s", (user_id,))
    msg = f"🔓 <b>تم كسر الوديعة.</b> تم إرجاع {final_return} لرصيدك."
    if penalty > 0: msg += f"\n⚠️ تم تطبيق غرامة {penalty} لكسر الوديعة مبكراً."
    await callback.answer(msg, show_alert=True)
    await back_to_main_handler(callback, pool=pool)

@dp.callback_query(F.data == "redeem_promo")
async def redeem_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoCode.waiting_for_code)
    await callback.message.edit_text("🎟️ <b>أرسل كود الهدية الذي حصلت عليه الآن:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]))

@dp.message(PromoCode.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext, pool):
    code_text = message.text.strip().upper()
    user_id = message.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM promo_codes WHERE code = %s", (code_text,))
            promo = await cur.fetchone()
            if not promo or promo['used_count'] >= promo['max_uses']: return await message.answer("❌ الكود غير صحيح أو منتهي.", reply_markup=get_main_menu())
            
            await cur.execute("SELECT * FROM user_promos WHERE user_id = %s AND code_id = %s", (user_id, promo['id']))
            if await cur.fetchone(): return await message.answer("❌ استخدمت هذا الكود مسبقاً.", reply_markup=get_main_menu())
            
            if promo['reward_type'] == 'miq': await cur.execute("UPDATE users SET miq_balance = miq_balance + %s WHERE id = %s", (promo['reward'], user_id))
            else: await cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (promo['reward'], user_id))
            await cur.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE id = %s", (promo['id'],))
            await cur.execute("INSERT INTO user_promos (user_id, code_id) VALUES (%s, %s)", (user_id, promo['id']))
    await state.clear()
    await message.answer(f"🎉 <b>مبروك! حصلت على {promo['reward']}.</b>", reply_markup=get_main_menu())

@dp.callback_query(F.data == "transfer_points")
async def transfer_points_start(callback: CallbackQuery, state: FSMContext, pool):
    fee = int(await get_setting(pool, 'transfer_fee', 0))
    text = "💸 <b>تحويل نقاط (P2P)</b>\n"
    text += f"⚠️ <i>رسوم التحويل: {fee} نقطة.</i>\n" if fee > 0 else "✅ <i>التحويل مجاني اليوم!</i>\n"
    text += "🔢 <b>أرسل الآيدي الخاص بالمستلم:</b>"
    await state.set_state(TransferPoints.waiting_for_id)
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]))

@dp.message(TransferPoints.waiting_for_id)
async def process_transfer_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("أرقام الآيدي فقط.")
    await state.update_data(target_id=int(message.text))
    await state.set_state(TransferPoints.waiting_for_amount)
    await message.answer("💰 <b>أرسل عدد النقاط المراد تحويلها:</b>")

@dp.message(TransferPoints.waiting_for_amount)
async def process_transfer_amount(message: Message, state: FSMContext, pool):
    if not message.text.isdigit(): return await message.answer("أرقام فقط.")
    amount = int(message.text)
    user_id = message.from_user.id
    target_id = (await state.get_data())['target_id']
    fee = int(await get_setting(pool, 'transfer_fee', 0))
    total = amount + fee
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            if user['points'] < total: return await message.answer(f"❌ رصيدك غير كافٍ. تحتاج {total}.", reply_markup=get_main_menu())
            
            await cur.execute("UPDATE users SET points = points - %s WHERE id = %s", (total, user_id))
            await cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (amount, target_id))
    await state.clear()
    await message.answer(f"✅ تم تحويل {amount} نقطة للآيدي {target_id}.", reply_markup=get_main_menu())
    try: await bot.send_message(chat_id=target_id, text=f"🎉 <b>استلام حوالة!</b> وصلتك {amount} نقطة من {user_id}.")
    except Exception: pass

@dp.callback_query(F.data == "exchange_menu")
async def exchange_menu_handler(callback: CallbackQuery, pool):
    miq_buy_price = int(await get_setting(pool, 'miq_buy_price', 1000))
    miq_sell_price = int(await get_setting(pool, 'miq_sell_price', 900))
    text = f"💱 <b>صرافة المليون</b>\n🟢 شراء 1 MIQ = {miq_buy_price} نقطة\n🔴 بيع 1 MIQ = {miq_sell_price} نقطة\n"
    keyboard = [[InlineKeyboardButton(text="🟢 تحويل (نقاط) إلى (MIQ)", callback_data="exch_pts_to_miq")], [InlineKeyboardButton(text="🔴 تحويل (MIQ) إلى (نقاط)", callback_data="exch_miq_to_pts")], [InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("exch_"))
async def exchange_start_handler(callback: CallbackQuery, state: FSMContext):
    exch_type = "buy_miq" if "pts_to_miq" in callback.data else "sell_miq"
    await state.update_data(exch_type=exch_type)
    await state.set_state(ExchangeCurrency.waiting_for_amount)
    prompt = "شراء" if exch_type == "buy_miq" else "بيع"
    await callback.message.edit_text(f"🔢 <b>أرسل كمية MIQ التي تريد {prompt}ها:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="back_to_main")]]))

@dp.message(ExchangeCurrency.waiting_for_amount)
async def process_exchange_amount(message: Message, state: FSMContext, pool):
    if not message.text.isdigit(): return await message.answer("❌ أرقام فقط.")
    amount_miq = int(message.text)
    if amount_miq <= 0: return await message.answer("❌ الكمية يجب أن تكون أكبر من صفر.")
    exch_type = (await state.get_data())['exch_type']
    user_id = message.from_user.id
    miq_buy_price = int(await get_setting(pool, 'miq_buy_price', 1000))
    miq_sell_price = int(await get_setting(pool, 'miq_sell_price', 900))
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT points, miq_balance FROM users WHERE id = %s", (user_id,))
            user = await cur.fetchone()
            if exch_type == "buy_miq":
                cost = amount_miq * miq_buy_price
                if user['points'] < cost: return await message.answer(f"❌ رصيدك غير كافٍ. تحتاج {cost} نقطة.", reply_markup=get_main_menu())
                await cur.execute("UPDATE users SET points = points - %s, miq_balance = miq_balance + %s WHERE id = %s", (cost, amount_miq, user_id))
                await message.answer(f"✅ اشتريت {amount_miq} MIQ بـ {cost} نقطة.", reply_markup=get_main_menu())
            else: 
                if user['miq_balance'] < amount_miq: return await message.answer(f"❌ رصيدك من MIQ غير كافٍ.", reply_markup=get_main_menu())
                gross = amount_miq * miq_sell_price
                await cur.execute("UPDATE users SET miq_balance = miq_balance - %s, points = points + %s WHERE id = %s", (amount_miq, gross, user_id))
                await message.answer(f"✅ بعت {amount_miq} MIQ بـ {gross} نقطة.", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "point_store")
async def point_store_handler(callback: CallbackQuery, pool):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM advanced_store ORDER BY id DESC")
            offers = await cur.fetchall()

    keyboard = []
    for offer in offers:
        btn_text = f"🛒 {offer['name']} بـ {offer['price']} {offer['currency']}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"buy_adv_offer_{offer['id']}")])
        
    keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")])
    await callback.message.edit_text(f"🛒 <b>المتجر الإمبراطوري الشامل</b>\nاختر المنتج الذي تود شراءه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("buy_adv_offer_"))
async def buy_adv_package_handler(callback: CallbackQuery, state: FSMContext, pool):
    offer_id = int(callback.data.split("_")[3])
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM advanced_store WHERE id = %s", (offer_id,))
            offer = await cur.fetchone()
            
    if not offer: return await callback.answer("❌ هذا العرض لم يعد متاحاً.", show_alert=True)
    
    await state.update_data(pending_item_id=offer['id'], price=offer['price'], curr=offer['currency'])
    await state.set_state(BuyPoints.waiting_for_receipt)
    
    text = f"💳 <b>شراء: {offer['name']}</b>\nالسعر: {offer['price']} {offer['currency']}\nالوصف: {offer['description']}\n\nإذا كان الدفع بغير النقاط والـ MIQ، يرجى إرسال 📸 <b>صورة إثبات التحويل</b> هنا. إذا كان الدفع بالنقاط سيتم الخصم مباشرة إذا تواصلت مع الدعم."
    keyboard = [[InlineKeyboardButton(text="❌ إلغاء الطلب", callback_data="back_to_main")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(BuyPoints.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("✅ <b>تم استلام طلب الشراء والوصل بنجاح، جاري المراجعة.</b>", reply_markup=get_main_menu())
    await state.clear()
    try: await bot.send_photo(chat_id=LOG_CHANNEL_ID, photo=message.photo[-1].file_id, caption=f"💰 <b>طلب شراء من المتجر</b>\nرقم المنتج: {data['pending_item_id']}\nمن العميل: {message.from_user.id}")
    except Exception: pass

@dp.callback_query(F.data == "leaderboard")
async def leaderboard_handler(callback: CallbackQuery, pool):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id, points FROM users ORDER BY points DESC LIMIT 5")
            top_users = await cur.fetchall()
            
    text = "🏆 <b>قائمة المتصدرين الفرديين</b> 🏆\n━━━━━━━━━━━━━━━━━━\n"
    for i, user in enumerate(top_users): text += f"{i+1}. <code>{str(user['id'])[:3]}****</code> - <b>{user['points']}</b> نقطة\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]))

@dp.callback_query(F.data == "daily_reward")
async def daily_reward_handler(callback: CallbackQuery, pool):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id FROM users WHERE id = %s AND DATE(last_daily_reward) = CURDATE()", (user_id,))
            if await cur.fetchone(): return await callback.answer("❌ لقد استلمت مكافأتك اليوم بالفعل! عد غداً.", show_alert=True)
            
            reward_pts = int(await get_setting(pool, 'daily_reward_pts', 5))
            await cur.execute("UPDATE users SET points = points + %s, last_daily_reward = CURRENT_TIMESTAMP WHERE id = %s", (reward_pts, user_id))
    await callback.answer(f"🎉 مبروك! استلمت {reward_pts} نقاط مكافأة يومية.", show_alert=True)
    await back_to_main_handler(callback, pool=pool)

@dp.callback_query(F.data == "my_account")
async def my_account_handler(callback: CallbackQuery, pool):
    user_data, _ = await get_or_create_user(pool, callback.from_user.id, callback.from_user.username)
    province_name = user_data.get('province', 'غير محدد')
    text = f"👤 <b>معلومات حسابي:</b>\n━━━━━━━━━━━━━━━━━━\nالآيدي: <code>{callback.from_user.id}</code>\nالرصيد: <b>{user_data['points']}</b> نقطة\nرصيد MIQ: <b>{int(user_data['miq_balance'])}</b>\nالمحافظة: <b>{province_name}</b>"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]))

@dp.callback_query(F.data == "referral_link")
async def referral_link_handler(callback: CallbackQuery, pool):
    bot_info = await bot.get_me()
    invite_reward = await get_setting(pool, 'invite_reward_pts', 15)
    text = f"🔗 <b>رابط الدعوة الخاص بك:</b>\nhttps://t.me/{bot_info.username}?start={callback.from_user.id}\n<i>اربح {invite_reward} نقاط عن كل دعوة!</i>"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_main")]]))

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery, pool):
    if callback.from_user.id != SUPER_ADMIN_ID: return
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT COUNT(id) FROM users")
            users_count = (await cur.fetchone())[0]
            await cur.execute("SELECT SUM(points) FROM users")
            total_points = (await cur.fetchone())[0] or 0
    text = f"📊 <b>إحصائيات النظام:</b>\n👥 المستخدمين: <code>{users_count}</code>\n💎 النقاط في السوق: <code>{total_points}</code>"
    await callback.message.edit_text(text, reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != SUPER_ADMIN_ID: return
    await state.set_state(AdminBroadcast.waiting_for_message)
    await callback.message.edit_text("📢 <b>النظام الإذاعي:</b>\nأرسل رسالة الإذاعة الآن:")

@dp.message(AdminBroadcast.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, pool):
    await message.answer("⏳ جاري إرسال الإذاعة، يرجى الانتظار...")
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id FROM users")
            users = await cur.fetchall()
            
    success_count = 0
    for user in users:
        try:
            await message.copy_to(chat_id=user['id'])
            success_count += 1
            await asyncio.sleep(0.05) 
        except Exception: pass
            
    await state.clear()
    await message.answer(f"✅ <b>اكتملت الإذاعة!</b>\nوصلت إلى {success_count} مستخدم.", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_web_info")
async def admin_web_info_handler(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID: return
    await callback.answer("التحكم الكامل (الإذاعة والمراقبة) يتم عبر الداشبورد على الويب بكل سهولة!", show_alert=True)

@dp.callback_query(F.data == "cancel_order")
@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, pool, state: FSMContext=None):
    if state: await state.clear()
    user_data, _ = await get_or_create_user(pool, callback.from_user.id, callback.from_user.username)
    welcome_text = f"👋 <b>أهلاً بك يا {callback.from_user.first_name}</b>\n━━━━━━━━━━━━━━━━━━\n💼 <b>النقاط:</b> <code>{user_data['points']}</code>\n🪙 <b>عملة MIQ:</b> <code>{int(user_data['miq_balance'])}</code>\n"
    try: await callback.message.edit_text(welcome_text, reply_markup=get_main_menu())
    except Exception: await callback.message.answer(welcome_text, reply_markup=get_main_menu())

async def main():
    pool = await create_db_pool()
    commands = [
        BotCommand(command="start", description="🔄 إعادة تشغيل البوت وإظهار القائمة"),
        BotCommand(command="admin", description="👑 لوحة تحكم الإدارة السريعة")
    ]
    await bot.set_my_commands(commands)
    
    print("🎇 محرك البوت الماستر يعمل بنجاح ومغلق بثغرة الـ 4 ساعات لمنجم المليون! 🎇")
    try:
        await dp.start_polling(bot, pool=pool, allowed_updates=dp.resolve_used_update_types())
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
