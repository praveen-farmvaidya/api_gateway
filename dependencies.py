from fastapi import Request, Depends, HTTPException, status
from httpx import AsyncClient, Response
import os

# A simple Pydantic model to represent the validated user from the API key
class ValidatedUser(object):
    def __init__(self, user_id: str):
        self.id = user_id

IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL")

async def get_validated_user(request: Request) -> ValidatedUser:
    """
    This dependency is the core of your API key security.
    It extracts the API key, sends it to the api_key_service for validation,
    and returns user info or raises an error.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header is missing")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format. Use 'Bearer <api_key>'")
    
    plain_key = parts[1]
    
    # This is the crucial service-to-service call
    async with AsyncClient() as client:
        try:
            response = await client.post(
                f"{IDENTITY_SERVICE_URL}/keys/validate",
                json={"plain_key": plain_key}
            )
            response.raise_for_status() # Raise HTTP errors for 4xx/5xx responses
        except Exception as e:
            # This catches network errors or if the service is down
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API Key service is unavailable")

    data = response.json()
    return ValidatedUser(user_id=data["user_id"])

# Placeholder for JWT validation for user-specific actions like creating keys
async def get_current_user_from_jwt(request: Request) -> ValidatedUser:
    """
    PLACEHOLDER: In a real app, this would decode a JWT from the
    Authorization header and return the user's ID.
    For this POC, we will simulate a validated user.
    """
    # This is a temporary measure for testing.
    # We will replace this with real JWT logic later.
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT authentication is required for this endpoint. (Simulated with x-user-id header for POC)"
        )
    return ValidatedUser(user_id=user_id)
