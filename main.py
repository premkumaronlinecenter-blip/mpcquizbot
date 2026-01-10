import telebot
import google.generativeai as genai
from PIL import Image
import io
import time
from telebot import types

# --- सही कॉन्फ़िगरेशन ---
GEMINI_API_KEY = "AIzaSyByJOC15zNpSahRWEE9IVAEBgELVy-Pfjw"
TELEGRAM_BOT_TOKEN = "8231937886:AAHSZc_E4b9BZg4Io-3MxbXFDsS_dgKSJNM"

genai.configure(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# मॉडल का नाम gemini-2.5-flash रखें
model = genai.GenerativeModel(model_name='gemini-2.5-flash')

user_data = {} 

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Hindi (हिंदी)', 'English')
    bot.send_message(message.chat.id, "नमस्ते! भाषा चुनें और अपनी फोटो सीरियल से भेजें:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Hindi (हिंदी)', 'English'])
def set_lang(message):
    lang = "Hindi" if "Hindi" in message.text else "English"
    user_data[message.chat.id] = {'lang': lang, 'images': []}
    bot.send_message(message.chat.id, f"ठीक है! अब फोटो भेजें। मैं उन्हें क्रम (Serial) से प्रोसेस करूँगा।")

@bot.message_handler(content_types=['photo'])
def handle_docs(message):
    cid = message.chat.id
    if cid not in user_data: user_data[cid] = {'lang': 'Hindi', 'images': []}
    
    fid = message.photo[-1].file_id
    finfo = bot.get_file(fid)
    downloaded = bot.download_file(finfo.file_path)
    
    # फोटो को समय (ID) के साथ स्टोर करें
    user_data[cid]['images'].append({
        'id': message.message_id, 
        'img': Image.open(io.BytesIO(downloaded))
    })

    if len(user_data[cid]['images']) == 1:
        bot.send_message(cid, "फोटो मिल रही हैं... मैं सीरियल चेक कर रहा हूँ। 6 सेकंड रुकें।")
        time.sleep(7) 
        process_images(cid)

def process_images(cid):
    data = user_data.get(cid)
    if not data or not data['images']: return
    
    # फोटो को उनके भेजने के क्रम के हिसाब से सॉर्ट करना
    sorted_images = sorted(data['images'], key=lambda x: x['id'])
    final_images = [x['img'] for x in sorted_images]
    
    bot.send_message(cid, f"कुल {len(final_images)} फोटो मिली हैं। पहली फोटो से प्रोसेसिंग शुरू कर रहा हूँ...")

    try:
        # प्रॉम्प्ट में हमने डैश हटाने और सीरियल का नियम पक्का कर दिया है
        prompt = f"""
Strictly follow this formatting:
1. Output MUST be in a single code block.
2. IMPORTANT: Start extracting from the VERY FIRST question of the FIRST image and go until the last question. Do not skip the beginning.
3. YES question numbers or bullet points in the output.
4. Options must be a), b), c), and d).
5. Mark the correct answer with '✅' on the right side.
6. Provide explanation starting with 'Ex: ' after the options.
7. Separate each question block with ONLY a double line break (empty space).
8. DO NOT use any dashes (---), horizontal lines, or special markdown symbols like stars outside the block.
9. Language: {data['lang']}.
        """
        
        response = model.generate_content([prompt] + final_images)
        text = response.text
        
        # --- सुधारा हुआ हिस्सा (HTML Mode) ---
        # Markdown एरर से बचने के लिए HTML टैग <pre> का उपयोग
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                chunk = text[i:i+4000].replace('<', '&lt;').replace('>', '&gt;') # सुरक्षा के लिए
                bot.send_message(cid, f"<pre>{chunk}</pre>", parse_mode="HTML")
        else:
            final_text = text.replace('<', '&lt;').replace('>', '&gt;')
            bot.send_message(cid, f"<pre>{final_text}</pre>", parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(cid, f"Error: {str(e)}")
    
    user_data[cid]['images'] = [] # मेमोरी साफ़ करें

print("बॉट अब एरर-फ्री HTML मोड में तैयार है...")
bot.polling()
