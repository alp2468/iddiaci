"""
Premium System Helper
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PremiumHelper:
    # Fiyatlar
    PRICES = {
        "monthly": 99,
        "yearly": 990  # 2 ay bedava
    }
    
    # Limitler
    FREE_DAILY_LIMIT = 5
    PREMIUM_DAILY_LIMIT = 999999  # Sınırsız
    
    # Ödeme bilgileri (SENİN BİLGİLERİN)
    PAYMENT_INFO = {
        "papara": "1234567890",  # Senin Papara no
        "papara_name": "İsim Soyisim",  # Senin adın
        "iban": "TR00 0000 0000 0000 0000 0000",  # Senin IBAN
        "iban_name": "İsim Soyisim"  # Senin adın
    }
    
    @staticmethod
    def is_premium_active(user: Dict) -> bool:
        """Premium aktif mi kontrol et"""
        if not user.get('is_premium'):
            return False
        
        premium_until = user.get('premium_until')
        if not premium_until:
            return False
        
        try:
            until_date = datetime.fromisoformat(premium_until)
            return datetime.utcnow() < until_date
        except:
            return False
    
    @staticmethod
    def get_daily_limit(user: Dict) -> int:
        """Kullanıcının günlük limitini döndür"""
        if PremiumHelper.is_premium_active(user):
            return PremiumHelper.PREMIUM_DAILY_LIMIT
        return PremiumHelper.FREE_DAILY_LIMIT
    
    @staticmethod
    def can_create_coupon(user: Dict) -> tuple[bool, str]:
        """Kupon oluşturabilir mi kontrol et"""
        # Günlük limit kontrolü
        today = datetime.utcnow().strftime("%Y-%m-%d")
        last_coupon_date = user.get('last_coupon_date', '')
        
        # Yeni gün başlamışsa sayacı sıfırla
        if last_coupon_date != today:
            return True, "OK"
        
        daily_count = user.get('daily_coupon_count', 0)
        limit = PremiumHelper.get_daily_limit(user)
        
        if daily_count >= limit:
            if PremiumHelper.is_premium_active(user):
                return True, "OK"  # Premium sınırsız
            else:
                return False, f"Günlük kupon limitiniz doldu! ({daily_count}/{limit})\\n\\n💎 Premium ile sınırsız kupon\\n/premium"
        
        return True, "OK"
    
    @staticmethod
    def can_use_risk_level(user: Dict, risk_level: str) -> tuple[bool, str]:
        """Risk seviyesini kullanabilir mi"""
        if risk_level == "zor":
            if not PremiumHelper.is_premium_active(user):
                return False, "❌ Zor seviye sadece Premium üyeler için!\\n\\n💎 Premium'a geç\\n/premium"
        
        return True, "OK"
    
    @staticmethod
    def activate_premium(user_id: str, premium_type: str) -> Dict:
        """Premium aktif et"""
        now = datetime.utcnow()
        
        if premium_type == "monthly":
            until = now + timedelta(days=30)
        elif premium_type == "yearly":
            until = now + timedelta(days=365)
        else:
            until = now + timedelta(days=30)
        
        return {
            "is_premium": True,
            "premium_since": now.isoformat(),
            "premium_until": until.isoformat(),
            "premium_type": premium_type
        }
    
    @staticmethod
    def deactivate_premium() -> Dict:
        """Premium kaldır"""
        return {
            "is_premium": False,
            "premium_since": None,
            "premium_until": None,
            "premium_type": "free"
        }
    
    @staticmethod
    def get_remaining_days(user: Dict) -> int:
        """Kalan gün sayısı"""
        if not PremiumHelper.is_premium_active(user):
            return 0
        
        try:
            until = datetime.fromisoformat(user['premium_until'])
            diff = until - datetime.utcnow()
            return max(0, diff.days)
        except:
            return 0
    
    @staticmethod
    def format_premium_info() -> str:
        """Premium bilgi mesajı"""
        return f"""💎 **Premium Üyelik**

🆓 **Ücretsiz Plan:**
• Günde 5 kupon
• Banko + Orta seviye
• Temel AI analizi

💎 **Premium - ₺{PremiumHelper.PRICES['monthly']}/ay:**
• ✨ Sınırsız kupon
• ✨ Tüm seviyeler (Zor dahil)
• ✨ Detaylı AI analizi (%85+ güven)
• ✨ Özel destek

📱 **Ödeme Bilgileri:**

**Papara:** {PremiumHelper.PAYMENT_INFO['papara']}
Ad: {PremiumHelper.PAYMENT_INFO['papara_name']}

**VEYA**

**IBAN:** {PremiumHelper.PAYMENT_INFO['iban']}
Ad: {PremiumHelper.PAYMENT_INFO['iban_name']}

⚠️ **Önemli:**
Ödeme açıklamasına Telegram kullanıcı adınızı yazın!

Örnek: "@kullaniciadi PREMIUM"

**Ödeme yaptıktan sonra:**
/odemeyaptim komutu ile dekontu gönderin
"""
