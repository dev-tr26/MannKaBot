from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta,timezone 
from bson import ObjectId
from database import get_db
from auth_utils import get_current_user
from routes.sarvam import analyze_mood_from_text, sarvam_tts

router = APIRouter()


def serialize_entry(entry: dict) -> dict:

    entry["id"] = str(entry["_id"])
    del entry["_id"]
    if "created_at" in entry and isinstance(entry["created_at"], datetime):
        entry["created_at"] = entry["created_at"].isoformat()
    return entry


@router.post("/")
async def create_entry(
    request: dict,
    current_user: dict = Depends(get_current_user)
):

    transcript = request.get("transcript", "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is required")
    

    mood_analysis = await analyze_mood_from_text(transcript)
    
    ai_audio = await sarvam_tts(
        mood_analysis["ai_response"],
        language_code="hi-IN",
        speaker="anushka"
    )
    

    title = request.get("title") or transcript[:60].strip() + ("..." if len(transcript) > 60 else "")
    

    tags = [mood_analysis["mood"]] + mood_analysis.get("emotions", [])[:2]
    
    entry = {
        "user_id": str(current_user["_id"]),
        "title": title,
        "transcript": transcript,
        "translated_text": request.get("translated_text"),
        "audio_language": request.get("audio_language", "hi-IN"),
        "detected_mood": mood_analysis["mood"],
        "mood_score": mood_analysis["score"],
        "ai_response": mood_analysis["ai_response"],
        "ai_response_audio": ai_audio,
        "suggestions": mood_analysis.get("suggestions", []),
        "tags": list(set(tags)),
        "created_at": datetime.now(timezone.utc),
        "audio_duration": request.get("audio_duration", 0)
    }
    
    db = get_db()
    result = await db.journal_entries.insert_one(entry)
    

    user_id = ObjectId(current_user["_id"])
    user = await db.users.find_one({"_id": user_id})
    

    new_streak = user.get("streak", 0)
    last_entry = user.get("last_entry_date")
    today = datetime.now(timezone.utc).date()
    
    if last_entry:
        last_date = last_entry.date() if isinstance(last_entry, datetime) else last_entry
        diff = (today - last_date).days
        if diff == 1:
            new_streak += 1
        elif diff > 1:
            new_streak = 1

    else:
        new_streak = 1
    
    await db.users.update_one(
        {"_id": user_id},
        {
            "$inc": {"total_entries": 1},
            "$set": {
                "streak": new_streak,
                "last_entry_date": datetime.now(timezone.utc)
            }
        }
    )
    
    entry["id"] = str(result.inserted_id)
    entry["created_at"] = entry["created_at"].isoformat()

    if "_id" in entry:
        del entry["_id"]
    
    return entry



@router.get("/")
async def get_entries(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    mood: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    query = {"user_id": str(current_user["_id"])}
    
    if mood:
        query["detected_mood"] = mood
    
    if search:
        query["$or"] = [
            {"transcript": {"$regex": search, "$options": "i"}},
            {"title": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    total = await db.journal_entries.count_documents(query)
    
    cursor = db.journal_entries.find(query).sort("created_at", -1).skip(skip).limit(limit)
    entries = []
    async for entry in cursor:
        entries.append(serialize_entry(entry))
    
    return {
        "entries": entries,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }



@router.get("/insights")
async def get_insights(
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    user_id = str(current_user["_id"])
    

    total = await db.journal_entries.count_documents({"user_id": user_id})
    

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$detected_mood", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    mood_dist = {}
    async for doc in db.journal_entries.aggregate(pipeline):
        if doc["_id"]:
            mood_dist[doc["_id"]] = doc["count"]
    

    avg_pipeline = [
        {"$match": {"user_id": user_id, "mood_score": {"$exists": True}}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$mood_score"}}}
    ]
    avg_score = None
    async for doc in db.journal_entries.aggregate(avg_pipeline):
        avg_score = round(doc["avg_score"], 2)
    

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
            "avg_mood": {"$avg": "$mood_score"}
        }},
        {"$sort": {"_id": 1}}
    ]
    weekly = []
    async for doc in db.journal_entries.aggregate(weekly_pipeline):
        weekly.append({
            "date": doc["_id"],
            "count": doc["count"],
            "avg_mood": round(doc.get("avg_mood", 0.5), 2)
        })
    

    most_common = max(mood_dist, key=mood_dist.get) if mood_dist else "neutral"
    

    tags_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    recent_tags = []
    async for doc in db.journal_entries.aggregate(tags_pipeline):
        recent_tags.append(doc["_id"])
    

    positive_moods = ["very_happy", "happy", "excited", "grateful"]
    positive_count = sum(mood_dist.get(m, 0) for m in positive_moods)
    positive_pct = round((positive_count / total * 100) if total > 0 else 0, 1)
    
    return {
        "total_entries": total,
        "streak": current_user.get("streak", 0),
        "mood_distribution": mood_dist,
        "average_mood_score": avg_score,
        "most_common_mood": most_common,
        "weekly_entries": weekly,
        "recent_tags": recent_tags,
        "positive_days_percentage": positive_pct
    }


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    
    try:
        entry = await db.journal_entries.find_one({
            "_id": ObjectId(entry_id),
            "user_id": str(current_user["_id"])
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry ID")
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return serialize_entry(entry)


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    
    try:
        result = await db.journal_entries.delete_one({
            "_id": ObjectId(entry_id),
            "user_id": str(current_user["_id"])
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$inc": {"total_entries": -1}}
    )
    
    return {"message": "Entry deleted successfully"}