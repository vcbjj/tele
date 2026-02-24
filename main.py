import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.tl.types import Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("scanner")

api_id = 27295431
api_hash = "5124b552db3516a5ee65e4c232a12cc1"
phone_number = "+966574947105"
session_file = "hos_alt2"
target_chat = -1003888846034

pattern_list = [
    r'(ابي|أبي|ابغى|أبغى|احتاج|أحتاج|محتاج|محتاجه|محتاجة|تعرفون|تعرفوا|تعرفو|يعرف|يعرفو|من|مين|منو|اللي|الى|عنده|عندكم|أبي|ابى|أبى|ابي|ابا|أبا|أبغي|ابغي|أبغا|ابغا|بغيت|حدا|أحد|احد|واحد|واحده|وحده|حد|طلب|أحتاجه|ساعدني|محتاجين|تبغى|ممكن|مجانا|مجاني|اطلب|ابعث|أرسلي|أرسللي|ممكن تساعد|أريد|نحتاج|أرجو|مطلوب).*?(يسوي|تسوي|يسوى|يسوون|يحل|تحل|يحلون|يشرح|تشرح|يشرحها|يكتب|يصمم|مدرس|معلم|سكليف|سكاليف|عذر|تقرير|تقارير|يساعد|خصوصي|خصوصية|خصوصيين|خصوصيه|تحل|تسوي|يلخص|ملخص|ارقام|رقم|وهميه|شرح|واجب|واجبات|مشروع|مشروع|تصميم|تصميمات|كود|كود برمجي|حساب|حسابات|تعليمات|تلخيص|حل|ملخصات|برامج|تعديل|يسويلي|صحتي)'
]

block_list = [
    r'خدمات', r'نقدم', r'05', r'نسوي', r'يعلن', r'اعلان', r'ممنوع',
    r'بوت', r'فريق', r'يوتيوب', r'تنزيل', r'روابط', r'فيسبوك',
    r'إعلان', r'إعلان تجاري', r'عروض', r'هكر', r'قرصنة'
]

max_words = 20


class Detector:
    def __init__(self):
        self.app = TelegramClient(session_file, api_id, api_hash)
        self.block_re = re.compile('|'.join(block_list), re.I)
        self.match_re = re.compile('|'.join(pattern_list), re.I)
        self.done = set()
        self.users = {}

    async def begin(self):
        await self.app.start(phone=phone_number)
        log.info("connected")

        @self.app.on(events.NewMessage)
        async def catch(e):
            await self.check(e.message)

        await self.app.run_until_disconnected()

    async def check(self, m: Message):
        if not m or m.chat_id == target_chat:
            return
        if m.id in self.done:
            return
        self.done.add(m.id)
        if len(self.done) > 5000:
            self.done = set(list(self.done)[2500:])

        txt = ""
        if m.text:
            txt += m.text
        if m.media and getattr(m.media, "caption", None):
            txt += " " + m.media.caption

        txt = txt.strip()
        if not txt or len(txt.split()) > max_words:
            return

        if self.block_re.search(txt):
            return
        if not self.match_re.search(txt):
            return

        try:
            info = await self.get_user(m)
            grp = await self.get_chat(m.chat_id)
            link = await self.make_link(m)
            await self.send(txt, info, grp, link)
        except Exception as ex:
            log.error(f"error: {ex}")

    async def get_user(self, m: Message):
        uid = m.sender_id
        if uid in self.users:
            return self.users[uid]
        try:
            s = await m.get_sender()
            uname = getattr(s, "username", None)
            fn = getattr(s, "first_name", "") or ""
            ln = getattr(s, "last_name", "") or ""
            nm = (fn + " " + ln).strip() or f"user{uid}"
            link = f"https://t.me/{uname}" if uname else f"tg://user?id={uid}"
            data = {"id": uid, "name": nm, "link": link}
            self.users[uid] = data
            return data
        except:
            data = {"id": uid, "name": f"user{uid}", "link": f"tg://user?id={uid}"}
            self.users[uid] = data
            return data

    async def get_chat(self, cid):
        try:
            c = await self.app.get_entity(cid)
            t = getattr(c, "title", f"chat{cid}")
            u = getattr(c, "username", None)
            l = f"https://t.me/{u}" if u else f"tg://resolve?domain={abs(cid)}"
            return {"title": t, "link": l}
        except:
            return {"title": f"chat{cid}", "link": f"tg://resolve?domain={abs(cid)}"}

    async def make_link(self, m: Message):
        try:
            c = await self.app.get_entity(m.chat_id)
            if getattr(c, "username", None):
                return f"https://t.me/{c.username}/{m.id}"
            return f"https://t.me/c/{abs(c.id)}/{m.id}"
        except:
            return f"https://t.me/c/{abs(m.chat_id)}/{m.id}"

    async def send(self, text, user, chat, link):
        try:
            if len(text) > 400:
                text = text[:400] + "..."
            msg = f"{text}\n\n👤 [{user['name']}]({user['link']})\n🏷️ [{chat['title']}]({chat['link']})\n🔗 [message]({link})\n`{user['id']}`"
            await self.app.send_message(target_chat, msg, link_preview=False)
            log.info(f"sent from {user['name']}")
        except Exception as err:
            log.error(err)


async def main():
    d = Detector()
    await d.begin()


if __name__ == "__main__":
    asyncio.run(main())
