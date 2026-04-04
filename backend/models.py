from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime
import uuid

class BettingOption(BaseModel):
    """Bahis seçeneği modeli"""
    bet_type: str  # '1X2', 'over_under', 'btts', 'double_chance', 'first_half'
    option: str    # '1', 'X', '2', 'over_2.5', 'under_2.5', 'yes', 'no', etc.
    odds: float
    bookmaker: Optional[str] = None

class Match(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_match_id: Optional[str] = None
    league: str
    league_country: Optional[str] = None
    home_team: str
    away_team: str
    match_date: str
    match_time: Optional[str] = None
    venue: Optional[str] = None
    
    # Bahis seçenekleri
    betting_options: List[BettingOption] = []
    
    # İstatistikler
    home_form: Optional[List[str]] = None
    away_form: Optional[List[str]] = None
    h2h_results: Optional[List[Dict]] = None
    
    # Takım istatistikleri
    home_goals_avg: Optional[float] = None
    away_goals_avg: Optional[float] = None
    home_goals_conceded_avg: Optional[float] = None
    away_goals_conceded_avg: Optional[float] = None
    
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Prediction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    bet_type: str  # '1X2', 'over_under', 'btts', etc.
    recommended_option: str  # '1', 'over_2.5', 'yes', etc.
    predicted_odds: float
    confidence: float
    ai_analysis: str
    ai_model: str
    factors: Optional[Dict] = None  # Analiz faktörleri
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class CouponMatch(BaseModel):
    """Kuponda yer alan maç bilgisi"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    bet_type: str
    recommended_option: str
    odds: float
    confidence: float
    analysis_summary: Optional[str] = None

class Coupon(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    risk_level: str  # 'banko', 'orta', 'zor'
    matches: List[Dict]  # CouponMatch as dict
    total_odds: float
    potential_return: Optional[float] = None  # 100 TL için
    user_telegram_id: Optional[str] = None
    status: str = "pending"  # pending, won, lost
    result_checked: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    result_date: Optional[str] = None

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_interaction: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class BotActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    activity_type: str
    user_telegram_id: str
    details: Optional[Dict] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())