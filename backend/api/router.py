from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form,requests
from backend.services.license_service import verify_license, check_session
from backend.services.data_processing import load_file, clean_data, compute_summary_stats, generate_forecast, recommended_reorder
from backend.services.chart_service import build_forecast_chart, build_summary_chart
from backend.services.pdf_service import generate_pdf_report
from backend.services.excel_service import generate_excel_report
from backend.services.payment_service import init_paystack_payment, verify_paystack_payment, handle_paystack_webhook
from backend.utils.database import get_db
import os
import requests

router = APIRouter()

def get_license_from_token(token: str, supabase):
    session = check_session(supabase, token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return session

@router.post("/verify-license")
def verify_license_endpoint(license_key: str = Form(...), supabase = Depends(get_db)):
    from utils.device import get_device_hash
    device_hash = get_device_hash()
    result = verify_license(supabase, license_key, device_hash)
    if not result["valid"]:
        raise HTTPException(status_code=403, detail=result["error"])
    return result

@router.post("/analyze")
def analyze_file(
    file: UploadFile = File(...),
    forecast_period: int = Form(30),
    token: str = Form(...),
    supabase = Depends(get_db)
):
    session = get_license_from_token(token, supabase)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    allowed_ext = {".csv", ".xlsx", ".xls"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    try:
        file_bytes = file.file.read()
        df = load_file(file_bytes, file.filename)
        df_clean, cleaning_report = clean_data(df)
        summary = compute_summary_stats(df_clean)
        forecast_df, forecast_meta = generate_forecast(df_clean, forecast_period)
        reorder = recommended_reorder(forecast_df, summary["avg_demand"])

        forecast_chart = build_forecast_chart(df_clean, forecast_df)
        summary_chart = build_summary_chart(summary)

        pdf_bytes = generate_pdf_report(summary, forecast_meta, reorder, forecast_meta["method"])
        excel_bytes = generate_excel_report(df_clean, forecast_df, summary, reorder)

        return {
            "success": True,
            "summary": summary,
            "cleaning_report": cleaning_report,
            "forecast": forecast_df.to_dict(orient="records"),
            "forecast_meta": forecast_meta,
            "reorder": reorder,
            "charts": {
                "forecast": forecast_chart,
                "summary": summary_chart,
            },
            "pdf_base64": __import__("base64").b64encode(pdf_bytes).decode("utf-8"),
            "excel_base64": __import__("base64").b64encode(excel_bytes).decode("utf-8"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paystack/init")
def paystack_init(email: str = Form(...), supabase = Depends(get_db)):
    try:
        result = init_paystack_payment(email)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment initialization failed.")


@router.get("/paystack/verify/{reference}")
def paystack_verify(reference: str, supabase = Depends(get_db)):
    try:
        result = verify_paystack_payment(reference, supabase)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment verification failed.")


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request, supabase = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload.")

    try:
        result = handle_paystack_webhook(payload, supabase)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Webhook processing failed.")
