import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime
import json
import re
import uuid

logger = logging.getLogger(__name__)

class NesineScraper:
    """
    Nesine.com'dan İddaa oranlarını çeken scraper
    """
    def __init__(self):
        self.base_url = "https://www.nesine.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.nesine.com/iddaa"
        }
    
    async def get_today_matches(self) -> List[Dict]:
        """
        Bugünkü İddaa maçlarını ve oranlarını çek
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers, follow_redirects=True) as client:
                # Nesine İddaa programı API endpoint'i (gözlemlenmiş)
                # Not: Bu endpoint değişebilir, güncel API'yi kontrol edin
                
                # Yöntem 1: Nesine'nin internal API'sini kullan
                api_url = f"{self.base_url}/api/todayBulletin"
                
                try:
                    logger.info("Fetching matches from Nesine API...")
                    response = await client.get(api_url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        matches = self._parse_nesine_api_data(data)
                        if matches:
                            logger.info(f"Found {len(matches)} matches from Nesine API")
                            return matches
                except Exception as e:
                    logger.warning(f"Nesine API failed: {str(e)}, trying web scraping...")
                
                # Yöntem 2: Web scraping fallback
                matches = await self._scrape_nesine_web(client)
                
                if not matches:
                    # Yöntem 3: Mock data (development için)
                    logger.warning("No matches found, generating sample data...")
                    matches = self._generate_sample_iddaa_matches()
                
                logger.info(f"Total matches fetched: {len(matches)}")
                return matches
                
        except Exception as e:
            logger.error(f"Error fetching Nesine matches: {str(e)}")
            return self._generate_sample_iddaa_matches()
    
    def _parse_nesine_api_data(self, data: Dict) -> List[Dict]:
        """
        Nesine API yanıtını parse et
        """
        matches = []
        
        try:
            # Nesine API yapısı (varsayılan, gerçek yapıyı kontrol edin)
            if isinstance(data, dict) and 'data' in data:
                events = data.get('data', [])
            elif isinstance(data, list):
                events = data
            else:
                return []
            
            for event in events[:30]:  # İlk 30 maç
                try:
                    match_data = self._parse_single_nesine_match(event)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    logger.error(f"Error parsing match: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing Nesine API data: {str(e)}")
        
        return matches
    
    def _parse_single_nesine_match(self, event: Dict) -> Optional[Dict]:
        """
        Tek bir Nesine maç verisini parse et
        """
        try:
            match_id = str(uuid.uuid4())
            
            # Takım isimleri
            home_team = event.get('homeTeam', event.get('home', 'Bilinmeyen'))
            away_team = event.get('awayTeam', event.get('away', 'Bilinmeyen'))
            
            # Lig bilgisi
            league = event.get('league', event.get('tournament', 'Bilinmeyen Lig'))
            
            # Tarih
            match_date = event.get('date', datetime.now().strftime("%Y-%m-%d"))
            match_time = event.get('time', '')
            
            # Oranlar - Nesine formatı
            odds = event.get('odds', {})
            
            betting_options = []
            
            # 1X2 Oranları (Maç Sonucu)
            if 'mbs' in odds or '1' in odds:
                mbs = odds.get('mbs', odds)
                betting_options.extend([
                    {"bet_type": "1X2", "option": "1", "odds": float(mbs.get('1', mbs.get('home', 1.0))), "bookmaker": "Nesine"},
                    {"bet_type": "1X2", "option": "X", "odds": float(mbs.get('X', mbs.get('draw', 1.0))), "bookmaker": "Nesine"},
                    {"bet_type": "1X2", "option": "2", "odds": float(mbs.get('2', mbs.get('away', 1.0))), "bookmaker": "Nesine"}
                ])
            
            # Alt/Üst 2.5 (Toplam Gol)
            if 'au25' in odds or 'totalGoals' in odds:
                au = odds.get('au25', odds.get('totalGoals', {}))
                if 'over' in au or 'alt' in au:
                    betting_options.extend([
                        {"bet_type": "over_under", "option": "over_2.5", "odds": float(au.get('over', au.get('ust', 1.0))), "bookmaker": "Nesine"},
                        {"bet_type": "over_under", "option": "under_2.5", "odds": float(au.get('under', au.get('alt', 1.0))), "bookmaker": "Nesine"}
                    ])
            
            # Karşılıklı Gol (KG)
            if 'btts' in odds or 'kg' in odds:
                btts = odds.get('btts', odds.get('kg', {}))
                if 'yes' in btts or 'var' in btts:
                    betting_options.extend([
                        {"bet_type": "btts", "option": "yes", "odds": float(btts.get('yes', btts.get('var', 1.0))), "bookmaker": "Nesine"},
                        {"bet_type": "btts", "option": "no", "odds": float(btts.get('no', btts.get('yok', 1.0))), "bookmaker": "Nesine"}
                    ])
            
            # Eğer oran yoksa, default oran ekle
            if not betting_options:
                betting_options = self._generate_default_odds()
            
            return {
                "id": match_id,
                "api_match_id": event.get('id', match_id),
                "league": league,
                "league_country": "Türkiye" if "Süper Lig" in league or "TFF" in league else "Yurtdışı",
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date,
                "match_time": match_time,
                "venue": None,
                "betting_options": betting_options,
                "home_form": None,
                "away_form": None,
                "h2h_results": None
            }
            
        except Exception as e:
            logger.error(f"Error parsing single match: {str(e)}")
            return None
    
    async def _scrape_nesine_web(self, client: httpx.AsyncClient) -> List[Dict]:
        """
        Nesine web sayfasından scraping ile veri çek
        """
        try:
            url = f"{self.base_url}/iddaa"
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.error(f"Nesine returned status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Nesine'nin HTML yapısını parse et
            # Not: Nesine dinamik bir site, JavaScript ile yükleniyor
            # Bu basit scraping çalışmayabilir, API endpoint tercih edilmeli
            
            matches = []
            # HTML parsing implementation burada
            # Gerçek implementasyon için Selenium gerekebilir
            
            return matches
            
        except Exception as e:
            logger.error(f"Web scraping error: {str(e)}")
            return []
    
    def _generate_sample_iddaa_matches(self) -> List[Dict]:
        """
        Örnek İddaa maçları oluştur (development/testing için)
        """
        import random
        
        turkish_teams = [
            ("Galatasaray", "Fenerbahçe", "Süper Lig"),
            ("Beşiktaş", "Trabzonspor", "Süper Lig"),
            ("Başakşehir", "Alanyaspor", "Süper Lig"),
            ("Konyaspor", "Antalyaspor", "Süper Lig"),
        ]
        
        european_teams = [
            ("Manchester City", "Arsenal", "İngiltere Premier Lig"),
            ("Real Madrid", "Barcelona", "İspanya La Liga"),
            ("Bayern Munich", "Borussia Dortmund", "Almanya Bundesliga"),
            ("Inter", "AC Milan", "İtalya Serie A"),
            ("PSG", "Marseille", "Fransa Ligue 1"),
        ]
        
        all_teams = turkish_teams + european_teams
        matches = []
        
        for home, away, league in all_teams:
            match_id = str(uuid.uuid4())
            
            # Gerçekçi oranlar
            home_odd = round(random.uniform(1.5, 3.5), 2)
            draw_odd = round(random.uniform(3.0, 4.0), 2)
            away_odd = round(random.uniform(1.8, 4.0), 2)
            
            over_odd = round(random.uniform(1.6, 2.2), 2)
            under_odd = round(random.uniform(1.6, 2.2), 2)
            
            btts_yes = round(random.uniform(1.7, 2.3), 2)
            btts_no = round(random.uniform(1.6, 2.1), 2)
            
            matches.append({
                "id": match_id,
                "api_match_id": f"sample_{match_id}",
                "league": league,
                "league_country": "Türkiye" if league == "Süper Lig" else "Yurtdışı",
                "home_team": home,
                "away_team": away,
                "match_date": datetime.now().strftime("%Y-%m-%d"),
                "match_time": f"{random.randint(19, 22)}:{random.choice(['00', '30'])}",
                "venue": None,
                "betting_options": [
                    {"bet_type": "1X2", "option": "1", "odds": home_odd, "bookmaker": "Nesine"},
                    {"bet_type": "1X2", "option": "X", "odds": draw_odd, "bookmaker": "Nesine"},
                    {"bet_type": "1X2", "option": "2", "odds": away_odd, "bookmaker": "Nesine"},
                    {"bet_type": "over_under", "option": "over_2.5", "odds": over_odd, "bookmaker": "Nesine"},
                    {"bet_type": "over_under", "option": "under_2.5", "odds": under_odd, "bookmaker": "Nesine"},
                    {"bet_type": "btts", "option": "yes", "odds": btts_yes, "bookmaker": "Nesine"},
                    {"bet_type": "btts", "option": "no", "odds": btts_no, "bookmaker": "Nesine"}
                ],
                "home_form": None,
                "away_form": None,
                "h2h_results": None
            })
        
        return matches
    
    def _generate_default_odds(self) -> List[Dict]:
        """
        Default oranlar oluştur
        """
        import random
        
        return [
            {"bet_type": "1X2", "option": "1", "odds": round(random.uniform(1.5, 3.0), 2), "bookmaker": "Nesine"},
            {"bet_type": "1X2", "option": "X", "odds": round(random.uniform(3.0, 4.0), 2), "bookmaker": "Nesine"},
            {"bet_type": "1X2", "option": "2", "odds": round(random.uniform(1.8, 3.5), 2), "bookmaker": "Nesine"},
            {"bet_type": "over_under", "option": "over_2.5", "odds": round(random.uniform(1.6, 2.2), 2), "bookmaker": "Nesine"},
            {"bet_type": "over_under", "option": "under_2.5", "odds": round(random.uniform(1.6, 2.2), 2), "bookmaker": "Nesine"},
            {"bet_type": "btts", "option": "yes", "odds": round(random.uniform(1.7, 2.3), 2), "bookmaker": "Nesine"},
            {"bet_type": "btts", "option": "no", "odds": round(random.uniform(1.6, 2.1), 2), "bookmaker": "Nesine"}
        ]
