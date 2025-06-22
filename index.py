import os
import uuid
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from pdf2docx import Converter
from docx2pdf import convert
from concurrent.futures import ThreadPoolExecutor

BOT_TOKEN = '7652247095:AAEciZe1ScwKdMAKazhh1qDGX4Tig_CjnP4'  # 🔁 Replace with your bot token
executor = ThreadPoolExecutor()
user_mode = {}  # Keeps track of user conversion choice

# Show main menu
async def send_main_menu(target, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📄 ប្តូរពី​​ PDF ទៅ​ WORD", callback_data='pdf_to_word'),
            InlineKeyboardButton("📝 ប្តូរពី​ Word ទៅ​  PDF", callback_data='word_to_pdf'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(target, Update):  # from /start
        await target.message.reply_text("👋 Welcome!\nWhat would you like to do?", reply_markup=reply_markup)
    else:  # from callback
        await target.edit_message_text("👋 Welcome!\nWhat would you like to do?", reply_markup=reply_markup)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context)

# Handle user selecting an option or going back
async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    choice = query.data

    if choice == "go_home":
        await send_main_menu(query, context)
        return

    user_mode[user_id] = choice

    selected_text = "📄 PDF ➡️ Word" if choice == 'pdf_to_word' else "📝 Word ➡️ PDF"
    await query.edit_message_text(
        text=f"You selected: {selected_text}\n\n📤 Please send your file."
    )

# Convert PDF to DOCX
def convert_pdf_to_word(pdf_path, output_path):
    cv = Converter(pdf_path)
    cv.convert(output_path)
    cv.close()

# Convert DOCX to PDF
def convert_word_to_pdf(docx_path, output_path):
    convert(docx_path, output_path)

# Handle uploaded file
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    mode = user_mode.get(user_id)

    if not mode:
        await update.message.reply_text("⚠️ Please start with /start and choose a conversion type first.")
        return

    file = update.message.document
    file_name = file.file_name
    file_path = f"./{uuid.uuid4()}_{file_name}"

    if file.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("❗ File too large. Max size is 50MB.")
        return

    tg_file = await file.get_file()
    await tg_file.download_to_drive(file_path)

    status_msg = await update.message.reply_text("⏳ Converting your file, please wait...")

    try:
        output_path = ""
        loop = asyncio.get_event_loop()

        if mode == 'pdf_to_word' and file_name.endswith(".pdf"):
            output_path = file_path.replace(".pdf", ".docx")
            await loop.run_in_executor(executor, convert_pdf_to_word, file_path, output_path)
            await update.message.reply_document(document=open(output_path, "rb"))

        elif mode == 'word_to_pdf' and file_name.endswith(".docx"):
            output_path = file_path.replace(".docx", ".pdf")
            await loop.run_in_executor(executor, convert_word_to_pdf, file_path, output_path)
            await update.message.reply_document(document=open(output_path, "rb"))

        else:
            await update.message.reply_text("❌ Unsupported file type for your selected option.")
            await status_msg.delete()
            return

        await status_msg.delete()

        # Back to home button
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="go_home")]
        ])
        await update.message.reply_text("✅ Done! Choose another option:", reply_markup=back_markup)

    except Exception as e:
        await status_msg.edit_text("⚠️ Conversion failed. Please try again.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)

# Setup bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_selection))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

print("🤖 Bot is running...")
app.run_polling()
