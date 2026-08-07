import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from psycopg2.extras import RealDictCursor
from utils.device import get_device_hash

SECRET_KEY = os.getenv("SECRET_KEY", "priscomac-secret-key-change-in-production")
ALGORITHM = "HS256"
LICENSE_SESSION_HOURS = int(os.getenv("LICENSE_SESSION_HOURS", "24"))

def create_session_token(license_id: int) -> str:
    payload = {
        "sub": str(license_id),
        "exp": datetime.utcnow() + timedelta(hours=LICENSE_SESSION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_session_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_license(conn, license_key: str, device_hash: str) -> Optional[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, product_name, status, max_devices, devices_used, demand_forecast_tool FROM licenses WHERE license_key = %s", (license_key,))
        license = cur.fetchone()

    if not license:
        return {"valid": False, "error": "License key not found."}

    if license["status"] != "active":
        return {"valid": False, "error": "License is not active."}

    if not license["demand_forecast_tool"]:
        return {"valid": False, "error": "License does not include Demand Forecast Tool access."}

    if license["devices_used"] >= license["max_devices"]:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM device_activations WHERE license_id = %s AND device_hash = %s", (license["id"], device_hash))
            existing = cur.fetchone()
        if not existing:
            return {"valid": False, "error": "Device activation limit exceeded."}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM device_activations WHERE license_id = %s AND device_hash = %s", (license["id"], device_hash))
        existing_activation = cur.fetchone()

    if not existing_activation:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO device_activations (license_id, device_hash) VALUES (%s, %s)", (license["id"], device_hash))
            cur.execute("UPDATE licenses SET devices_used = devices_used + 1 WHERE id = %s", (license["id"],))
        conn.commit()

    token = create_session_token(license["id"])
    return {
        "valid": True,
        "token": token,
        "product": license["product_name"],
        "license_id": license["id"],
    }

def check_session(conn, token: str) -> Optional[dict]:
    payload = verify_session_token(token)
    if not payload:
        return None

    license_id = int(payload.get("sub"))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT product_name FROM licenses WHERE id = %s AND status = 'active'", (license_id,))
        license = cur.fetchone()

    if not license:
        return None

    return {"license_id": license_id, "product": license["product_name"]}
