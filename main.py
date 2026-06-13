#!/usr/bin/env python3
"""
API + Telegram Bot متكامل يعتمد على دوال البوت الثالث (KESHVEXFF) لتجنب الحظر.
الاستخدام:
  GET /3?uid=12345678&api_key=...
  GET /5?uid=12345678&api_key=...
  GET /6?uid=12345678&api_key=...
  GET /inv?team_code=ABC123&uid=12345678&api_key=...
  GET /dance?emote_id=909000001&team_code=ABC123&uids=111,222&api_key=...
"""

import asyncio
import ssl
import logging
import os
import sys
import json
import time
import random
import re
from datetime import datetime
from typing import Optional

import aiohttp
import urllib3
from fastapi import FastAPI, Query, HTTPException
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# استيراد الدوال الأساسية من البوت الثالث (KESHVEXFF-DATA)
# تأكد من وجود هذا الملف في نفس المجلد
from KESHVEXFF import (
    OpEnSq, cHSq, SEnd_InV, ExiT, GenJoinSquadsPacket, Emote_k,
    Ua, EnC_PacKeT, DecodE_HeX, GeneRaTePk, CrEaTe_ProTo, FS,
    GeNeRaTeAccEss, EncRypTMajoRLoGin, MajorLogin, DecRypTMajoRLoGin,
    GetLoginData, DecRypTLoGinDaTa, xAuThSTarTuP, DeCode_PackEt
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================== إعدادات عامة ==================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "zakaria_li7wak",
    "auto_restart_hours": 4,
    "api_enabled": True,
    "backup_accounts": {}
}

BOT_TOKEN = "8299557522:AAHNa8PxOiN7WRvBOr_zhnx2MeNBPWtEqXE"  # ضع توكن البوت الخاص بك
ADMIN_ID = 6848455321  # معرف المسؤول في تلغرام

# تحميل الإعدادات
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

config = load_config()
API_KEY = config["api_key"]
AUTO_RESTART_HOURS = config["auto_restart_hours"]
API_ENABLED = config["api_enabled"]
BACKUP_ACCOUNTS = config["backup_accounts"]

# متغيرات الاتصال (ستُملأ بعد تسجيل الدخول)
online_writer = None
whisper_writer = None
key = None
iv = None
region = None
bot_uid = None
FF_UID = None
FF_PASSWORD = None

app = FastAPI(title="FPI Squad & Dance API (Anti-Ban)")
logging.basicConfig(level=logging.INFO)

# ================== دوال تحميل الاعتماديات من الملف ==================
def load_credentials_from_file(filename="keshvexff.txt"):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        uid_match = re.search(r'uid[=:]\s*(\d+)', content, re.I)
        pwd_match = re.search(r'password[=:]\s*(\S+)', content, re.I)
        if uid_match and pwd_match:
            return uid_match.group(1), pwd_match.group(1)
        else:
            logging.error("لم يتم العثور على uid أو password في الملف")
            return None, None
    except FileNotFoundError:
        logging.error(f"الملف {filename} غير موجود")
        return None, None

def save_token_to_file(token, region, bot_uid_val):
    data = {
        "token": token,
        "saved_at": time.time(),
        "bot_uid": str(bot_uid_val),
        "region": region
    }
    with open("token.json", "w") as f:
        json.dump(data, f)
    logging.info("تم حفظ التوكن في token.json")

def load_cached_token():
    if os.path.exists("token.json"):
        try:
            with open("token.json", "r") as f:
                data = json.load(f)
            if time.time() - data.get("saved_at", 0) < 3 * 3600:  # صالح لمدة 3 ساعات
                return data["token"], data["region"], data["bot_uid"]
        except Exception as e:
            logging.warning(f"خطأ في قراءة التوكن المخزن: {e}")
    return None, None, None

# ================== دوال الاتصال الأساسية (من البوت الثالث) ==================
# ملاحظة: الدوال GeNeRaTeAccEss, EncRypTMajoRLoGin, MajorLogin, ... تم استيرادها من KESHVEXFF
# لذلك لا داعي لإعادة تعريفها هنا.

async def SEndPacKeT(typE, packet):
    global online_writer, whisper_writer
    if typE == 'OnLine' and online_writer:
        online_writer.write(packet)
        await online_writer.drain()
    elif typE == 'ChaT' and whisper_writer:
        whisper_writer.write(packet)
        await whisper_writer.drain()

# ================== تسجيل الدخول للعبة (مقاوم للحظر) ==================
async def login_to_freefire():
    global key, iv, region, online_writer, whisper_writer, bot_uid, FF_UID, FF_PASSWORD
    try:
        # تحميل الاعتماديات من الملف
        uid, pwd = load_credentials_from_file()
        if not uid or not pwd:
            logging.error("فشل تحميل الاعتماديات")
            return False
        FF_UID = uid
        FF_PASSWORD = pwd
        logging.info(f"جاري تسجيل الدخول باستخدام UID: {FF_UID}")

        open_id, access_token = await GeNeRaTeAccEss(FF_UID, FF_PASSWORD)
        if not open_id:
            logging.error("فشل الحصول على open_id / access_token")
            return False

        payload = await EncRypTMajoRLoGin(open_id, access_token)
        response = await MajorLogin(payload)
        if not response:
            logging.error("فشل MajorLogin")
            return False

        login_res = await DecRypTMajoRLoGin(response)
        url = login_res.url
        region = login_res.region
        token = login_res.token
        bot_uid = login_res.account_uid
        key = login_res.key
        iv = login_res.iv
        timestamp = login_res.timestamp

        # حفظ التوكن في ملف للاستخدام لاحقاً
        save_token_to_file(token, region, bot_uid)

        login_data = await GetLoginData(url, payload, token)
        if not login_data:
            logging.error("فشل GetLoginData")
            return False

        login_dec = await DecRypTLoGinDaTa(login_data)
        online_ip, online_port = login_dec.Online_IP_Port.split(":")
        chat_ip, chat_port = login_dec.AccountIP_Port.split(":")
        auth_token = await xAuThSTarTuP(int(bot_uid), token, int(timestamp), key, iv)

        async def run_online():
            global online_writer
            while True:
                try:
                    reader, writer = await asyncio.open_connection(online_ip, int(online_port))
                    online_writer = writer
                    writer.write(bytes.fromhex(auth_token))
                    await writer.drain()
                    while True:
                        data = await reader.read(4096)
                        if not data:
                            break
                        # يمكن معالجة الحزم الواردة هنا إذا لزم الأمر
                except Exception as e:
                    logging.error(f"Online connection error: {e}")
                    await asyncio.sleep(5)

        async def run_chat():
            global whisper_writer
            while True:
                try:
                    reader, writer = await asyncio.open_connection(chat_ip, int(chat_port))
                    whisper_writer = writer
                    writer.write(bytes.fromhex(auth_token))
                    await writer.drain()
                    while True:
                        data = await reader.read(4096)
                        if not data:
                            break
                except Exception as e:
                    logging.error(f"Chat connection error: {e}")
                    await asyncio.sleep(5)

        asyncio.create_task(run_online())
        asyncio.create_task(run_chat())
        await asyncio.sleep(2)  # انتظار تأكيد الاتصال
        logging.info("تم تسجيل الدخول وربط الاتصالات بنجاح")
        return True

    except Exception as e:
        logging.error(f"فشل تسجيل الدخول: {e}")
        return False

# ================== دوال الأوامر الأساسية ==================
async def cmd_3(uid: int):
    try:
        await asyncio.sleep(random.uniform(0.2, 0.8))
        PAc = await OpEnSq(key, iv, region)
        await SEndPacKeT('OnLine', PAc)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        C = await cHSq(3, uid, key, iv, region)
        await SEndPacKeT('OnLine', C)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        V = await SEnd_InV(3, uid, key, iv, region)
        await SEndPacKeT('OnLine', V)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        E = await ExiT(None, key, iv)
        await SEndPacKeT('OnLine', E)
        return True
    except Exception as e:
        logging.error(f"cmd_3 error: {e}")
        return False

async def cmd_5(uid: int):
    try:
        await asyncio.sleep(random.uniform(0.2, 0.8))
        PAc = await OpEnSq(key, iv, region)
        await SEndPacKeT('OnLine', PAc)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        C = await cHSq(5, uid, key, iv, region)
        await SEndPacKeT('OnLine', C)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        V = await SEnd_InV(5, uid, key, iv, region)
        await SEndPacKeT('OnLine', V)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        E = await ExiT(None, key, iv)
        await SEndPacKeT('OnLine', E)
        return True
    except Exception as e:
        logging.error(f"cmd_5 error: {e}")
        return False

async def cmd_6(uid: int):
    try:
        await asyncio.sleep(random.uniform(0.2, 0.8))
        PAc = await OpEnSq(key, iv, region)
        await SEndPacKeT('OnLine', PAc)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        C = await cHSq(6, uid, key, iv, region)
        await SEndPacKeT('OnLine', C)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        V = await SEnd_InV(6, uid, key, iv, region)
        await SEndPacKeT('OnLine', V)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        E = await ExiT(None, key, iv)
        await SEndPacKeT('OnLine', E)
        return True
    except Exception as e:
        logging.error(f"cmd_6 error: {e}")
        return False

async def cmd_inv(team_code: str, target_uid: int):
    try:
        join_packet = await GenJoinSquadsPacket(team_code, key, iv)
        await SEndPacKeT('OnLine', join_packet)
        await asyncio.sleep(random.uniform(1, 2))
        invite_packet = await SEnd_InV(5, target_uid, key, iv, region)
        await SEndPacKeT('OnLine', invite_packet)
        await asyncio.sleep(random.uniform(2, 3))
        exit_packet = await ExiT(None, key, iv)
        await SEndPacKeT('OnLine', exit_packet)
        return True
    except Exception as e:
        logging.error(f"cmd_inv error: {e}")
        return False

async def cmd_dance(emote_id: int, team_code: str, uids: list):
    try:
        join_packet = await GenJoinSquadsPacket(team_code, key, iv)
        await SEndPacKeT('OnLine', join_packet)
        await asyncio.sleep(random.uniform(1, 2))
        for uid in uids:
            emote_packet = await Emote_k(int(uid), emote_id, key, iv, region)
            await SEndPacKeT('OnLine', emote_packet)
            await asyncio.sleep(random.uniform(0.2, 0.5))
        await asyncio.sleep(random.uniform(1, 2))
        exit_packet = await ExiT(None, key, iv)
        await SEndPacKeT('OnLine', exit_packet)
        return True
    except Exception as e:
        logging.error(f"cmd_dance error: {e}")
        return False

# ================== حلقات الخلفية للحماية من الحظر ==================
async def keep_alive_loop():
    global key, iv, region, online_writer
    while True:
        await asyncio.sleep(60)  # كل 60 ثانية
        if online_writer and key and iv and region:
            try:
                packet = await FS(key, iv, region)
                if packet:
                    await SEndPacKeT('OnLine', packet)
                    logging.info("📡 Keep-alive packet sent")
            except Exception as e:
                logging.warning(f"Keep-alive failed: {e}")

async def token_refresh_loop():
    global FF_UID, FF_PASSWORD, key, iv, region, online_writer, whisper_writer
    while True:
        await asyncio.sleep(4 * 3600)  # كل 4 ساعات
        logging.info("🔄 Refreshing token...")
        try:
            open_id, access_token = await GeNeRaTeAccEss(FF_UID, FF_PASSWORD)
            if not open_id:
                continue
            payload = await EncRypTMajoRLoGin(open_id, access_token)
            response = await MajorLogin(payload)
            if not response:
                continue
            login_res = await DecRypTMajoRLoGin(response)
            key = login_res.key
            iv = login_res.iv
            region = login_res.region
            token = login_res.token
            save_token_to_file(token, region, login_res.account_uid)
            logging.info("Token refreshed successfully")
        except Exception as e:
            logging.error(f"Token refresh error: {e}")

async def auto_restart_loop():
    while True:
        await asyncio.sleep(AUTO_RESTART_HOURS * 3600)
        logging.info(f"Auto-restart after {AUTO_RESTART_HOURS} hours...")
        os._exit(1)

# ================== بوت تلغرام ==================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def is_admin(message: Message):
    return message.from_user.id == ADMIN_ID

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message):
        return
    await message.answer("🎮 أهلاً بك في لوحة تحكم FPI API Anti-Ban!\nاستخدم /help لرؤية الأوامر.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        "📋 الأوامر المتاحة:\n"
        "/status - حالة الاتصال الحالية\n"
        "/settings - عرض الإعدادات\n"
        "/set_account [UID] [PASSWORD] - تغيير حساب اللعبة الرئيسي\n"
        "/set_restart [ساعات] - تغيير مدة إعادة التشغيل\n"
        "/restart - إعادة تشغيل الخادم\n"
        "/enable_api - تفعيل API\n"
        "/disable_api - تعطيل API\n"
        "/add_backup [UID] [PASSWORD] - إضافة حساب احتياطي\n"
        "/backups - عرض الحسابات الاحتياطية\n"
        "/logs - آخر 10 أسطر من السجل (محاكاة)\n"
        "/api_key - عرض مفتاح API الحالي"
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message):
        return
    status = "✅ متصل" if online_writer else "❌ غير متصل"
    await message.answer(
        f"📊 الحالة:\n"
        f"الاتصال باللعبة: {status}\n"
        f"المنطقة: {region or 'N/A'}\n"
        f"API: {'مفعل' if API_ENABLED else 'معطل'}\n"
        f"إعادة التشغيل كل: {AUTO_RESTART_HOURS} ساعة\n"
        f"عدد الحسابات الاحتياطية: {len(BACKUP_ACCOUNTS)}"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    await cmd_status(message)

@dp.message(Command("set_account"))
async def cmd_set_account(message: Message):
    global FF_UID, FF_PASSWORD
    if not is_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("❌ استخدم: /set_account [UID] [PASSWORD]")
    uid, pwd = parts[1], parts[2]
    # حفظ في ملف keshvexff.txt
    with open("keshvexff.txt", "w") as f:
        f.write(f"uid={uid}\npassword={pwd}")
    FF_UID = uid
    FF_PASSWORD = pwd
    await message.answer(f"✅ تم تغيير الحساب الرئيسي إلى {uid}.\nسيتم إعادة الاتصال بعد إعادة التشغيل.")

@dp.message(Command("set_restart"))
async def cmd_set_restart(message: Message):
    global AUTO_RESTART_HOURS
    if not is_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("❌ استخدم: /set_restart [عدد الساعات]")
    hours = int(parts[1])
    if hours < 1:
        hours = 1
    AUTO_RESTART_HOURS = hours
    config["auto_restart_hours"] = hours
    save_config(config)
    await message.answer(f"✅ تم ضبط إعادة التشغيل كل {hours} ساعة.")

@dp.message(Command("restart"))
async def cmd_restart(message: Message):
    if not is_admin(message):
        return
    await message.answer("🔄 جاري إعادة التشغيل...")
    os._exit(1)

@dp.message(Command("enable_api"))
async def cmd_enable_api(message: Message):
    global API_ENABLED
    if not is_admin(message):
        return
    API_ENABLED = True
    config["api_enabled"] = True
    save_config(config)
    await message.answer("✅ تم تفعيل API.")

@dp.message(Command("disable_api"))
async def cmd_disable_api(message: Message):
    global API_ENABLED
    if not is_admin(message):
        return
    API_ENABLED = False
    config["api_enabled"] = False
    save_config(config)
    await message.answer("⛔ تم تعطيل API.")

@dp.message(Command("add_backup"))
async def cmd_add_backup(message: Message):
    global BACKUP_ACCOUNTS
    if not is_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("❌ استخدم: /add_backup [UID] [PASSWORD]")
    uid, pwd = parts[1], parts[2]
    BACKUP_ACCOUNTS[uid] = pwd
    config["backup_accounts"] = BACKUP_ACCOUNTS
    save_config(config)
    await message.answer(f"✅ أضيف الحساب الاحتياطي {uid}.")

@dp.message(Command("backups"))
async def cmd_backups(message: Message):
    if not is_admin(message):
        return
    if not BACKUP_ACCOUNTS:
        return await message.answer("لا توجد حسابات احتياطية.")
    txt = "📋 الحسابات الاحتياطية:\n"
    for uid, pwd in BACKUP_ACCOUNTS.items():
        txt += f"- {uid}: {pwd}\n"
    await message.answer(txt)

@dp.message(Command("logs"))
async def cmd_logs(message: Message):
    if not is_admin(message):
        return
    await message.answer("📜 لعرض السجلات، استخدم أمر `railway logs` في بيئة Railway.")

@dp.message(Command("api_key"))
async def cmd_api_key(message: Message):
    if not is_admin(message):
        return
    await message.answer(f"🔑 API Key الحالي: {API_KEY}")

async def start_telegram():
    await dp.start_polling(bot)

# ================== نقاط نهاية API ==================
def check_auth(api_key: str):
    if not API_ENABLED:
        raise HTTPException(status_code=503, detail="API معطل حالياً")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="مفتاح API غير صحيح")

@app.on_event("startup")
async def startup():
    logging.info("جاري تسجيل الدخول...")
    if not await login_to_freefire():
        logging.error("فشل الاتصال باللعبة! سيتم إعادة المحاولة لاحقاً.")
    else:
        logging.info("تم الاتصال بنجاح.")
        # تشغيل حلقات الخلفية
        asyncio.create_task(keep_alive_loop())
        asyncio.create_task(token_refresh_loop())
        asyncio.create_task(auto_restart_loop())
    asyncio.create_task(start_telegram())

@app.get("/3")
async def squad_3(uid: int = Query(...), api_key: str = Query("")):
    check_auth(api_key)
    success = await cmd_3(uid)
    return {"status": "success" if success else "failed", "command": "squad_3", "uid": uid}

@app.get("/5")
async def squad_5(uid: int = Query(...), api_key: str = Query("")):
    check_auth(api_key)
    success = await cmd_5(uid)
    return {"status": "success" if success else "failed", "command": "squad_5", "uid": uid}

@app.get("/6")
async def squad_6(uid: int = Query(...), api_key: str = Query("")):
    check_auth(api_key)
    success = await cmd_6(uid)
    return {"status": "success" if success else "failed", "command": "squad_6", "uid": uid}

@app.get("/inv")
async def invite(team_code: str = Query(...), uid: int = Query(...), api_key: str = Query("")):
    check_auth(api_key)
    success = await cmd_inv(team_code, uid)
    return {"status": "success" if success else "failed", "command": "invite", "team_code": team_code, "uid": uid}

@app.get("/dance")
async def dance(
    emote_id: int = Query(...),
    team_code: str = Query(...),
    uids: str = Query(..., description="قائمة UIDs مفصولة بفواصل"),
    api_key: str = Query("")
):
    check_auth(api_key)
    uid_list = [int(u.strip()) for u in uids.split(",") if u.strip().isdigit()]
    if not uid_list:
        raise HTTPException(status_code=400, detail="لم يتم إرسال أي UID صحيح")
    success = await cmd_dance(emote_id, team_code, uid_list)
    return {"status": "success" if success else "failed", "command": "dance", "emote_id": emote_id, "uids": uid_list}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "connected": online_writer is not None,
        "region": region,
        "api_enabled": API_ENABLED
    }

# ================== تشغيل ==================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)