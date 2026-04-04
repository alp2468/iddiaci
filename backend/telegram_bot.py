from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
import logging
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from cache_manager import MatchCacheManager
from premium_helper import PremiumHelper

logger = logging.getLogger(__name__)

class BettingBot:
    def __init__(self, db, scraper, analyzer, coupon_gen):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.db = db
        self.scraper = scraper
        self.analyzer = analyzer
        self.coupon_gen = coupon_gen
        self.cache_manager = MatchCacheManager(db, scraper)
        self.premium_helper = PremiumHelper()
        self.admin_id = os.environ.get('ADMIN_TELEGRAM_ID', '7936836513')  # SENİN TELEGRAM ID'N
        self.app = None
        self.waiting_for_receipt = {}  # Ödeme dekontu bekleyen kullanıcılar
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command
        """
        user = update.effective_user
        is_admin = str(user.id) == self.admin_id
        
        # Save user to database
        await self.db.users.update_one(
            {"telegram_id": str(user.id)},
            {
                "$set": {
                    "telegram_id": str(user.id),
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_admin": is_admin,
                    "last_interaction": datetime.utcnow().isoformat()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            upsert=True
        )
        
        admin_text = "\n/admin - Admin paneli" if is_admin else ""
        
        welcome_message = f"""
**Hos Geldiniz {user.first_name}!**

Ben futbol maclarini analiz edip sizin icin bahis kuponlari olusturan bir botum.

**Ozellikler:**
- 9 farkli ligden mac analizi
- Yapay zeka destekli tahminler
- 3 farkli risk seviyesi

**Komutlar:**
/kupon - Yeni kupon olustur
/maclar - Bugunku maclari gor
/kuponlarim - Kuponlarimi gor
/premium - Premium uyelik
/help - Yardim menusu{admin_text}

Ucretsiz 3 kupon hakkiniz var!
Hemen baslamak icin /kupon komutunu kullanin!
        """
        
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
        
        # Log activity
        await self.db.bot_activities.insert_one({
            "activity_type": "start",
            "user_telegram_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def kupon_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /kupon command - show risk level buttons with success rates
        """
        user = update.effective_user
        
        # Kullanıcı bilgisini al
        user_data = await self.db.users.find_one({"telegram_id": str(user.id)})
        is_premium = user_data and self.premium_helper.is_premium_active(user_data)
        is_admin = user_data and user_data.get('is_admin', False)
        
        # Günlük kullanım hesapla
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_count = 0
        if user_data:
            if user_data.get('last_coupon_date') == today:
                daily_count = user_data.get('daily_coupon_count', 0)
        
        unlimited = is_premium or is_admin
        remaining = 999 if unlimited else max(0, self.premium_helper.FREE_DAILY_LIMIT - daily_count)
        
        # Aylık başarı oranlarını hesapla
        success_rates = await self._calculate_monthly_success_rates()
        
        # Zor seviye kilidi
        zor_label = f"Zor (+10 Oran) | Bu Ay: %{success_rates['zor']}"
        if not unlimited:
            zor_label = "Zor (PREMIUM GEREKLI)"
        
        keyboard = [
            [InlineKeyboardButton(
                f"Banko (2-3 Oran) | Bu Ay: %{success_rates['banko']}", 
                callback_data="risk_banko"
            )],
            [InlineKeyboardButton(
                f"Orta (5-7 Oran) | Bu Ay: %{success_rates['orta']}", 
                callback_data="risk_orta"
            )],
            [InlineKeyboardButton(
                zor_label, 
                callback_data="risk_zor"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if unlimited:
            status_text = "Admin - Sinirsiz kupon" if is_admin else "Premium - Sinirsiz kupon"
        else:
            status_text = f"Ucretsiz - Kalan hak: {remaining}/{self.premium_helper.FREE_DAILY_LIMIT}"
        
        message = f"""
**Kupon Olustur**

{status_text}

Lutfen risk seviyesini secin:

**Banko:** Dusuk riskli, 2-3 mac | Bu ay %{success_rates['banko']} basari
**Orta:** Orta riskli, 3-5 mac | Bu ay %{success_rates['orta']} basari
**Zor:** Yuksek riskli, yuksek oran | Bu ay %{success_rates['zor']} basari {'(Premium)' if not unlimited else ''}

**Toplam Kupon:** {success_rates['total_coupons']} | Kazanan: {success_rates['won_coupons']}
        """
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        
        # Log activity
        await self.db.bot_activities.insert_one({
            "activity_type": "kupon_request",
            "user_telegram_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle button callbacks
        """
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if query.data.startswith("risk_"):
            risk_level = query.data.replace("risk_", "")
            
            # Kullanıcı bilgisini al
            user_data = await self.db.users.find_one({"telegram_id": str(user.id)})
            if not user_data:
                user_data = {"telegram_id": str(user.id), "daily_coupon_count": 0, "last_coupon_date": ""}
            
            # Premium kontrol: Zor seviye sadece premium
            can_use, msg = self.premium_helper.can_use_risk_level(user_data, risk_level)
            if not can_use:
                await query.edit_message_text(msg)
                return
            
            # Premium kontrol: Günlük limit
            can_create, msg = self.premium_helper.can_create_coupon(user_data)
            if not can_create:
                await query.edit_message_text(msg)
                return
            
            # Show processing message with progress
            progress_msg = await query.edit_message_text(
                "⏳ Kupon hazırlanıyor...\n\n🔄 Başlatılıyor..."
            )
            
            try:
                # Generate coupon with progress updates
                coupon = await self._generate_coupon(risk_level, str(user.id), progress_msg)
                
                # Format and send coupon
                coupon_message = self._format_coupon(coupon)
                
                # Kupon durumu için inline butonlar ekle
                status_keyboard = [
                    [
                        InlineKeyboardButton("✅ TUTTU", callback_data=f"status_won_{coupon['id']}"),
                        InlineKeyboardButton("❌ TUTMADI", callback_data=f"status_lost_{coupon['id']}")
                    ]
                ]
                status_markup = InlineKeyboardMarkup(status_keyboard)
                
                await progress_msg.edit_text(
                    coupon_message, 
                    parse_mode="Markdown",
                    reply_markup=status_markup
                )
                
            except Exception as e:
                logger.error(f"Error generating coupon: {str(e)}")
                await progress_msg.edit_text(
                    f"❌ Kupon oluşturulurken bir hata oluştu: {str(e)}\n\nLütfen tekrar deneyin."
                )
        
        # Kupon durumu güncelleme
        elif query.data.startswith("status_"):
            parts = query.data.split("_")
            status = parts[1]  # won or lost
            coupon_id = parts[2]
            
            try:
                # Kuponu güncelle
                result = await self.db.coupons.update_one(
                    {"id": coupon_id},
                    {
                        "$set": {
                            "status": status,
                            "result_checked": True,
                            "result_date": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    status_text = "✅ KAZANDI!" if status == "won" else "❌ TUTMADI"
                    await query.answer(f"Kupon durumu güncellendi: {status_text}")
                    
                    # Mesajı güncelle
                    updated_message = query.message.text + f"\n\n🏁 **SONUÇ:** {status_text}"
                    await query.edit_message_text(updated_message, parse_mode="Markdown")
                else:
                    await query.answer("Kupon bulunamadı.")
            except Exception as e:
                logger.error(f"Error updating coupon status: {str(e)}")
                await query.answer("Bir hata oluştu.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /help command
        """
        help_text = """
**Yardim Menusu**

**Komutlar:**
/start - Botu baslat
/kupon - Yeni kupon olustur
/maclar - Bugunku maclari listele
/kuponlarim - Kuponlarimi goruntule
/premium - Premium uyelik bilgisi
/odemeyaptim - Odeme dekontu gonder
/help - Bu yardim menusunu goster

**Risk Seviyeleri:**

**Banko (2-3 Oran)**
- 2-3 mac
- Yuksek guvenilirlik
- Dusuk kazanc potansiyeli

**Orta (5-7 Oran)**
- 3-5 mac
- Orta guvenilirlik
- Orta kazanc potansiyeli

**Zor (+10 Oran)** (Premium)
- 2 yuksek oranli mac veya 5-8 mac
- Dusuk guvenilirlik
- Yuksek kazanc potansiyeli

**Uyelik:**
Ucretsiz: Gunde 3 kupon (Banko + Orta)
Premium: Sinirsiz kupon + Zor seviye

**Analiz Edilen Ligler:**
Turkiye Super Lig, Ingiltere Premier Lig,
Ispanya La Liga, Almanya Bundesliga,
Italya Serie A, Fransa Ligue 1,
Ingiltere Championship, Turkiye 1. Lig,
Hollanda Eredivisie

Not: Tum tahminler yapay zeka destekli analizlere dayanir. Bahis oynarken dikkatli olun!
        """
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def my_coupons_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /kuponlarim command - show user's recent coupons
        """
        user = update.effective_user
        
        try:
            # Son 10 kuponu çek
            coupons = await self.db.coupons.find({
                "user_telegram_id": str(user.id)
            }).sort("created_at", -1).limit(10).to_list(10)
            
            if not coupons:
                await update.message.reply_text(
                    "Henüz kuponunuz yok. /kupon komutu ile yeni kupon oluşturabilirsiniz."
                )
                return
            
            message = "**Son Kuponlariniz:**\n\n"
            
            for i, coupon in enumerate(coupons, 1):
                risk_emoji = {"banko": "Banko", "orta": "Orta", "zor": "Zor"}.get(coupon['risk_level'], "?")
                status_emoji = {
                    "won": "KAZANDI",
                    "lost": "TUTMADI",
                    "pending": "Bekliyor"
                }.get(coupon.get('status', 'pending'), "Bekliyor")
                
                created = coupon.get('created_at', '')[:10]
                
                message += f"{i}. {risk_emoji} {coupon['risk_level'].upper()} | Oran: {coupon['total_odds']}\n"
                message += f"   {status_emoji} | {created}\n"
                message += f"   {coupon['match_count']} mac | {coupon.get('potential_return', 0):.0f} TL kazanc\n\n"
            
            message += "\nIpucu: Kupon sonuclarini manuel olarak kontrol edebilirsiniz."
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error fetching user coupons: {str(e)}")
            await update.message.reply_text("Kuponlar yüklenirken bir hata oluştu.")
    
    async def _calculate_monthly_success_rates(self) -> Dict:
        """
        Bu ayki kupon başarı oranlarını hesapla
        """
        from datetime import datetime, timedelta
        
        # Bu ayın başı
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        try:
            # Bu ayki tüm kuponları çek
            all_coupons = await self.db.coupons.find({
                "created_at": {"$gte": month_start.isoformat()}
            }).to_list(1000)
            
            # Risk seviyelerine göre grupla
            stats = {
                'banko': {'total': 0, 'won': 0},
                'orta': {'total': 0, 'won': 0},
                'zor': {'total': 0, 'won': 0}
            }
            
            total_coupons = len(all_coupons)
            won_coupons = 0
            
            for coupon in all_coupons:
                risk = coupon.get('risk_level', 'banko')
                if risk in stats:
                    stats[risk]['total'] += 1
                    if coupon.get('status') == 'won':
                        stats[risk]['won'] += 1
                        won_coupons += 1
            
            # Başarı yüzdelerini hesapla
            return {
                'banko': round((stats['banko']['won'] / stats['banko']['total'] * 100) if stats['banko']['total'] > 0 else 0),
                'orta': round((stats['orta']['won'] / stats['orta']['total'] * 100) if stats['orta']['total'] > 0 else 0),
                'zor': round((stats['zor']['won'] / stats['zor']['total'] * 100) if stats['zor']['total'] > 0 else 0),
                'total_coupons': total_coupons,
                'won_coupons': won_coupons
            }
        except Exception as e:
            logger.error(f"Error calculating success rates: {str(e)}")
            return {
                'banko': 0,
                'orta': 0,
                'zor': 0,
                'total_coupons': 0,
                'won_coupons': 0
            }
    
    async def _generate_coupon(self, risk_level: str, user_id: str, progress_message=None) -> Dict:
        """
        Generate coupon with progress updates
        """
        try:
            # 1. Maçları cache'den getir (hızlı!)
            if progress_message:
                await progress_message.edit_text("⏳ Kupon hazırlanıyor...\n\n🔄 Maçlar yükleniyor...")
            
            matches = await self.cache_manager.get_cached_matches()
            
            if not matches:
                raise Exception("Bugün için maç bulunamadı.")
            
            if progress_message:
                await progress_message.edit_text(
                    f"⏳ Kupon hazırlanıyor...\n\n"
                    f"✅ {len(matches)} maç yüklendi\n"
                    f"🤖 AI analiz yapılıyor..."
                )
            
            # 2. AI analizi (ilk 15 maç)
            all_predictions = []
            analysis_batch_size = min(15, len(matches))
            
            for i, match in enumerate(matches[:analysis_batch_size], 1):
                predictions = await self.analyzer.analyze_match(match)
                for pred in predictions:
                    await self.db.predictions.insert_one(pred)
                    all_predictions.append(pred)
                
                # Her 3 maçta bir progress güncelle
                if i % 3 == 0 and progress_message:
                    await progress_message.edit_text(
                        f"⏳ Kupon hazırlanıyor...\n\n"
                        f"✅ {len(matches)} maç yüklendi\n"
                        f"🤖 AI analiz: {i}/{analysis_batch_size} maç"
                    )
            
            if progress_message:
                await progress_message.edit_text(
                    f"⏳ Kupon hazırlanıyor...\n\n"
                    f"✅ {len(matches)} maç yüklendi\n"
                    f"✅ {len(all_predictions)} tahmin oluşturuldu\n"
                    f"🎯 En iyi seçimler yapılıyor..."
                )
            
            # 3. Kupon oluştur
            coupon = self.coupon_gen.generate_coupon(risk_level, matches, all_predictions)
            coupon["user_telegram_id"] = user_id
            
            # 4. Kuponu kaydet
            await self.db.coupons.insert_one(coupon)
            
            # 5. Günlük kupon sayısını güncelle
            today = datetime.utcnow().strftime("%Y-%m-%d")
            user_data = await self.db.users.find_one({"telegram_id": user_id})
            current_date = user_data.get('last_coupon_date', '') if user_data else ''
            
            if current_date == today:
                await self.db.users.update_one(
                    {"telegram_id": user_id},
                    {"$inc": {"daily_coupon_count": 1, "total_coupons": 1}}
                )
            else:
                await self.db.users.update_one(
                    {"telegram_id": user_id},
                    {"$set": {"daily_coupon_count": 1, "last_coupon_date": today}, "$inc": {"total_coupons": 1}},
                    upsert=True
                )
            
            # 6. Log activity
            await self.db.bot_activities.insert_one({
                "activity_type": "coupon_generated",
                "user_telegram_id": user_id,
                "details": {
                    "risk_level": risk_level,
                    "total_odds": coupon["total_odds"],
                    "match_count": coupon["match_count"]
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return coupon
            
        except Exception as e:
            logger.error(f"Error generating coupon: {str(e)}")
            raise
    
    def _format_coupon(self, coupon: Dict) -> str:
        """
        Format coupon for Telegram message
        """
        risk_emoji = {
            "banko": "🟢",
            "orta": "🟡",
            "zor": "🔴"
        }
        
        risk_name = {
            "banko": "BANKO",
            "orta": "ORTA",
            "zor": "ZOR"
        }
        
        emoji = risk_emoji.get(coupon["risk_level"], "⚪")
        name = risk_name.get(coupon["risk_level"], "BİLİNMEYEN")
        
        # Kupon tarihi
        from datetime import datetime
        kupon_tarihi = datetime.utcnow().strftime("%d.%m.%Y %H:%M")
        
        message = f"""
{emoji} **{name} KUPON**
📅 **Tarih:** {kupon_tarihi}

📊 **Toplam Oran:** {coupon['total_odds']}
🎯 **Maç Sayısı:** {coupon['match_count']}
💰 **100 TL İçin Kazanç:** {coupon.get('potential_return', 0):.2f} TL

**Maçlar:**
\n"""
        
        for i, match in enumerate(coupon["matches"], 1):
            # Yeni format - farklı bahis türlerini destekler
            bet_type = match.get('bet_type', '1X2')
            option = match.get('recommended_option', match.get('recommended_bet', '1'))
            
            bet_type_display = {
                "1X2": "Maç Sonucu",
                "over_under": "Alt/Üst",
                "btts": "Karşılıklı Gol"
            }.get(bet_type, bet_type)
            
            option_display = {
                "1": "Ev Sahibi",
                "X": "Beraberlik",
                "2": "Deplasman",
                "yes": "Evet",
                "no": "Hayır",
                "over_2.5": "Üst 2.5",
                "under_2.5": "Alt 2.5"
            }.get(option, option)
            
            odds_value = match.get('odds', match.get('predicted_odds', 0))
            
            message += f"""{i}. **{match['home_team']} vs {match['away_team']}**
   🏆 Lig: {match['league']}
   📌 Bahis: {bet_type_display}
   ✅ Tahmin: {option_display}
   💵 Oran: {odds_value}
   🎯 Güven: {match.get('confidence', 0):.0f}%

"""
        
        message += "\n⚠️ **Uyarı:** Bu kupon AI analizi ile oluşturulmuştur. Bahis oynarken dikkatli olun!"
        
        return message
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin yonetim paneli"""
        user = update.effective_user
        
        if str(user.id) != self.admin_id:
            await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
            return
        
        # Istatistikler
        total_users = await self.db.users.count_documents({})
        premium_users = await self.db.users.count_documents({"is_premium": True})
        total_coupons = await self.db.coupons.count_documents({})
        pending_payments = await self.db.payments.count_documents({"status": "pending"})
        
        # Bugunun kuponlari
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_coupons = await self.db.coupons.count_documents({
            "created_at": {"$regex": f"^{today}"}
        })
        
        message = f"""**ADMIN PANELI**

**Istatistikler:**
- Toplam Kullanici: {total_users}
- Premium Kullanici: {premium_users}
- Toplam Kupon: {total_coupons}
- Bugun Kupon: {today_coupons}
- Bekleyen Odeme: {pending_payments}

**Admin Komutlari:**
/admin\\_payments - Bekleyen odemeleri gor
/admin\\_users - Kullanici listesi
/admin\\_cache - Cache'i yenile
/admin\\_premium @kullanici - Manuel premium ver
/admin\\_stats - Detayli istatistik

Senin ID: `{self.admin_id}`
"""
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def admin_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Kullanici listesi"""
        user = update.effective_user
        if str(user.id) != self.admin_id:
            return
        
        users = await self.db.users.find({}).sort("last_interaction", -1).limit(20).to_list(20)
        
        if not users:
            await update.message.reply_text("Henuz kullanici yok.")
            return
        
        message = f"**Kullanicilar** ({len(users)})\n\n"
        for i, u in enumerate(users, 1):
            username = u.get('username', '-')
            premium = "Premium" if u.get('is_premium') else "Ucretsiz"
            admin = " (ADMIN)" if u.get('is_admin') else ""
            coupon_count = u.get('total_coupons', 0)
            message += f"{i}. @{username} | {premium}{admin} | {coupon_count} kupon\n"
        
        if len(message) > 4000:
            message = message[:3990] + "\n..."
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def admin_cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Cache yenile"""
        user = update.effective_user
        if str(user.id) != self.admin_id:
            return
        
        await update.message.reply_text("Cache yenileniyor...")
        await self.cache_manager.force_refresh()
        
        matches = await self.db.matches.find({}).to_list(1000)
        await update.message.reply_text(f"Cache yenilendi! {len(matches)} mac yuklendi.")
    
    async def admin_give_premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Manuel premium ver"""
        user = update.effective_user
        if str(user.id) != self.admin_id:
            return
        
        # /admin_premium @username veya telegram_id
        args = context.args
        if not args:
            await update.message.reply_text("Kullanim: /admin\\_premium <telegram\\_id veya @username>")
            return
        
        target = args[0].replace("@", "")
        
        # Kullaniciyi bul (username veya telegram_id)
        target_user = await self.db.users.find_one({
            "$or": [
                {"username": target},
                {"telegram_id": target}
            ]
        })
        
        if not target_user:
            await update.message.reply_text(f"Kullanici bulunamadi: {target}")
            return
        
        # Premium ver
        premium_data = self.premium_helper.activate_premium(target_user['telegram_id'], "monthly")
        await self.db.users.update_one(
            {"telegram_id": target_user['telegram_id']},
            {"$set": premium_data}
        )
        
        username = target_user.get('username', target_user['telegram_id'])
        await update.message.reply_text(f"@{username} artik 30 gunluk Premium!")
        
        # Kullaniciya bildirim
        try:
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text="Premium uyeliginiz aktif edildi! 30 gun boyunca sinirsiz kupon ve tum seviyelere erisim.\n\n/kupon - Hemen kupon olustur"
            )
        except Exception as e:
            logger.error(f"Kullaniciya bildirim gonderilemedi: {str(e)}")
    
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Detayli istatistik"""
        user = update.effective_user
        if str(user.id) != self.admin_id:
            return
        
        # Son 7 gun
        from datetime import timedelta
        now = datetime.utcnow()
        week_ago = (now - timedelta(days=7)).isoformat()
        
        weekly_coupons = await self.db.coupons.count_documents({
            "created_at": {"$gte": week_ago}
        })
        weekly_users = await self.db.users.count_documents({
            "last_interaction": {"$gte": week_ago}
        })
        
        # Risk dagilimi
        banko_count = await self.db.coupons.count_documents({"risk_level": "banko"})
        orta_count = await self.db.coupons.count_documents({"risk_level": "orta"})
        zor_count = await self.db.coupons.count_documents({"risk_level": "zor"})
        
        # Kazanma orani
        won = await self.db.coupons.count_documents({"status": "won"})
        lost = await self.db.coupons.count_documents({"status": "lost"})
        total_resolved = won + lost
        win_rate = round((won / total_resolved * 100) if total_resolved > 0 else 0)
        
        # Gelir
        approved_payments = await self.db.payments.count_documents({"status": "approved"})
        total_revenue = approved_payments * 99
        
        message = f"""**DETAYLI ISTATISTIK**

**Son 7 Gun:**
- Aktif Kullanici: {weekly_users}
- Olusturulan Kupon: {weekly_coupons}

**Risk Dagilimi:**
- Banko: {banko_count}
- Orta: {orta_count}
- Zor: {zor_count}

**Basari Orani:**
- Kazanan: {won} | Kaybeden: {lost}
- Genel Basari: %{win_rate}

**Gelir:**
- Onaylanan Odeme: {approved_payments}
- Toplam: {total_revenue}TL
"""
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def maclar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bugünkü maçları listele"""
        
        try:
            matches = await self.cache_manager.get_cached_matches()
            
            if not matches:
                await update.message.reply_text("Bugün için maç bulunamadı. Daha sonra tekrar deneyin.")
                return
            
            # Liglere göre grupla
            leagues = {}
            for match in matches:
                league = match.get('league', 'Diğer')
                if league not in leagues:
                    leagues[league] = []
                leagues[league].append(match)
            
            message = f"**Bugünkü Maclar** ({len(matches)} mac)\n\n"
            
            for league, league_matches in leagues.items():
                message += f"**{league}**\n"
                for m in league_matches[:10]:
                    time_str = m.get('match_time', '')
                    message += f"  {time_str} {m['home_team']} vs {m['away_team']}\n"
                message += "\n"
            
            message += "\n/kupon - Kupon olustur"
            
            # Telegram mesaj limiti 4096 karakter
            if len(message) > 4000:
                message = message[:3990] + "\n..."
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in maclar command: {str(e)}")
            await update.message.reply_text("Maclar yuklenirken hata olustu.")
    
    def setup_handlers(self):
        """
        Setup bot handlers
        """
        self.app = Application.builder().token(self.token).build()
        
        # Temel komutlar
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("kupon", self.kupon_command))
        self.app.add_handler(CommandHandler("kuponlarim", self.my_coupons_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("maclar", self.maclar_command))
        
        # Premium komutlar
        self.app.add_handler(CommandHandler("premium", self.premium_command))
        self.app.add_handler(CommandHandler("odemeyaptim", self.odemeyaptim_command))
        
        # Admin komutlar
        self.app.add_handler(CommandHandler("admin", self.admin_command))
        self.app.add_handler(CommandHandler("admin_payments", self.admin_payments_command))
        self.app.add_handler(CommandHandler("admin_users", self.admin_users_command))
        self.app.add_handler(CommandHandler("admin_cache", self.admin_cache_command))
        self.app.add_handler(CommandHandler("admin_premium", self.admin_give_premium_command))
        self.app.add_handler(CommandHandler("admin_stats", self.admin_stats_command))
        
        # Fotoğraf handler (dekont)
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Admin onay/red komutları (approve_XXX, reject_XXX)
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^/(approve|reject)_') & filters.User(int(self.admin_id)),
            self.handle_admin_action
        ))
        
        # Buton callback'leri
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("Bot handlers setup complete")
    
    async def start_polling(self):
        """
        Start bot polling
        """
        if not self.app:
            self.setup_handlers()
        
        logger.info("Starting bot polling...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
    
    async def stop_polling(self):
        """
        Stop bot polling
        """
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Premium bilgileri göster"""
        user = update.effective_user
        
        # Kullanıcı bilgisini al
        user_data = await self.db.users.find_one({"telegram_id": str(user.id)})
        
        if user_data and self.premium_helper.is_premium_active(user_data):
            # Zaten premium
            remaining = self.premium_helper.get_remaining_days(user_data)
            message = f"""
💎 **Premium Üyeliğiniz Aktif!**

✨ Aktif Özellikler:
• Sınırsız kupon
• Tüm seviyeler
• Detaylı AI analizi

⏰ Kalan Süre: **{remaining} gün**
📅 Bitiş: {user_data['premium_until'][:10]}

Premium süreniz bittiğinde yenileyebilirsiniz.
"""
        else:
            # Premium değil
            message = self.premium_helper.format_premium_info()
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def odemeyaptim_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ödeme yapıldı bildirimi"""
        user = update.effective_user
        
        # Kullanıcıyı dekont bekleme moduna al
        self.waiting_for_receipt[str(user.id)] = {
            "waiting": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = """
📸 **Ödeme Dekontunu Gönderin**

Lütfen ödeme dekontunuzun fotoğrafını buraya gönderin.

**Dekontta görünmeli:**
• Tutar: ₺99
• Alıcı: {name}
• Tarih

Dekontu bir sonraki mesaj olarak gönderin 👇
""".format(name=self.premium_helper.PAYMENT_INFO['papara_name'])
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fotoğraf (dekont) alındığında"""
        user = update.effective_user
        
        # Bu kullanıcı dekont bekliyor mu?
        if str(user.id) not in self.waiting_for_receipt:
            return
        
        # Dekontu kaydet
        photo = update.message.photo[-1]  # En yüksek çözünürlük
        caption = update.message.caption or ""
        
        payment_id = f"PAY{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Payment kaydı oluştur
        payment = {
            "id": payment_id,
            "user_telegram_id": str(user.id),
            "username": user.username,
            "first_name": user.first_name,
            "amount": 99,
            "payment_type": "premium_monthly",
            "status": "pending",
            "receipt_photo_id": photo.file_id,
            "receipt_caption": caption,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.db.payments.insert_one(payment)
        
        # Bekleme modundan çıkar
        del self.waiting_for_receipt[str(user.id)]
        
        # Kullanıcıya bilgi
        await update.message.reply_text(
            f"""
✅ **Ödemeniz Alındı!**

🔄 İşlem durumu: Onay bekliyor
⏱️ Tahmini süre: 2-24 saat

Onaylandığında bildirim alacaksınız.

Referans No: #{payment_id}
            """,
            parse_mode="Markdown"
        )
        
        # Admin'e bildirim gönder
        try:
            admin_message = f"""
🔔 **Yeni Ödeme!**

👤 Kullanıcı: @{user.username or 'N/A'} ({user.first_name})
💰 Tutar: ₺99
📋 Ref: #{payment_id}

/admin_payments - Bekleyen ödemeler
            """
            await context.bot.send_photo(
                chat_id=self.admin_id,
                photo=photo.file_id,
                caption=admin_message
            )
        except Exception as e:
            logger.error(f"Admin bildirimi gönderilemedi: {str(e)}")
    
    async def admin_payments_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Bekleyen ödemeler"""
        user = update.effective_user
        
        if str(user.id) != self.admin_id:
            await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok.")
            return
        
        # Bekleyen ödemeleri getir
        payments = await self.db.payments.find({"status": "pending"}).sort("created_at", -1).to_list(10)
        
        if not payments:
            await update.message.reply_text("✅ Bekleyen ödeme yok!")
            return
        
        message = f"📋 **Bekleyen Ödemeler** ({len(payments)})\n\n"
        
        for i, payment in enumerate(payments, 1):
            created = payment['created_at'][:16].replace('T', ' ')
            message += f"""{i}️⃣ **Ref:** #{payment['id']}
👤 @{payment.get('username', 'N/A')}
💰 ₺{payment['amount']}
📅 {created}

Onayla: /approve_{payment['id']}
Reddet: /reject_{payment['id']}

"""
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin onay/red işlemleri"""
        user = update.effective_user
        
        if str(user.id) != self.admin_id:
            return
        
        command = update.message.text
        
        if command.startswith('/approve_'):
            payment_id = command.replace('/approve_', '')
            await self._approve_payment(payment_id, update, context)
        elif command.startswith('/reject_'):
            payment_id = command.replace('/reject_', '')
            await self._reject_payment(payment_id, update, context)
    
    async def _approve_payment(self, payment_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ödemeyi onayla ve premium ver"""
        # Payment'ı bul
        payment = await self.db.payments.find_one({"id": payment_id})
        
        if not payment:
            await update.message.reply_text("❌ Ödeme bulunamadı!")
            return
        
        if payment['status'] != 'pending':
            await update.message.reply_text("❌ Bu ödeme zaten işlendi!")
            return
        
        # Kullanıcıya premium ver
        user_telegram_id = payment['user_telegram_id']
        premium_data = self.premium_helper.activate_premium(user_telegram_id, "monthly")
        
        await self.db.users.update_one(
            {"telegram_id": user_telegram_id},
            {"$set": premium_data}
        )
        
        # Payment'ı onayla
        await self.db.payments.update_one(
            {"id": payment_id},
            {"$set": {
                "status": "approved",
                "processed_at": datetime.utcnow().isoformat(),
                "processed_by": str(update.effective_user.id)
            }}
        )
        
        # Admin'e bilgi
        await update.message.reply_text(
            f"""
✅ **Ödeme Onaylandı!**

@{payment.get('username', 'N/A')} premium yapıldı!
Süre: 30 gün

Kullanıcıya bildirim gönderildi.
            """,
            parse_mode="Markdown"
        )
        
        # Kullanıcıya bildirim
        try:
            user_message = """
🎉 **Premium Üyeliğiniz Aktif!**

Premium özelliklere şimdi erişebilirsiniz:
• ✨ Sınırsız kupon
• ✨ Zor seviye aktif
• ✨ Detaylı AI analizi

⏰ Süre: 30 gün

/premium - Durumunuzu görün
/kupon - Hemen kupon oluşturun!
            """
            await context.bot.send_message(
                chat_id=user_telegram_id,
                text=user_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Kullanıcıya bildirim gönderilemedi: {str(e)}")
    
    async def _reject_payment(self, payment_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ödemeyi reddet"""
        payment = await self.db.payments.find_one({"id": payment_id})
        
        if not payment:
            await update.message.reply_text("❌ Ödeme bulunamadı!")
            return
        
        # Payment'ı reddet
        await self.db.payments.update_one(
            {"id": payment_id},
            {"$set": {
                "status": "rejected",
                "processed_at": datetime.utcnow().isoformat(),
                "processed_by": str(update.effective_user.id)
            }}
        )
        
        await update.message.reply_text(
            f"""
❌ **Ödeme Reddedildi**

Ref: #{payment_id}

Kullanıcıya bildirim gönder:
/notify_{payment['user_telegram_id']}_Ödemeniz reddedildi
            """,
            parse_mode="Markdown"
        )
