# MannKaBot — Voice AI Journal

A beautiful, voice-powered AI journal that listens in Hindi (and other Indian languages), understands your emotions, and responds with compassionate AI support — powered by **Sarvam AI models**.

---

## Features

-  **Voice Recording** — Record journal entries in Hindi, English, Tamil, Telugu, Bengali, Marathi & more
-  **Mood Detection** — AI analyzes your emotional state from speech
-  **AI Responses** — Personalized, mood-aware replies in Hindi (with TTS audio)
-  **Insights Dashboard** — Charts, mood trends, streaks & wellness score
-  **Google OAuth** — Secure sign-in with Gmail
-  **MongoDB** — All entries persisted per user
-  **Multi-language** — 10 Indian languages via Sarvam AI

---

##  Project Structure

```
voice-journal/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # MongoDB Motor connection
│   ├── auth_utils.py        # JWT authentication utilities
│   ├── models.py            # Pydantic models
│   └── routes/
│       ├── auth.py          # Google OAuth routes
│       ├── journal.py       # Journal CRUD API
│       └── sarvam.py        # Sarvam AI (STT, TTS, Translation)
├── frontend/
│   ├── templates/
│   │   ├── index.html       # Landing/Home page
│   │   ├── login.html       # Google Sign-In page
│   │   ├── dashboard.html   # Main dashboard + voice recorder
│   │   ├── journal.html     # Journal entries list
│   │   └── insights.html    # Mood analytics & charts
│   └── static/              # CSS, JS, assets
├── requirements.txt
├── .env.example
└── setup.sh
```

---

##  Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo>
cd voice-journal
chmod +x setup.sh && ./setup.sh
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=voice_journal_db

# JWT
JWT_SECRET=your-random-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=xxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Sarvam AI
SARVAM_API_KEY=your-sarvam-api-key
```

### 3. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google+ API** and **OAuth2 API**
4. Go to **Credentials → Create OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized redirect URI: `http://localhost:8000/auth/google/callback`
7. Copy Client ID and Client Secret to `.env`

### 4. Get Sarvam AI API Key

1. Visit [https://app.sarvam.ai](https://app.sarvam.ai)
2. Sign up and create an API key
3. Add to `SARVAM_API_KEY` in `.env`

> **Note**: App works in **Demo Mode** without Sarvam API key — voice recording will return sample transcriptions.

### 5. Start MongoDB

```bash
# macOS (Homebrew)
brew services start mongodb-community

# Ubuntu/Linux
sudo systemctl start mongod

# Or use MongoDB Atlas cloud - update MONGODB_URL accordingly
```

### 6. Run the App

```bash
cd voice-journal
source venv/bin/activate
cd backend
python main.py
```

Open [http://localhost:8000](http://localhost:8000) 🎉

---

## 📡 API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Redirect to Google OAuth |
| GET | `/auth/google/callback` | OAuth callback (sets JWT) |
| GET | `/auth/me` | Get current user |

### Journal
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/journal/` | Create entry (with mood analysis) |
| GET | `/api/journal/` | List entries (paginated, filterable) |
| GET | `/api/journal/insights` | Get mood analytics |
| GET | `/api/journal/{id}` | Get single entry |
| DELETE | `/api/journal/{id}` | Delete entry |

### Sarvam AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sarvam/transcribe` | Audio → Text (STT) |
| POST | `/api/sarvam/analyze-mood` | Text → Mood + AI response |
| POST | `/api/sarvam/tts` | Text → Audio (TTS) |
| POST | `/api/sarvam/translate` | Translate text |

---

##  Pages Overview

| Page | Route | Description |
|------|-------|-------------|
|  Home | `/` | Landing page with features, how-it-works |
|  Login | `/login` | Google OAuth sign-in |
|  Dashboard | `/dashboard` | Stats + voice recorder + recent entries |
|  Journal | `/journal` | All entries with search & mood filter |
|  Insights | `/insights` | Mood trends, charts, analytics |

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | MongoDB (via Motor async driver) |
| Auth | Google OAuth2 + JWT |
| AI / Voice | Sarvam AI (STT, TTS, Translation) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Charts | Chart.js |
| Fonts | Google Fonts (Playfair Display, DM Sans) |

---

##  Supported Languages (Sarvam AI)

- 🇮🇳 Hindi (`hi-IN`)
- 🇬🇧 English (`en-IN`)
- Bengali (`bn-IN`)
- Tamil (`ta-IN`)
- Telugu (`te-IN`)
- Marathi (`mr-IN`)
- Gujarati (`gu-IN`)
- Kannada (`kn-IN`)
- Malayalam (`ml-IN`)
- Punjabi (`pa-IN`)

---

##  Demo Mode

If `SARVAM_API_KEY` is not set, the app runs in **Demo Mode**:
- Voice transcription returns a placeholder message
- Mood analysis works fully (keyword-based)
- TTS audio responses are disabled
- All other features work normally

---

##  Security Notes

- JWT tokens stored in `localStorage` (7-day expiry)
- All API endpoints require Bearer token authentication
- User data is isolated by `user_id` in MongoDB
- Google OAuth handles authentication securely

---

##  License

MIT License — Built for educational/personal use.

---

*Built with ❤️ for the Indian developer community*
