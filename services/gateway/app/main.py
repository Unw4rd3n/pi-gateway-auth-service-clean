from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
import httpx

from .config import settings
from .security import PUBLIC_PATHS, decode_access_token


app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_to_auth(path: str, request: Request):
    target_path = f"/auth/{path}" if not path.startswith("auth/") else f"/{path}"
    public_alias = f"/api/{path}"

    if public_alias not in PUBLIC_PATHS:
        token_payload = decode_access_token(request.headers.get("Authorization"))
        # Basic role enforcement for admin routes in gateway layer.
        if public_alias.startswith("/api/admin/") and token_payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")

    target_url = f"{settings.auth_service_url}{target_path}"
    content = await request.body()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        upstream = await client.request(
            request.method,
            target_url,
            content=content,
            headers=headers,
            params=request.query_params,
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in {"content-encoding", "transfer-encoding", "connection"}
    }

    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)


@app.exception_handler(httpx.RequestError)
async def upstream_error_handler(_: Request, exc: httpx.RequestError):
    return JSONResponse(status_code=502, content={"detail": f"Upstream unavailable: {exc}"})
