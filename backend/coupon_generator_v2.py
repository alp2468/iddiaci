from typing import List, Dict
import logging
import random

logger = logging.getLogger(__name__)

class CouponGeneratorV2:
    def __init__(self):
        # Lig öncelikleri - buyuk ligler agirlikli oncelikli
        self.league_priority = {
            # Buyuk 5 Lig + Turkiye (EN YUKSEK ONCELIK)
            "İngiltere Premier Lig": 20,
            "İspanya La Liga": 20,
            "Almanya Bundesliga": 20,
            "Fransa Ligue 1": 20,
            "Türkiye Süper Lig": 18,
            "İtalya Serie A": 20,
            
            # Buyuk Kupalar
            "Türkiye Kupası": 12,
            "İngiltere FA Kupası": 14,
            "İspanya Copa del Rey": 14,
            "Almanya DFB Pokal": 14,
            "İtalya Coppa Italia": 14,
            "Fransa Coupe de France": 14,
            "UEFA Şampiyonlar Ligi": 20,
            "UEFA Avrupa Ligi": 16,
            "UEFA Konferans Ligi": 14,
            
            # Alt Ligler (DUSUK ONCELIK)
            "Türkiye 1. Lig": 5,
            "İngiltere Championship": 6,
            "Hollanda Eredivisie": 8,
            "Portekiz Liga": 8,
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
                    'adjusted_confidence': pred.get('confidence', 0) + (league_priority * 3)
                })
        return enriched
    
    def _weighted_sample(self, items: List[Dict], count: int, weight_key: str = 'adjusted_confidence') -> List[Dict]:
        """Agirlikli rastgele secim - yuksek guvenli olanlar daha fazla sans alir ama garanti degil"""
        if len(items) <= count:
            return items[:]
        
        weights = []
        for item in items:
            w = max(item.get(weight_key, 50), 1)
            weights.append(w)
        
        selected = []
        remaining = list(range(len(items)))
        remaining_weights = weights[:]
        
        for _ in range(count):
            if not remaining:
                break
            total = sum(remaining_weights)
            if total <= 0:
                idx_in_remaining = random.randint(0, len(remaining) - 1)
            else:
                r = random.uniform(0, total)
                cumulative = 0
                idx_in_remaining = 0
                for j, w in enumerate(remaining_weights):
                    cumulative += w
                    if cumulative >= r:
                        idx_in_remaining = j
                        break
            
            selected.append(items[remaining[idx_in_remaining]])
            remaining.pop(idx_in_remaining)
            remaining_weights.pop(idx_in_remaining)
        
        return selected
    
    def _generate_banko_coupon(self, predictions: List[Dict]) -> List[Dict]:
        high_confidence = [p for p in predictions if p.get('adjusted_confidence', 0) > 60]
        safe_predictions = [
            p for p in high_confidence
            if 1.3 <= p.get('predicted_odds', 0) <= 2.5
        ]
        if not safe_predictions:
            safe_predictions = high_confidence[:] if high_confidence else predictions[:]
        
        # Lig filtresi: buyuk lig oncelikli, alt lig en fazla 1
        top_league = [p for p in safe_predictions if p.get('league_priority', 3) >= 12]
        low_league = [p for p in safe_predictions if p.get('league_priority', 3) < 12]
        
        # Agirlikli rastgele sec
        target_count = random.choice([2, 3])
        selected = self._weighted_sample(top_league, target_count)
        
        # Eksikse alt ligden 1 tane ekle
        if len(selected) < target_count and low_league:
            selected.extend(self._weighted_sample(low_league, 1))
        
        # Hala bossa fallback
        if not selected:
            selected = self._weighted_sample(safe_predictions, target_count)
        if not selected:
            selected = self._weighted_sample(predictions, 2)
        
        # Toplam oran kontrolu
        total = 1.0
        for p in selected:
            total *= p.get('predicted_odds', 1.0)
        if total > 3.5 and len(selected) > 2:
            selected = selected[:2]
        return selected
    
    def _generate_orta_coupon(self, predictions: List[Dict]) -> List[Dict]:
        medium_confidence = [p for p in predictions if p.get('adjusted_confidence', 0) > 55]
        medium_predictions = [
            p for p in medium_confidence
            if 1.5 <= p.get('predicted_odds', 0) <= 2.8
        ]
        if not medium_predictions:
            medium_predictions = medium_confidence[:] if medium_confidence else predictions[:]
        
        # Lig filtresi: buyuk lig oncelikli
        top_league = [p for p in medium_predictions if p.get('league_priority', 3) >= 12]
        low_league = [p for p in medium_predictions if p.get('league_priority', 3) < 12]
        
        target_count = random.choice([3, 4, 5])
        selected = self._weighted_sample(top_league, target_count)
        
        # Eksikse alt ligden max 2 ekle
        remaining_need = target_count - len(selected)
        if remaining_need > 0 and low_league:
            selected.extend(self._weighted_sample(low_league, min(2, remaining_need)))
        
        if not selected:
            selected = self._weighted_sample(medium_predictions, target_count)
        if not selected:
            selected = self._weighted_sample(predictions, 4)
        
        # Oran hedefi 5-8 arasi: fazla yuksekse kirp
        total = 1.0
        for p in selected:
            total *= p.get('predicted_odds', 1.0)
        if total > 8.0 and len(selected) > 3:
            selected = selected[:3]
        
        return selected
    
    def _generate_zor_coupon(self, predictions: List[Dict]) -> List[Dict]:
        # Tum gecerli yuksek oran ciftlerini bul
        valid_pairs = []
        for i in range(len(predictions)):
            for j in range(i + 1, len(predictions)):
                p1 = predictions[i]
                p2 = predictions[j]
                total = p1.get('predicted_odds', 1.0) * p2.get('predicted_odds', 1.0)
                if total >= 10:
                    valid_pairs.append((p1, p2, total))
        
        if valid_pairs:
            # Rastgele bir cift sec
            pair = random.choice(valid_pairs)
            return [pair[0], pair[1]]
        
        # Cift bulunamazsa: rastgele 5-7 mac sec (karma strateji)
        target = random.choice([5, 6, 7])
        selected = self._weighted_sample(predictions, target, weight_key='predicted_odds')
        return selected if selected else predictions[:6]
