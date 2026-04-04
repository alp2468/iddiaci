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
from real_scraper import RealFootballScraper
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
scraper = RealFootballScraper()
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
    
    yield
    
    # Shutdown
    logger.info("Stopping Telegram bot...")
    if bot_task:
        await bot.stop_polling()
        bot_task.cancel()
    client.close()
    logger.info("Shutdown complete")

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