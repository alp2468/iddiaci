from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CouponGeneratorV2:
    def __init__(self):
        # Lig öncelikleri (skor: yüksek = öncelikli)
        self.league_priority = {
            # 5 Büyük Lig (Öncelikli)
            "İngiltere Premier Lig": 10,
            "İspanya La Liga": 10,
            "Almanya Bundesliga": 10,
            "İtalya Serie A": 10,
            "Fransa Ligue 1": 10,
            "Türkiye Süper Lig": 9,
            
            # Kupalar (Orta öncelik)
            "Türkiye Kupası": 7,
            "İngiltere FA Kupası": 8,
            "İspanya Copa del Rey": 8,
            "Almanya DFB Pokal": 8,
            "İtalya Coppa Italia": 8,
            "Fransa Coupe de France": 8,
            
            # Alt Ligler (Düşük öncelik)
            "Türkiye 1. Lig": 4,
            "İngiltere Championship": 5,
            "Hollanda Eredivisie": 6,
        }
    
    def _get_league_priority(self, league: str) -> int:
        """Lig öncelik skorunu döndür"""
        return self.league_priority.get(league, 3)  # Default: 3
    
    def generate_coupon(self, risk_level: str, matches: List[Dict], predictions: List[Dict]) -> Dict:
        try:
            enriched_predictions = self._enrich_predictions(matches, predictions)
            
            if risk_level == "banko":
                selected = self._generate_banko_coupon(enriched_predictions)
            elif risk_level == "orta":
                selected = self._generate_orta_coupon(enriched_predictions)
            elif risk_level == "zor":
                selected = self._generate_zor_coupon(enriched_predictions)
            else:
                selected = self._generate_banko_coupon(enriched_predictions)
            
            total_odds = 1.0
            for pred in selected:
                total_odds *= pred["predicted_odds"]
            
            coupon_matches = []
            for pred in selected:
                match = next((m for m in matches if m['id'] == pred['match_id']), None)
                if match:
                    coupon_matches.append({
                        "match_id": pred['match_id'],
                        "home_team": match['home_team'],
                        "away_team": match['away_team'],
                        "league": match['league'],
                        "bet_type": pred['bet_type'],
                        "recommended_option": pred['recommended_option'],
                        "odds": pred['predicted_odds'],
                        "confidence": pred['confidence'],
                        "analysis_summary": pred.get('ai_analysis', '')[:100]
                    })
            
            return {
                "id": str(__import__('uuid').uuid4()),
                "risk_level": risk_level,
                "matches": coupon_matches,
                "total_odds": round(total_odds, 2),
                "potential_return": round(total_odds * 100, 2),
                "match_count": len(coupon_matches),
                "status": "pending",
                "result_checked": False
            }
        except Exception as e:
            logger.error(f"Error generating coupon: {str(e)}")
            return {
                "risk_level": risk_level,
                "matches": [],
                "total_odds": 0.0,
                "potential_return": 0.0,
                "match_count": 0,
                "error": str(e)
            }
    
    def _enrich_predictions(self, matches: List[Dict], predictions: List[Dict]) -> List[Dict]:
        enriched = []
        for pred in predictions:
            match = next((m for m in matches if m['id'] == pred.get('match_id')), None)
            if match:
                league = match['league']
                league_priority = self._get_league_priority(league)
                
                enriched.append({
                    **pred,
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'league': league,
                    'league_priority': league_priority,
                    'adjusted_confidence': pred.get('confidence', 0) + (league_priority * 1.5)
                })
        return enriched
    
    def _generate_banko_coupon(self, predictions: List[Dict]) -> List[Dict]:
        # Adjusted confidence'a göre sırala (lig önceliği dahil)
        high_confidence = sorted(
            [p for p in predictions if p.get('adjusted_confidence', 0) > 60],
            key=lambda x: x.get('adjusted_confidence', 0),
            reverse=True
        )
        safe_predictions = [
            p for p in high_confidence
            if 1.3 <= p.get('predicted_odds', 0) <= 2.5
        ]
        if not safe_predictions:
            safe_predictions = high_confidence[:3]
        if not safe_predictions and predictions:
            safe_predictions = predictions[:3]
        
        # En fazla 1 alt lig maçı (öncelik < 7)
        selected = []
        low_league_count = 0
        for pred in safe_predictions:
            if pred.get('league_priority', 5) < 7:
                if low_league_count < 1:  # En fazla 1 alt lig
                    selected.append(pred)
                    low_league_count += 1
            else:
                selected.append(pred)
            
            if len(selected) >= 3:
                break
        
        if not selected:
            selected = safe_predictions[:3]
        
        total = 1.0
        for p in selected:
            total *= p.get('predicted_odds', 1.0)
        if total > 3.5 and len(selected) > 2:
            selected = selected[:2]
        return selected
    
    def _generate_orta_coupon(self, predictions: List[Dict]) -> List[Dict]:
        medium_confidence = sorted(
            [p for p in predictions if p.get('adjusted_confidence', 0) > 55],
            key=lambda x: x.get('adjusted_confidence', 0),
            reverse=True
        )
        medium_predictions = [
            p for p in medium_confidence
            if 1.5 <= p.get('predicted_odds', 0) <= 2.8
        ]
        if not medium_predictions:
            medium_predictions = medium_confidence
        if not medium_predictions and predictions:
            medium_predictions = predictions
        
        # En fazla 2 alt lig maçı
        selected = []
        low_league_count = 0
        for pred in medium_predictions:
            if pred.get('league_priority', 5) < 7:
                if low_league_count < 2:
                    selected.append(pred)
                    low_league_count += 1
            else:
                selected.append(pred)
            
            if len(selected) >= 6:
                break
        
        for count in range(4, 6):
            temp_selected = selected[:count]
            total = 1.0
            for p in temp_selected:
                total *= p.get('predicted_odds', 1.0)
            if 5.0 <= total <= 8.0:
                return temp_selected
        return selected[:4]
    
    def _generate_zor_coupon(self, predictions: List[Dict]) -> List[Dict]:
        high_odds = sorted(
            predictions,
            key=lambda x: x.get('predicted_odds', 0),
            reverse=True
        )
        for i in range(len(high_odds)):
            for j in range(i + 1, len(high_odds)):
                p1 = high_odds[i]
                p2 = high_odds[j]
                total = p1.get('predicted_odds', 1.0) * p2.get('predicted_odds', 1.0)
                if total >= 10:
                    return [p1, p2]
        sorted_by_confidence = sorted(
            predictions,
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        return sorted_by_confidence[:6]
