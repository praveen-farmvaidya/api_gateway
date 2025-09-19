from fastapi import Request
from fastapi.responses import Response
from httpx import AsyncClient

async def proxy_request(
    client: AsyncClient,
    request: Request,
    downstream_url: str,
    params: dict = None
):
    """
    A general-purpose function to transparently proxy an incoming request
    to a downstream service.
    """
    body = await request.body()
    headers = dict(request.headers)
    
    headers.pop("host", None)
    # Preserve original content-type for file uploads in other tools
    content_type = headers.get("content-type")

    rp = await client.request(
        method=request.method,
        url=downstream_url,
        headers=headers,
        content=body,
        params=params or dict(request.query_params)
    )
    
    # Make the proxy robust
    try:
        content = rp.content
    except Exception:
        content = b''
    
    # Use the original response's media type
    media_type = rp.headers.get("content-type")

    return Response(
        content=content,
        status_code=rp.status_code,
        media_type=media_type
    )