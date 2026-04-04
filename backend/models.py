from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime
import uuid

class Match(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    league: str
    home_team: str
    away_team: str
    match_date: str
    odds_1: Optional[float] = None
    odds_x: Optional[float] = None
    odds_2: Optional[float] = None
    home_form: Optional[List[str]] = None
    away_form: Optional[List[str]] = None
    h2h_results: Optional[List[str]] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Prediction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    ai_analysis: str
    confidence: float
    recommended_bet: str
    predicted_odds: float
    ai_model: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Coupon(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    risk_level: str
    matches: List[Dict]
    total_odds: float
    user_telegram_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

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