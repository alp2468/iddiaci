from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import asyncio
from contextlib import asynccontextmanager

# Import custom modules
from models import Match, Prediction, Coupon, User, BotActivity
from api_football_scraper import APIFootballScraper
from ai_analyzer_v2 import AIMatchAnalyzerV2
from coupon_generator_v2 import CouponGeneratorV2
from telegram_bot import BettingBot

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize components
scraper = APIFootballScraper()
analyzer = AIMatchAnalyzerV2()
coupon_gen = CouponGeneratorV2()
bot = BettingBot(db, scraper, analyzer, coupon_gen)

# Global bot task
bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global bot_task
    logger.info("Starting Telegram bot...")
    bot.setup_handlers()
    bot_task = asyncio.create_task(bot.start_polling())
    logger.info("Telegram bot started")
    
    # Premium kontrol gorevi (her 6 saatte bir)
    premium_task = asyncio.create_task(premium_check_loop())
    
    yield
    
    # Shutdown
    logger.info("Stopping Telegram bot...")
    premium_task.cancel()
    if bot_task:
        await bot.stop_polling()
        bot_task.cancel()
    client.close()
    logger.info("Shutdown complete")


async def premium_check_loop():
    """Suresi dolan premiumlari kaldir, hatirlatma gonder"""
    while True:
        try:
            await asyncio.sleep(6 * 3600)  # 6 saat
            await bot.check_expired_premiums()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Premium check error: {e}")

# Create the main app
app = FastAPI(lifespan=lifespan)

# Create API router
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {"message": "Betting Bot API", "status": "running"}

@api_router.get("/stats")
async def get_stats():
    """
    Get bot statistics for dashboard
    """
    try:
        total_users = await db.users.count_documents({})
        total_coupons = await db.coupons.count_documents({})
        total_matches = await db.matches.count_documents({})
        total_predictions = await db.predictions.count_documents({})
        
        # Get recent activities
        recent_activities = await db.bot_activities.find({}).sort("timestamp", -1).limit(10).to_list(10)
        
        # Remove _id from activities
        for activity in recent_activities:
            activity.pop('_id', None)
        
        return {
            "total_users": total_users,
            "total_coupons": total_coupons,
            "total_matches": total_matches,
            "total_predictions": total_predictions,
            "recent_activities": recent_activities
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/matches/today")
async def get_today_matches():
    """
    Get today's matches
    """
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        matches = await db.matches.find(
            {"match_date": today},
            {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        
        return {"matches": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Error getting matches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/coupons/recent")
async def get_recent_coupons():
    """
    Get recent coupons
    """
    try:
        coupons = await db.coupons.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
        
        return {"coupons": coupons, "count": len(coupons)}
    except Exception as e:
        logger.error(f"Error getting coupons: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/predictions/recent")
async def get_recent_predictions():
    """
    Get recent AI predictions
    """
    try:
        predictions = await db.predictions.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1).limit(30).to_list(30)
        
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scrape/trigger")
async def trigger_scrape():
    """
    Manually trigger match scraping
    """
    try:
        matches = await scraper.get_today_matches()
        
        # Save to database
        for match in matches:
            await db.matches.insert_one(match)
        
        return {"status": "success", "matches_scraped": len(matches)}
    except Exception as e:
        logger.error(f"Error scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/users")
async def get_users():
    """
    Get all users
    """
    try:
        users = await db.users.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
        return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/coupons/{coupon_id}/status")
async def update_coupon_status(coupon_id: str, status: str):
    """
    Update coupon status (won/lost)
    """
    try:
        from datetime import datetime
        
        result = await db.coupons.update_one(
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
            return {"status": "success", "message": "Kupon durumu güncellendi"}
        else:
            raise HTTPException(status_code=404, detail="Kupon bulunamadı")
    except Exception as e:
        logger.error(f"Error updating coupon: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/success-rates")
async def get_success_rates():
    """
    Get monthly success rates by risk level
    """
    try:
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        all_coupons = await db.coupons.find({
            "created_at": {"$gte": month_start.isoformat()}
        }).to_list(1000)
        
        stats = {
            'banko': {'total': 0, 'won': 0},
            'orta': {'total': 0, 'won': 0},
            'zor': {'total': 0, 'won': 0}
        }
        
        for coupon in all_coupons:
            risk = coupon.get('risk_level', 'banko')
            if risk in stats:
                stats[risk]['total'] += 1
                if coupon.get('status') == 'won':
                    stats[risk]['won'] += 1
        
        return {
            'banko': round((stats['banko']['won'] / stats['banko']['total'] * 100) if stats['banko']['total'] > 0 else 0),
            'orta': round((stats['orta']['won'] / stats['orta']['total'] * 100) if stats['orta']['total'] > 0 else 0),
            'zor': round((stats['zor']['won'] / stats['zor']['total'] * 100) if stats['zor']['total'] > 0 else 0),
            'total_coupons': len(all_coupons),
            'won_coupons': sum(1 for c in all_coupons if c.get('status') == 'won')
        }
    except Exception as e:
        logger.error(f"Error getting success rates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/dashboard")
async def admin_dashboard():
    """Admin dashboard verileri"""
    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        week_ago = (now - timedelta(days=7)).isoformat()
        today = now.strftime("%Y-%m-%d")

        total_users = await db.users.count_documents({})
        premium_users = await db.users.count_documents({"is_premium": True})
        total_coupons = await db.coupons.count_documents({})
        pending_payments = await db.payments.count_documents({"status": "pending"})
        approved_payments = await db.payments.count_documents({"status": "approved"})
        weekly_coupons = await db.coupons.count_documents({"created_at": {"$gte": week_ago}})
        today_coupons = await db.coupons.count_documents({"created_at": {"$regex": f"^{today}"}})
        won = await db.coupons.count_documents({"status": "won"})
        lost = await db.coupons.count_documents({"status": "lost"})
        resolved = won + lost
        win_rate = round((won / resolved * 100) if resolved > 0 else 0)
        revenue = approved_payments * 99

        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "total_coupons": total_coupons,
            "today_coupons": today_coupons,
            "weekly_coupons": weekly_coupons,
            "pending_payments": pending_payments,
            "approved_payments": approved_payments,
            "won": won,
            "lost": lost,
            "win_rate": win_rate,
            "revenue": revenue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/users")
async def admin_users():
    """Tum kullanicilari getir"""
    try:
        users = await db.users.find({}, {"_id": 0}).sort("last_interaction", -1).to_list(200)
        return {"users": users, "count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/payments")
async def admin_payments():
    """Tum odemeleri getir"""
    try:
        payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
        return {"payments": payments, "count": len(payments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PremiumAction(BaseModel):
    telegram_id: str
    action: str  # "activate" or "deactivate"


@api_router.post("/admin/premium")
async def admin_premium_action(data: PremiumAction):
    """Premium aktif/deaktif et"""
    try:
        from premium_helper import PremiumHelper
        ph = PremiumHelper()

        user = await db.users.find_one({"telegram_id": data.telegram_id})
        if not user:
            raise HTTPException(status_code=404, detail="Kullanici bulunamadi")

        if data.action == "activate":
            premium_data = ph.activate_premium(data.telegram_id, "monthly")
        else:
            premium_data = ph.deactivate_premium()

        await db.users.update_one(
            {"telegram_id": data.telegram_id},
            {"$set": premium_data}
        )
        return {"status": "success", "action": data.action, "telegram_id": data.telegram_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PaymentAction(BaseModel):
    payment_id: str
    action: str  # "approve" or "reject"


@api_router.post("/admin/payment-action")
async def admin_payment_action(data: PaymentAction):
    """Odeme onayla/reddet"""
    try:
        from datetime import datetime
        from premium_helper import PremiumHelper

        payment = await db.payments.find_one({"id": data.payment_id})
        if not payment:
            raise HTTPException(status_code=404, detail="Odeme bulunamadi")

        if data.action == "approve":
            ph = PremiumHelper()
            premium_data = ph.activate_premium(payment['user_telegram_id'], "monthly")
            await db.users.update_one(
                {"telegram_id": payment['user_telegram_id']},
                {"$set": premium_data}
            )
            await db.payments.update_one(
                {"id": data.payment_id},
                {"$set": {"status": "approved", "processed_at": datetime.utcnow().isoformat()}}
            )
        else:
            await db.payments.update_one(
                {"id": data.payment_id},
                {"$set": {"status": "rejected", "processed_at": datetime.utcnow().isoformat()}}
            )

        return {"status": "success", "action": data.action}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)