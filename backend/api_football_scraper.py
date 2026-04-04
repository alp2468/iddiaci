import httpx
from typing import List, Dict
import asyncio
import logging
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Lig ve Kupa ID'leri
LEAGUES_AND_CUPS = {
    # Türkiye
    203: "Türkiye Süper Lig",
    204: "Türkiye 1. Lig",
    205: "Türkiye Kupası",
    
    # İngiltere
    39: "İngiltere Premier Lig",
    40: "İngiltere Championship",
    2: "İngiltere FA Kupası",
    48: "İngiltere EFL Kupası",
    
    # İspanya
    140: "İspanya La Liga",
    143: "İspanya Copa del Rey",
    
    # Almanya
    78: "Almanya Bundesliga",
    81: "Almanya DFB Pokal",
    
    # İtalya
    135: "İtalya Serie A",
    137: "İtalya Coppa Italia",
    
    # Fransa
    61: "Fransa Ligue 1",
    66: "Fransa Coupe de France",
    
    # Hollanda
    88: "Hollanda Eredivisie",
    94: "Hollanda KNVB Beker"
}

class APIFootballScraper:
    def __init__(self):
        self.api_key = os.environ.get('API_FOOTBALL_KEY')
        self.base_url = "https://v3.football.api-sports.io"
        
    async def get_today_matches(self) -> List[Dict]:
        """
        Bugünkü tüm maçları API-Football'dan çek
        """
        today = datetime.now().strftime("%Y-%m-%d")
        all_matches = []
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                logger.info(f"Fetching matches for {today}...")
                
                # Bugünün tüm maçlarını çek
                url = f"{self.base_url}/fixtures"
                params = {"date": today}
                
                response = await client.get(url, params=params)
                data = response.json()
                
                if data.get('response'):
                    fixtures = data['response']
                    logger.info(f"Total fixtures today: {len(fixtures)}")
                    
                    # Sadece bizim ligleri filtrele
                    for fixture in fixtures:
                        league_id = fixture['league']['id']
                        if league_id in LEAGUES_AND_CUPS:
                            match = await self._parse_fixture(fixture, client, headers)
                            if match:
                                all_matches.append(match)
                    
                    logger.info(f"Filtered matches from our leagues: {len(all_matches)}")
                
            except Exception as e:
                logger.error(f"Error fetching matches: {str(e)}")
        
        # Eğer bugün maç yoksa yarının maçlarını çek
        if not all_matches:
            logger.info("No matches today, fetching tomorrow's matches...")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            all_matches = await self._fetch_matches_for_date(tomorrow, headers)
        
        logger.info(f"Total real matches: {len(all_matches)}")
        return all_matches
    
    async def _fetch_matches_for_date(self, date: str, headers: Dict) -> List[Dict]:
        """
        Belirli bir tarih için maçları çek
        """
        matches = []
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                url = f"{self.base_url}/fixtures"
                params = {"date": date}
                
                response = await client.get(url, params=params)
                data = response.json()
                
                if data.get('response'):
                    for fixture in data['response']:
                        league_id = fixture['league']['id']
                        if league_id in LEAGUES_AND_CUPS:
                            match = await self._parse_fixture(fixture, client, headers)
                            if match:
                                matches.append(match)
            except Exception as e:
                logger.error(f"Error: {str(e)}")
        
        return matches
    
    async def _parse_fixture(self, fixture: Dict, client, headers) -> Dict:
        """
        Fixture'ı parse et
        """
        try:
            match_id = str(uuid.uuid4())
            fixture_id = fixture['fixture']['id']
            league_id = fixture['league']['id']
            
            match_data = {
                "id": match_id,
                "api_match_id": str(fixture_id),
                "league": LEAGUES_AND_CUPS[league_id],
                "league_country": fixture['league']['country'],
                "home_team": fixture['teams']['home']['name'],
                "away_team": fixture['teams']['away']['name'],
                "match_date": fixture['fixture']['date'][:10],
                "match_time": fixture['fixture']['date'][11:16],
                "venue": fixture['fixture']['venue']['name'] if fixture['fixture'].get('venue') else None,
                "betting_options": []
            }
            
            # Bahis oranlarını çek
            try:
                odds_url = f"{self.base_url}/odds"
                odds_params = {"fixture": fixture_id}
                odds_response = await client.get(odds_url, params=odds_params)
                odds_data = odds_response.json()
                
                if odds_data.get('response') and len(odds_data['response']) > 0:
                    bookmakers = odds_data['response'][0].get('bookmakers', [])
                    if bookmakers:
                        bets = bookmakers[0].get('bets', [])
                        match_data['betting_options'] = self._extract_betting_options(bets)
                
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Could not fetch odds for {fixture_id}: {str(e)}")
            
            # Eğer oran yoksa default ekle
            if not match_data['betting_options']:
                match_data['betting_options'] = self._generate_default_odds()
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing fixture: {str(e)}")
            return None
    
    def _extract_betting_options(self, bets: List[Dict]) -> List[Dict]:
        """
        Bahis seçeneklerini extract et
        """
        options = []
        
        for bet in bets:
            bet_name = bet.get('name', '')
            values = bet.get('values', [])
            
            # Match Winner (1X2)
            if 'Match Winner' in bet_name or 'Home/Away' in bet_name:
                for value in values:
                    option_name = value.get('value')
                    odds = float(value.get('odd', 0))
                    
                    if 'Home' in option_name:
                        options.append({"bet_type": "1X2", "option": "1", "odds": odds, "bookmaker": None})
                    elif 'Draw' in option_name:
                        options.append({"bet_type": "1X2", "option": "X", "odds": odds, "bookmaker": None})
                    elif 'Away' in option_name:
                        options.append({"bet_type": "1X2", "option": "2", "odds": odds, "bookmaker": None})
            
            # Over/Under
            elif 'Goals Over/Under' in bet_name:
                for value in values:
                    option_name = value.get('value', '')
                    odds = float(value.get('odd', 0))
                    
                    if 'Over' in option_name:
                        options.append({"bet_type": "over_under", "option": "over_2.5", "odds": odds, "bookmaker": None})
                    elif 'Under' in option_name:
                        options.append({"bet_type": "over_under", "option": "under_2.5", "odds": odds, "bookmaker": None})
            
            # BTTS
            elif 'Both Teams Score' in bet_name:
                for value in values:
                    option_name = value.get('value', '')
                    odds = float(value.get('odd', 0))
                    
                    if 'Yes' in option_name:
                        options.append({"bet_type": "btts", "option": "yes", "odds": odds, "bookmaker": None})
                    elif 'No' in option_name:
                        options.append({"bet_type": "btts", "option": "no", "odds": odds, "bookmaker": None})
        
        return options if options else self._generate_default_odds()
    
    def _generate_default_odds(self) -> List[Dict]:
        """
        Default oranlar
        """
        import random
        return [
            {"bet_type": "1X2", "option": "1", "odds": round(random.uniform(1.6, 2.8), 2), "bookmaker": None},
            {"bet_type": "1X2", "option": "X", "odds": round(random.uniform(3.0, 3.8), 2), "bookmaker": None},
            {"bet_type": "1X2", "option": "2", "odds": round(random.uniform(1.8, 3.2), 2), "bookmaker": None},
            {"bet_type": "over_under", "option": "over_2.5", "odds": round(random.uniform(1.7, 2.1), 2), "bookmaker": None},
            {"bet_type": "over_under", "option": "under_2.5", "odds": round(random.uniform(1.7, 2.1), 2), "bookmaker": None},
            {"bet_type": "btts", "option": "yes", "odds": round(random.uniform(1.8, 2.2), 2), "bookmaker": None},
            {"bet_type": "btts", "option": "no", "odds": round(random.uniform(1.7, 2.0), 2), "bookmaker": None}
        ]
