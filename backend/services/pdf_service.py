import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO

def generate_pdf_report(summary: dict, forecast: dict, reorder: dict, method: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Priscomac Analytics - Forecast Report", styles["Title"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"Forecasting Method: {method}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    data = [
        ["Metric", "Value"],
        ["Total Records", str(summary["total_records"])],
        ["Date Range", f"{summary['date_range']['start']} to {summary['date_range']['end']}"],
        ["Total Demand", f"{summary['total_demand']:.2f}"],
        ["Average Demand", f"{summary['avg_demand']:.2f}"],
        ["Max Demand", f"{summary['max_demand']:.2f}"],
        ["Min Demand", f"{summary['min_demand']:.2f}"],
        ["Growth Trend", f"{forecast.get('growth_percent', 0):.2f}%"],
        ["Recommended Reorder", f"{reorder['recommended_reorder_quantity']:.2f}"],
        ["Safety Stock", f"{reorder['safety_stock']:.2f}"],
    ]

    table = Table(data, colWidths=[3 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D32F2F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
