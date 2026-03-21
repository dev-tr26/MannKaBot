from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MoodEnum(str, Enum):
    VERY_HAPPY = "very_happy"
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    VERY_SAD = "very_sad"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    EXCITED = "excited"
    TIRED = "tired"
    GRATEFUL = "grateful"


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None
    google_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime
    streak: int = 0
    total_entries: int = 0


class JournalEntryCreate(BaseModel):
    transcript: str
    audio_language: str = "hi-IN"
    title: Optional[str] = None


class JournalEntryResponse(BaseModel):
    id: str
    user_id: str
    title: str
    transcript: str
    translated_text: Optional[str] = None
    detected_mood: Optional[MoodEnum] = None
    mood_score: Optional[float] = None
    ai_response: Optional[str] = None
    ai_response_audio: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    audio_duration: Optional[float] = None


class MoodAnalysis(BaseModel):
    mood: MoodEnum
    score: float
    emotions: List[str]
    summary: str
    ai_response: str
    suggestions: List[str]


class SarvamSTTRequest(BaseModel):
    language_code: str = "hi-IN"
    model: str = "saarika:v2"


class SarvamTTSRequest(BaseModel):
    text: str
    language_code: str = "hi-IN"
    speaker: str = "meera"
    model: str = "bulbul:v1"


class InsightsSummary(BaseModel):
    total_entries: int
    streak: int
    mood_distribution: dict
    average_mood_score: float
    most_common_mood: str
    weekly_entries: List[dict]
    recent_tags: List[str]
    positive_days_percentage: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse