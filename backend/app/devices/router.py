from fastapi import APIRouter, Depends, Request
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.common.audit import log_action
from app.devices import schemas, service

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("", response_model=schemas.DeviceResponse)
async def register_device(
    request: Request,
    body: schemas.DeviceRegisterRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Register this device for push; safe to call on every launch."""
    device = await service.register_device(current_user["id"], body.model_dump())

    await log_action(
        user_id=current_user["id"],
        action="registered_device",
        resource_type="device",
        resource_id=device["id"],
        details={"platform": body.platform, "device_label": body.device_label},
        ip_address=request.client.host if request.client else None,
    )

    return schemas.DeviceResponse(**device)


@router.get("", response_model=schemas.DeviceListResponse)
async def list_devices(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List the caller's registered devices."""
    devices = await service.list_devices(current_user["id"])
    return schemas.DeviceListResponse(
        devices=[schemas.DeviceResponse(**d) for d in devices],
        total=len(devices),
    )


@router.delete("/{device_id}", response_model=schemas.MessageResponse)
async def unregister_device(
    device_id: str,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Stop sending push notifications to a device. Called on sign-out."""
    await service.unregister_device(current_user["id"], device_id)

    await log_action(
        user_id=current_user["id"],
        action="unregistered_device",
        resource_type="device",
        resource_id=device_id,
        ip_address=request.client.host if request.client else None,
    )

    return schemas.MessageResponse(message="Device unregistered.")
