"""
Match Cache Manager - Performans için maç verilerini cache'ler
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
        self.cache_duration_hours = 6  # 6 saatte bir yenile
    
    async def get_cached_matches(self) -> List[Dict]:
        """
        Cache'den maçları getir, yoksa veya eskiyse yenile
        """
        try:
            # Son cache zamanını kontrol et
            cache_info = await self.db.cache_info.find_one({"type": "matches"})
            
            needs_refresh = True
            if cache_info:
                last_update = datetime.fromisoformat(cache_info['last_update'])
                age = datetime.utcnow() - last_update
                
                if age < timedelta(hours=self.cache_duration_hours):
                    needs_refresh = False
                    logger.info(f"Using cached matches (age: {age})")
            
            if needs_refresh:
                logger.info("Cache expired or missing, fetching fresh matches...")
                await self.refresh_cache()
            
            # Cache'den maçları getir
            matches = await self.db.matches.find({}).to_list(1000)
            
            # _id'leri temizle
            for match in matches:
                match.pop('_id', None)
            
            logger.info(f"Returning {len(matches)} cached matches")
            return matches
            
        except Exception as e:
            logger.error(f"Cache error: {str(e)}")
            # Hata durumunda direkt API'den çek
            return await self.scraper.get_today_matches()
    
    async def refresh_cache(self):
        """
        Cache'i yenile - API'den maçları çek ve kaydet
        """
        try:
            logger.info("Refreshing match cache...")
            
            # API'den maçları çek
            fresh_matches = await self.scraper.get_today_matches()
            
            if not fresh_matches:
                logger.warning("No matches fetched, keeping old cache")
                return
            
            # Eski maçları temizle
            await self.db.matches.delete_many({})
            
            # Yeni maçları kaydet
            if fresh_matches:
                await self.db.matches.insert_many(fresh_matches)
            
            # Cache bilgisini güncelle
            await self.db.cache_info.update_one(
                {"type": "matches"},
                {
                    "$set": {
                        "type": "matches",
                        "last_update": datetime.utcnow().isoformat(),
                        "match_count": len(fresh_matches)
                    }
                },
                upsert=True
            )
            
            logger.info(f"Cache refreshed with {len(fresh_matches)} matches")
            
        except Exception as e:
            logger.error(f"Error refreshing cache: {str(e)}")
    
    async def force_refresh(self):
        """
        Manuel cache yenileme (admin komutu için)
        """
        await self.refresh_cache()
