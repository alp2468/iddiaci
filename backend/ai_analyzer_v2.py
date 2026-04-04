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
Mac Analizi Yapilacak:

Lig: {match.get('league', 'Bilinmiyor')}
Ev Sahibi: {match.get('home_team', 'Bilinmiyor')}
Deplasman: {match.get('away_team', 'Bilinmiyor')}
Tarih: {match.get('match_date', 'Bilinmiyor')} {match.get('match_time', '')}

Mevcut Bahis Secenekleri:
{betting_opts_text}

Bu mac icin EN IYI 4 bahis tahmini yap. Farkli bahis turlerinden sec.
Her tahmin icin su formati kullan:
BAHIS_TURU: [1X2/over_under/over_under_1_5/over_under_3_5/btts/double_chance/ht_result/odd_even]
TAHMIN: [orn: 1, X, 2, over_2.5, under_2.5, over_1.5, under_3.5, yes, no, 1X, 12, X2, HT_1, HT_X, HT_2, tek, cift]
ORAN: [bahis orani]
GUVEN: [0-100]
ANALIZ: [Kisa analiz]
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
                    line_upper = line.upper()
                    if 'BAHIS' in line_upper or 'BAHİS' in line_upper:
                        bet_type = line.split(':')[1].strip().lower()
                        pred['bet_type'] = bet_type
                    elif 'TAHMIN' in line_upper or 'TAHMİN' in line_upper:
                        option = line.split(':')[1].strip()
                        pred['option'] = option
                    elif 'ORAN' in line_upper:
                        try:
                            odds = float(line.split(':')[1].strip())
                            pred['odds'] = odds
                        except Exception:
                            pred['odds'] = 2.0
                    elif 'GUVEN' in line_upper or 'GÜV' in line_upper:
                        try:
                            conf_str = line.split(':')[1].strip()
                            conf = float(''.join(filter(str.isdigit, conf_str)))
                            pred['confidence'] = conf
                        except Exception:
                            pred['confidence'] = 60.0
                    elif 'ANALIZ' in line_upper or 'ANALİZ' in line_upper:
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
        """Fallback: farkli turlerden tahminler olustur"""
        import random
        predictions = []
        bet_opts = match.get('betting_options', [])
        
        # 1X2
        x2_options = [opt for opt in bet_opts if opt['bet_type'] == '1X2']
        if x2_options:
            safe_option = min(x2_options, key=lambda x: x['odds'])
            predictions.append({
                "match_id": match['id'], "bet_type": "1X2",
                "recommended_option": safe_option['option'],
                "predicted_odds": safe_option['odds'],
                "confidence": 65.0, "ai_analysis": "Mac sonucu tahmini",
                "ai_model": "fallback"
            })
        
        # Cifte Sans
        dc_options = [opt for opt in bet_opts if opt['bet_type'] == 'double_chance']
        if dc_options:
            safe_dc = min(dc_options, key=lambda x: x['odds'])
            predictions.append({
                "match_id": match['id'], "bet_type": "double_chance",
                "recommended_option": safe_dc['option'],
                "predicted_odds": safe_dc['odds'],
                "confidence": 75.0, "ai_analysis": "Cifte sans guvenli secim",
                "ai_model": "fallback"
            })
        
        # Over/Under 2.5
        ou_options = [opt for opt in bet_opts if opt['bet_type'] == 'over_under']
        if ou_options:
            pick = random.choice(ou_options)
            predictions.append({
                "match_id": match['id'], "bet_type": "over_under",
                "recommended_option": pick['option'],
                "predicted_odds": pick['odds'],
                "confidence": 60.0, "ai_analysis": "Ust/Alt 2.5 tahmini",
                "ai_model": "fallback"
            })
        
        # Over/Under 1.5
        ou15_options = [opt for opt in bet_opts if opt['bet_type'] == 'over_under_1_5']
        if ou15_options:
            over15 = next((o for o in ou15_options if 'over' in o['option']), ou15_options[0])
            predictions.append({
                "match_id": match['id'], "bet_type": "over_under_1_5",
                "recommended_option": over15['option'],
                "predicted_odds": over15['odds'],
                "confidence": 72.0, "ai_analysis": "1.5 ust guvenli",
                "ai_model": "fallback"
            })
        
        # BTTS
        btts_options = [opt for opt in bet_opts if opt['bet_type'] == 'btts']
        if btts_options:
            pick = random.choice(btts_options)
            predictions.append({
                "match_id": match['id'], "bet_type": "btts",
                "recommended_option": pick['option'],
                "predicted_odds": pick['odds'],
                "confidence": 58.0, "ai_analysis": "KG tahmini",
                "ai_model": "fallback"
            })
        
        # Ilk Yari
        ht_options = [opt for opt in bet_opts if opt['bet_type'] == 'ht_result']
        if ht_options:
            pick = random.choice(ht_options)
            predictions.append({
                "match_id": match['id'], "bet_type": "ht_result",
                "recommended_option": pick['option'],
                "predicted_odds": pick['odds'],
                "confidence": 55.0, "ai_analysis": "Ilk yari sonucu",
                "ai_model": "fallback"
            })
        
        # Tek/Cift
        oe_options = [opt for opt in bet_opts if opt['bet_type'] == 'odd_even']
        if oe_options:
            pick = random.choice(oe_options)
            predictions.append({
                "match_id": match['id'], "bet_type": "odd_even",
                "recommended_option": pick['option'],
                "predicted_odds": pick['odds'],
                "confidence": 50.0, "ai_analysis": "Tek/Cift tahmini",
                "ai_model": "fallback"
            })
        
        random.shuffle(predictions)
        return predictions[:4]
