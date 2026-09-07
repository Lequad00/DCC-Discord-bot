import discord
from discord.ext import commands
import os
import threading
import datetime
import asyncio
import re
from flask import Flask

# ── WEB SUNUCUSU (UptimeRobot / Render Ping) ──────────────
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot aktif!'

def run_web():
    app.run(host='0.0.0.0', port=3000)

threading.Thread(target=run_web, daemon=True).start()

# ── BOT AYARLARI ──────────────────────────────────────────
MY_GUILD = discord.Object(id=1545763046717263894)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

VERIFY_ROLE_ID = 1521967908341682316
WELCOME_CHANNEL_ID = 1523295990164230224

# ── YARDIMCI FONKSİYONLAR ─────────────────────────────────
def id_ayristir(metin: str):
    return [int(x) for x in re.findall(r'\d+', metin)]

def sure_ayristir(sure_str: str):
    match = re.match(r'^(\d+)(dk|sa|g|hafta)$', sure_str.lower())
    if not match:
        return None
    deger, birim = int(match.group(1)), match.group(2)
    if birim == 'dk':
        return datetime.timedelta(minutes=deger)
    elif birim == 'sa':
        return datetime.timedelta(hours=deger)
    elif birim == 'g':
        return datetime.timedelta(days=deger)
    elif birim == 'hafta':
        return datetime.timedelta(weeks=deger)
    return None

def sure_formatla(td: datetime.timedelta):
    saniye = int(td.total_seconds())
    gun, kalan = divmod(saniye, 86400)
    saat, kalan = divmod(kalan, 3600)
    dakika, _ = divmod(kalan, 60)
    parcalar = []
    if gun: parcalar.append(f"{gun} gün")
    if saat: parcalar.append(f"{saat} saat")
    if dakika: parcalar.append(f"{dakika} dakika")
    return " ".join(parcalar) or "0 dakika"

# ── ON READY & COMMAND SYNC ───────────────────────────────
@bot.event
async def on_ready():
    print(f"🔄 {bot.user} bağlandı, komutlar aktarılıyor...")
    try:
        # Önce global komutları tanımlı Guild'e kopyala
        bot.tree.copy_global_to(guild=MY_GUILD)
        # Ardından o sunucuya senkronize et
        synced = await bot.tree.sync(guild=MY_GUILD)
        print(f"✅ BAŞARILI! Toplam {len(synced)} adet komut bu sunucuya yüklendi.")
    except Exception as e:
        print(f"❌ Senkronizasyon hatası: {e}")

# ── VERIFY ────────────────────────────────────────────────
@bot.tree.command(name="verify", description="Verify yourself to gain access to the server.")
async def verify(interaction: discord.Interaction):
    rol = interaction.guild.get_role(VERIFY_ROLE_ID)
    if rol is None:
        await interaction.response.send_message("❌ Verified role not found. Please contact an admin.", ephemeral=True)
        return
    if rol in interaction.user.roles:
        await interaction.response.send_message("✅ You are already verified!", ephemeral=True)
        return
    await interaction.user.add_roles(rol)
    embed = discord.Embed(title="Member Updated", color=discord.Color.green())
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Added Roles", value=rol.mention, inline=True)
    embed.add_field(name="Nickname", value=interaction.user.display_name, inline=True)
    await interaction.response.send_message(
        content=f"👋 Welcome to **DCC | Diplomatic Chaos Council**, {interaction.user.mention}!",
        embed=embed
    )

# ── WELCOME MESSAGE ───────────────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    kanal = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if kanal is None:
        return
    embed = discord.Embed(
        title="👋 Welcome to DCC | Diplomatic Chaos Council!",
        description=(
            f"Hey {member.mention}, welcome to the server!\n\n"
            f"Please head to the verification channel and use `/verify` to gain access."
        ),
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")
    await kanal.send(embed=embed)

# ── BAN ───────────────────────────────────────────────────
@bot.tree.command(name="ban", description="Bir veya birden fazla üyeyi banla.")
@discord.app_commands.describe(
    uyeler="Kullanıcı ID'leri veya mention'ları, boşlukla ayır",
    sebep="Ban sebebi",
    sure="Geçici ban süresi: ör. 30dk, 12sa, 7g, 2hafta (boş bırakırsan kalıcı)",
    mesaj_sil="Mesaj geçmişini sil (0–7 gün, varsayılan 0)"
)
@discord.app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, uyeler: str, sebep: str = "Sebep belirtilmedi", sure: str = None, mesaj_sil: int = 0):
    await interaction.response.defer()
    mesaj_sil = max(0, min(mesaj_sil, 7))
    sure_td = None
    if sure:
        sure_td = sure_ayristir(sure)
        if sure_td is None:
            await interaction.followup.send("❌ Geçersiz süre formatı. Örnekler: `30dk`, `12sa`, `7g`, `2hafta`", ephemeral=True)
            return

    banlananlar, basarisizlar = [], []
    for uid in id_ayristir(uyeler):
        try:
            kullanici = await bot.fetch_user(uid)
            await interaction.guild.ban(kullanici, reason=sebep, delete_message_days=mesaj_sil)
            banlananlar.append((uid, kullanici))
        except Exception as e:
            basarisizlar.append(f"`{uid}` — {e}")

    embed = discord.Embed(
        title="🔨 Geçici Ban" if sure_td else "🔨 Kalıcı Ban",
        color=discord.Color.red()
    )
    if banlananlar:
        embed.add_field(name=f"✅ Banlananlar ({len(banlananlar)})", value="\n".join(f"`{u}`" for _, u in banlananlar), inline=False)
    if basarisizlar:
        embed.add_field(name=f"❌ Başarısız ({len(basarisizlar)})", value="\n".join(basarisizlar), inline=False)
    embed.add_field(name="Sebep", value=sebep, inline=True)
    embed.add_field(name="Süre", value=sure_formatla(sure_td) if sure_td else "Kalıcı", inline=True)
    embed.set_footer(text=f"İşlemi yapan: {interaction.user}")
    await interaction.followup.send(embed=embed)

    if sure_td:
        async def otomatik_unban(guild, kullanicilar, saniye):
            await asyncio.sleep(saniye)
            for uid, kullanici in kullanicilar:
                try:
                    await guild.unban(kullanici, reason="Geçici ban süresi doldu")
                except Exception:
                    pass
        asyncio.create_task(otomatik_unban(interaction.guild, banlananlar, sure_td.total_seconds()))

# ── UNBAN ─────────────────────────────────────────────────
@bot.tree.command(name="unban", description="Bir veya birden fazla kullanıcının banını kaldır.")
@discord.app_commands.describe(kullanici_idleri="ID'leri boşlukla ayır", sebep="Unban sebebi")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, kullanici_idleri: str, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer()
    unbanlananlar, basarisizlar = [], []
    for uid in id_ayristir(kullanici_idleri):
        try:
            kullanici = await bot.fetch_user(uid)
            await interaction.guild.unban(kullanici, reason=sebep)
            unbanlananlar.append(f"`{kullanici}`")
        except Exception as e:
            basarisizlar.append(f"`{uid}` — {e}")
    embed = discord.Embed(title="✅ Unban Sonuçları", color=discord.Color.green())
    if unbanlananlar:
        embed.add_field(name=f"✅ Banı Kaldırılanlar ({len(unbanlananlar)})", value="\n".join(unbanlananlar), inline=False)
    if basarisizlar:
        embed.add_field(name=f"❌ Başarısız ({len(basarisizlar)})", value="\n".join(basarisizlar), inline=False)
    embed.add_field(name="Sebep", value=sebep, inline=True)
    embed.set_footer(text=f"İşlemi yapan: {interaction.user}")
    await interaction.followup.send(embed=embed)

# ── KICK ──────────────────────────────────────────────────
@bot.tree.command(name="kick", description="Bir veya birden fazla üyeyi sunucudan at.")
@discord.app_commands.describe(uyeler="Kullanıcı ID'leri veya mention'ları, boşlukla ayır", sebep="Atma sebebi")
@discord.app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, uyeler: str, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer()
    atilanlar, basarisizlar = [], []
    for uid in id_ayristir(uyeler):
        try:
            uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            await uye.kick(reason=sebep)
            atilanlar.append(f"`{uye}`")
        except Exception as e:
            basarisizlar.append(f"`{uid}` — {e}")
    embed = discord.Embed(title="👢 Kick Sonuçları", color=discord.Color.orange())
    if atilanlar:
        embed.add_field(name=f"✅ Atılanlar ({len(atilanlar)})", value="\n".join(atilanlar), inline=False)
    if basarisizlar:
        embed.add_field(name=f"❌ Başarısız ({len(basarisizlar)})", value="\n".join(basarisizlar), inline=False)
    embed.add_field(name="Sebep", value=sebep, inline=True)
    embed.set_footer(text=f"İşlemi yapan: {interaction.user}")
    await interaction.followup.send(embed=embed)

# ── MUTE ──────────────────────────────────────────────────
@bot.tree.command(name="mute", description="Bir veya birden fazla üyeyi sustur.")
@discord.app_commands.describe(
    uyeler="Kullanıcı ID'leri veya mention'ları, boşlukla ayır",
    sure="Susturma süresi: ör. 10dk, 2sa, 1g (maks. 28 gün)",
    sebep="Susturma sebebi"
)
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, uyeler: str, sure: str = "10dk", sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer()
    sure_td = sure_ayristir(sure)
    if sure_td is None:
        await interaction.followup.send("❌ Geçersiz süre formatı. Örnekler: `10dk`, `2sa`, `7g`, `1hafta`", ephemeral=True)
        return
    if sure_td > datetime.timedelta(days=28):
        await interaction.followup.send("❌ Maksimum susturma süresi 28 gündür.", ephemeral=True)
        return

    susturulanlar, basarisizlar = [], []
    for uid in id_ayristir(uyeler):
        try:
            uye = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            await uye.timeout(sure_td, reason=sebep)
            susturulanlar.append(f"`{uye}`")
        except Exception as e:
            basarisizlar.append(f"`{uid}` — {e}")
    embed = discord.Embed(title="🔇 Mute Sonuçları", color=discord.Color.dark_gray())
    if susturulanlar:
        embed.add_field(name=f"✅ Susturulanlar ({len(susturulanlar)})", value="\n".join(susturulanlar), inline=False)
    if basarisizlar:
        embed.add_field(name=f"❌ Başarısız ({len(basarisizlar)})", value="\n".join(basarisizlar), inline=False)
    embed.add_field(name="Süre", value=sure_formatla(sure_td), inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=True)
    embed.set_footer(text=f"İşlemi yapan: {interaction.user}")
    await interaction.followup.send(embed=embed)

# ── UNMUTE ────────────────────────────────────────────────
@bot.tree.command(name="unmute", description="Bir üyenin susturmasını kaldır.")
@discord.app_commands.describe(uye="Susturması kaldırılacak üye", sebep="Kaldırma sebebi")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, uye: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await uye.timeout(None, reason=sebep)
    embed = discord.Embed(
        title="🔊 Susturma Kaldırıldı",
        description=f"**{uye}** adlı üyenin susturması kaldırıldı.\n**Sebep:** {sebep}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"İşlemi yapan: {interaction.user}")
    await interaction.response.send_message(embed=embed)

# ── DURUM DEĞİŞTİRME KOMUTU ──────────────────────────────
@bot.tree.command(name="durum", description="Botun durumunu değiştirir.")
@discord.app_commands.describe(degistir="Seçmek istediğin durum")
@discord.app_commands.choices(degistir=[
    discord.app_commands.Choice(name="Çevrimiçi", value="online"),
    discord.app_commands.Choice(name="Boşta", value="idle"),
    discord.app_commands.Choice(name="Rahatsız Etme", value="dnd")
])
async def durum(interaction: discord.Interaction, degistir: str):
    await interaction.response.defer(ephemeral=True)

    gerekli_rol_id = 1521970736627978362
    if not any(rol.id == gerekli_rol_id for rol in interaction.user.roles):
        await interaction.followup.send("❌ Bu komutu kullanmak için gerekli yetkiye sahip değilsin.", ephemeral=True)
        return

    durum_map = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd
    }
    await bot.change_presence(status=durum_map.get(degistir))
    await interaction.followup.send(f"✅ Durum başarıyla **{degistir}** olarak değiştirildi.", ephemeral=True)

# ── GENEL HATA YÖNETİCİSİ ────────────────────────────────
@bot.tree.error
async def hata_yoneticisi(interaction: discord.Interaction, hata: discord.app_commands.AppCommandError):
    komut_adi = interaction.command.name if interaction.command else "Bilinmeyen Komut"
    print(f"[HATA] /{komut_adi}: {hata}")
    
    if isinstance(hata, discord.app_commands.MissingPermissions):
        mesaj = "❌ Bu komutu kullanmak için yetkin yok."
    else:
        mesaj = f"❌ Bir hata oluştu: {hata}"

    if interaction.response.is_done():
        await interaction.followup.send(mesaj, ephemeral=True)
    else:
        await interaction.response.send_message(mesaj, ephemeral=True)

# ── BOTU BAŞLAT ───────────────────────────────────────────
bot.run(os.environ['TOKEN'])
