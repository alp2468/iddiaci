from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import logging
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logger = logging.getLogger(__name__)

class BettingBot:
    def __init__(self, db, scraper, analyzer, coupon_gen):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.db = db
        self.scraper = scraper
        self.analyzer = analyzer
        self.coupon_gen = coupon_gen
        self.app = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command
        """
        user = update.effective_user
        
        # Save user to database
        await self.db.users.update_one(
            {"telegram_id": str(user.id)},
            {
                "$set": {
                    "telegram_id": str(user.id),
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "last_interaction": datetime.utcnow().isoformat()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            upsert=True
        )
        
        welcome_message = f"""
🎯 **Hoş Geldiniz {user.first_name}!**

Ben futbol maçlarını analiz edip sizin için bahis kuponları oluşturan bir botum.

📊 **Özellikler:**
• 9 farklı ligden maç analizi
• Yapay zeka destekli tahminler
• 3 farklı risk seviyesi

🎮 **Komutlar:**
/kupon - Yeni kupon oluştur
/help - Yardım menüsü

Hemen başlamak için /kupon komutunu kullanın!
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
        
        # Aylık başarı oranlarını hesapla
        success_rates = await self._calculate_monthly_success_rates()
        
        keyboard = [
            [InlineKeyboardButton(
                f"🟢 Banko (2-3 Oran) | Bu Ay: %{success_rates['banko']}", 
                callback_data="risk_banko"
            )],
            [InlineKeyboardButton(
                f"🟡 Orta (5-7 Oran) | Bu Ay: %{success_rates['orta']}", 
                callback_data="risk_orta"
            )],
            [InlineKeyboardButton(
                f"🔴 Zor (+10 Oran) | Bu Ay: %{success_rates['zor']}", 
                callback_data="risk_zor"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
🎯 **Kupon Oluştur**

Lütfen risk seviyesini seçin:

🟢 **Banko:** Düşük riskli, 2-3 maç | Bu ay %{success_rates['banko']} başarı
🟡 **Orta:** Orta riskli, 3-5 maç | Bu ay %{success_rates['orta']} başarı
🔴 **Zor:** Yüksek riskli, yüksek oran | Bu ay %{success_rates['zor']} başarı

📊 **Toplam Kupon:** {success_rates['total_coupons']} | ✅ Kazanan: {success_rates['won_coupons']}
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
            
            # Show processing message
            await query.edit_message_text(
                "⏳ Maçlar analiz ediliyor... Lütfen bekleyin..."
            )
            
            try:
                # Generate coupon
                coupon = await self._generate_coupon(risk_level, str(user.id))
                
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
                
                await query.edit_message_text(
                    coupon_message, 
                    parse_mode="Markdown",
                    reply_markup=status_markup
                )
                
            except Exception as e:
                logger.error(f"Error generating coupon: {str(e)}")
                await query.edit_message_text(
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
📚 **Yardım Menüsü**

**Komutlar:**
/start - Botu başlat
/kupon - Yeni kupon oluştur
/kuponlarim - Kuponlarımı görüntüle
/help - Bu yardım menüsünü göster

**Risk Seviyeleri:**

🟢 **Banko (2-3 Oran)**
• 2-3 maç
• Yüksek güvenilirlik
• Düşük kazanç potansiyeli

🟡 **Orta (5-7 Oran)**
• 3-5 maç
• Orta güvenilirlik
• Orta kazanç potansiyeli

🔴 **Zor (+10 Oran)**
• 2 yüksek oranlı maç veya 5-8 maç
• Düşük güvenilirlik
• Yüksek kazanç potansiyeli

**Analiz Edilen Ligler:**
• Türkiye Süper Lig
• İngiltere Premier Lig
• İngiltere Championship
• İspanya La Liga
• Almanya Bundesliga
• İtalya Serie A
• Fransa Ligue 1
• Türkiye 1. Lig
• Hollanda Eredivisie

💡 **Not:** Tüm tahminler yapay zeka destekli analizlere dayanır. Bahis oynarken dikkatli olun!
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
            
            message = "📋 **Son Kuponlarınız:**\\n\\n"
            
            for i, coupon in enumerate(coupons, 1):
                risk_emoji = {"banko": "🟢", "orta": "🟡", "zor": "🔴"}.get(coupon['risk_level'], "⚪")
                status_emoji = {
                    "won": "✅ KAZANDI",
                    "lost": "❌ TUTMADI",
                    "pending": "⏳ Bekliyor"
                }.get(coupon.get('status', 'pending'), "⏳")
                
                created = coupon.get('created_at', '')[:10]
                
                message += f"{i}. {risk_emoji} {coupon['risk_level'].upper()} | Oran: {coupon['total_odds']}\\n"
                message += f"   {status_emoji} | {created}\\n"
                message += f"   {coupon['match_count']} maç | {coupon.get('potential_return', 0):.0f} TL kazanç\\n\\n"
            
            message += "\\n💡 **İpucu:** Kupon sonuçlarını manuel olarak kontrol edebilirsiniz."
            
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
    
    async def _generate_coupon(self, risk_level: str, user_id: str) -> Dict:
        """
        Generate coupon by scraping matches, analyzing, and creating coupon
        """
        # Scrape today's matches (real data)
        matches = await self.scraper.get_today_matches()
        
        if not matches:
            raise Exception("Bugün için maç bulunamadı.")
        
        # Save matches to database
        for match in matches:
            await self.db.matches.insert_one(match)
        
        # Analyze matches with AI (her maç için birden fazla tahmin)
        all_predictions = []
        for match in matches[:15]:  # İlk 15 maç
            predictions = await self.analyzer.analyze_match(match)
            for pred in predictions:
                await self.db.predictions.insert_one(pred)
                all_predictions.append(pred)
        
        # Generate coupon
        coupon = self.coupon_gen.generate_coupon(risk_level, matches, all_predictions)
        coupon["user_telegram_id"] = user_id
        
        # Save coupon
        await self.db.coupons.insert_one(coupon)
        
        # Log activity
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
        
        message = f"""
{emoji} **{name} KUPON**

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
    
    def setup_handlers(self):
        """
        Setup bot handlers
        """
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("kupon", self.kupon_command))
        self.app.add_handler(CommandHandler("kuponlarim", self.my_coupons_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
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