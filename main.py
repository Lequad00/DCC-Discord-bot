# 1. BÖLÜM: Kütüphaneler ve Web Sunucusu Başlangıcı
import discord
from discord.ext import commands
import os
import threading
import datetime
import asyncio
import re
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot aktif!'

def run_web():
    app.run(host='0.0.0.0', port=3000)

threading.Thread(target=run_web, daemon=True).start()

# 2. BÖLÜM: Bot Ayarları ve Yapılandırması
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

VERIFY_ROLE_ID = 1521967908341682316
WELCOME_CHANNEL_ID = 1523295990164230224

# 3. BÖLÜM: Küfür Filtresi ve Uyarı Sistemi Verileri
KUFUR_LISTESI = [
    "amk", "aq", "aw", "awk", "am", "oe", "oç", "amına", "amına koyayım",
    "amcık", "amını", "siktir", "siktir git", "sg", "sik", "sikerim",
    "sikeyim", "siktirgit", "sikiş", "sikişmek", "siken", "orospu",
    "orospuçocuğu", "orospu çocuğu", "oç", "göt", "götlek", "götveren",
    "göte", "gote", "bok", "boktan", "boklu", "piç", "piçlik",
    "yarrak", "yarak", "ibne", "ibnelik", "pezevenk", "pezo",
    "kahpe", "kaltak", "sürtük", "gerizekalı", "geri zekalı",
    "aptal", "salak", "dangalak", "mal", "embesil", "haysiyetsiz",
    "ananı", "ananın", "anana", "ananıs", "anasını", "babanı",
    "pipi", "vajina", "göğüs", "meme", "göt deliği", "yarağı",
    "fahişe", "s1ktir", "s1k", "@mk", "a.m.k",
    "fuck", "fucker", "fucking", "fucked", "fck", "f*ck",
    "shit", "shithead", "bullshit", "sh1t",
    "dick", "dickhead",
    "ass", "asshole", "arse",
    "bitch", "b1tch",
    "bastard",
    "cunt",
    "cock",
    "pussy",
    "sex", "sexy",
    "whore",
    "slut",
    "nigga", "nigger",
    "retard",
    "idiot", "stupid",
    "damn", "damnit",
    "motherfucker", "mf",
    "wtf", "stfu",
]

uyari_sayaci: dict[int, dict[int, int]] = {}

# 4. BÖLÜM: Yardımcı Fonksiyonlar (Süre ve ID Ayrıştırma)
def sure_ayristir(sure_str: str) -> datetime.timedelta | None:
    eslesme = re.fullmatch(r'(\d+)\s*(s|sn|m|dk|h|sa|d|g|w|h|hafta)s?', sure_str.strip().lower())
    if not eslesme: return None
    deger = int(eslesme.group(1))
    birim = eslesme.group(2)
    if birim in ('s', 'sn'): return datetime.timedelta(seconds=deger)
    elif birim in ('m', 'dk'): return datetime.timedelta(minutes=deger)
    elif birim in ('h', 'sa'): return datetime.timedelta(hours=deger)
    elif birim in ('d', 'g'): return datetime.timedelta(days=deger)
    elif birim in ('w', 'hafta'): return datetime.timedelta(weeks=deger)
    return None

def sure_formatla(td: datetime.timedelta) -> str:
    toplam = int(td.total_seconds())
    if toplam < 60: return f"{toplam} saniye"
    elif toplam < 3600: return f"{toplam // 60} dakika"
    elif toplam < 86400: return f"{toplam // 3600} saat"
    else: return f"{toplam // 86400} gün"

def id_ayristir(ham: str) -> list[int]:
    idler = []
    for token in ham.replace(',', ' ').split():
        token = token.strip('<@!> ')
        if token.isdigit(): idler.append(int(token))
    return idler

# 5. BÖLÜM: Otomatik Event İşleyicileri (Küfür Filtresi ve Hoş Geldin Mesajı)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild: return
    icerik = message.content.lower()
    if any(kufur in icerik for kufur in KUFUR_LISTESI):
        try: await message.delete()
        except: pass
        guild_id, user_id = message.guild.id, message.author.id
        if guild_id not in uyari_sayaci: uyari_sayaci[guild_id] = {}
        uyari_sayaci[guild_id][user_id] = uyari_sayaci[guild_id].get(user_id, 0) + 1
        uyari = uyari_sayaci[guild_id][user_id]
        if uyari >= 3:
            await message.author.timeout(datetime.timedelta(hours=6), reason="3 uyarı")
            uyari_sayaci[guild_id][user_id] = 0
            await message.channel.send(f"{message.author.mention} 3 uyarı aldığı için 6 saat susturuldu.", delete_after=10)
        else:
            await message.channel.send(f"{message.author.mention}, küfürlü mesaj silindi! Uyarı: {uyari}/3", delete_after=8)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member: discord.Member):
    kanal = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if kanal:
        embed = discord.Embed(title="Hoş geldin!", description="Verify için /verify komutunu kullan.", color=discord.Color.red())
        await kanal.send(embed=embed)

# 6. BÖLÜM: Slash Komutları (Verify, Durum, Ban, Kick, Mute vb.)
@bot.tree.command(name="verify", description="Verify yourself.")
async def verify(interaction: discord.Interaction):
    rol = interaction.guild.get_role(VERIFY_ROLE_ID)
    if not rol:
        await interaction.response.send_message("Rol bulunamadı.", ephemeral=True)
        return
    await interaction.user.add_roles(rol)
    await interaction.response.send_message(f"Hoş geldin {interaction.user.mention}!", ephemeral=True)

@bot.tree.command(name="durum", description="Botun durumunu değiştirir.")
@discord.app_commands.choices(degistir=[
    discord.app_commands.Choice(name="Çevrimiçi", value="online"),
    discord.app_commands.Choice(name="Boşta", value="idle"),
    discord.app_commands.Choice(name="Rahatsız Etme", value="dnd")
])
async def durum(interaction: discord.Interaction, degistir: str):
    # Yetki kontrolü (Belirttiğin rol ID'si ile)
    gerekli_rol_id = 1521970736627978362
    if not any(rol.id == gerekli_rol_id for rol in interaction.user.roles):
        await interaction.response.send_message("❌ Yetkin yok.", ephemeral=True)
        return
    
    durum_map = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd}
    await bot.change_presence(status=durum_map.get(degistir))
    await interaction.response.send_message(f"✅ Durum başarıyla **{degistir}** yapıldı.", ephemeral=True)

@bot.tree.command(name="ban", description="Üyeyi banla.")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, uyeler: str, sebep: str = "Sebep yok"):
    await interaction.response.defer()
    for uid in id_ayristir(uyeler):
        try:
            kullanici = await bot.fetch_user(uid)
            await interaction.guild.ban(kullanici, reason=sebep)
        except: pass
    await interaction.followup.send("İşlem tamamlandı.")

@bot.tree.command(name="unban", description="Banı kaldır.")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, kullanici_idleri: str, sebep: str = "Sebep yok"):
    await interaction.response.defer()
    for uid in id_ayristir(kullanici_idleri):
        try:
            kullanici = await bot.fetch_user(uid)
            await interaction.guild.unban(kullanici, reason=sebep)
        except: pass
    await interaction.followup.send("Ban kaldırıldı.")

@bot.tree.command(name="kick", description="Üyeyi at.")
@discord.app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, uyeler: str, sebep: str = "Sebep yok"):
    await interaction.response.defer()
    for uid in id_ayristir(uyeler):
        try:
            uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            await uye.kick(reason=sebep)
        except: pass
    await interaction.followup.send("Atıldı.")

@bot.tree.command(name="mute", description="Üyeyi sustur.")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, uyeler: str, sure: str = "10dk", sebep: str = "Sebep yok"):
    await interaction.response.defer()
    sure_td = sure_ayristir(sure)
    for uid in id_ayristir(uyeler):
        try:
            uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            await uye.timeout(sure_td, reason=sebep)
        except: pass
    await interaction.followup.send("Susturuldu.")

@bot.tree.command(name="unmute", description="Susturmayı kaldır.")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, uye: discord.Member, sebep: str = "Sebep yok"):
    await uye.timeout(None, reason=sebep)
    await interaction.response.send_message("Susturma kaldırıldı.")

# 7. BÖLÜM: Hata Yönetimi ve Bot Başlangıç (Ready) Eventi
@bot.tree.error
async def hata_yoneticisi(interaction: discord.Interaction, hata):
    await interaction.response.send_message(f"Hata oluştu: {hata}", ephemeral=True)

@bot.event
async def on_ready():
    game = discord.Game("SCP Roleplay oynuyor")
    await bot.change_presence(status=discord.Status.online, activity=game)
    await bot.tree.sync()
    print(f'{bot.user} hazır ve komutlar senkronize edildi!')

bot.run(os.environ['TOKEN'])
