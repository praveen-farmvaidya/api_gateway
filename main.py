from fastapi.responses import Response
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from httpx import AsyncClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from dependencies import get_validated_user, get_current_user_from_jwt, ValidatedUser

load_dotenv()

# --- Configuration ---
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL")
QUEUE_SERVICE_URL = os.getenv("QUEUE_SERVICE_URL")
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "100/minute")

# --- Rate Limiting Setup ---
limiter = Limiter(key_func=get_remote_address)

# --- App Lifecycle ---
# Use a dictionary to hold the client, as recommended by FastAPI docs
clients = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create a single, reusable client for the app's entire lifespan
    clients["http_client"] = AsyncClient()
    yield
    # Cleanly close the client when the app is shutting down
    await clients["http_client"].aclose()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="FarmVidhya API Gateway",
    description="The single entry point for all FarmVidhya services.",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# --- Helper function for proxying requests ---
async def _proxy_request(request: Request, url: str, params: dict = None):
    client: AsyncClient = clients["http_client"]
    body = await request.body()
    headers = dict(request.headers)
    
    headers.pop("host", None)

    rp = await client.request(
        method=request.method,
        url=url,
        headers=headers,
        content=body,
        params=params or request.query_params
    )
    
    # This is the most robust way to handle proxying.
    if "application/json" in rp.headers.get("content-type", ""):
        return JSONResponse(status_code=rp.status_code, content=rp.json())
    else:
        return Response(content=rp.content, status_code=rp.status_code, media_type=rp.headers.get("content-type"))
# --- Public, Unauthenticated Routes ---
# Routes for user signup and login are proxied directly to the user service
@app.post("/signup")
@app.post("/login")
@app.post("/verify-otp")
@app.get("/auth/google/login")
@app.get("/auth/google/callback")
async def auth_proxy(request: Request):
    path = request.url.path
    return await _proxy_request(request, f"{IDENTITY_SERVICE_URL}{path}")

# --- API Key Secured Routes ---
@app.post("/jobs")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def submit_job(request: Request, user: ValidatedUser = Depends(get_validated_user)):
    # The get_validated_user dependency has already secured this endpoint.
    # We now forward the request to the queue service, passing the user_id.
    return await _proxy_request(
        request,
        f"{QUEUE_SERVICE_URL}/jobs",
        params={"user_id": user.id} # Pass validated user_id as a query param
    )

# --- JWT Secured Routes (Simulated) ---
# These routes manage API keys and should only be accessible by a logged-in user.
@app.post("/keys")
async def create_key(request: Request, user: ValidatedUser = Depends(get_current_user_from_jwt)):
    # This endpoint is protected by our simulated JWT dependency
    return await _proxy_request(request, f"{IDENTITY_SERVICE_URL}/keys/user/{user_id}")

@app.get("/keys/user/{user_id}")
async def get_keys(request: Request, user_id: str, user: ValidatedUser = Depends(get_current_user_from_jwt)):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await _proxy_request(request, f"{API_KEY_SERVICE_URL}/keys/user/{user_id}")

# Add other proxied routes (e.g., DELETE key, GET balance) following the same pattern.
