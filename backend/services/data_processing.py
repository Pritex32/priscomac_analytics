import pandas as pd
import numpy as np
from typing import Tuple, Optional
from io import BytesIO

REQUIRED_COLUMNS = ["date", "demand", "product"]

def load_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.endswith(".csv"):
        return pd.read_csv(BytesIO(file_bytes))
    elif filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(file_bytes))
    else:
        raise ValueError("Unsupported file format. Use .csv, .xlsx, or .xls")

def clean_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    report = {"rows_before": len(df), "duplicates_removed": 0, "missing_values_dropped": 0}

    df.columns = [c.strip().lower() for c in df.columns]

    col_map = {}
    for col in df.columns:
        if "date" in col:
            col_map[col] = "date"
        elif "demand" in col or "sales" in col or "qty" in col or "quantity" in col:
            col_map[col] = "demand"
        elif "product" in col or "item" in col or "sku" in col:
            col_map[col] = "product"

    df = df.rename(columns=col_map)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.drop_duplicates()
    report["duplicates_removed"] = report["rows_before"] - len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    report["missing_values_dropped"] += report["rows_before"] - len(df) - report["duplicates_removed"]

    df["demand"] = pd.to_numeric(df["demand"], errors="coerce")
    df = df.dropna(subset=["demand"])
    df["demand"] = df["demand"].clip(lower=0)

    df = df.sort_values("date").reset_index(drop=True)
    report["rows_after"] = len(df)

    return df, report

def compute_summary_stats(df: pd.DataFrame) -> dict:
    return {
        "total_records": int(len(df)),
        "date_range": {
            "start": df["date"].min().strftime("%Y-%m-%d"),
            "end": df["date"].max().strftime("%Y-%m-%d"),
        },
        "total_demand": float(df["demand"].sum()),
        "avg_demand": float(df["demand"].mean()),
        "max_demand": float(df["demand"].max()),
        "min_demand": float(df["demand"].min()),
        "std_demand": float(df["demand"].std()),
        "unique_products": int(df["product"].nunique()) if "product" in df.columns else 1,
    }

def generate_forecast(df: pd.DataFrame, periods: int) -> Tuple[pd.DataFrame, dict]:
    try:
        from prophet import Prophet
        ts = df.groupby("date")["demand"].sum().reset_index()
        ts.columns = ["ds", "y"]
        if len(ts) < 5:
            raise ValueError("Insufficient data for Prophet")
        m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        m.fit(ts)
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)
        result.columns = ["date", "predicted", "lower", "upper"]
        growth = ((result["predicted"].iloc[-1] - result["predicted"].iloc[0]) / (result["predicted"].iloc[0] + 1e-9)) * 100
        return result, {"method": "Prophet", "growth_percent": round(float(growth), 2)}
    except Exception:
        return moving_average_forecast(df, periods)

def moving_average_forecast(df: pd.DataFrame, periods: int) -> Tuple[pd.DataFrame, dict]:
    ts = df.groupby("date")["demand"].sum()
    last_date = ts.index[-1]
    dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq="D")
    window = min(7, len(ts))
    ma = ts.rolling(window=window).mean().iloc[-1]
    predictions = np.linspace(ma, ma * 1.05, periods)
    result = pd.DataFrame({"date": dates, "predicted": predictions, "lower": predictions * 0.85, "upper": predictions * 1.15})
    growth = ((predictions[-1] - predictions[0]) / (predictions[0] + 1e-9)) * 100
    return result, {"method": "Moving Average", "growth_percent": round(float(growth), 2)}

def recommended_reorder(predicted: pd.DataFrame, avg_demand: float) -> dict:
    total = float(predicted["predicted"].sum())
    safety_stock = avg_demand * 0.2
    reorder = total + safety_stock
    return {
        "recommended_reorder_quantity": round(reorder, 2),
        "safety_stock": round(safety_stock, 2),
        "total_predicted_demand": round(total, 2),
    }
