import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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
db = db_client["telegram_file_sharing_bot"] # Database အမည်
files_collection = db["stored_files"]      # Collection (Table) အမည်

REQUIRED_CHANNELS = {
    "-1003786933619": "https://t.me/+57dXzOlHgcQzYjZl"
    #"@my_public_channel": "https://t.me/my_public_channel",
    #"-1001122334455": "https://t.me/+OpQrStUvWxYz" 
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

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    user_id = message.from_user.id

    if len(args) > 1:
        file_code = args[1]
        
        unjoined_channels = get_unjoined_channels(user_id)
        
        if unjoined_channels:
            markup = InlineKeyboardMarkup(row_width=1)
            channel_count = 1
            
            for chat_id, link in unjoined_channels.items():
                markup.add(InlineKeyboardButton(f" Join Channel ", url=link)) #markup.add(InlineKeyboardButton(f"Channel {channel_count} ကို Join ပါ", url=link))
                channel_count += 1
                
            check_url = f"https://t.me/{BOT_USERNAME}?start={file_code}"
            markup.add(InlineKeyboardButton("✅ Join ပြီးပါပြီ ", url=check_url))
            
            bot.send_message(
                message.chat.id, 
                "⚠️ ဖိုင်ရယူနိုင်ရန် အောက်ပါ Channel ကို Join ပေးပါ။ \n\nJoin ပြီးပါက '✅ Join ပြီးပါပြီ' ကိုနှိပ်ပါ။", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

        file_data = files_collection.find_one({"file_code": file_code})
        
        if file_data:
            file_id = file_data['file_id']
            file_type = file_data['file_type']
            original_caption = file_data.get('original_caption', '') 

            ads_text = "\n\n<b>Powered by:</b> <a href='https://kyawmintun.onrender.com'> Kyaw Min Tun</a>"
            
            final_caption = f"{original_caption}{ads_text}" if original_caption else ads_text
            
            if file_type == 'document':
                bot.send_document(message.chat.id, file_id, caption=final_caption, parse_mode="HTML")
            elif file_type == 'video':
                bot.send_video(message.chat.id, file_id, caption=final_caption, parse_mode="HTML")
            elif file_type == 'photo':
                bot.send_photo(message.chat.id, file_id, caption=final_caption, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "Hi there! 👋 \n\n Check Website - https://kyawmintun.onrender.com")

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

    # မူရင်း Caption ရှိမရှိ စစ်ဆေးပြီး ဖမ်းယူခြင်း (HTML format ဖြင့်ယူခြင်း)
    original_caption = message.html_caption if message.html_caption else ""

    import uuid
    file_code = str(uuid.uuid4())[:8]
    
    # Database ထဲသို့ Data ထည့်သွင်းရာတွင် Caption ကိုပါ ထည့်သိမ်းခြင်း
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

# Background thread ဖြင့် Port ဖွင့်ခြင်း
threading.Thread(target=run_dummy_server, daemon=True).start()

print("Bot with MongoDB and Dummy Port is running...")
bot.polling(none_stop=True)
