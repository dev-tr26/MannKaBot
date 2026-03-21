import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi
import ssl

load_dotenv()

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_db():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    
    is_atlas = "mongodb.net" in mongo_url
    
    if is_atlas:

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        db_instance.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=10000,
            tls=True,
            tlsCAFile=certifi.where()
        )
    else:
        db_instance.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000
        )
    
    db_instance.db = db_instance.client[os.getenv("DATABASE_NAME", "voice_journal_db")]
    
    await db_instance.db.users.create_index("email", unique=True)
    await db_instance.db.journal_entries.create_index("user_id")
    await db_instance.db.journal_entries.create_index("created_at")
    
    print("Connected to MongoDB")

async def close_db():
    if db_instance.client:
        db_instance.client.close()
        print(" MongoDB connection closed")

def get_db():
    return db_instance.db