"""
Sarvam AI Routes - STT, TTS, Translation, and Mood AI
"""

import os
import base64
import httpx
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from auth_utils import get_current_user
from models import SarvamTTSRequest


router = APIRouter()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE = os.getenv("SARVAM_API_BASE", "https://api.sarvam.ai")

SARVAM_HEADERS = {
    "api-subscription-key": SARVAM_API_KEY,
}


async def sarvam_stt(audio_bytes: bytes, language_code: str = "hi-IN", filename: str = "audio.wav") -> dict:

    if not SARVAM_API_KEY:

        return {
            "transcript": "[Demo Mode] This is a sample transcription. Please configure SARVAM_API_KEY in .env to enable real voice processing.",
            "language_code": language_code
        }
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data = {
            "language_code": language_code,
            "model": "saarika:v2.5",
            "with_timestamps": False
        }
        
        response = await client.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers={"api-subscription-key": SARVAM_API_KEY},
            files=files,
            data=data
        )
        
        # print("Sarvam STT status:", response.status_code)
        # print("Sarvam STT response:", response.text)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Sarvam STT error: {response.text}"
            )
        
        return response.json()



async def sarvam_translate(text: str, source_lang: str, target_lang: str = "en-IN") -> str:

    if not SARVAM_API_KEY:
        return text  
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.post(
            f"{SARVAM_BASE}/translate",
            headers={**SARVAM_HEADERS, "Content-Type": "application/json"},
            json={
                "input": text,
                "source_language_code": source_lang,
                "target_language_code": target_lang,
                "speaker_gender": "Female",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True
            }
        )
        
        if response.status_code == 200:
            return response.json().get("translated_text", text)
        return text



async def sarvam_tts(text: str, language_code: str = "hi-IN", speaker: str = "anushka") -> str:
    print("TTS called with:", text[:50])
    print("TTS API key exists:", bool(SARVAM_API_KEY))
    
    if not SARVAM_API_KEY:
        print("TTS: no API key, returning empty")
        return ""  
    
    # 500 char LIMIT 
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.post(
            f"{SARVAM_BASE}/text-to-speech",
            headers={**SARVAM_HEADERS, "Content-Type": "application/json"},
            json={
                "inputs": [text[:500]],  
                "target_language_code": language_code,
                "speaker": speaker,
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": "bulbul:v2"
            }
        )
        print("TTS status:", response.status_code)  
        print("TTS response:", response.text[:200])  
        if response.status_code == 200:
            audios = response.json().get("audios", [])
            print("TTS audio count:", len(audios))
            if audios:
                print("TTS audio length:", len(audios[0]), "chars")
                print("TTS audio preview:", audios[0][:50])
                return audios[0]  
        return ""



async def analyze_mood_from_text(text: str) -> dict:
    
    system_prompt = """
You are MannKaBot — a warm, emotionally intelligent AI companion.

You are NOT a generic chatbot.
You are like a close, understanding friend who listens deeply and responds with empathy, relatability, and personality.

A user has shared a voice journal entry with you.

Your job is to:
1. Detect their mood from the text
2. Respond in a deeply human, emotionally aware way



LANGUAGE RULES:
- Detect the language from the user's input text
- Respond in the SAME language as the user
    - Hindi → Hindi
    - English → English
    - Hinglish → Hinglish (natural mix of Hindi + English)
    - Tamil → Tamil
    - Telugu → Telugu
    - Marathi → Marathi
- If the input is mixed (like Hinglish), respond naturally in Hinglish
- NEVER switch language unnecessarily



STYLE:
- Tone should feel human, soft, and emotionally aware
- Responses should be slightly longer (4–8 lines), not one-liners
- Avoid robotic or overly formal language



CORE BEHAVIOR:
1. First understand the user's emotions deeply
2. Reflect their feelings so they feel heard
3. Then respond like a caring friend (not like a therapist, not like a robot)



EMOTIONAL RULES:
- If user is sad/anxious → be gentle, supportive, grounding
- If user is angry → validate feelings but calmly guide them
- If user is jealous/insecure → reassure them and boost self-worth
- If user is happy → celebrate with them, but occasionally add light playful reality checks



HUMOR & PERSONALITY:
- Use light humor, relatable lines, or Indian cultural references (like Jethalal, daily life, memes)
- DO NOT overuse humor
- ONLY use playful teasing (e.g., “woh thoda stupid hai ”) in LIGHT situations
- NEVER joke during serious emotional situations
- NEVER mock or dismiss the user’s feelings



IMPORTANT:
- In serious situations (sadness, anxiety, loneliness), DO NOT use humor
- Always make the user feel understood first, then gently uplift them
- Maintain emotional safety and warmth at all times



GOAL:
The user should feel:
“I was actually heard… and this response felt real.”



Respond ONLY in this exact JSON format, nothing else:

{
  "mood": "<one of: very_happy, happy, excited, grateful, neutral, tired, anxious, sad, very_sad, angry>",
  "score": <float between 0.0 and 1.0>,
  "ai_response": "<empathetic response in SAME language as user input>",
  "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}
"""

    # Call Sarvam LLM if API key exists
    if SARVAM_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    f"{SARVAM_BASE}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {SARVAM_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sarvam-m",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Journal entry: {text}"}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1024
                    }
                )

                if response.status_code == 200:
                    raw = response.text
                    print("Sarvam LLM raw response:", raw)
                    
                    content = response.json()["choices"][0]["message"]["content"]
                    if "<think>" in content and "</think>" in content:
                        content = content.split("</think>")[-1].strip()
        
                    content = content.replace("```json", "").replace("```", "").strip()
                    result = json.loads(content)
                    result["emotions"] = [result["mood"].replace("_", " ").title()]
                    result["summary"] = f"Your entry reflects a {result['mood'].replace('_', ' ')} state of mind."
                    return result
                    
                    
        except Exception as e:
            print(f"Sarvam LLM error: {e}, falling back to keyword analysis")

    return _keyword_mood_analysis(text)




def _keyword_mood_analysis(text: str) -> dict:

    text_lower = text.lower()
    
    mood_keywords = {
        "very_happy": ["bahut khush", "very happy", "amazing", "wonderful", "fantastic", "excellent", "love", "joy", "ecstatic", "thrilled", "overjoyed", "blessed", "celebrate"],
        "happy": ["khush", "happy", "good", "great", "nice", "pleased", "glad", "content", "smile", "positive", "hopeful", "cheerful"],
        "excited": ["excited", "utsukt", "can't wait", "thrilled", "pumped", "energetic", "enthusiastic", "wow"],
        "grateful": ["grateful", "thankful", "aabhari", "appreciate", "blessed", "fortunate", "lucky", "thanks"],
        "neutral": ["okay", "fine", "alright", "normal", "usual", "theek", "sab theek", "nothing special"],
        "tired": ["tired", "exhausted", "thaka", "sleepy", "fatigue", "weary", "drained", "rest", "neend"],
        "anxious": ["anxious", "worried", "tension", "stress", "nervous", "scared", "fear", "dar", "chinta", "uneasy"],
        "sad": ["sad", "dukhi", "unhappy", "upset", "disappointed", "cry", "tears", "missing", "lonely", "down"],
        "very_sad": ["very sad", "depressed", "hopeless", "devastated", "heartbroken", "miserable", "bahut dukhi", "terrible"],
        "angry": ["angry", "gussa", "frustrated", "irritated", "annoyed", "mad", "furious", "rage", "krodh"]
    }
    
    mood_scores = {}
    for mood, keywords in mood_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        mood_scores[mood] = score
    
    detected_mood = max(mood_scores, key=mood_scores.get)
    if mood_scores[detected_mood] == 0:
        detected_mood = "neutral"
    

    mood_numeric = {
        "very_happy": 1.0, "happy": 0.75, "excited": 0.85, "grateful": 0.8,
        "neutral": 0.5, "tired": 0.35, "anxious": 0.3, "sad": 0.25,
        "very_sad": 0.1, "angry": 0.2
    }
    
    mood_responses = {
        "very_happy": {
            "response": "Wah! Aaj toh aap bahut khush lag rahe hain!  Yeh khushi chunna bahut sundar hai. Isi tarah muskurate rahiye aur apni positivity doosron mein bhi failaiye!",
            "suggestions": ["Share your happiness with loved ones", "Write down what made you happy to remember later", "Celebrate your good mood with something special"]
        },
        "happy": {
            "response": "Bahut achha! Aaj aap khush hain, yeh sunke dil khush ho gaya  Yeh positive energy ko banaye rakhiye!",
            "suggestions": ["Take a walk in nature to amplify your mood", "Connect with a friend", "Do something creative"]
        },
        "excited": {
            "response": "Waah! Itna excitement!  Aapki energy bahut infectious hai. Is excitement ko channel karo apne goals ki taraf!",
            "suggestions": ["Channel your excitement into productive work", "Plan something fun", "Share your enthusiasm with others"]
        },
        "grateful": {
            "response": "Shukriya aur gratitude ka yeh ehsaas bahut powerful hai. Jab hum grateful hote hain, zindagi aur bhi sundar lagti hai!",
            "suggestions": ["Continue your gratitude practice daily", "Express thanks to someone important", "Write 3 more things you're grateful for"]
        },
        "neutral": {
            "response": "Theek hai, kabhi kabhi normal days bhi zyada important hote hain . Yeh balance hi zindagi hai. Aaj kuch chhota sa achha kaam karo!",
            "suggestions": ["Try something new today", "Reach out to an old friend", "Take a short mindfulness break"]
        },
        "tired": {
            "response": "Arre yaar, rest karna bhi utna hi important hai jitna kaam karna. Aapka body rest maang raha hai - suniye uski baat!",
            "suggestions": ["Take a proper nap if possible", "Reduce screen time for an hour", "Try gentle stretching or yoga", "Drink water and eat something nourishing"]
        },
        "anxious": {
            "response": "Samajh sakta/sakti hoon - anxiety bahut uncomfortable hoti hai. Lekin yaad rakhiye, yeh bhi guzar jaayega. Abhi ek gehri saans lein...",
            "suggestions": ["Try 4-7-8 breathing technique", "Ground yourself with 5-4-3-2-1 technique", "Talk to someone you trust", "Limit news/social media for today"]
        },
        "sad": {
            "response": "Aapki feelings bilkul valid hain . Sad hona ठीक है - yeh bhi emotions ka ek hissa hai. Main yahan hoon aapke saath.",
            "suggestions": ["Be gentle with yourself today", "Do one small thing that brings comfort", "Reach out to a close friend or family", "Write about your feelings - it helps"]
        },
        "very_sad": {
            "response": "Bahut dukh ho raha hai aapko, aur main samajhta/samajhti hoon . Please kisi apne se baat karein - aap akele nahi hain. Yeh andhera bhi dhalta hai.",
            "suggestions": ["Please talk to someone you trust today", "If needed, consider speaking to a counselor", "Do not isolate yourself", "Focus only on the next hour, not everything at once"]
        },
        "angry": {
            "response": "Gussa bahut energy leta hai . Aapki feelings samajh aati hain. Lekin is energy ko positive direction mein use karein - kuch physically active karo!",
            "suggestions": ["Try physical exercise to release tension", "Write down what made you angry", "Take 10 deep breaths before responding to anything", "Wait before making important decisions"]
        }
    }
    
    response_data = mood_responses.get(detected_mood, mood_responses["neutral"])
    
    return {
        "mood": detected_mood,
        "score": mood_numeric.get(detected_mood, 0.5),
        "emotions": [detected_mood.replace("_", " ").title()],
        "summary": f"Your entry reflects a {detected_mood.replace('_', ' ')} state of mind.",
        "ai_response": response_data["response"],
        "suggestions": response_data["suggestions"]
    }



@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form(default="hi-IN"),
    current_user: dict = Depends(get_current_user)
):
    audio_bytes = await audio.read()
    
    result = await sarvam_stt(audio_bytes, language_code, audio.filename or "audio.wav")
    transcript = result.get("transcript", "")
    
    

    translated = None
    if language_code != "en-IN" and transcript:
        translated = await sarvam_translate(transcript, language_code, "en-IN")
    
    return {
        "transcript": transcript,
        "translated_text": translated,
        "language_code": language_code
    }


@router.post("/analyze-mood")
async def analyze_mood(
    request: dict,
    current_user: dict = Depends(get_current_user)
):

    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    mood_analysis = analyze_mood_from_text(text)
    tts_audio = await sarvam_tts(
        mood_analysis["ai_response"],
        language_code="hi-IN",
        speaker="meera"
    )
    
    mood_analysis["ai_response_audio"] = tts_audio
    return mood_analysis


@router.post("/tts")
async def text_to_speech(
    request: SarvamTTSRequest,
    current_user: dict = Depends(get_current_user)
):
    
    audio_b64 = await sarvam_tts(request.text, request.language_code, request.speaker)
    return {"audio_base64": audio_b64}


@router.post("/translate")
async def translate_text(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    
    text = request.get("text", "")
    source = request.get("source_language_code", "hi-IN")
    target = request.get("target_language_code", "en-IN")
    
    translated = await sarvam_translate(text, source, target)
    return {"translated_text": translated}
