from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from typing import Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class AIMatchAnalyzerV2:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.models = [
            ("openai", "gpt-5.2"),
            ("anthropic", "claude-sonnet-4-5-20250929")
        ]
    
    async def analyze_match(self, match: Dict) -> List[Dict]:
        try:
            match_context = self._prepare_match_context(match)
            predictions = await self._get_multi_model_predictions(match_context, match)
            parsed_predictions = []
            for pred in predictions:
                parsed = self._parse_ai_predictions(pred, match)
                if parsed:
                    parsed_predictions.extend(parsed)
            
            # Eğer hiç prediction yoksa fallback kullan
            if not parsed_predictions:
                logger.warning("No predictions parsed, using fallback")
                parsed_predictions = self._generate_fallback_prediction(match)
            
            return parsed_predictions
        except Exception as e:
            logger.error(f"Error analyzing match: {str(e)}")
            return self._generate_fallback_prediction(match)
    
    def _prepare_match_context(self, match: Dict) -> str:
        betting_opts_text = "\n".join([
            f"  - {opt['bet_type']}: {opt['option']} @ {opt['odds']}"
            for opt in match.get('betting_options', [])[:10]
        ])
        
        context = f"""
Maç Analizi Yapılacak:

Lig: {match.get('league', 'Bilinmiyor')}
Ev Sahibi: {match.get('home_team', 'Bilinmiyor')}
Deplasman: {match.get('away_team', 'Bilinmiyor')}
Tarih: {match.get('match_date', 'Bilinmiyor')} {match.get('match_time', '')}

Mevcut Bahis Seçenekleri:
{betting_opts_text}

Bu maç için EN İYİ 2 bahis tahmini yap.
Her tahmin için şu formatı kullan:
BAHİS_TÜRÜ: [1X2/over_under/btts]
TAHMİN: [örn: 1, over_2.5, yes]
ORAN: [bahis oranı]
GÜVEN: [0-100]
ANALİZ: [Kısa analiz]
---
"""
        return context
    
    async def _get_multi_model_predictions(self, context: str, match: Dict) -> List[Dict]:
        predictions = []
        for provider, model in self.models[:1]:
            try:
                chat = LlmChat(
                    api_key=self.api_key,
                    session_id=f"match_analysis_{provider}",
                    system_message="Sen profesyonel bir futbol analisti ve bahis uzmanısın."
                ).with_model(provider, model)
                
                message = UserMessage(text=context)
                response = await chat.send_message(message)
                
                logger.info(f"AI Response type: {type(response)}, value: {response}")
                
                # Response None ise veya boşsa skip
                if not response:
                    logger.warning(f"Empty response from {provider}")
                    continue
                
                predictions.append({
                    "provider": provider,
                    "model": model,
                    "response": str(response),  # String'e çevir
                    "match": match
                })
                
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error with {provider} {model}: {str(e)}")
                continue
        return predictions
    
    def _parse_ai_predictions(self, pred_data: Dict, match: Dict) -> List[Dict]:
        response = pred_data["response"]
        predictions = []
        sections = response.split('---')
        
        for section in sections:
            if not section.strip():
                continue
            try:
                pred = {}
                lines = section.strip().split('\n')
                
                for line in lines:
                    if 'BAHİS' in line or 'BAHIS' in line:
                        bet_type = line.split(':')[1].strip()
                        pred['bet_type'] = bet_type
                    elif 'TAHMİN' in line or 'TAHMIN' in line:
                        option = line.split(':')[1].strip()
                        pred['option'] = option
                    elif 'ORAN' in line:
                        try:
                            odds = float(line.split(':')[1].strip())
                            pred['odds'] = odds
                        except Exception:
                            pred['odds'] = 2.0
                    elif 'GÜV' in line or 'GUVEN' in line:
                        try:
                            conf_str = line.split(':')[1].strip()
                            conf = float(''.join(filter(str.isdigit, conf_str)))
                            pred['confidence'] = conf
                        except Exception:
                            pred['confidence'] = 60.0
                    elif 'ANALİZ' in line or 'ANALIZ' in line:
                        analysis = line.split(':')[1].strip()
                        pred['analysis'] = analysis
                
                if pred.get('bet_type') and pred.get('option'):
                    if 'odds' not in pred:
                        pred['odds'] = self._find_odds_for_option(
                            match, pred['bet_type'], pred['option']
                        )
                    
                    predictions.append({
                        "match_id": match['id'],
                        "bet_type": pred['bet_type'],
                        "recommended_option": pred['option'],
                        "predicted_odds": pred.get('odds', 2.0),
                        "confidence": pred.get('confidence', 65.0),
                        "ai_analysis": pred.get('analysis', ''),
                        "ai_model": f"{pred_data['provider']}-{pred_data['model']}"
                    })
            except Exception as e:
                logger.error(f"Error parsing section: {str(e)}")
                continue
        
        if not predictions:
            predictions = self._generate_fallback_prediction(match)
        return predictions
    
    def _find_odds_for_option(self, match: Dict, bet_type: str, option: str) -> float:
        for bet_opt in match.get('betting_options', []):
            if bet_opt['bet_type'] == bet_type and bet_opt['option'] == option:
                return bet_opt['odds']
        return 2.0
    
    def _generate_fallback_prediction(self, match: Dict) -> List[Dict]:
        """
        AI yanıt vermezse fallback predictions oluştur
        """
        predictions = []
        
        # 1X2 - En düşük oranlı seçeneği bul
        x2_options = [opt for opt in match.get('betting_options', []) if opt['bet_type'] == '1X2']
        if x2_options:
            safe_option = min(x2_options, key=lambda x: x['odds'])
            predictions.append({
                "match_id": match['id'],
                "bet_type": "1X2",
                "recommended_option": safe_option['option'],
                "predicted_odds": safe_option['odds'],
                "confidence": 65.0,
                "ai_analysis": "Güvenli seçim (düşük oran)",
                "ai_model": "fallback"
            })
        
        # Over/Under - Genelde under güvenli
        ou_options = [opt for opt in match.get('betting_options', []) if opt['bet_type'] == 'over_under']
        if ou_options:
            under_opt = next((opt for opt in ou_options if 'under' in opt['option']), ou_options[0])
            predictions.append({
                "match_id": match['id'],
                "bet_type": "over_under",
                "recommended_option": under_opt['option'],
                "predicted_odds": under_opt['odds'],
                "confidence": 60.0,
                "ai_analysis": "Alt güvenli seçim",
                "ai_model": "fallback"
            })
        
        # BTTS
        btts_options = [opt for opt in match.get('betting_options', []) if opt['bet_type'] == 'btts']
        if btts_options:
            no_opt = next((opt for opt in btts_options if opt['option'] == 'no'), btts_options[0])
            predictions.append({
                "match_id": match['id'],
                "bet_type": "btts",
                "recommended_option": no_opt['option'],
                "predicted_odds": no_opt['odds'],
                "confidence": 58.0,
                "ai_analysis": "Karşılıklı gol yok tahmini",
                "ai_model": "fallback"
            })
        
        return predictions[:2]  # İlk 2 tahmini al
