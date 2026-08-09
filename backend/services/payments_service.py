import os
import secrets
import string
import logging
import requests
from datetime import datetime
from typing import Optional
from backend.utils.database import supabase

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")
USD_PRICE_CENTS = int(os.getenv("LICENSE_USD_PRICE_CENTS", "3000"))
PRODUCT_NAME = os.getenv("LICENSE_PRODUCT_NAME", "Demand Forecast Tool")

headers = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}


def generate_license_key() -> str:
    raw = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    return f"PMA-{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


def create_license(supabase, license_key: str, product_name: str = PRODUCT_NAME) -> dict:
    data = {
        "license_key": license_key,
        "product_name": product_name,
        "status": "active",
        "max_devices": 1,
        "devices_used": 0,
        "demand_forecast_tool": True,
    }
    result = supabase.table("licenses").insert(data).execute()
    return result.data[0] if result.data else data


def log_payment(paystack_ref: str, **kwargs):
    logger.info("========== LICENSE USD PAYMENT ==========")
    for key, value in kwargs.items():
        logger.info(f"{key}: {value}")
    logger.info(f"Paystack Reference: {paystack_ref}")


def init_paystack_payment(email: str) -> dict:
    if not PAYSTACK_SECRET_KEY:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")

    callback_url = os.getenv(
        "PAYSTACK_CALLBACK_URL",
        f"{os.getenv('VITE_API_BASE_URL', 'https://priscomac-analytics.onrender.com')}/get-license",
    )

    metadata = {
        "type": "license_purchase",
        "product": PRODUCT_NAME,
    }

    payload = {
        "email": email,
        "amount": USD_PRICE_CENTS,
        "currency": "USD",
        "callback_url": callback_url,
        "metadata": metadata,
    }

    resp = requests.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("status"):
        raise RuntimeError(f"Paystack init failed: {data.get('message')}")

    return {
        "authorization_url": data["data"]["authorization_url"],
        "access_code": data["data"]["access_code"],
        "reference": data["data"]["reference"],
    }


def verify_paystack_payment(reference: str, supabase) -> dict:
    if not PAYSTACK_SECRET_KEY:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")

    resp = requests.get(
        f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("status"):
        raise RuntimeError(f"Paystack verify failed: {data.get('message')}")

    paystack_data = data.get("data", {})
    payment_status = paystack_data.get("status")
    currency = paystack_data.get("currency")
    amount = paystack_data.get("amount")
    metadata = paystack_data.get("metadata", {})
    customer = paystack_data.get("customer", {})
    email = customer.get("email", "")

    log_payment(
        reference,
        **{
            "User Email": email,
            "Product": metadata.get("product", PRODUCT_NAME),
            "USD Price": f"${USD_PRICE_CENTS / 100:.2f}",
            "Paystack Reference": reference,
            "Currency": currency,
            "Amount": amount,
            "Payment Status": payment_status,
            "Metadata": metadata,
        },
    )

    if payment_status != "success":
        return {"success": False, "paid": False, "error": "Payment not successful."}

    if currency != "USD":
        return {"success": False, "paid": False, "error": "Invalid currency. Expected USD."}

    if amount != USD_PRICE_CENTS:
        return {"success": False, "paid": False, "error": "Invalid amount."}

    existing = (
        supabase.table("license_purchases")
        .select("id, status, license_id")
        .eq("paystack_reference", reference)
        .execute()
        .data
    )
    purchase = existing[0] if existing else None

    if purchase and purchase.get("license_id"):
        license_row = (
            supabase.table("licenses")
            .select("license_key")
            .eq("id", purchase["license_id"])
            .execute()
            .data
        )
        license_key = license_row[0]["license_key"] if license_row else None
        return {
            "success": True,
            "paid": True,
            "license": license_key,
            "already_processed": True,
        }

    if not purchase or not purchase.get("license_id"):
        license_key = generate_license_key()
        create_license(supabase, license_key, PRODUCT_NAME)
        license_row = (
            supabase.table("licenses")
            .select("id")
            .eq("license_key", license_key)
            .execute()
            .data
        )
        license_id = license_row[0]["id"] if license_row else None

        purchase_data = {
            "paystack_reference": reference,
            "email": email,
            "amount": amount,
            "currency": currency,
            "status": "success",
            "license_id": license_id,
            "metadata": metadata,
        }
        supabase.table("license_purchases").insert(purchase_data).execute()

        logger.info(f"License Generated: {license_key}")
        logger.info(f"License: {license_key}")

        return {
            "success": True,
            "paid": True,
            "license": license_key,
            "already_processed": False,
        }

    return {"success": False, "paid": False, "error": "Payment verification failed."}


def handle_paystack_webhook(payload: dict, supabase) -> dict:
    event = payload.get("event")
    paystack_data = payload.get("data", {})
    reference = paystack_data.get("reference")
    currency = paystack_data.get("currency")
    amount = paystack_data.get("amount")
    metadata = paystack_data.get("metadata", {})
    status = paystack_data.get("status")

    logger.info(f"Paystack webhook event: {event}")

    if event != "charge.success":
        return {"received": True, "processed": False}

    if not reference:
        return {"received": True, "processed": False, "error": "Missing reference."}

    existing = (
        supabase.table("license_purchases")
        .select("id, status, license_id")
        .eq("paystack_reference", reference)
        .execute()
        .data
    )
    purchase = existing[0] if existing else None

    if purchase and purchase.get("license_id"):
        return {"received": True, "processed": True, "already_processed": True}

    if currency != "USD":
        return {"received": True, "processed": False, "error": "Invalid currency."}

    if amount != USD_PRICE_CENTS:
        return {"received": True, "processed": False, "error": "Invalid amount."}

    customer = paystack_data.get("customer", {})
    email = customer.get("email", metadata.get("email", ""))

    license_key = generate_license_key()
    license_row = create_license(supabase, license_key, metadata.get("product", PRODUCT_NAME))
    license_id = license_row.get("id") if isinstance(license_row, dict) else license_row[0].get("id")

    purchase_data = {
        "paystack_reference": reference,
        "email": email,
        "amount": amount,
        "currency": currency,
        "status": "success",
        "license_id": license_id,
        "metadata": metadata,
    }
    supabase.table("license_purchases").insert(purchase_data).execute()

    logger.info(f"License Generated via webhook: {license_key}")
    logger.info(f"License: {license_key}")

    return {"received": True, "processed": True, "license": license_key}
