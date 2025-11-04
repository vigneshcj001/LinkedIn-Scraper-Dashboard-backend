import os
import time
import requests
import logging
import statistics
from collections import Counter
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

# =========================================================
# SETUP
# =========================================================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LinkedInScraperAPI")

app = FastAPI(title="LinkedIn Scraper API Wrapper")

# CORS for local + dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"

# =========================================================
# RATE LIMITER (to prevent 429)
# =========================================================
last_call_time = 0

def rate_limit(min_interval=1.2):
    """Ensure at least 1.2 seconds between RapidAPI calls."""
    global last_call_time
    now = time.time()
    elapsed = now - last_call_time
    if elapsed < min_interval:
        sleep_for = min_interval - elapsed
        logger.info(f"⏳ Rate limit enforced, sleeping {sleep_for:.2f}s")
        time.sleep(sleep_for)
    last_call_time = time.time()

# =========================================================
# HELPERS
# =========================================================
def clean_linkedin_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query=""))

def fetch_from_rapidapi(endpoint: str, params: dict, rapidapi_key: str = None):
    """Generic fetch with retry + rate limiting"""
    key_to_use = rapidapi_key or RAPIDAPI_KEY
    if not key_to_use:
        raise HTTPException(status_code=400, detail="Missing RapidAPI key.")

    headers = {
        "x-rapidapi-key": key_to_use,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    url = f"https://{RAPIDAPI_HOST}/{endpoint}"

    for attempt in range(3):
        try:
            rate_limit()
            logger.info(f"➡️ [{attempt+1}/3] Fetching {url} params={params}")
            res = requests.get(url, headers=headers, params=params, timeout=30)

            if res.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"⚠️ 429 quota hit — retrying after {wait}s...")
                time.sleep(wait)
                continue

            res.raise_for_status()
            data = res.json()
            if not data:
                raise HTTPException(status_code=502, detail="Empty response.")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            if attempt == 2:
                raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=429, detail="RapidAPI quota exceeded.")

# =========================================================
# ROUTES
# =========================================================

@app.get("/")
async def root():
    return {"status": "✅ LinkedIn Scraper API is running"}

@app.get("/api/profile")
def get_profile(request: Request, username: str):
    return fetch_from_rapidapi("profile/detail", {"username": username}, request.headers.get("x-rapidapi-key"))

@app.get("/api/posts")
def get_posts(request: Request, username: str, page_number: int = 1):
    return fetch_from_rapidapi("profile/posts", {"username": username, "page_number": page_number}, request.headers.get("x-rapidapi-key"))

@app.get("/api/comments")
def get_comments(request: Request, post_url: str, page_number: int = 1, sort_order: str = "Most relevant"):
    clean_url = clean_linkedin_url(post_url)
    return fetch_from_rapidapi("post/comments", {"post_url": clean_url, "page_number": page_number, "sort_order": sort_order}, request.headers.get("x-rapidapi-key"))

@app.get("/api/company")
def get_company(request: Request, identifier: str):
    return fetch_from_rapidapi("companies/detail", {"identifier": identifier}, request.headers.get("x-rapidapi-key"))

@app.get("/api/analytics/comments")
def comment_analytics(request: Request, post_url: str):
    clean_url = clean_linkedin_url(post_url)
    data = fetch_from_rapidapi("post/comments", {"post_url": clean_url}, request.headers.get("x-rapidapi-key"))
    comments = data.get("data", {}).get("comments", [])
    if not comments:
        return {"success": False, "error": "No comments found"}

    authors = [c.get("author", {}).get("name") for c in comments if c.get("author", {}).get("name")]
    reactions = [c.get("stats", {}).get("total_reactions", 0) for c in comments]
    return {
        "success": True,
        "summary": {
            "total_comments": len(comments),
            "unique_commenters": len(set(authors)),
            "average_reactions": statistics.mean(reactions) if reactions else 0,
            "top_commenters": Counter(authors).most_common(5),
        },
    }

class ReactionRequest(BaseModel):
    post_url: str
    page_number: str = "1"
    reaction_type: str = "ALL"

@app.post("/api/post/reactions")
async def get_post_reactions(request_data: ReactionRequest, request: Request):
    post_url = request_data.post_url.strip()
    if not post_url:
        raise HTTPException(status_code=400, detail="Missing post_url")

    key = request.headers.get("x-rapidapi-key", RAPIDAPI_KEY)
    params = {
        "post_url": post_url,
        "page_number": request_data.page_number,
        "reaction_type": request_data.reaction_type,
    }

    data = fetch_from_rapidapi("post/reactions", params, key)
    return data
