from fastapi import Request, Depends, HTTPException, status
from httpx import AsyncClient
import os

class ValidatedUser:
    """A simple class to hold the validated user ID from a token."""
    def __init__(self, user_id: str):
        self.id = user_id

IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL")

async def get_validated_user_from_api_key(request: Request) -> ValidatedUser:
    """
    Security Dependency for API Key authentication (for /jobs endpoint).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header is missing")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format. Use 'Bearer <api_key>'")
    
    plain_key = parts[1]
    
    validation_url = f"{IDENTITY_SERVICE_URL}/keys/validate"
    
    async with AsyncClient() as client:
        try:
            response = await client.post(validation_url, json={"plain_key": plain_key})
            response.raise_for_status()
        except Exception:
            raise HTTPException(status_code=503, detail="Identity service is unavailable for key validation.")

    data = response.json()
    return ValidatedUser(user_id=data["user_id"])

async def get_validated_user_from_jwt(request: Request) -> ValidatedUser:
    """
    [POC SIMULATION] Security Dependency for user-session (JWT) authentication.
    """
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT authentication is required. (Simulated with 'x-user-id' header for POC)"
        )
    return ValidatedUser(user_id=user_id)