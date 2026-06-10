import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import os
import uuid
import pymongo
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
BOT_USERNAME = os.environ.get("BOT_USERNAME")
MONGO_URI = os.environ.get("MONGO_URI")

bot = telebot.TeleBot(TOKEN)
db_client = pymongo.MongoClient(MONGO_URI)
db = db_client["telegram_file_sharing_bot"] 
files_collection = db["stored_files"]      

REQUIRED_CHANNELS = {
    "-1003786933619": "https://t.me/+57dXzOlHgcQzYjZl"
}

def get_unjoined_channels(user_id):
    unjoined = {}
    for chat_id, link in REQUIRED_CHANNELS.items():
        try:
            check_id = int(chat_id) if chat_id.lstrip('-').isdigit() else chat_id
            member = bot.get_chat_member(check_id, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                unjoined[chat_id] = link
        except Exception as e:
            print(f"Error checking channel {chat_id}: {e}")
            unjoined[chat_id] = link 
    return unjoined

def send_file_to_user(chat_id, file_code):
    file_data = files_collection.find_one({"file_code": file_code})
    
    if file_data:
        file_id = file_data['file_id']
        file_type = file_data['file_type']
        original_caption = file_data.get('original_caption', '') 

        ads_text = "\n\n<b>Powered by:</b> <a href='https://t.me/+57dXzOlHgcQzYjZl'> Data House </a>"
        
        final_caption = f"{original_caption}{ads_text}" if original_caption else ads_text
        
        remove_kb = ReplyKeyboardRemove()
        
        # ဖိုင်ပို့တဲ့အခါ reply_markup=remove_kb ကို တွဲထည့်ပေးလိုက်ပါ
        if file_type == 'document':
            bot.send_document(chat_id, file_id, caption=final_caption, parse_mode="HTML", reply_markup=remove_kb)
        elif file_type == 'video':
            bot.send_video(chat_id, file_id, caption=final_caption, parse_mode="HTML", reply_markup=remove_kb)
        elif file_type == 'photo':
            bot.send_photo(chat_id, file_id, caption=final_caption, parse_mode="HTML", reply_markup=remove_kb)
    else:
        bot.send_message(chat_id, "❌ 404, File not Found! ")

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    user_id = message.from_user.id

    if len(args) > 1:
        file_code = args[1]
        unjoined_channels = get_unjoined_channels(user_id)
        
        if unjoined_channels:
            markup = InlineKeyboardMarkup(row_width=1)
            
            for chat_id, link in unjoined_channels.items():
                markup.add(InlineKeyboardButton(" Join Channel ", url=link))
                
            # 🔴 ပြင်ဆင်ချက် - URL အစား Callback Data ပြောင်းသုံးထားသည် (START ခလုတ် ထပ်မပေါ်စေရန်)
            markup.add(InlineKeyboardButton("✅ Join ပြီးပါပြီ ", callback_data=f"check_{file_code}"))
            
            bot.send_message(
                message.chat.id, 
                "⚠️ ဖိုင်ရယူနိုင်ရန် အောက်ပါ Channel ကို Join ပေးပါ။ \n\nJoin ပြီးပါက '✅ Join ပြီးပါပြီ' ကိုနှိပ်ပါ။", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

        # အားလုံး Join ထားပြီးသားဆိုလျှင် ဖိုင်တိုက်ရိုက်ပို့ရန်
        send_file_to_user(message.chat.id, file_code)
        
    else:
        # 🔴 ပြင်ဆင်ချက် - /start အလွတ်ရိုက်လျှင် ပြမည့်စာ (Indent နေရာမှန်ပြင်ထားသည်)
        bot.send_message(message.chat.id, "Hi there! 👋 \n\n Join Community - https://t.me/+57dXzOlHgcQzYjZl")

# 🔴 ပြင်ဆင်ချက် - ✅ Join ပြီးပါပြီ Button ကို နှိပ်လျှင် အလုပ်လုပ်မည့် နေရာ (Callback Query)
@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def handle_check_join(call):
    file_code = call.data.split('_')[1]
    user_id = call.from_user.id
    
    unjoined_channels = get_unjoined_channels(user_id)
    
    if unjoined_channels:
        # မ Join ရသေးလျှင် Alert ပြမည် (Telegram ရဲ့ အပေါ်ကနေ ပေါ်လာမည့်စာ)
        bot.answer_callback_query(call.id, "Channel ကို Join ရန် လိုအပ်ပါသေးသည်!", show_alert=True)
    else:
        # Join ပြီးသွားလျှင် "Join ရန် လိုအပ်သည်" ဆိုသည့် Message အဟောင်းကို ဖျက်ပြီး ဖိုင်ပို့ပေးမည်
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_file_to_user(call.message.chat.id, file_code)

@bot.message_handler(content_types=['document', 'video', 'photo'])
def handle_files(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.document:
        file_id = message.document.file_id
        file_type = 'document'
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'

    original_caption = message.html_caption if message.html_caption else ""

    import uuid
    file_code = str(uuid.uuid4())[:8]
    
    document_to_save = {
        "file_code": file_code,
        "file_id": file_id,
        "file_type": file_type,
        "uploader_id": message.from_user.id,
        "original_caption": original_caption
    }
    files_collection.insert_one(document_to_save)

    link = f"https://t.me/{BOT_USERNAME}?start={file_code}"
    reply_text = f"✅Successful Saved!\n\n📌 Link :\n<code>{link}</code>"
    
    bot.reply_to(message, reply_text, parse_mode="HTML")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_dummy_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

print("Bot with MongoDB and Dummy Port is running...")
bot.polling(none_stop=True)
