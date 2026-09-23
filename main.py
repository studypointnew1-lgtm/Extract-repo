import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

APPX_BASE_URL = os.environ.get("APPX_BASE_URL", "https://api.appx.co.in")
APPX_AUTH_TOKEN = os.environ.get("APPX_AUTH_TOKEN", "")

app = Client("auto_batch_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
        "Authorization": f"Bearer {APPX_AUTH_TOKEN}",
        "Client-Service": "Appx",
        "Content-Type": "application/json"
    }

def is_admin(user_id):
    return user_id == ADMIN_ID

# Command: /settoken <token>
@app.on_message(filters.command("settoken") & filters.private)
async def set_token(client, message):
    global APPX_AUTH_TOKEN
    if not is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Usage:** `/settoken <YOUR_AUTH_TOKEN>`")
        return
    APPX_AUTH_TOKEN = message.command[1]
    await message.reply_text("✅ **Auth Token Successfully Set!**\n\nAb `/start` bhejkar apne purchased batches dekhein.")

# Command: /start - Auto-fetch Purchased Batches
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    global APPX_AUTH_TOKEN
    if not is_admin(message.from_user.id):
        return

    if not APPX_AUTH_TOKEN:
        await message.reply_text("❌ Token set nahi hai! Pehle `/settoken <token>` se token enter karein.")
        return

    msg = await message.reply_text("⏳ **Aapke purchased batches fetch ho rahe hain...**")

    try:
        url = f"{APPX_BASE_URL}/get-my-courses"
        resp = requests.get(url, headers=get_headers())

        if resp.status_code != 200:
            await msg.edit_text(f"❌ API Error: {resp.status_code}. Token expire ho gaya hai ya galat hai.")
            return

        courses = resp.json().get("data", [])

        if not courses:
            await msg.edit_text("⚠️ Is account me koi active/purchased batch nahi mila.")
            return

        buttons = []
        for course in courses:
            c_name = course.get("title", "Unknown Batch")
            c_id = course.get("id")
            buttons.append([InlineKeyboardButton(f"📦 {c_name}", callback_data=f"txt_{c_id}")])

        reply_markup = InlineKeyboardMarkup(buttons)
        await msg.edit_text("👇 **Aapke Purchased Batches:**\nJis batch ki TXT file chahiye, us button par click karein:", reply_markup=reply_markup)

    except Exception as e:
        await msg.edit_text(f"❌ Error: `{str(e)}`")

# Helper function for Uploader-Compatible TXT
def extract_uploader_txt(folder_id):
    txt_lines = []
    url = f"{APPX_BASE_URL}/get-contents?folder_id={folder_id}"
    resp = requests.get(url, headers=get_headers())

    if resp.status_code != 200:
        return txt_lines

    items = resp.json().get("data", [])

    for item in items:
        item_type = item.get("type")
        title = item.get("title", "Untitled").replace(":", " - ").replace("/", "-").strip()

        if item_type == "folder":
            sub_id = item.get("id")
            txt_lines.extend(extract_uploader_txt(sub_id))

        elif item_type == "pdf":
            file_url = item.get("file_url")
            if file_url:
                txt_lines.append(f"{title}.pdf:{file_url}")

        elif item_type == "video":
            video_url = item.get("video_url")
            if video_url:
                txt_lines.append(f"{title}:{video_url}")

    return txt_lines

# Callback Query Handler for Buttons
@app.on_callback_query()
async def handle_batch_click(client, callback_query: CallbackQuery):
    data = callback_query.data

    if data.startswith("txt_"):
        course_id = data.split("_")[1]
        await callback_query.answer("Batch select ho gaya! TXT file ban rahi hai...")
        
        status_msg = await callback_query.message.reply_text(f"⏳ **Batch ID {course_id} scan ho raha hai...**")

        try:
            lines = extract_uploader_txt(course_id)

            if not lines:
                await status_msg.edit_text("⚠️ Iss batch me koi content nahi mila.")
                return

            file_name = f"Batch_{course_id}_Uploader.txt"

            with open(file_name, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            await client.send_document(
                chat_id=callback_query.message.chat.id,
                document=file_name,
                caption=(
                    f"✅ **Uploader Compatible TXT File Ready!**\n\n"
                    f"🆔 **Batch ID:** `{course_id}`\n"
                    f"📊 **Total Links Extracted:** `{len(lines)}`\n\n"
                    f"📌 Is file ko apne Uploader Bot me send karein."
                )
            )

            if os.path.exists(file_name):
                os.remove(file_name)

            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(f"❌ Error: `{str(e)}`")

app.run()
  
