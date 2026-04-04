import httpx
from typing import List, Dict
import asyncio
import logging
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SPORTS_MAP = {
    "Turkey Super League": "soccer_turkey_super_league",
    "England Premier League": "soccer_epl",
    "England League 1": "soccer_england_league1",
    "Spain La Liga": "soccer_spain_la_liga",
    "Germany Bundesliga": "soccer_germany_bundesliga",
    "Italy Serie A": "soccer_italy_serie_a",
    "France Ligue 1": "soccer_france_ligue_one",
    "Netherlands Eredivisie": "soccer_netherlands_eredivisie"
}

class TheOddsAPIScraper:
    def __init__(self):
        self.api_key = os.environ.get('THE_ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        
    async def get_today_matches(self) -> List[Dict]:
        """
        The Odds API'den bugünkü maçları çek
        """
        all_matches = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for league_name, sport_key in SPORTS_MAP.items():
                try:
                    logger.info(f"Fetching {league_name}...")
                    
                    url = f"{self.base_url}/sports/{sport_key}/odds/"
                    params = {
                        "apiKey": self.api_key,
                        "regions": "eu",
                        "markets": "h2h",
                        "oddsFormat": "decimal"
                    }
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for game in data:
                            match = self._parse_odds_api_game(game, league_name)
                            if match:
                                all_matches.append(match)
                    else:
                        logger.warning(f"{league_name}: Status {response.status_code}")
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error fetching {league_name}: {str(e)}")
                    continue
        
        logger.info(f"Total real matches fetched: {len(all_matches)}")
        return all_matches
    
    def _parse_odds_api_game(self, game: Dict, league: str) -> Dict:
        """
        The Odds API game verisini parse et
        """
        try:
            match_id = str(uuid.uuid4())
            
            # Teams
            home_team = game.get('home_team', 'Unknown')
            away_team = game.get('away_team', 'Unknown')
            
            # Date
            commence_time = game.get('commence_time', '')
            match_date = commence_time[:10] if commence_time else datetime.now().strftime("%Y-%m-%d")
            match_time = commence_time[11:16] if len(commence_time) > 16 else ""
            
            # Betting options
            betting_options = []
            bookmakers = game.get('bookmakers', [])
            
            if bookmakers:
                # İlk bookmaker'ı al
                bookmaker = bookmakers[0]
                markets = bookmaker.get('markets', [])
                
                for market in markets:
                    market_key = market.get('key')
                    outcomes = market.get('outcomes', [])
                    
                    # H2H (1X2 - Maç Sonucu)
                    if market_key == 'h2h':
                        for outcome in outcomes:
                            name = outcome.get('name')
                            price = outcome.get('price', 1.0)
                            
                            if name == home_team:
                                betting_options.append({
                                    "bet_type": "1X2",
                                    "option": "1",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                            elif name == away_team:
                                betting_options.append({
                                    "bet_type": "1X2",
                                    "option": "2",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                            elif name.lower() == 'draw':
                                betting_options.append({
                                    "bet_type": "1X2",
                                    "option": "X",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                    
                    # Totals (Over/Under - Alt/Üst)
                    elif market_key == 'totals':
                        point = market.get('point', 2.5)
                        for outcome in outcomes:
                            name = outcome.get('name')
                            price = outcome.get('price', 1.0)
                            
                            if name.lower() == 'over':
                                betting_options.append({
                                    "bet_type": "over_under",
                                    "option": f"over_{point}",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                            elif name.lower() == 'under':
                                betting_options.append({
                                    "bet_type": "over_under",
                                    "option": f"under_{point}",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                    
                    # BTTS (Both Teams To Score - Karşılıklı Gol)
                    elif market_key == 'btts':
                        for outcome in outcomes:
                            name = outcome.get('name')
                            price = outcome.get('price', 1.0)
                            
                            if name.lower() == 'yes':
                                betting_options.append({
                                    "bet_type": "btts",
                                    "option": "yes",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
                            elif name.lower() == 'no':
                                betting_options.append({
                                    "bet_type": "btts",
                                    "option": "no",
                                    "odds": float(price),
                                    "bookmaker": bookmaker.get('title')
                                })
            
            return {
                "id": match_id,
                "api_match_id": game.get('id', match_id),
                "league": league,
                "league_country": "Türkiye" if "Turkey" in league else "Yurtdışı",
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
            logger.error(f"Error parsing game: {str(e)}")
            return None
