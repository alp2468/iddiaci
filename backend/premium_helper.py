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
        "yearly": 990
    }
    
    # Limitler
    FREE_TOTAL_LIMIT = 3  # Toplam 3 hak, sonra premium sart
    
    # Odeme bilgileri
    PAYMENT_INFO = {
        "papara": "1234567890",
        "papara_name": "Isim Soyisim",
        "iban": "TR00 0000 0000 0000 0000 0000",
        "iban_name": "Isim Soyisim"
    }
    
    @staticmethod
    def is_premium_active(user: Dict) -> bool:
        if not user.get('is_premium'):
            return False
        premium_until = user.get('premium_until')
        if not premium_until:
            return False
        try:
            until_date = datetime.fromisoformat(premium_until)
            return datetime.utcnow() < until_date
        except Exception:
            return False
    
    @staticmethod
    def can_create_coupon(user: Dict) -> tuple[bool, str]:
        if user.get('is_admin'):
            return True, "OK"
        if PremiumHelper.is_premium_active(user):
            return True, "OK"
        total = user.get('total_coupons', 0)
        if total >= PremiumHelper.FREE_TOTAL_LIMIT:
            return False, f"Ucretsiz kupon hakkiniz bitti! ({total}/{PremiumHelper.FREE_TOTAL_LIMIT})\n\nDevam etmek icin Premium'a gecin\n/premium"
        return True, "OK"
    
    @staticmethod
    def can_use_risk_level(user: Dict, risk_level: str) -> tuple[bool, str]:
        if user.get('is_admin'):
            return True, "OK"
        if risk_level == "zor":
            if not PremiumHelper.is_premium_active(user):
                return False, "Zor seviye sadece Premium uyeler icin!\n\nPremium'a gec\n/premium"
        return True, "OK"
    
    @staticmethod
    def activate_premium(user_id: str, premium_type: str) -> Dict:
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
            "premium_type": premium_type,
            "expiry_reminder_sent": False
        }
    
    @staticmethod
    def deactivate_premium() -> Dict:
        return {
            "is_premium": False,
            "premium_since": None,
            "premium_until": None,
            "premium_type": "free"
        }
    
    @staticmethod
    def get_remaining_days(user: Dict) -> int:
        if not PremiumHelper.is_premium_active(user):
            return 0
        try:
            until = datetime.fromisoformat(user['premium_until'])
            diff = until - datetime.utcnow()
            return max(0, diff.days)
        except Exception:
            return 0
    
    @staticmethod
    def format_premium_info() -> str:
        return f"""**Premium Uyelik**

**Ucretsiz Plan:**
- Toplam {PremiumHelper.FREE_TOTAL_LIMIT} kupon hakki
- Banko + Orta seviye

**Premium - {PremiumHelper.PRICES['monthly']}TL/ay:**
- Sinirsiz kupon
- Tum seviyeler (Zor dahil)
- Detayli AI analizi
- Ozel destek

**Odeme Bilgileri:**

**Papara:** {PremiumHelper.PAYMENT_INFO['papara']}
Ad: {PremiumHelper.PAYMENT_INFO['papara_name']}

**VEYA**

**IBAN:** {PremiumHelper.PAYMENT_INFO['iban']}
Ad: {PremiumHelper.PAYMENT_INFO['iban_name']}

Odeme aciklamasina Telegram kullanici adinizi yazin!
Ornek: "@kullaniciadi PREMIUM"

**Odeme yaptiktan sonra:**
/odemeyaptim komutu ile dekontu gonderin
"""
