import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from backend.utils.database import get_db
from backend.utils.device import get_device_hash

SECRET_KEY = os.getenv("SECRET_KEY", "priscomac-secret-key-change-in-production")
ALGORITHM = "HS256"
LICENSE_SESSION_HOURS = int(os.getenv("LICENSE_SESSION_HOURS", "24"))

def create_session_token(license_id: int) -> str:
    payload = {
        "sub": str(license_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=LICENSE_SESSION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_session_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_license(supabase, license_key: str, device_hash: str) -> Optional[dict]:
    license = supabase.table("licenses").select("id, product_name, status, max_devices, devices_used, demand_forecast_tool, expires_at").eq("license_key", license_key).execute().data
    license = license[0] if license else None

    if not license:
        return {"valid": False, "error": "License key not found."}

    if license["status"] != "active":
        return {"valid": False, "error": "License is not active."}

    expires_at = license.get("expires_at")
    if expires_at:
        if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
            return {"valid": False, "error": "License has expired."}

    if not license["demand_forecast_tool"]:
        return {"valid": False, "error": "License does not include Demand Forecast Tool access."}

    if license["devices_used"] >= license["max_devices"]:
        existing = supabase.table("device_activations").select("id").eq("license_id", license["id"]).eq("device_hash", device_hash).execute().data
        if not existing:
            return {"valid": False, "error": "Device activation limit exceeded."}

    existing_activation = supabase.table("device_activations").select("id").eq("license_id", license["id"]).eq("device_hash", device_hash).execute().data

    if not existing_activation:
        supabase.table("device_activations").insert({"license_id": license["id"], "device_hash": device_hash}).execute()
        supabase.table("licenses").update({"devices_used": license["devices_used"] + 1}).eq("id", license["id"]).execute()

    token = create_session_token(license["id"])
    return {
        "valid": True,
        "token": token,
        "product": license["product_name"],
        "license_id": license["id"],
    }

def check_session(supabase, token: str) -> Optional[dict]:
    payload = verify_session_token(token)
    if not payload:
        return None

    license_id = int(payload.get("sub"))
    license = supabase.table("licenses").select("product_name, expires_at").eq("id", license_id).eq("status", "active").execute().data
    license = license[0] if license else None

    if not license:
        return None

    expires_at = license.get("expires_at")
    if expires_at:
        if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
            return None

    return {"license_id": license_id, "product": license["product_name"]}
