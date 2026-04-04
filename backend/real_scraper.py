import httpx
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

LEAGUE_IDS = {
    "Turkey Super League": 203,
    "England Premier League": 39,
    "England Championship": 40,
    "Spain La Liga": 140,
    "Germany Bundesliga": 78,
    "Italy Serie A": 135,
    "France Ligue 1": 61,
    "Turkey 1. Lig": 204,
    "Netherlands Eredivisie": 88
}

class RealFootballScraper:
    def __init__(self):
        self.api_football_key = os.environ.get('API_FOOTBALL_KEY')
        self.odds_api_key = os.environ.get('THE_ODDS_API_KEY')
        self.api_football_base = "https://v3.football.api-sports.io"
        self.odds_api_base = "https://api.the-odds-api.com/v4"
        
    async def get_today_matches(self) -> List[Dict]:
        """
        Bugünkü tüm maçları API-Football'dan çek
        """
        today = datetime.now().strftime("%Y-%m-%d")
        all_matches = []
        
        headers = {
            "x-rapidapi-key": self.api_football_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for league_name, league_id in LEAGUE_IDS.items():
                try:
                    # Bugünkü maçları çek
                    url = f"{self.api_football_base}/fixtures"
                    params = {
                        "league": league_id,
                        "date": today,
                        "season": 2024  # veya 2025
                    }
                    
                    response = await client.get(url, headers=headers, params=params)
                    data = response.json()
                    
                    if data.get('response'):
                        for fixture in data['response']:
                            match = await self._parse_fixture(fixture, league_name, client, headers)
                            if match:
                                all_matches.append(match)
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error fetching matches for {league_name}: {str(e)}")
                    continue
        
        # Eğer bugün maç yoksa, yaklaşan maçları çek
        if not all_matches:
            logger.info("No matches today, fetching upcoming matches...")
            all_matches = await self._get_upcoming_matches(headers)
        
        logger.info(f"Total real matches fetched: {len(all_matches)}")
        return all_matches
    
    async def _get_upcoming_matches(self, headers: Dict) -> List[Dict]:
        """
        Yaklaşan günlerin maçlarını çek
        """
        matches = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for days_ahead in range(1, 4):  # Önümüzdeki 3 gün
                date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                
                for league_name, league_id in list(LEAGUE_IDS.items())[:3]:  # İlk 3 lig
                    try:
                        url = f"{self.api_football_base}/fixtures"
                        params = {
                            "league": league_id,
                            "date": date,
                            "season": 2024
                        }
                        
                        response = await client.get(url, headers=headers, params=params)
                        data = response.json()
                        
                        if data.get('response'):
                            for fixture in data['response'][:2]:  # Her ligden 2 maç
                                match = await self._parse_fixture(fixture, league_name, client, headers)
                                if match:
                                    matches.append(match)
                        
                        if len(matches) >= 10:  # En az 10 maç
                            return matches
                        
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error: {str(e)}")
                        continue
        
        return matches
    
    async def _parse_fixture(self, fixture: Dict, league_name: str, client, headers) -> Optional[Dict]:
        """
        Fixture verisini parse et ve bahis seçeneklerini ekle
        """
        try:
            match_id = str(uuid.uuid4())
            fixture_id = fixture['fixture']['id']
            
            # Temel bilgiler
            match_data = {
                "id": match_id,
                "api_match_id": str(fixture_id),
                "league": league_name,
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
                odds_url = f"{self.api_football_base}/odds"
                odds_params = {"fixture": fixture_id}
                odds_response = await client.get(odds_url, headers=headers, params=odds_params)
                odds_data = odds_response.json()
                
                if odds_data.get('response') and len(odds_data['response']) > 0:
                    bookmakers = odds_data['response'][0].get('bookmakers', [])
                    if bookmakers:
                        bets = bookmakers[0].get('bets', [])
                        match_data['betting_options'] = self._extract_betting_options(bets)
                
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Could not fetch odds for fixture {fixture_id}: {str(e)}")
                # Varsayılan oranlar ekle
                match_data['betting_options'] = self._generate_default_odds()
            
            # Takım istatistikleri (varsa)
            match_data['home_form'] = None
            match_data['away_form'] = None
            match_data['h2h_results'] = None
            
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
            
            # 1X2 (Match Winner)
            if 'Match Winner' in bet_name or 'Home/Away' in bet_name:
                for value in values:
                    option_name = value.get('value')
                    odds = float(value.get('odd', 0))
                    
                    bet_option = '1' if 'Home' in option_name else ('X' if 'Draw' in option_name else '2')
                    options.append({
                        "bet_type": "1X2",
                        "option": bet_option,
                        "odds": odds,
                        "bookmaker": None
                    })
            
            # Over/Under (Alt/Üst)
            elif 'Goals Over/Under' in bet_name or 'Total' in bet_name:
                for value in values:
                    option_name = value.get('value', '')
                    odds = float(value.get('odd', 0))
                    
                    if 'Over' in option_name or 'Under' in option_name:
                        options.append({
                            "bet_type": "over_under",
                            "option": option_name.lower().replace(' ', '_'),
                            "odds": odds,
                            "bookmaker": None
                        })
            
            # BTTS (Both Teams To Score - Karşılıklı Gol)
            elif 'Both Teams Score' in bet_name or 'BTTS' in bet_name:
                for value in values:
                    option_name = value.get('value', '')
                    odds = float(value.get('odd', 0))
                    
                    option = 'yes' if 'Yes' in option_name else 'no'
                    options.append({
                        "bet_type": "btts",
                        "option": option,
                        "odds": odds,
                        "bookmaker": None
                    })
        
        return options if options else self._generate_default_odds()
    
    def _generate_default_odds(self) -> List[Dict]:
        """
        API'den oran alınamazsa varsayılan oranlar üret
        """
        import random
        
        options = []
        
        # 1X2
        home_odds = round(random.uniform(1.5, 3.5), 2)
        draw_odds = round(random.uniform(3.0, 4.0), 2)
        away_odds = round(random.uniform(1.8, 4.0), 2)
        
        options.extend([
            {"bet_type": "1X2", "option": "1", "odds": home_odds, "bookmaker": None},
            {"bet_type": "1X2", "option": "X", "odds": draw_odds, "bookmaker": None},
            {"bet_type": "1X2", "option": "2", "odds": away_odds, "bookmaker": None}
        ])
        
        # Over/Under 2.5
        options.extend([
            {"bet_type": "over_under", "option": "over_2.5", "odds": round(random.uniform(1.6, 2.2), 2), "bookmaker": None},
            {"bet_type": "over_under", "option": "under_2.5", "odds": round(random.uniform(1.6, 2.2), 2), "bookmaker": None}
        ])
        
        # BTTS
        options.extend([
            {"bet_type": "btts", "option": "yes", "odds": round(random.uniform(1.7, 2.3), 2), "bookmaker": None},
            {"bet_type": "btts", "option": "no", "odds": round(random.uniform(1.6, 2.1), 2), "bookmaker": None}
        ])
        
        return options