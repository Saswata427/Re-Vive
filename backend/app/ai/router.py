"""Authenticated gateway from the RE:VIVE API to the Recovery Risk AI service."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/ai", tags=["Recovery Risk AI"])
settings = get_settings()


class RecoveryRiskPayload(BaseModel):
    """The feature payload accepted by the AI microservice."""
    model_config = ConfigDict(extra="allow")


@router.get("/health")
async def ai_health(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Check whether the AI service is reachable without exposing it publicly."""
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{settings.AI_SERVICE_URL}/health")
        if response.status_code >= 400:
            raise HTTPException(status_code=503, detail="Recovery Risk AI is unavailable")
        return response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Recovery Risk AI is unavailable") from exc


@router.post("/predict")
async def predict_risk(
    payload: RecoveryRiskPayload,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Forward an authenticated prediction request to the AI microservice."""
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.AI_SERVICE_URL}/predict",
                json=payload.model_dump(exclude_none=True),
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Recovery Risk AI timed out") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Recovery Risk AI is unavailable") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Recovery Risk AI returned invalid data") from exc

    if response.status_code >= 400:
        detail = data.get("detail", "Recovery Risk AI rejected the request") if isinstance(data, dict) else "Recovery Risk AI rejected the request"
        raise HTTPException(status_code=502, detail=detail)

    return data
