from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CouponGeneratorV2:
    def __init__(self):
        pass
    
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
                enriched.append({
                    **pred,
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'league': match['league']
                })
        return enriched
    
    def _generate_banko_coupon(self, predictions: List[Dict]) -> List[Dict]:
        high_confidence = sorted(
            [p for p in predictions if p.get('confidence', 0) > 70],
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        safe_predictions = [
            p for p in high_confidence
            if 1.3 <= p.get('predicted_odds', 0) <= 2.0
        ]
        if not safe_predictions:
            safe_predictions = high_confidence[:3]
        selected = safe_predictions[:3]
        total = 1.0
        for p in selected:
            total *= p.get('predicted_odds', 1.0)
        if total > 3.5 and len(selected) > 2:
            selected = selected[:2]
        return selected
    
    def _generate_orta_coupon(self, predictions: List[Dict]) -> List[Dict]:
        medium_confidence = sorted(
            [p for p in predictions if p.get('confidence', 0) > 60],
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        medium_predictions = [
            p for p in medium_confidence
            if 1.5 <= p.get('predicted_odds', 0) <= 2.8
        ]
        if not medium_predictions:
            medium_predictions = medium_confidence
        for count in range(4, 6):
            selected = medium_predictions[:count]
            total = 1.0
            for p in selected:
                total *= p.get('predicted_odds', 1.0)
            if 5.0 <= total <= 8.0:
                return selected
        return medium_predictions[:4]
    
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
