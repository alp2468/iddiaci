import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

LEAGUES_CONFIG = {
    "Turkey Super League": "super-lig",
    "England Premier League": "premier-league",
    "England Championship": "championship",
    "Spain La Liga": "laliga",
    "Germany Bundesliga": "bundesliga",
    "Italy Serie A": "serie-a",
    "France Ligue 1": "ligue-1",
    "Turkey 1. Lig": "1-lig",
    "Netherlands Eredivisie": "eredivisie"
}

class SofaScoreScraper:
    def __init__(self):
        self.base_url = "https://www.sofascore.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def get_today_matches(self, league: str) -> List[Dict]:
        """
        Scrape today's matches for a specific league
        Note: This is a simplified version. Real scraping would need more sophisticated parsing.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                logger.info(f"Scraping matches for {league}...")
                
                # For demo purposes, returning mock data
                # In production, you would parse actual HTML from SofaScore
                mock_matches = await self._get_mock_matches(league)
                return mock_matches
                
        except Exception as e:
            logger.error(f"Error scraping {league}: {str(e)}")
            return []
    
    async def _get_mock_matches(self, league: str) -> List[Dict]:
        """
        Generate mock match data for testing
        In production, replace with actual web scraping logic
        """
        import random
        
        teams_by_league = {
            "Turkey Super League": [
                "Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor",
                "Başakşehir", "Alanyaspor", "Konyaspor", "Antalyaspor"
            ],
            "England Premier League": [
                "Manchester City", "Arsenal", "Liverpool", "Chelsea",
                "Manchester United", "Tottenham", "Newcastle", "Brighton"
            ],
            "Spain La Liga": [
                "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
                "Real Sociedad", "Villarreal", "Real Betis", "Valencia"
            ],
            "Germany Bundesliga": [
                "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
                "Union Berlin", "Freiburg", "Eintracht Frankfurt", "Wolfsburg"
            ],
            "Italy Serie A": [
                "Inter Milan", "AC Milan", "Juventus", "Napoli",
                "Roma", "Lazio", "Atalanta", "Fiorentina"
            ],
            "France Ligue 1": [
                "PSG", "Marseille", "Monaco", "Lyon",
                "Lille", "Nice", "Lens", "Rennes"
            ],
            "England Championship": [
                "Leeds", "Sheffield United", "Burnley", "Middlesbrough",
                "West Brom", "Norwich", "Sunderland", "Coventry"
            ],
            "Turkey 1. Lig": [
                "Eyüpspor", "Ankaragücü", "Göztepe", "Sakaryaspor",
                "Boluspor", "Erzurumspor", "Giresunspor", "Bandırmaspor"
            ],
            "Netherlands Eredivisie": [
                "Ajax", "PSV", "Feyenoord", "AZ Alkmaar",
                "FC Twente", "FC Utrecht", "Sparta Rotterdam", "Heerenveen"
            ]
        }
        
        teams = teams_by_league.get(league, [])
        if len(teams) < 4:
            return []
        
        # Generate 2-4 random matches
        num_matches = random.randint(2, 4)
        matches = []
        
        used_teams = set()
        for _ in range(num_matches):
            available_teams = [t for t in teams if t not in used_teams]
            if len(available_teams) < 2:
                break
                
            home_team = random.choice(available_teams)
            available_teams.remove(home_team)
            away_team = random.choice(available_teams)
            
            used_teams.add(home_team)
            used_teams.add(away_team)
            
            # Generate realistic odds
            home_strength = random.uniform(1.5, 4.0)
            draw_odds = random.uniform(3.0, 4.5)
            away_strength = random.uniform(1.5, 4.0)
            
            # Generate form (last 5 matches)
            home_form = [random.choice(['W', 'D', 'L']) for _ in range(5)]
            away_form = [random.choice(['W', 'D', 'L']) for _ in range(5)]
            
            # Generate H2H results
            h2h = [f"{random.choice([home_team, away_team, 'Draw'])}" for _ in range(3)]
            
            matches.append({
                "id": str(uuid.uuid4()),
                "league": league,
                "home_team": home_team,
                "away_team": away_team,
                "match_date": datetime.now().strftime("%Y-%m-%d"),
                "odds_1": round(home_strength, 2),
                "odds_x": round(draw_odds, 2),
                "odds_2": round(away_strength, 2),
                "home_form": home_form,
                "away_form": away_form,
                "h2h_results": h2h
            })
        
        return matches
    
    async def scrape_all_leagues(self) -> List[Dict]:
        """
        Scrape matches from all configured leagues
        """
        all_matches = []
        
        for league_name in LEAGUES_CONFIG.keys():
            matches = await self.get_today_matches(league_name)
            all_matches.extend(matches)
            await asyncio.sleep(1)  # Rate limiting
        
        logger.info(f"Total matches scraped: {len(all_matches)}")
        return all_matches