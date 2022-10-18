from dotenv import load_dotenv

load_dotenv(
    "config.env",
    override=True,
)
import asyncio
import os
import shutil
import time

import psutil
from PIL import Image
from pyrogram import Client, filters,enums
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserIsBlocked,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from pyromod import listen

from __init__ import (
    AUDIO_EXTENSIONS,
    BROADCAST_MSG,
    LOGGER,
    MERGE_MODE,
    SUBTITLE_EXTENSIONS,
    UPLOAD_AS_DOC,
    UPLOAD_TO_DRIVE,
    VIDEO_EXTENSIONS,
    bMaker,
    formatDB,
    gDict,
    queueDB,
    replyDB,
)
from config import Config
from helpers import database
from helpers.utils import UserSettings, get_readable_file_size, get_readable_time

botStartTime = time.time()
parent_id = Config.GDRIVE_FOLDER_ID


class MergeBot(Client):
    def start(self):
        super().start()
        try:
            self.send_message(chat_id=int(Config.OWNER), text="<b>Bot Started!</b>")
        except Exception as err:
            LOGGER.error("Boot alert failed! Please start bot in PM")
        return LOGGER.info("Bot Started!")

    def stop(self):
        super().stop()
        return LOGGER.info("Bot Stopped")


mergeApp = MergeBot(
    name="merge-bot",
    api_hash=Config.API_HASH,
    api_id=int(Config.TELEGRAM_API),
    bot_token=Config.BOT_TOKEN,
    workers=300,
    plugins=dict(root="plugins"),
    app_version="4.0+yash-multiMergeSupport",
)


if os.path.exists("downloads") == False:
    os.makedirs("downloads")


@mergeApp.on_message(filters.command(["log"]) & filters.user(Config.OWNER_USERNAME))
async def sendLogFile(c: Client, m: Message):
    await m.reply_document(document="./mergebotlog.txt")
    return


@mergeApp.on_message(filters.command(["login"]) & filters.private)
async def loginHandler(c: Client, m: Message):
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    if user.banned:
        await m.reply_text(text=f"**Banned User Detected!**\n  🛡️ Unfortunately you can't use me\n\nContact: 🈲 @{Config.OWNER_USERNAME}", quote=True)
        return
    if user.user_id == int(Config.OWNER):
        user.allowed = True
    if user.allowed:
        await m.reply_text(text=f"**Dont Spam**\n  ⚡ You can use me!!", quote=True)
    else:
        try:
            passwd = m.text.split(" ", 1)[1]
        except:
            await m.reply_text("**Command:**\n  `/login <password>`\n\n**Usage:**\n  `password`: Get the password from owner",quote=True,parse_mode=enums.parse_mode.ParseMode.MARKDOWN)
        passwd = passwd.strip()
        if passwd == Config.PASSWORD:
            user.allowed = True
            await m.reply_text(
                text=f"**Login passed ✅,**\n  ⚡ Now you can use me!!", quote=True
            )
        else:
            await m.reply_text(
                text=f"**Login failed ❌,**\n  🛡️ Unfortunately you can't use me\n\nContact: 🈲 @{Config.OWNER_USERNAME}",
                quote=True,
            )
    user.set()
    del user
    return


@mergeApp.on_message(filters.command(["stats"]) & filters.private)
async def stats_handler(c: Client, m: Message):
    currentTime = get_readable_time(time.time() - botStartTime)
    total, used, free = shutil.disk_usage(".")
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    stats = (
        f"<b>╭「 💠 BOT STATISTICS 」</b>\n"
        f"<b>│</b>\n"
        f"<b>├⏳ Bot Uptime : {currentTime}</b>\n"
        f"<b>├💾 Total Disk Space : {total}</b>\n"
        f"<b>├📀 Total Used Space : {used}</b>\n"
        f"<b>├💿 Total Free Space : {free}</b>\n"
        f"<b>├🔺 Total Upload : {sent}</b>\n"
        f"<b>├🔻 Total Download : {recv}</b>\n"
        f"<b>├🖥 CPU : {cpuUsage}%</b>\n"
        f"<b>├⚙️ RAM : {memory}%</b>\n"
        f"<b>╰💿 DISK : {disk}%</b>"
    )
    await m.reply_text(text=stats, quote=True)


@mergeApp.on_message(
    filters.command(["broadcast"])
    & filters.private
    & filters.user(Config.OWNER_USERNAME)
)
async def broadcast_handler(c: Client, m: Message):
    msg = m.reply_to_message
    userList = await database.broadcast()
    len = userList.collection.count_documents({})
    status = await m.reply_text(text=BROADCAST_MSG.format(str(len), "0"), quote=True)
    success = 0
    for i in range(len):
        try:
            uid = userList[i]["_id"]
            if uid != int(Config.OWNER):
                await msg.copy(chat_id=uid)
            success = i + 1
            await status.edit_text(text=BROADCAST_MSG.format(len, success))
            LOGGER.info(f"Message sent to {userList[i]['name']} ")
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await msg.copy(chat_id=userList[i]["_id"])
            LOGGER.info(f"Message sent to {userList[i]['name']} ")
        except InputUserDeactivated:
            await database.deleteUser(userList[i]["_id"])
            LOGGER.info(f"{userList[i]['_id']} - {userList[i]['name']} : deactivated\n")
        except UserIsBlocked:
            await database.deleteUser(userList[i]["_id"])
            LOGGER.info(
                f"{userList[i]['_id']} - {userList[i]['name']} : blocked the bot\n"
            )
        except PeerIdInvalid:
            await database.deleteUser(userList[i]["_id"])
            LOGGER.info(
                f"{userList[i]['_id']} - {userList[i]['name']} : user id invalid\n"
            )
        except Exception as err:
            LOGGER.warning(f"{err}\n")
        await asyncio.sleep(3)
    await status.edit_text(
        text=BROADCAST_MSG.format(len, success)
        + f"**Failed: {str(len-success)}**\n\n__🤓 Broadcast completed sucessfully__",
    )


@mergeApp.on_message(filters.command(["start"]) & filters.private)
async def start_handler(c: Client, m: Message):
    user = UserSettings(m.from_user.id, m.from_user.first_name)

    if m.from_user.id != int(Config.OWNER):
        if user.allowed is False:
            res = await m.reply_text(
                text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Unfortunately you can't use me\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
                quote=True,
            )
            return
    else:
        user.allowed = True
        user.set()
    res = await m.reply_text(
        text=f"Hi **{m.from_user.first_name}**\n\n ⚡ I am a file/video merger bot\n\n😎 I can merge Telegram files!, And upload it to telegram\n\n**Owner: 🈲 @{Config.OWNER_USERNAME}** ",
        quote=True,
    )
    del user


@mergeApp.on_message(
    (filters.document | filters.video | filters.audio) & filters.private
)
async def files_handler(c: Client, m: Message):
    user_id = m.from_user.id
    user = UserSettings(user_id, m.from_user.first_name)
    if user_id != int(Config.OWNER):
        if user.allowed is False:
            res = await m.reply_text(
                text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Unfortunately you can't use me\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
                quote=True,
            )
            return
    if user.merge_mode == 4: # extract_mode
        return
    input_ = f"downloads/{str(user_id)}/input.txt"
    if os.path.exists(input_):
        await m.reply_text("Sorry Bro,\nAlready One process in Progress!\nDon't Spam.")
        return
    media = m.video or m.document or m.audio
    if media.file_name is None:
        await m.reply_text("File Not Found")
        return
    currentFileNameExt = media.file_name.rsplit(sep=".")[-1].lower()
    if currentFileNameExt in "conf":
        await m.reply_text(
            text="**💾 Config file found, Do you want to save it?**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Yes", callback_data=f"rclone_save"),
                        InlineKeyboardButton("❌ No", callback_data="rclone_discard"),
                    ]
                ]
            ),
            quote=True,
        )
        return
    # if MERGE_MODE.get(user_id) is None:
    #     userMergeMode = database.getUserMergeSettings(user_id)
    #     if userMergeMode is not None:
    #         MERGE_MODE[user_id] = userMergeMode
    #     else:
    #         database.setUserMergeMode(uid=user_id, mode=1)
    #         MERGE_MODE[user_id] = 1

    if user.merge_mode == 1:

        if queueDB.get(user_id, None) is None:
            formatDB.update({user_id: currentFileNameExt})
        if formatDB.get(
            user_id, None
        ) is not None and currentFileNameExt != formatDB.get(user_id):
            await m.reply_text(
                f"First you sent a {formatDB.get(user_id).upper()} file so now send only that type of file.",
                quote=True,
            )
            return
        if currentFileNameExt not in VIDEO_EXTENSIONS:
            await m.reply_text(
                "This Video Format not Allowed!\nOnly send MP4 or MKV or WEBM.",
                quote=True,
            )
            return
        editable = await m.reply_text("Please Wait ...", quote=True)
        MessageText = "Okay,\nNow Send Me Next Video or Press **Merge Now** Button!"

        if queueDB.get(user_id, None) is None:
            queueDB.update({user_id: {"videos": [], "subtitles": [], "audios": []}})
        if (
            len(queueDB.get(user_id)["videos"]) >= 0
            and len(queueDB.get(user_id)["videos"]) < 10
        ):
            queueDB.get(user_id)["videos"].append(m.id)
            queueDB.get(m.from_user.id)["subtitles"].append(None)

            # LOGGER.info(
            #     queueDB.get(user_id)["videos"], queueDB.get(m.from_user.id)["subtitles"]
            # )

            if len(queueDB.get(user_id)["videos"]) == 1:
                reply_ = await editable.edit(
                    "**Send me some more videos to merge them into single file**",
                    reply_markup=InlineKeyboardMarkup(
                        bMaker.makebuttons(["Cancel"], ["cancel"])
                    ),
                )
                replyDB.update({user_id: reply_.id})
                return
            if queueDB.get(user_id, None)["videos"] is None:
                formatDB.update({user_id: currentFileNameExt})
            if replyDB.get(user_id, None) is not None:
                await c.delete_messages(
                    chat_id=m.chat.id, message_ids=replyDB.get(user_id)
                )
            if len(queueDB.get(user_id)["videos"]) == 10:
                MessageText = "Okay, Now Just Press **Merge Now** Button Plox!"
            markup = await makeButtons(c, m, queueDB)
            reply_ = await editable.edit(
                text=MessageText, reply_markup=InlineKeyboardMarkup(markup)
            )
            replyDB.update({user_id: reply_.id})
        elif len(queueDB.get(user_id)["videos"]) > 10:
            markup = await makeButtons(c, m, queueDB)
            await editable.text(
                "Max 10 videos allowed", reply_markup=InlineKeyboardMarkup(markup)
            )

    elif user.merge_mode == 2:
        editable = await m.reply_text("Please Wait ...", quote=True)
        MessageText = (
            "Okay,\nNow Send Me Some More <u>Audios</u> or Press **Merge Now** Button!"
        )

        if queueDB.get(user_id, None) is None:
            queueDB.update({user_id: {"videos": [], "subtitles": [], "audios": []}})
        if len(queueDB.get(user_id)["videos"]) == 0:
            queueDB.get(user_id)["videos"].append(m.id)
            # if len(queueDB.get(user_id)["videos"])==1:
            reply_ = await editable.edit(
                text="Now, Send all the audios you want to merge",
                reply_markup=InlineKeyboardMarkup(
                    bMaker.makebuttons(["Cancel"], ["cancel"])
                ),
            )
            replyDB.update({user_id: reply_.id})
            return
        elif (
            len(queueDB.get(user_id)["videos"]) >= 1
            and currentFileNameExt in AUDIO_EXTENSIONS
        ):
            queueDB.get(user_id)["audios"].append(m.id)
            if replyDB.get(user_id, None) is not None:
                await c.delete_messages(
                    chat_id=m.chat.id, message_ids=replyDB.get(user_id)
                )
            markup = await makeButtons(c, m, queueDB)

            reply_ = await editable.edit(
                text=MessageText, reply_markup=InlineKeyboardMarkup(markup)
            )
            replyDB.update({user_id: reply_.id})
        else:
            await m.reply("This Filetype is not valid")
            return

    elif user.merge_mode == 3:

        editable = await m.reply_text("Please Wait ...", quote=True)
        MessageText = "Okay,\nNow Send Me Some More <u>Subtitles</u> or Press **Merge Now** Button!"
        if queueDB.get(user_id, None) is None:
            queueDB.update({user_id: {"videos": [], "subtitles": [], "audios": []}})
        if len(queueDB.get(user_id)["videos"]) == 0:
            queueDB.get(user_id)["videos"].append(m.id)
            # if len(queueDB.get(user_id)["videos"])==1:
            reply_ = await editable.edit(
                text="Now, Send all the subtitles you want to merge",
                reply_markup=InlineKeyboardMarkup(
                    bMaker.makebuttons(["Cancel"], ["cancel"])
                ),
            )
            replyDB.update({user_id: reply_.id})
            return
        elif (
            len(queueDB.get(user_id)["videos"]) >= 1
            and currentFileNameExt in SUBTITLE_EXTENSIONS
        ):
            queueDB.get(user_id)["subtitles"].append(m.id)
            if replyDB.get(user_id, None) is not None:
                await c.delete_messages(
                    chat_id=m.chat.id, message_ids=replyDB.get(user_id)
                )
            markup = await makeButtons(c, m, queueDB)

            reply_ = await editable.edit(
                text=MessageText, reply_markup=InlineKeyboardMarkup(markup)
            )
            replyDB.update({user_id: reply_.id})
        else:
            await m.reply("This Filetype is not valid")
            return


@mergeApp.on_message(filters.photo & filters.private)
async def photo_handler(c: Client, m: Message):
    user = UserSettings(m.chat.id, m.from_user.first_name)
    if m.from_user.id != int(Config.OWNER):
        if user.allowed is False:
            res = await m.reply_text(
                text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Unfortunately you can't use me\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
                quote=True,
            )
            del user
            return
    thumbnail = m.photo.file_id
    msg = await m.reply_text("Saving Thumbnail. . . .", quote=True)
    user.thumbnail = thumbnail
    user.set()
    # await database.saveThumb(m.from_user.id, thumbnail)
    LOCATION = f"downloads/{m.from_user.id}_thumb.jpg"
    await c.download_media(message=m, file_name=LOCATION)
    await msg.edit_text(text="✅ Custom Thumbnail Saved!")
    del user


@mergeApp.on_message(filters.command(["extract"]) & filters.private)
async def media_extracter(c: Client, m: Message):
    user = UserSettings(uid=m.from_user.id, name=m.from_user.first_name)
    if not user.allowed:
        return
    if user.merge_mode == 4:
        if m.reply_to_message is None:
            await m.reply(text="Reply /extract to a video or document file")
            return
        rmess = m.reply_to_message
        if rmess.video or rmess.document:
            media = rmess.video or rmess.document
            mid=rmess.id
            file_name = media.file_name
            if file_name is None:
                await m.reply("File name not found; goto @yashoswalyo")
                return
            markup = bMaker.makebuttons(
                set1=["Audio", "Subtitle", "Cancel"],
                set2=[f"extract_audio_{mid}", f"extract_subtitle_{mid}", 'cancel'],
                isCallback=True,
                rows=2,
            )
            await m.reply(
                text="Choose from below what you want to extract?",
                quote=True,
                reply_markup=InlineKeyboardMarkup(markup),
            )
    else:
        await m.reply(
            text="Change settings and set mode to extract\nthen use /extract command"
        )


@mergeApp.on_message(filters.command(["help"]) & filters.private)
async def help_msg(c: Client, m: Message):
    await m.reply_text(
        text="""**Follow These Steps:

1) Send me the custom thumbnail (optional).
2) Send two or more Your Videos Which you want to merge
3) After sending all files select merge options
4) Select the upload mode.
5) Select rename if you want to give custom file name else press default**""",
        quote=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Close 🔐", callback_data="close")]]
        ),
    )


@mergeApp.on_message(filters.command(["about"]) & filters.private)
async def about_handler(c: Client, m: Message):
    await m.reply_text(
        text="""
**𝐖𝐇𝐀𝐓'𝐒 𝐍𝐄𝐖:**
+ (𝐈𝐧𝐜𝐨𝐦𝐩𝐥𝐞𝐭𝐞)
👨‍💻 𝐔𝐩𝐥𝐨𝐚𝐝 𝐭𝐨 𝐝𝐫𝐢𝐯𝐞 𝐮𝐬𝐢𝐧𝐠 𝐲𝐨𝐮𝐫 𝐨𝐰𝐧 𝐫𝐜𝐥𝐨𝐧𝐞 𝐜𝐨𝐧𝐟𝐢𝐠
👨‍💻 𝐌𝐞𝐫𝐠𝐞𝐝 𝐯𝐢𝐝𝐞𝐨 𝐩𝐫𝐞𝐬𝐞𝐫𝐯𝐞𝐬 𝐚𝐥𝐥 𝐬𝐭𝐫𝐞𝐚𝐦𝐬 𝐨𝐟 𝐭𝐡𝐞 𝐟𝐢𝐫𝐬𝐭 𝐯𝐢𝐝𝐞𝐨 𝐲𝐨𝐮 𝐬𝐞𝐧𝐝 (𝐢.𝐞. 𝐚𝐥𝐥 𝐚𝐮𝐝𝐢𝐨𝐭𝐫𝐚𝐜𝐤𝐬/𝐬𝐮𝐛𝐭𝐢𝐭𝐥𝐞𝐬)
➖➖➖➖➖➖➖➖➖➖➖➖
**𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞𝐝**
⚡ 𝐄𝐱𝐭𝐫𝐚𝐱𝐜𝐭 𝐚𝐥𝐥 𝐚𝐮𝐝𝐢𝐨 + 𝐬𝐮𝐛𝐭𝐢𝐭𝐥𝐞𝐬 𝐤𝐞𝐞𝐩𝐢𝐧𝐠 𝐚𝐥𝐥 𝐦𝐞𝐭𝐚𝐝𝐚𝐭𝐚
⚡ 𝐍𝐨𝐰 𝐨𝐰𝐧𝐞𝐫 𝐜𝐚𝐧 𝐛𝐚𝐧 𝐮𝐬𝐞𝐫𝐬 𝐚𝐧𝐝 𝐮𝐧𝐛𝐚𝐧 𝐮𝐬𝐞𝐫𝐬 𝐰𝐡𝐨 𝐚𝐫𝐞 𝐮𝐬𝐢𝐧𝐠 𝐛𝐨𝐭
➖➖➖➖➖➖➖➖➖➖➖➖
**𝐅𝐄𝐀𝐓𝐔𝐑𝐄𝐒:**
🔰 𝐌𝐞𝐫𝐠𝐞 𝐔𝐩𝐭𝐨 𝟏𝟎 𝐯𝐢𝐝𝐞𝐨𝐬 𝐢𝐧 𝐨𝐧𝐞
🔰 𝐔𝐩𝐥𝐨𝐚𝐝 𝐚𝐬 𝐝𝐨𝐜𝐮𝐦𝐞𝐧𝐭/𝐯𝐢𝐝𝐞𝐨
🔰 𝐂𝐮𝐬𝐭𝐨𝐦 𝐭𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 𝐬𝐮𝐩𝐩𝐨𝐫𝐭
🔰 𝐔𝐬𝐞𝐫𝐬 𝐜𝐚𝐧 𝐥𝐨𝐠𝐢𝐧 𝐭𝐨 𝐛𝐨𝐭 𝐮𝐬𝐢𝐧𝐠 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝
🔰 𝐎𝐰𝐧𝐞𝐫 𝐜𝐚𝐧 𝐛𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐭𝐨 𝐚𝐥𝐥 𝐮𝐬𝐞𝐫𝐬
		""",
        quote=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Developer", url="https://t.me/yashoswalyo")],
                [
                    InlineKeyboardButton(
                        "Source Code", url="https://github.com/yashoswalyo/MERGE-BOT"
                    ),
                    InlineKeyboardButton(
                        "Deployed By", url=f"https://t.me/{Config.OWNER_USERNAME}"
                    ),
                ],
                [InlineKeyboardButton("Close 🔐", callback_data="close")],
            ]
        ),
    )


@mergeApp.on_message(
    filters.command(["savethumb", "setthumb", "savethumbnail"]) & filters.private
)
async def save_thumbnail(c: Client, m: Message):
    if m.reply_to_message:
        if m.reply_to_message.photo:
            await photo_handler(c, m.reply_to_message)
        else:
            await m.reply(text="Please reply to a valid photo")
    else:
        await m.reply(text="Please reply to a message")
    return


@mergeApp.on_message(filters.command(["showthumbnail"]) & filters.private)
async def show_thumbnail(c: Client, m: Message):
    try:
        user = UserSettings(m.from_user.id, m.from_user.first_name)
        thumb_id = user.thumbnail
        LOCATION = f"downloads/{m.from_user.id}_thumb.jpg"
        await c.download_media(message=str(thumb_id), file_name=LOCATION)
        if os.path.exists(LOCATION) is False:
            await m.reply_text(text="❌ Custom thumbnail not found", quote=True)
        else:
            await m.reply_photo(
                photo=LOCATION, caption="🖼️ Your custom thumbnail", quote=True
            )
        del user
    except Exception as err:
        LOGGER.info(err)
        await m.reply_text(text="❌ Custom thumbnail not found", quote=True)


@mergeApp.on_message(filters.command(["deletethumbnail"]) & filters.private)
async def delete_thumbnail(c: Client, m: Message):
    try:
        user = UserSettings(m.from_user.id, m.from_user.first_name)
        user.thumbnail = None
        user.set()
        if os.path.exists(f"downloads/{str(m.from_user.id)}"):
            os.remove(f"downloads/{str(m.from_user.id)}")
        await m.reply_text("✅ Deleted Sucessfully", quote=True)
        del user
    except Exception as err:
        await m.reply_text(text="❌ Custom thumbnail not found", quote=True)

@mergeApp.on_message(filters.command(["ban","unban"]) & filters.private)
async def ban_user(c:Client,m:Message):
    incoming=m.text.split(' ')[0]
    if incoming == '/ban':
        if m.from_user.id == int(Config.OWNER):
            try:
                abuser_id = int(m.text.split(" ")[1])
                if abuser_id == int(Config.OWNER):
                    await m.reply_text("I can't ban you master,\nPlease don't abandon me. ",quote=True)
                else:
                    try:
                        user_obj: User = await c.get_users(abuser_id)
                        udata  = UserSettings(uid=abuser_id,name=user_obj.first_name)
                        udata.banned=True
                        udata.allowed=False
                        udata.set()
                        await m.reply_text(f"Pooof, {user_obj.first_name} has been **BANNED**",quote=True)
                    except Exception as e:
                        LOGGER.error(e)
            except:
                await m.reply_text("**Command:**\n  `/ban <user_id>`\n\n**Usage:**\n  `user_id`: User ID of the user",quote=True,parse_mode=enums.parse_mode.ParseMode.MARKDOWN)
        else:
            await m.reply_text("**(Only for __OWNER__)\nCommand:**\n  `/ban <user_id>`\n\n**Usage:**\n  `user_id`: User ID of the user",quote=True,parse_mode=enums.parse_mode.ParseMode.MARKDOWN)
        return
    elif incoming == '/unban':
        if m.from_user.id == int(Config.OWNER):
            try:
                abuser_id = int(m.text.split(" ")[1])
                if abuser_id == int(Config.OWNER):
                    await m.reply_text("I can't ban you master,\nPlease don't abandon me. ",quote=True)
                else:
                    try:
                        user_obj: User = await c.get_users(abuser_id)
                        udata  = UserSettings(uid=abuser_id,name=user_obj.first_name)
                        udata.banned=False
                        udata.allowed=False
                        udata.set()
                        await m.reply_text(f"Pooof, {user_obj.first_name} has been **UN_BANNED**",quote=True)
                    except Exception as e:
                        LOGGER.error(e)
            except:
                await m.reply_text("**Command:**\n  `/unban <user_id>`\n\n**Usage:**\n  `user_id`: User ID of the user",quote=True,parse_mode=enums.parse_mode.ParseMode.MARKDOWN)
        else:
            await m.reply_text("**(Only for __OWNER__)\nCommand:**\n  `/unban <user_id>`\n\n**Usage:**\n  `user_id`: User ID of the user",quote=True,parse_mode=enums.parse_mode.ParseMode.MARKDOWN)
        return
async def showQueue(c: Client, cb: CallbackQuery):
    try:
        markup = await makeButtons(c, cb.message, queueDB)
        await cb.message.edit(
            text="Okay,\nNow Send Me Next Video or Press **Merge Now** Button!",
            reply_markup=InlineKeyboardMarkup(markup),
        )
    except ValueError:
        await cb.message.edit("Send Some more videos")
    return


async def delete_all(root):
    try:
        shutil.rmtree(root)
    except Exception as e:
        LOGGER.info(e)


async def makeButtons(bot: Client, m: Message, db: dict):
    markup = []
    user = UserSettings(m.chat.id, m.chat.first_name)
    if user.merge_mode == 1:
        for i in await bot.get_messages(
            chat_id=m.chat.id, message_ids=db.get(m.chat.id)["videos"]
        ):
            media = i.video or i.document or None
            if media is None:
                continue
            else:
                markup.append(
                    [
                        InlineKeyboardButton(
                            f"{media.file_name}",
                            callback_data=f"showFileName_{i.id}",
                        )
                    ]
                )

    elif user.merge_mode == 2:
        msgs: list[Message] = await bot.get_messages(
            chat_id=m.chat.id, message_ids=db.get(m.chat.id)["audios"]
        )
        msgs.insert(
            0,
            await bot.get_messages(
                chat_id=m.chat.id, message_ids=db.get(m.chat.id)["videos"][0]
            ),
        )
        for i in msgs:
            media = i.audio or i.document or i.video or None
            if media is None:
                continue
            else:
                markup.append(
                    [
                        InlineKeyboardButton(
                            f"{media.file_name}",
                            callback_data=f"tryotherbutton",
                        )
                    ]
                )

    elif user.merge_mode == 3:
        msgs: list[Message] = await bot.get_messages(
            chat_id=m.chat.id, message_ids=db.get(m.chat.id)["subtitles"]
        )
        msgs.insert(
            0,
            await bot.get_messages(
                chat_id=m.chat.id, message_ids=db.get(m.chat.id)["videos"][0]
            ),
        )
        for i in msgs:
            media = i.video or i.document or None

            if media is None:
                continue
            else:
                markup.append(
                    [
                        InlineKeyboardButton(
                            f"{media.file_name}",
                            callback_data=f"tryotherbutton",
                        )
                    ]
                )

    markup.append([InlineKeyboardButton("🔗 Merge Now", callback_data="merge")])
    markup.append([InlineKeyboardButton("💥 Clear Files", callback_data="cancel")])
    return markup


LOGCHANNEL = Config.LOGCHANNEL
try:
    if Config.USER_SESSION_STRING is None:
        raise KeyError
    LOGGER.info("Starting USER Session")
    userBot = Client(
        name="merge-bot-user",
        session_string=Config.USER_SESSION_STRING,
        no_updates=True,
    )

except KeyError:
    userBot = None
    LOGGER.warning("No User Session, Default Bot session will be used")


if __name__ == "__main__":
    # with mergeApp:
    #     bot:User = mergeApp.get_me()
    #     bot_username = bot.username
    try:
        with userBot:
            userBot.send_message(
                chat_id=int(LOGCHANNEL),
                text="Bot booted with Premium Account,\n\n  Thanks for using <a href='https://github.com/yashoswalyo/merge-bot'>this repo</a>",
                disable_web_page_preview=True,
            )
            user = userBot.get_me()
            Config.IS_PREMIUM = user.is_premium
    except Exception as err:
        LOGGER.error(f"{err}")
        Config.IS_PREMIUM = False
        pass

    mergeApp.run()
