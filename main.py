from dotenv import load_dotenv
import os
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from httpx import AsyncClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .dependencies import (
    get_validated_user_from_api_key,
    get_validated_user_from_jwt,
    ValidatedUser
)
from .proxy_utils import proxy_request

# --- Configuration ---
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL")
QUEUE_SERVICE_URL = os.getenv("QUEUE_SERVICE_URL")
BILLING_SERVICE_URL = os.getenv("BILLING_SERVICE_URL")
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "100/minute")

limiter = Limiter(key_func=get_remote_address)
clients = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    clients["http_client"] = AsyncClient()
    yield
    await clients["http_client"].aclose()

app = FastAPI(
    title="FarmVidhya API Gateway",
    description="The single entry point for all FarmVidhya services.",
    version="2.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- ROUTING DEFINITIONS ---

@app.post("/signup", tags=["Authentication"])
@app.post("/login", tags=["Authentication"])
@app.post("/verify-otp", tags=["Authentication"])
@app.get("/auth/google/login", tags=["Authentication"])
@app.get("/auth/google/callback", tags=["Authentication"])
async def auth_proxy(request: Request):
    path = request.url.path
    return await proxy_request(clients["http_client"], request, f"{IDENTITY_SERVICE_URL}{path}")

@app.post("/keys", tags=["User Management"])
@app.get("/keys/user/{user_id}", tags=["User Management"])
@app.delete("/keys/{key_id}/user/{user_id}", tags=["User Management"])
async def keys_proxy(request: Request, user: ValidatedUser = Depends(get_validated_user_from_jwt)):
    path = request.url.path
    return await proxy_request(clients["http_client"], request, f"{IDENTITY_SERVICE_URL}{path}")

@app.post("/initiate-payment", tags=["User Management"])
@app.get("/balance/{user_id}", tags=["User Management"])
async def billing_proxy(request: Request, user: ValidatedUser = Depends(get_validated_user_from_jwt)):
    path = request.url.path
    return await proxy_request(clients["http_client"], request, f"{BILLING_SERVICE_URL}{path}")

@app.post("/jobs/initiate-upload", tags=["Jobs"])
@limiter.limit(DEFAULT_RATE_LIMIT)
async def jobs_proxy(request: Request, user: ValidatedUser = Depends(get_validated_user_from_api_key)):
    path = request.url.path
    return await proxy_request(
        clients["http_client"],
        request,
        f"{QUEUE_SERVICE_URL}{path}",
        params={"user_id": user.id}
    )
        
@app.post("/webhook/razorpay", tags=["Webhooks"])
async def webhook_proxy(request: Request):
    return await proxy_request(clients["http_client"], request, f"{BILLING_SERVICE_URL}/webhook/razorpay")