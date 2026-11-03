
from io import BytesIO
from pathlib import Path

import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .data import AGE_ORDER


# ==================================================
# 1. LOAD THAI FONTS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = BASE_DIR / "assets" / "fonts"

FONT_REGULAR = FONT_DIR / "THSarabunNew.ttf"
FONT_BOLD = FONT_DIR / "THSarabunNew Bold.ttf"
FONT_ITALIC = FONT_DIR / "THSarabunNew Italic.ttf"
FONT_BOLD_ITALIC = FONT_DIR / "THSarabunNew BoldItalic.ttf"


def register_thai_fonts():

    required_fonts = [
        FONT_REGULAR,
        FONT_BOLD,
        FONT_ITALIC,
        FONT_BOLD_ITALIC
    ]

    for font in required_fonts:
        if not font.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์ฟอนต์: {font}"
            )

    registered = pdfmetrics.getRegisteredFontNames()

    if "THSarabun" not in registered:
        pdfmetrics.registerFont(
            TTFont("THSarabun", str(FONT_REGULAR))
        )

    if "THSarabun-Bold" not in registered:
        pdfmetrics.registerFont(
            TTFont("THSarabun-Bold", str(FONT_BOLD))
        )

    if "THSarabun-Italic" not in registered:
        pdfmetrics.registerFont(
            TTFont("THSarabun-Italic", str(FONT_ITALIC))
        )

    if "THSarabun-BoldItalic" not in registered:
        pdfmetrics.registerFont(
            TTFont("THSarabun-BoldItalic", str(FONT_BOLD_ITALIC))
        )

    pdfmetrics.registerFontFamily(
        "THSarabun",
        normal="THSarabun",
        bold="THSarabun-Bold",
        italic="THSarabun-Italic",
        boldItalic="THSarabun-BoldItalic"
    )


# ==================================================
# 2. PDF STYLES
# ==================================================

def get_thai_styles():

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ThaiTitle",
        fontName="THSarabun-Bold",
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#174B75"),
        spaceAfter=12
    ))

    styles.add(ParagraphStyle(
        name="ThaiHeading",
        fontName="THSarabun-Bold",
        fontSize=18,
        leading=23,
        textColor=colors.HexColor("#174B75"),
        spaceBefore=8,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ThaiNormal",
        fontName="THSarabun",
        fontSize=15,
        leading=20,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name="ThaiSmall",
        fontName="THSarabun",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748B")
    ))

    styles.add(ParagraphStyle(
        name="ThaiTable",
        fontName="THSarabun",
        fontSize=14,
        leading=18
    ))

    styles.add(ParagraphStyle(
        name="ThaiTableHeader",
        fontName="THSarabun-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.white
    ))

    return styles


# ==================================================
# 3. TABLE FUNCTION
# ==================================================

def make_table(data, styles, col_widths):

    converted = []

    for row_index, row in enumerate(data):

        style = (
            styles["ThaiTableHeader"]
            if row_index == 0
            else styles["ThaiTable"]
        )

        converted.append([
            Paragraph(str(value), style)
            for value in row
        ])

    table = Table(
        converted,
        colWidths=col_widths,
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#174B75")),

        ("GRID", (0, 0), (-1, -1),
         0.4, colors.HexColor("#D5E1EC")),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [
             colors.white,
             colors.HexColor("#F1F6FB")
         ]),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    return table


# ==================================================
# 4. BUILD PDF
# ==================================================

def build_pdf(df, area, title):

    register_thai_fonts()

    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = get_thai_styles()

    story = []

    # Title
    story.append(Paragraph(
        "T-DTAF",
        styles["ThaiTitle"]
    ))

    story.append(Paragraph(
        str(title),
        styles["ThaiHeading"]
    ))

    story.append(Paragraph(
        f"พื้นที่รายงาน: {area}",
        styles["ThaiNormal"]
    ))

    story.append(Spacer(1, 15))

    if df.empty:

        story.append(Paragraph(
            "ไม่พบข้อมูลตามเงื่อนไขที่เลือก",
            styles["ThaiNormal"]
        ))

    else:

        # ------------------------------------------
        # Disease summary
        # ------------------------------------------

        story.append(Paragraph(
            "สรุปจำนวนผู้ป่วยแยกตามโรค",
            styles["ThaiHeading"]
        ))

        summary = (
            df.groupby("disease", as_index=False)["cases"]
            .sum()
            .sort_values("cases", ascending=False)
        )

        data = [
            ["โรค", "จำนวนผู้ป่วย (ราย)"]
        ]

        for row in summary.itertuples():
            data.append([
                row.disease,
                f"{int(row.cases):,}"
            ])

        story.append(make_table(
            data,
            styles,
            [330, 160]
        ))

        story.append(Spacer(1, 20))

        # ------------------------------------------
        # Age summary
        # ------------------------------------------

        story.append(Paragraph(
            "สรุปจำนวนผู้ป่วยตามกลุ่มอายุ",
            styles["ThaiHeading"]
        ))

        ages = (
            df.groupby("age_group", as_index=False)["cases"]
            .sum()
        )

        if "age_group" in ages.columns:
            age_order = {
                age: i for i, age in enumerate(AGE_ORDER)
            }

            ages["_order"] = ages["age_group"].map(
                age_order
            )

            ages = ages.sort_values("_order")
            ages = ages.drop(columns="_order")

        age_data = [
            ["กลุ่มอายุ", "จำนวนผู้ป่วย (ราย)"]
        ]

        for row in ages.itertuples():
            age_data.append([
                row.age_group,
                f"{int(row.cases):,}"
            ])

        story.append(make_table(
            age_data,
            styles,
            [330, 160]
        ))

    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "หมายเหตุ: โปรดตรวจสอบแหล่งที่มาและความถูกต้องของข้อมูล "
        "ก่อนนำไปใช้อ้างอิง",
        styles["ThaiSmall"]
    ))

    # Build PDF
    doc.build(story)

    return buf.getvalue()
