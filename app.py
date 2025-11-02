import os
import requests
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from collections import Counter
import statistics

# ---------- Setup ----------
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LinkedIn Scraper API Wrapper")

# ---------- CORS (for frontend connection) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # You can replace "*" with your frontend URL for extra safety
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],   # Needed for x-rapidapi-key
)

# ---------- Config ----------
BASE_URL = "https://linkedin-data-api.p.rapidapi.com"  # Example RapidAPI endpoint


# ---------- Helper ----------
def get_rapidapi_key(request: Request) -> str:
    """Fetch RapidAPI key from header or environment."""
    key = request.headers.get("x-rapidapi-key") or os.getenv("RAPIDAPI_KEY")
    logger.info(f"🔑 RapidAPI key received: {'Yes' if key else 'No'}")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="RapidAPI key missing. Set in .env or send via x-rapidapi-key header.",
        )
    return key


# ---------- Routes ----------

@app.get("/api/profile")
async def get_profile(username: str, request: Request):
    """Fetch LinkedIn profile details by username."""
    rapidapi_key = get_rapidapi_key(request)

    url = f"{BASE_URL}/get-profile"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }
    params = {"username": username}

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ RapidAPI request failed: {e}")
        raise HTTPException(status_code=500, detail="Error fetching profile from RapidAPI")

    return res.json()


@app.get("/api/posts")
async def get_posts(username: str, request: Request, page: int = 1):
    """Fetch LinkedIn posts by username."""
    rapidapi_key = get_rapidapi_key(request)

    url = f"{BASE_URL}/get-profile-posts"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }
    params = {"username": username, "page": page}

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ RapidAPI request failed: {e}")
        raise HTTPException(status_code=500, detail="Error fetching posts from RapidAPI")

    return res.json()


@app.get("/api/comments")
async def get_comments(post_url: str, request: Request, page: int = 1):
    """Fetch LinkedIn comments for a specific post."""
    rapidapi_key = get_rapidapi_key(request)

    url = f"{BASE_URL}/get-post-comments"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }
    params = {"post_url": post_url, "page": page}

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ RapidAPI request failed: {e}")
        raise HTTPException(status_code=500, detail="Error fetching comments from RapidAPI")

    return res.json()


@app.get("/")
async def root():
    return {"status": "✅ LinkedIn Scraper Backend running successfully"}


# ---------- Start (Render runs with: uvicorn backend.main:app --host 0.0.0.0 --port 8000) ----------
