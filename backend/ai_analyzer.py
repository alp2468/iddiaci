from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from typing import Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class AIMatchAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.models = [
            ("openai", "gpt-5.2"),
            ("anthropic", "claude-sonnet-4-5-20250929")
        ]
    
    async def analyze_match(self, match: Dict) -> Dict:
        """
        Analyze a single match using multiple AI models
        """
        try:
            # Prepare match context
            match_context = self._prepare_match_context(match)
            
            # Get predictions from multiple AI models
            predictions = await self._get_multi_model_predictions(match_context)
            
            # Combine predictions
            combined_analysis = self._combine_predictions(predictions, match)
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing match: {str(e)}")
            return {
                "match_id": match.get("id", "unknown"),
                "confidence": 0.0,
                "recommended_bet": "1",
                "predicted_odds": match.get("odds_1", 2.0),
                "ai_analysis": f"Analysis failed: {str(e)}",
                "ai_model": "error"
            }
    
    def _prepare_match_context(self, match: Dict) -> str:
        """
        Prepare match data for AI analysis
        """
        home_form_str = "".join(match.get("home_form", []))
        away_form_str = "".join(match.get("away_form", []))
        h2h_str = ", ".join(match.get("h2h_results", []))
        
        context = f"""
Maç Analizi:

Lig: {match.get('league', 'Unknown')}
Ev Sahibi: {match.get('home_team', 'Unknown')}
Deplasman: {match.get('away_team', 'Unknown')}
Tarih: {match.get('match_date', 'Unknown')}

Bahis Oranları:
- Ev Sahibi Galibiyet (1): {match.get('odds_1', 'N/A')}
- Beraberlik (X): {match.get('odds_x', 'N/A')}
- Deplasman Galibiyet (2): {match.get('odds_2', 'N/A')}

Ev Sahibi Formu (Son 5 Maç): {home_form_str}
Deplasman Formu (Son 5 Maç): {away_form_str}

Karşılıklı Geçmiş Maçlar: {h2h_str}

Bu maçı analiz et ve en güvenli bahis tahminini yap. Sadece şu formatla cevap ver:
TAHMİN: [1/X/2]
GÜVEN: [0-100 arası sayı]
ANALİZ: [Kısa analiz]
"""
        return context
    
    async def _get_multi_model_predictions(self, context: str) -> List[Dict]:
        """
        Get predictions from multiple AI models
        """
        predictions = []
        
        for provider, model in self.models:
            try:
                chat = LlmChat(
                    api_key=self.api_key,
                    session_id=f"match_analysis_{provider}",
                    system_message="Sen bir futbol analisti ve bahis uzmanısın. Maç verilerini analiz edip en mantıklı tahmini yapıyorsun."
                ).with_model(provider, model)
                
                message = UserMessage(text=context)
                response = await chat.send_message(message)
                
                predictions.append({
                    "provider": provider,
                    "model": model,
                    "response": response
                })
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error with {provider} {model}: {str(e)}")
                continue
        
        return predictions
    
    def _combine_predictions(self, predictions: List[Dict], match: Dict) -> Dict:
        """
        Combine predictions from multiple AI models
        """
        if not predictions:
            return {
                "match_id": match.get("id", "unknown"),
                "confidence": 50.0,
                "recommended_bet": "1",
                "predicted_odds": match.get("odds_1", 2.0),
                "ai_analysis": "No AI predictions available",
                "ai_model": "fallback"
            }
        
        # Parse predictions
        parsed_predictions = []
        for pred in predictions:
            parsed = self._parse_ai_response(pred["response"])
            if parsed:
                parsed["model"] = f"{pred['provider']}-{pred['model']}"
                parsed_predictions.append(parsed)
        
        if not parsed_predictions:
            return {
                "match_id": match.get("id", "unknown"),
                "confidence": 50.0,
                "recommended_bet": "1",
                "predicted_odds": match.get("odds_1", 2.0),
                "ai_analysis": predictions[0]["response"][:200],
                "ai_model": f"{predictions[0]['provider']}-{predictions[0]['model']}"
            }
        
        # Combine by averaging confidence and taking majority vote
        bet_votes = {}
        total_confidence = 0
        
        for pred in parsed_predictions:
            bet = pred["bet"]
            bet_votes[bet] = bet_votes.get(bet, 0) + 1
            total_confidence += pred["confidence"]
        
        recommended_bet = max(bet_votes, key=bet_votes.get)
        avg_confidence = total_confidence / len(parsed_predictions)
        
        # Get odds for recommended bet
        odds_map = {
            "1": match.get("odds_1", 2.0),
            "X": match.get("odds_x", 3.0),
            "2": match.get("odds_2", 2.0)
        }
        
        # Combine analysis texts
        analysis_text = " | ".join([p["analysis"] for p in parsed_predictions if p.get("analysis")])
        
        return {
            "match_id": match.get("id", "unknown"),
            "confidence": round(avg_confidence, 2),
            "recommended_bet": recommended_bet,
            "predicted_odds": odds_map.get(recommended_bet, 2.0),
            "ai_analysis": analysis_text[:500],
            "ai_model": "multi-model",
            "votes": bet_votes
        }
    
    def _parse_ai_response(self, response: str) -> Dict:
        """
        Parse AI response to extract prediction, confidence, and analysis
        """
        try:
            lines = response.strip().split('\n')
            result = {}
            
            for line in lines:
                if 'TAHMİN:' in line or 'TAHMIN:' in line:
                    bet = line.split(':')[1].strip()
                    if bet in ['1', 'X', '2']:
                        result['bet'] = bet
                elif 'GÜVEN:' in line or 'GUVEN:' in line:
                    conf_str = line.split(':')[1].strip()
                    try:
                        result['confidence'] = float(''.join(filter(str.isdigit, conf_str)))
                    except:
                        result['confidence'] = 50.0
                elif 'ANALİZ:' in line or 'ANALIZ:' in line:
                    result['analysis'] = line.split(':')[1].strip()
            
            if 'bet' not in result:
                # Try to find bet in response
                if '1' in response and 'kazanır' in response.lower():
                    result['bet'] = '1'
                elif '2' in response and 'kazanır' in response.lower():
                    result['bet'] = '2'
                elif 'berabere' in response.lower():
                    result['bet'] = 'X'
                else:
                    result['bet'] = '1'
            
            if 'confidence' not in result:
                result['confidence'] = 60.0
            
            if 'analysis' not in result:
                result['analysis'] = response[:200]
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None