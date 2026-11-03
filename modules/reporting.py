
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)

from .data import AGE_ORDER, DISEASES, MONTHS
from .analysis import next_month_forecast


# =====================================================
# 1. COLORS AND FONT
# =====================================================

BLUE = colors.HexColor("#174B75")
DARK_BLUE = colors.HexColor("#123B62")
LIGHT_BLUE = colors.HexColor("#EAF3FA")
PALE_BLUE = colors.HexColor("#F4F8FC")
GRAY = colors.HexColor("#64748B")
BORDER = colors.HexColor("#D8E3ED")
WHITE = colors.white


def register_thai_fonts():

    font_dir = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "fonts"
    )

    regular = font_dir / "NotoLoopedThai-Regular.ttf"
    bold = font_dir / "NotoLoopedThai-Bold.ttf"

    if regular.exists() and bold.exists():

        if "ThaiRegular" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont("ThaiRegular", str(regular))
            )

        if "ThaiBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont("ThaiBold", str(bold))
            )

        return "ThaiRegular", "ThaiBold"

    # Fallback
    return "Helvetica", "Helvetica-Bold"


# =====================================================
# 2. PAGE HEADER AND FOOTER
# =====================================================

def draw_page(canvas, doc):

    canvas.saveState()

    width, height = A4

    canvas.setFillColor(DARK_BLUE)
    canvas.rect(
        0,
        height - 12 * mm,
        width,
        12 * mm,
        fill=1,
        stroke=0
    )

    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)

    canvas.drawString(
        15 * mm,
        height - 7.5 * mm,
        "T-DTAF | THAILAND DISEASE TREND ANALYSIS"
    )

    canvas.setStrokeColor(BORDER)
    canvas.line(
        15 * mm,
        13 * mm,
        width - 15 * mm,
        13 * mm
    )

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 8)

    canvas.drawString(
        15 * mm,
        8 * mm,
        "THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM"
    )

    canvas.drawRightString(
        width - 15 * mm,
        8 * mm,
        f"Page {doc.page} / 3"
    )

    canvas.restoreState()


# =====================================================
# 3. STYLES
# =====================================================

def create_styles():

    regular, bold = register_thai_fonts()

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ThaiTitle",
        fontName=bold,
        fontSize=19,
        leading=27,
        textColor=DARK_BLUE,
        alignment=TA_LEFT,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ThaiHeading",
        fontName=bold,
        fontSize=13,
        leading=19,
        textColor=BLUE,
        spaceBefore=7,
        spaceAfter=7
    ))

    styles.add(ParagraphStyle(
        name="ThaiSub",
        fontName=regular,
        fontSize=9,
        leading=14,
        textColor=GRAY,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ThaiBody",
        fontName=regular,
        fontSize=9,
        leading=15,
        textColor=colors.HexColor("#334155")
    ))

    styles.add(ParagraphStyle(
        name="ThaiSmall",
        fontName=regular,
        fontSize=8,
        leading=12,
        textColor=GRAY
    ))

    styles.add(ParagraphStyle(
        name="ThaiCell",
        fontName=regular,
        fontSize=8,
        leading=12
    ))

    styles.add(ParagraphStyle(
        name="ThaiCellBold",
        fontName=bold,
        fontSize=8,
        leading=12,
        textColor=DARK_BLUE
    ))

    return styles, regular, bold


# =====================================================
# 4. GENERAL FUNCTIONS
# =====================================================

def safe_text(value):

    if pd.isna(value):
        return "-"

    return escape(str(value))


def format_number(value):

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


def filter_area(df, area):

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    if area != "ประเทศไทย" and "health_region" in result.columns:
        result = result[result["health_region"] == area]

    return result


def make_table(data, widths, header=True):

    table = Table(
        data,
        colWidths=widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT"
    )

    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]

    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ])

    for row in range(1 if header else 0, len(data)):
        if row % 2 == 0:
            commands.append(
                ("BACKGROUND", (0, row), (-1, row), PALE_BLUE)
            )

    table.setStyle(TableStyle(commands))

    return table


def make_paragraph(text, style):

    return Paragraph(str(text), style)


# =====================================================
# 5. PAGE 1 : OVERVIEW
# =====================================================

def build_overview(df, area, styles, bold):

    story = []

    story.append(make_paragraph(
        "หน้า 1 : ภาพรวมสถานการณ์โรค",
        styles["ThaiTitle"]
    ))

    story.append(make_paragraph(
        f"พื้นที่รายงาน: {safe_text(area)}",
        styles["ThaiSub"]
    ))

    story.append(make_paragraph(
        "สรุปสถานการณ์ผู้ป่วยโรคเฝ้าระวังทั้ง 6 โรค",
        styles["ThaiHeading"]
    ))

    summary = (
        df.groupby("disease")["cases"].sum()
        if not df.empty
        else pd.Series(dtype=float)
    )

    total = int(summary.sum())

    rows = [[
        Paragraph("ลำดับ", styles["ThaiCellBold"]),
        Paragraph("ชื่อโรค", styles["ThaiCellBold"]),
        Paragraph("จำนวนผู้ป่วย (ราย)", styles["ThaiCellBold"])
    ]]

    for index, disease in enumerate(DISEASES, start=1):

        count = int(summary.get(disease, 0))

        rows.append([
            str(index),
            Paragraph(safe_text(disease), styles["ThaiCell"]),
            format_number(count)
        ])

    rows.append([
        "",
        Paragraph("รวมผู้ป่วยทั้งหมด", styles["ThaiCellBold"]),
        format_number(total)
    ])

    story.append(make_table(
        rows,
        [22 * mm, 95 * mm, 55 * mm]
    ))

    story.append(Spacer(1, 12))

    story.append(make_paragraph(
        "สรุปผลสถานการณ์",
        styles["ThaiHeading"]
    ))

    story.append(make_paragraph(
        f"พื้นที่ {safe_text(area)} มีจำนวนผู้ป่วยรวม "
        f"<b>{format_number(total)}</b> ราย "
        f"จากโรคเฝ้าระวังจำนวน {len(DISEASES)} โรค",
        styles["ThaiBody"]
    ))

    story.append(Spacer(1, 10))

    story.append(make_paragraph(
        "หมายเหตุ: รายงานนี้ใช้ข้อมูลตามเงื่อนไขที่เลือก "
        "โปรดตรวจสอบแหล่งที่มาของข้อมูลก่อนนำไปใช้อ้างอิง",
        styles["ThaiSmall"]
    ))

    return story


# =====================================================
# 6. PAGE 2 : TREND AND AGE ANALYSIS
# =====================================================

def build_trend(history, area, styles):

    story = []

    story.append(make_paragraph(
        "หน้า 2 : แนวโน้มและกลุ่มอายุ",
        styles["ThaiTitle"]
    ))

    story.append(make_paragraph(
        f"พื้นที่รายงาน: {safe_text(area)}",
        styles["ThaiSub"]
    ))

    story.append(make_paragraph(
        "6.1 เปรียบเทียบแนวโน้มข้อมูลย้อนหลัง 5 ปี",
        styles["ThaiHeading"]
    ))

    if history.empty:

        story.append(make_paragraph(
            "ไม่พบข้อมูลย้อนหลังสำหรับพื้นที่ที่เลือก",
            styles["ThaiBody"]
        ))

    else:

        years = sorted(
            history["year_be"].dropna().unique().tolist()
        )[-5:]

        trend = history[history["year_be"].isin(years)]

        pivot = trend.pivot_table(
            index="disease",
            columns="year_be",
            values="cases",
            aggfunc="sum",
            fill_value=0
        )

        rows = [[
            Paragraph("โรค", styles["ThaiCellBold"])
        ] + [
            Paragraph(str(int(y)), styles["ThaiCellBold"])
            for y in years
        ]]

        for disease in DISEASES:

            values = [
                format_number(pivot.loc[disease, year])
                if disease in pivot.index and year in pivot.columns
                else "0"
                for year in years
            ]

            rows.append([
                Paragraph(safe_text(disease), styles["ThaiCell"])
            ] + values)

        widths = [45 * mm] + [
            25 * mm for _ in years
        ]

        story.append(make_table(rows, widths))

    story.append(Spacer(1, 12))

    story.append(make_paragraph(
        "6.2 จำนวนผู้ป่วยจำแนกตามกลุ่มอายุ",
        styles["ThaiHeading"]
    ))

    if history.empty:

        story.append(make_paragraph(
            "ไม่มีข้อมูลสำหรับวิเคราะห์กลุ่มอายุ",
            styles["ThaiBody"]
        ))

    else:

        ages = (
            history.groupby("age_group")["cases"].sum()
        )

        rows = [[
            Paragraph("กลุ่มอายุ", styles["ThaiCellBold"]),
            Paragraph("จำนวนผู้ป่วย (ราย)", styles["ThaiCellBold"])
        ]]

        for age in AGE_ORDER:

            rows.append([
                Paragraph(safe_text(age), styles["ThaiCell"]),
                format_number(ages.get(age, 0))
            ])

        rows.append([
            Paragraph("รวม", styles["ThaiCellBold"]),
            format_number(ages.sum())
        ])

        story.append(make_table(
            rows,
            [80 * mm, 92 * mm]
        ))

    story.append(Spacer(1, 10))

    story.append(make_paragraph(
        "การวิเคราะห์นี้ใช้เปรียบเทียบแนวโน้มจำนวนผู้ป่วย "
        "และการกระจายตัวของผู้ป่วยตามกลุ่มอายุ "
        "เพื่อสนับสนุนการวางแผนเฝ้าระวัง",
        styles["ThaiSmall"]
    ))

    return story


# =====================================================
# 7. PAGE 3 : FORECAST AND RECOMMENDATIONS
# =====================================================

def build_forecast(history, area, styles):

    story = []

    story.append(make_paragraph(
        "หน้า 3 : การคาดการณ์",
        styles["ThaiTitle"]
    ))

    story.append(make_paragraph(
        f"พื้นที่รายงาน: {safe_text(area)}",
        styles["ThaiSub"]
    ))

    story.append(make_paragraph(
        "7.1 คาดการณ์จำนวนผู้ป่วยเดือนถัดไปแยกรายโรค",
        styles["ThaiHeading"]
    ))

    rows = [[
        Paragraph("ชื่อโรค", styles["ThaiCellBold"]),
        Paragraph("คาดการณ์ผู้ป่วย (ราย)", styles["ThaiCellBold"])
    ]]

    predictions = []

    for disease in DISEASES:

        try:

            pred = next_month_forecast(history, disease)

            value = int(pred.get("cases", 0))

        except Exception:

            value = 0

        predictions.append((disease, value))

        rows.append([
            Paragraph(safe_text(disease), styles["ThaiCell"]),
            format_number(value)
        ])

    total = sum(value for _, value in predictions)

    rows.append([
        Paragraph("รวมคาดการณ์", styles["ThaiCellBold"]),
        format_number(total)
    ])

    story.append(make_table(
        rows,
        [100 * mm, 72 * mm]
    ))

    story.append(Spacer(1, 14))

    story.append(make_paragraph(
        "7.2 ข้อเสนอแนะเพื่อการเฝ้าระวัง",
        styles["ThaiHeading"]
    ))

    ranked = sorted(
        predictions,
        key=lambda x: x[1],
        reverse=True
    )

    recommendations = [
        "1. ให้ความสำคัญกับโรคที่มีค่าคาดการณ์สูง "
        "และติดตามสถานการณ์อย่างต่อเนื่อง",
        "2. ตรวจสอบความถูกต้องและความครบถ้วนของข้อมูล "
        "ก่อนนำไปใช้วางแผนดำเนินงาน",
        "3. ติดตามการเปลี่ยนแปลงของจำนวนผู้ป่วย "
        "ในแต่ละเขตสุขภาพและกลุ่มอายุ",
        "4. ประสานงานทีมเฝ้าระวังในพื้นที่ "
        "เพื่อเตรียมความพร้อมในการติดตามสถานการณ์"
    ]

    if ranked:

        highest = ranked[0]

        recommendations.insert(
            0,
            "โรคที่มีค่าคาดการณ์สูงสุดคือ "
            f"<b>{safe_text(highest[0])}</b> "
            f"จำนวน {format_number(highest[1])} ราย "
            "ควรติดตามสถานการณ์อย่างใกล้ชิด"
        )

    for item in recommendations:

        story.append(make_paragraph(
            item,
            styles["ThaiBody"]
        ))

        story.append(Spacer(1, 6))

    story.append(Spacer(1, 12))

    story.append(make_paragraph(
        "หมายเหตุ: ผลการคาดการณ์เป็นค่าประมาณจากแบบจำลอง "
        "ไม่ใช่คำพยากรณ์ทางระบาดวิทยา "
        "และไม่ควรใช้แทนข้อมูลเฝ้าระวังจริง",
        styles["ThaiSmall"]
    ))

    return story


# =====================================================
# 8. MAIN PDF BUILDER
# =====================================================

def build_pdf(
    df,
    area,
    title,
    historical=None,
    forecast_data=None
):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"T-DTAF - {title}",
        author="T-DTAF"
    )

    styles, regular, bold = create_styles()

    # Monthly overview data
    overview = filter_area(df, area)

    # Historical data
    source = historical if historical is not None else df

    history = filter_area(source, area)

    if not history.empty and "year_be" in history.columns:

        history = history.copy()

        years = sorted(
            history["year_be"].dropna().unique().tolist()
        )[-5:]

        history = history[
            history["year_be"].isin(years)
        ]

    story = []

    # PAGE 1
    story.extend(
        build_overview(
            overview,
            area,
            styles,
            bold
        )
    )

    story.append(PageBreak())

    # PAGE 2
    story.extend(
        build_trend(
            history,
            area,
            styles
        )
    )

    story.append(PageBreak())

    # PAGE 3
    story.extend(
        build_forecast(
            history,
            area,
            styles
        )
    )

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page
    )

    buffer.seek(0)

    return buffer.getvalue()
