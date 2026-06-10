import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import uuid
import pymongo

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
                markup.add(InlineKeyboardButton(f"Channel {channel_count} ကို Join ပါ", url=link))
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

        # MongoDB ထဲမှ ဖိုင်အချက်အလက်ကို ရှာဖွေခြင်း
        file_data = files_collection.find_one({"file_code": file_code})
        
        if file_data:
            file_id = file_data['file_id']
            file_type = file_data['file_type']
            
            if file_type == 'document':
                bot.send_document(message.chat.id, file_id)
            elif file_type == 'video':
                bot.send_video(message.chat.id, file_id)
            elif file_type == 'photo':
                bot.send_photo(message.chat.id, file_id)
        else:
            bot.send_message(message.chat.id, "ဖိုင်ရှာမတွေ့ပါ။ လင့်ခ်မှားယွင်းနေနိုင်ပါသည် သို့မဟုတ် ဖျက်လိုက်ပါပြီ။")
    else:
        bot.send_message(message.chat.id, "မင်္ဂလာပါ။ ဖိုင်ရယူရန် သက်ဆိုင်ရာ Link ကိုနှိပ်ပါ။")

# Admin ထံမှ ဖိုင်များကို လက်ခံပြီး Database ထဲသိမ်းကာ Link ထုတ်ပေးမည့် နေရာ
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

    # Unique Code ထုတ်ခြင်း
    file_code = str(uuid.uuid4())[:8]
    
    # Database ထဲသို့ Data ထည့်သွင်းခြင်း
    document_to_save = {
        "file_code": file_code,
        "file_id": file_id,
        "file_type": file_type,
        "uploader_id": message.from_user.id
    }
    files_collection.insert_one(document_to_save)

    # Deep Link ထုတ်ပေးခြင်း
    link = f"https://t.me/{BOT_USERNAME}?start={file_code}"
    bot.reply_to(message, f"✅ ဖိုင်ကို Database ထဲသို့ အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။\n\n📌 မျှဝေရန် Link: {link}")

print("Bot with MongoDB is running...")
bot.polling(none_stop=True)
