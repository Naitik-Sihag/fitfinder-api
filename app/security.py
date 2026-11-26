import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    key: str | None = Security(_header), settings: Settings = Depends(get_settings)
) -> None:
    keys = settings.api_key_set
    if not keys:
        return  # auth disabled
    if not key or not any(secrets.compare_digest(key, k) for k in keys):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
