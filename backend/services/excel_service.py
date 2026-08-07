import pandas as pd
from io import BytesIO

def generate_excel_report(original: pd.DataFrame, forecast: pd.DataFrame, summary: dict, reorder: dict) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        original.to_excel(writer, sheet_name="Original Data", index=False)
        forecast.to_excel(writer, sheet_name="Forecast", index=False)

        summary_df = pd.DataFrame([
            ["Total Records", summary["total_records"]],
            ["Total Demand", summary["total_demand"]],
            ["Average Demand", summary["avg_demand"]],
            ["Max Demand", summary["max_demand"]],
            ["Min Demand", summary["min_demand"]],
            ["Recommended Reorder", reorder["recommended_reorder_quantity"]],
            ["Safety Stock", reorder["safety_stock"]],
        ], columns=["Metric", "Value"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    buffer.seek(0)
    return buffer.getvalue()
