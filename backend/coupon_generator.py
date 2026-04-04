from typing import List, Dict
import logging
from models import Match, Prediction

logger = logging.getLogger(__name__)

class CouponGenerator:
    def __init__(self):
        pass
    
    def generate_coupon(self, risk_level: str, matches: List[Dict], predictions: List[Dict]) -> Dict:
        """
        Generate betting coupon based on risk level
        
        Risk levels:
        - banko: 2-3 matches, total odds 2-3
        - orta: 3-5 matches, total odds 5-7
        - zor: 2 high-odds matches (min 10 odds) OR 5-8 matches
        """
        try:
            # Match predictions with matches
            enriched_matches = self._enrich_matches_with_predictions(matches, predictions)
            
            # Filter based on risk level
            if risk_level == "banko":
                selected = self._generate_banko_coupon(enriched_matches)
            elif risk_level == "orta":
                selected = self._generate_orta_coupon(enriched_matches)
            elif risk_level == "zor":
                selected = self._generate_zor_coupon(enriched_matches)
            else:
                selected = self._generate_banko_coupon(enriched_matches)
            
            # Calculate total odds
            total_odds = 1.0
            for match in selected:
                total_odds *= match["predicted_odds"]
            
            return {
                "risk_level": risk_level,
                "matches": selected,
                "total_odds": round(total_odds, 2),
                "match_count": len(selected)
            }
            
        except Exception as e:
            logger.error(f"Error generating coupon: {str(e)}")
            return {
                "risk_level": risk_level,
                "matches": [],
                "total_odds": 0.0,
                "match_count": 0,
                "error": str(e)
            }
    
    def _enrich_matches_with_predictions(self, matches: List[Dict], predictions: List[Dict]) -> List[Dict]:
        """
        Combine match data with AI predictions
        """
        enriched = []
        
        for match in matches:
            match_id = match.get("id")
            prediction = next((p for p in predictions if p.get("match_id") == match_id), None)
            
            if prediction:
                enriched.append({
                    **match,
                    "confidence": prediction.get("confidence", 0),
                    "recommended_bet": prediction.get("recommended_bet", "1"),
                    "predicted_odds": prediction.get("predicted_odds", 2.0),
                    "ai_analysis": prediction.get("ai_analysis", "")
                })
        
        return enriched
    
    def _generate_banko_coupon(self, matches: List[Dict]) -> List[Dict]:
        """
        Banko: 2-3 matches with low odds (1.5-2.5), high confidence
        """
        # Sort by confidence (descending) and odds (ascending)
        sorted_matches = sorted(
            matches,
            key=lambda x: (x.get("confidence", 0), -x.get("predicted_odds", 999)),
            reverse=True
        )
        
        # Filter matches with odds between 1.3 and 2.5
        banko_matches = [
            m for m in sorted_matches
            if 1.3 <= m.get("predicted_odds", 0) <= 2.5
        ]
        
        # Select 2-3 matches
        selected = banko_matches[:3]
        
        # Ensure total odds are around 2-3
        if len(selected) > 2:
            total_odds = 1.0
            for m in selected:
                total_odds *= m["predicted_odds"]
            
            # If odds are too high, reduce to 2 matches
            if total_odds > 3.5:
                selected = selected[:2]
        
        return selected
    
    def _generate_orta_coupon(self, matches: List[Dict]) -> List[Dict]:
        """
        Orta: 3-5 matches with medium odds (1.5-2.5), total odds 5-7
        """
        # Sort by confidence
        sorted_matches = sorted(
            matches,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        # Filter matches with reasonable odds
        medium_matches = [
            m for m in sorted_matches
            if 1.4 <= m.get("predicted_odds", 0) <= 2.8
        ]
        
        # Try different combinations to get total odds between 5-7
        for count in range(3, 6):
            selected = medium_matches[:count]
            total_odds = 1.0
            for m in selected:
                total_odds *= m["predicted_odds"]
            
            if 5.0 <= total_odds <= 8.0:
                return selected
        
        # Default to 4 matches
        return medium_matches[:4]
    
    def _generate_zor_coupon(self, matches: List[Dict]) -> List[Dict]:
        """
        Zor: 2 high-odds matches (min 10 total) OR 5-8 matches
        """
        # Sort by odds (descending)
        sorted_by_odds = sorted(
            matches,
            key=lambda x: x.get("predicted_odds", 0),
            reverse=True
        )
        
        # Try to find 2 high-odds matches with total >= 10
        for i in range(len(sorted_by_odds)):
            for j in range(i + 1, len(sorted_by_odds)):
                match1 = sorted_by_odds[i]
                match2 = sorted_by_odds[j]
                total = match1["predicted_odds"] * match2["predicted_odds"]
                
                if total >= 10:
                    return [match1, match2]
        
        # Otherwise, return 5-8 matches with decent confidence
        sorted_by_confidence = sorted(
            matches,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        return sorted_by_confidence[:6]