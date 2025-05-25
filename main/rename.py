#TG : @Sunrises_24
#ALL FILES UPLOADED - CREDITS 🌟 - @Sunrises_24
import subprocess
import os, json
import time
import ffmpeg
from pyrogram.types import Message
from pyrogram.types import Document, Video
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.errors import MessageNotModified
from main.utils import progress_message, humanbytes
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup,CallbackQuery
from config import AUTH_USERS, ADMIN, CAPTION
from main.utils import upload_files, download_media, download_file_from_drive
import aiohttp
from pyrogram.errors import RPCError, FloodWait
from main.ffmpeg import merge_videos_and_audios
from googleaiclient.http import MediaFileUpload
from main.gdrive import upload_to_google_drive, drive_service
from googleapiclient.errors import HttpError
from Database.database import db
import datetime
from datetime import timedelta
import psutil
from pymongo.errors import PyMongoError
from yt_dlp import YoutubeDL
from html_telegraph_poster import TelegraphPoster
from os import execl as osexecl
from sys import executable
from config import *
import logging

logging.basicConfig(
    filename='SunrisesBot.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Example of logging a message
logging.info('Bot started successfully!')

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import os
import asyncio
import time


MERGE_ENABLED = True
FILE_SIZE_LIMIT = 50 * 1024 * 1024  # example 50 MB limit
merge_state = {}



# Merging function with ffmpeg for video + multiple audios, no re-encode, just stream copy
async def merge_videos_and_audios(input_file, output_file):
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", input_file,
        "-c", "copy",
        output_file
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {stderr.decode()}")

@Client.on_message(filters.command("mergeaudio") & filters.private)
async def start_mergeaudio_command(bot, msg: Message):
    global MERGE_ENABLED
    if not MERGE_ENABLED:
        return await msg.reply_text("The merge feature is currently disabled.")
    user_id = msg.from_user.id
    merge_state[user_id] = {
        "files": [],
        "output_filename": None,
        "is_merging": False,
    }
    await msg.reply_text("Send up to 10 video or audio files one by one. When done, press the 'Merge Now' button below or send `/videomerge filename`.")

@Client.on_message((filters.video | filters.audio | filters.document) & filters.chat(GROUP))
async def handle_media_files(bot, msg: Message):
    user_id = msg.from_user.id
    if user_id in merge_state:
        if merge_state[user_id].get("is_merging"):
            await msg.reply_text("Merging process has started. No more files can be added.")
            return

        if len(merge_state[user_id]["files"]) >= 10:
            await msg.reply_text("You have already sent 10 files. Press the 'Merge Now' button below or send `/videomerge filename`.")
            return

        merge_state[user_id]["files"].append(msg)
        # Inline button for merge
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 Merge Now", callback_data=f"merge_now:{user_id}")]]
        )
        await msg.reply_text(
            f"File received! Total files: {len(merge_state[user_id]['files'])}\n"
            "Send more files or press 'Merge Now' to start merging.",
            reply_markup=markup
        )

@Client.on_callback_query(filters.regex(r"^merge_now:(\d+)$"))
async def on_merge_button(bot, cq: CallbackQuery):
    user_id = int(cq.data.split(":")[1])
    from_user_id = cq.from_user.id

    if from_user_id != user_id:
        return await cq.answer("This button isn't for you.", show_alert=True)

    if user_id not in merge_state or not merge_state[user_id]["files"]:
        return await cq.answer("No files to merge. Use /mergeaudio to start.", show_alert=True)

    if merge_state[user_id]["is_merging"]:
        return await cq.answer("Merging already in progress. Please wait.", show_alert=True)

    # Optionally ask for filename or set default
    merge_state[user_id]["output_filename"] = "merged_output.mp4"
    merge_state[user_id]["is_merging"] = True
    await cq.answer("Merging started!")

    # Use the message to reply/upload progress
    await merge_and_upload(bot, await bot.get_messages(cq.message.chat.id, cq.message.id))
    # Delete the inline button message after starting merge
    await cq.message.delete()

@Client.on_message(filters.command("videomerge") & private)
async def start_video_merge_command(bot, msg: Message):
    user_id = msg.from_user.id
    if user_id not in merge_state or not merge_state[user_id]["files"]:
        return await msg.reply_text("No files received for merging. Please send files using /mergeaudio command first.")

    if merge_state[user_id].get("is_merging"):
        return await msg.reply_text("Merging already in progress. Please wait.")

    output_filename = msg.text.split(' ', 1)[1].strip() if len(msg.text.split()) > 1 else "merged_output.mp4"
    merge_state[user_id]["output_filename"] = output_filename
    merge_state[user_id]["is_merging"] = True

    await merge_and_upload(bot, msg)

async def merge_and_upload(bot, msg: Message):
    user_id = msg.from_user.id
    if user_id not in merge_state:
        return await msg.reply_text("No merge state found. Start with /mergeaudio.")

    files_to_merge = merge_state[user_id]["files"]
    output_filename = merge_state[user_id].get("output_filename", "merged_output.mp4")
    output_path = output_filename

    sts = await msg.reply_text("🚀 Starting merge process...")

    try:
        file_paths = []
        for file_msg in files_to_merge:
            file_path = await download_media(file_msg, sts)
            file_paths.append(file_path)

        input_file = "input.txt"
        with open(input_file, "w") as f:
            for file_path in file_paths:
                f.write(f"file '{file_path}'\n")

        await sts.edit("💠 Merging files... ⚡")
        await merge_videos_and_audios(input_file, output_path)

        filesize = os.path.getsize(output_path)
        filesize_human = humanbytes(filesize)
        caption = f"{output_filename}\n\n🌟 Size: {filesize_human}"

        await sts.edit("💠 Uploading merged file... ⚡")

        c_time = time.time()

        if filesize > FILE_SIZE_LIMIT:
            file_link = await upload_to_google_drive(output_path, output_filename, sts)
            button = [[InlineKeyboardButton("☁️ CloudUrl ☁️", url=file_link)]]
            await msg.reply_text(
                f"File merged and uploaded to Google Drive!\n\nLink: [Click Here]({file_link})\n\n"
                f"Filename: {output_filename}\nRequested by: {msg.from_user.mention}\nSize: {filesize_human}",
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            await bot.send_document(
                user_id,
                document=output_path,
                caption=caption,
                progress=progress_message,
                progress_args=("Uploading merged file...", sts, c_time),
            )
            await msg.reply_text(f"Merge complete! File sent in PM, {msg.from_user.mention}")

    except Exception as e:
        await sts.edit(f"❌ Error: {e}")

    finally:
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_path):
            os.remove(output_path)

        if user_id in merge_state:
            del merge_state[user_id]

        await sts.delete()
    
                            
if __name__ == '__main__':
app = Client("my_bot", bot_token=BOT_TOKEN)
app.run()     
