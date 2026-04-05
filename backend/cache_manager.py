"""
Match Cache Manager - Her gun saat 10:00'da API'den mac ceker, gun boyunca cache kullanir
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class MatchCacheManager:
    def __init__(self, db: AsyncIOMotorDatabase, scraper):
        self.db = db
        self.scraper = scraper
    
    async def get_cached_matches(self) -> List[Dict]:
        """Cache'den maclari getir. Bugunun verisi yoksa bos doner (saat 10'da cekilecek)"""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cache_info = await self.db.cache_info.find_one({"type": "matches"})
            
            # Bugunun verisi var mi?
            if cache_info and cache_info.get('cache_date') == today:
                matches = await self.db.matches.find({}).to_list(1000)
                for match in matches:
                    match.pop('_id', None)
                logger.info(f"Using today's cache: {len(matches)} matches")
                return matches
            
            # Bugunun verisi yok - eski veri varsa onu dondur (saat 10'a kadar)
            matches = await self.db.matches.find({}).to_list(1000)
            if matches:
                for match in matches:
                    match.pop('_id', None)
                logger.info(f"Using old cache: {len(matches)} matches (waiting for daily refresh)")
                return matches
            
            # Hic veri yok - ilk kez cek
            logger.info("No cache at all, doing initial fetch...")
            await self.refresh_cache()
            matches = await self.db.matches.find({}).to_list(1000)
            for match in matches:
                match.pop('_id', None)
            return matches
            
        except Exception as e:
            logger.error(f"Cache error: {str(e)}")
            return []
    
    async def refresh_cache(self):
        """API'den maclari cek ve cache'e kaydet"""
        try:
            logger.info("Refreshing match cache from API...")
            today = datetime.utcnow().strftime("%Y-%m-%d")
            
            fresh_matches = await self.scraper.get_today_matches()
            
            if not fresh_matches:
                logger.warning("No matches fetched from API, keeping old cache")
                return False
            
            # Eski maclari temizle
            await self.db.matches.delete_many({})
            
            # Yeni maclari kaydet
            await self.db.matches.insert_many(fresh_matches)
            
            # Cache bilgisini guncelle
            await self.db.cache_info.update_one(
                {"type": "matches"},
                {
                    "$set": {
                        "type": "matches",
                        "last_update": datetime.utcnow().isoformat(),
                        "cache_date": today,
                        "match_count": len(fresh_matches)
                    }
                },
                upsert=True
            )
            
            logger.info(f"Cache refreshed: {len(fresh_matches)} matches for {today}")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing cache: {str(e)}")
            return False
    
    async def force_refresh(self):
        """Manuel cache yenileme (admin komutu icin)"""
        return await self.refresh_cache()
