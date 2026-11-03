
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Flowable
)

from .data import AGE_ORDER, DISEASES, MONTHS


# =====================================================
# 1. FONT CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = BASE_DIR / "assets" / "fonts"

FONT_FILES = {
    "THSarabun": FONT_DIR / "THSarabunNew.ttf",
    "THSarabun-Bold": FONT_DIR / "THSarabunNew Bold.ttf",
    "THSarabun-Italic": FONT_DIR / "THSarabunNew Italic.ttf",
    "THSarabun-BoldItalic": FONT_DIR / "THSarabunNew BoldItalic.ttf"
}


def register_thai_fonts():

    for name, path in FONT_FILES.items():

        if not path.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์ฟอนต์ {name}: {path}"
            )

        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(name, str(path))
            )

    pdfmetrics.registerFontFamily(
        "THSarabun",
        normal="THSarabun",
        bold="THSarabun-Bold",
        italic="THSarabun-Italic",
        boldItalic="THSarabun-BoldItalic"
    )


# =====================================================
# 2. COLOR THEME
# =====================================================

NAVY = colors.HexColor("#174B75")
BLUE = colors.HexColor("#2676A8")
LIGHT_BLUE = colors.HexColor("#EAF3FB")
PALE_BLUE = colors.HexColor("#F3F7FB")
GREY = colors.HexColor("#64748B")
GRID = colors.HexColor("#DCE5ED")
WHITE = colors.white

CHART_COLORS = [
    colors.HexColor("#2476B9"),
    colors.HexColor("#E69A32"),
    colors.HexColor("#48A078"),
    colors.HexColor("#8B75B7"),
    colors.HexColor("#D96B75"),
    colors.HexColor("#36A6A6")
]


# =====================================================
# 3. PDF STYLES
# =====================================================

def get_styles():

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TH_Title",
        fontName="THSarabun-Bold",
        fontSize=23,
        leading=28,
        alignment=TA_LEFT,
        textColor=NAVY,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="TH_Subtitle",
        fontName="THSarabun",
        fontSize=14,
        leading=19,
        textColor=GREY,
        spaceAfter=12
    ))

    styles.add(ParagraphStyle(
        name="TH_Heading",
        fontName="THSarabun-Bold",
        fontSize=19,
        leading=24,
        textColor=NAVY,
        spaceBefore=5,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="TH_Normal",
        fontName="THSarabun",
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#263648")
    ))

    styles.add(ParagraphStyle(
        name="TH_Small",
        fontName="THSarabun",
        fontSize=12,
        leading=16,
        textColor=GREY
    ))

    styles.add(ParagraphStyle(
        name="TH_Table",
        fontName="THSarabun",
        fontSize=14,
        leading=18
    ))

    styles.add(ParagraphStyle(
        name="TH_TableBold",
        fontName="THSarabun-Bold",
        fontSize=14,
        leading=18,
        textColor=WHITE
    ))

    styles.add(ParagraphStyle(
        name="TH_Recommendation",
        fontName="THSarabun",
        fontSize=15,
        leading=21,
        textColor=colors.HexColor("#263648"),
        leftIndent=8,
        spaceAfter=5
    ))

    return styles


def para(value, style):
    return Paragraph(
        escape(str(value)),
        style
    )


# =====================================================
# 4. TABLE GENERATOR
# =====================================================

def make_table(data, styles, widths):

    rows = []

    for index, row in enumerate(data):

        current_style = (
            styles["TH_TableBold"]
            if index == 0
            else styles["TH_Table"]
        )

        rows.append([
            para(value, current_style)
            for value in row
        ])

    table = Table(
        rows,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT"
    )

    table.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), NAVY),

        ("GRID", (0, 0), (-1, -1), 0.5, GRID),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [WHITE, PALE_BLUE]),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),

    ]))

    return table


# =====================================================
# 5. TREND LINE CHART
# =====================================================

class TrendLineChart(Flowable):

    def __init__(self, df, width=515, height=220):

        super().__init__()

        self.df = df.copy() if df is not None else pd.DataFrame()
        self.width = width
        self.height = height

    def draw(self):

        c = self.canv

        if self.df.empty or not {
            "period", "disease", "cases"
        }.issubset(self.df.columns):

            c.setFont("THSarabun", 14)
            c.drawString(20, self.height / 2, "ไม่มีข้อมูลแนวโน้ม")
            return

        pivot = self.df.pivot_table(
            index="period",
            columns="disease",
            values="cases",
            aggfunc="sum"
        ).fillna(0)

        pivot = pivot.sort_index()

        periods = [str(x) for x in pivot.index]
        diseases = list(pivot.columns)

        left = 45
        right = self.width - 15
        bottom = 48
        top = self.height - 20

        plot_width = right - left
        plot_height = top - bottom

        max_value = max(
            float(pivot.max().max()),
            1
        ) * 1.15

        # Horizontal grid
        c.setFont("THSarabun", 10)

        for i in range(5):

            value = max_value * i / 4
            y = bottom + plot_height * i / 4

            c.setStrokeColor(GRID)
            c.setLineWidth(0.5)
            c.line(left, y, right, y)

            c.setFillColor(GREY)
            c.drawRightString(
                left - 6,
                y - 3,
                f"{value:,.0f}"
            )

        # X axis
        if len(periods) > 1:
            step = plot_width / (len(periods) - 1)
        else:
            step = 0

        label_step = max(1, len(periods) // 6)

        c.setFont("THSarabun", 10)

        for i, period in enumerate(periods):

            if i % label_step == 0 or i == len(periods) - 1:

                x = left + i * step

                c.setFillColor(GREY)
                c.saveState()
                c.translate(x, bottom - 8)
                c.rotate(45)
                c.drawString(0, 0, period)
                c.restoreState()

        # Disease lines
        for disease_index, disease in enumerate(diseases):

            color = CHART_COLORS[
                disease_index % len(CHART_COLORS)
            ]

            values = pivot[disease].tolist()

            points = []

            for i, value in enumerate(values):

                x = left + i * step if len(values) > 1 else left
                y = bottom + (float(value) / max_value) * plot_height

                points.append((x, y))

            c.setStrokeColor(color)
            c.setLineWidth(1.8)

            if len(points) > 1:

                path = c.beginPath()
                path.moveTo(*points[0])

                for point in points[1:]:
                    path.lineTo(*point)

                c.drawPath(path)

            for x, y in points:
                c.setFillColor(color)
                c.circle(x, y, 2, fill=1, stroke=0)

        # Legend
        legend_y = 12
        legend_x = left

        c.setFont("THSarabun", 10)

        for i, disease in enumerate(diseases):

            color = CHART_COLORS[i % len(CHART_COLORS)]

            c.setFillColor(color)
            c.circle(legend_x, legend_y + 3, 3, fill=1, stroke=0)

            c.setFillColor(GREY)
            c.drawString(
                legend_x + 7,
                legend_y,
                str(disease)[:18]
            )

            legend_x += 85

            if legend_x > self.width - 80:
                break


# =====================================================
# 6. AGE BAR CHART
# =====================================================

class AgeBarChart(Flowable):

    def __init__(self, df, width=515, height=175):

        super().__init__()

        self.df = df.copy() if df is not None else pd.DataFrame()
        self.width = width
        self.height = height

    def draw(self):

        c = self.canv

        if self.df.empty:
            return

        left = 105
        right = self.width - 35
        top = self.height - 15

        max_value = max(
            float(self.df["cases"].max()),
            1
        )

        row_height = 23

        c.setFont("THSarabun", 12)

        for i, row in enumerate(self.df.itertuples()):

            y = top - (i + 1) * row_height

            value = float(row.cases)

            bar_width = (
                (right - left) * value / max_value
            )

            c.setFillColor(NAVY)
            c.rect(
                left,
                y,
                bar_width,
                13,
                fill=1,
                stroke=0
            )

            c.setFillColor(GREY)
            c.drawRightString(
                left - 8,
                y + 2,
                str(row.age_group)
            )

            c.drawString(
                min(left + bar_width + 5, right - 30),
                y + 2,
                f"{int(value):,}"
            )


# =====================================================
# 7. FOOTER
# =====================================================

def draw_footer(canvas, doc):

    canvas.saveState()

    canvas.setStrokeColor(GRID)
    canvas.line(
        35,
        28,
        A4[0] - 35,
        28
    )

    canvas.setFont("THSarabun", 10)
    canvas.setFillColor(GREY)

    canvas.drawString(
        35,
        16,
        "T-DTAF | THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM"
    )

    canvas.drawRightString(
        A4[0] - 35,
        16,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# =====================================================
# 8. BUILD THREE-PAGE PDF
# =====================================================

def build_pdf(
    df,
    area,
    title,
    trend_df=None,
    age_df=None,
    forecast_df=None,
    report_month=None,
    report_year=None
):

    register_thai_fonts()

    styles = get_styles()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=40,
        title="T-DTAF Disease Report",
        author="T-DTAF"
    )

    story = []

    month_text = (
        MONTHS[int(report_month) - 1]
        if report_month is not None
        and 1 <= int(report_month) <= 12
        else ""
    )

    period_text = (
        f"{month_text} พ.ศ. {report_year}"
        if month_text
        else str(title)
    )

    # =================================================
    # PAGE 1 - OVERVIEW
    # =================================================

    story.append(para(
        "หน้า 1 · ภาพรวมสถานการณ์โรค",
        styles["TH_Title"]
    ))

    story.append(para(
        f"รายงานสถานการณ์โรคในประเทศไทย | {period_text}",
        styles["TH_Subtitle"]
    ))

    story.append(para(
        f"พื้นที่รายงาน: {area}",
        styles["TH_Heading"]
    ))

    source = df.copy() if df is not None else pd.DataFrame()

    if source.empty:

        summary = pd.DataFrame(
            columns=["disease", "cases"]
        )

    else:

        summary = (
            source.groupby("disease", as_index=False)["cases"]
            .sum()
        )

    # Show all six diseases, including zero values
    disease_master = pd.DataFrame({
        "disease": DISEASES
    })

    summary = disease_master.merge(
        summary,
        on="disease",
        how="left"
    )

    summary["cases"] = (
        summary["cases"].fillna(0).astype(int)
    )

    summary = summary.sort_values(
        "cases",
        ascending=False
    )

    total_cases = int(summary["cases"].sum())

    story.append(para(
        f"จำนวนผู้ป่วยรวมทั้ง 6 โรค: {total_cases:,} ราย",
        styles["TH_Heading"]
    ))

    overview_data = [
        ["ลำดับ", "โรค", "จำนวนผู้ป่วย (ราย)"]
    ]

    for i, row in enumerate(summary.itertuples(), 1):

        overview_data.append([
            i,
            row.disease,
            f"{row.cases:,}"
        ])

    story.append(make_table(
        overview_data,
        styles,
        [55, 280, 155]
    ))

    story.append(Spacer(1, 18))

    story.append(para(
        "สรุปสถานการณ์",
        styles["TH_Heading"]
    ))

    if total_cases > 0:

        top_disease = summary.iloc[0]

        story.append(para(
            f"โรคที่มีจำนวนผู้ป่วยสูงสุดในพื้นที่และช่วงเวลาที่เลือก "
            f"คือ {top_disease['disease']} "
            f"จำนวน {int(top_disease['cases']):,} ราย",
            styles["TH_Normal"]
        ))

    else:

        story.append(para(
            "ไม่พบข้อมูลผู้ป่วยในช่วงเวลาและพื้นที่ที่เลือก",
            styles["TH_Normal"]
        ))

    story.append(Spacer(1, 15))

    story.append(para(
        "หมายเหตุ: ข้อมูลที่ใช้จัดทำรายงานขึ้นอยู่กับแหล่งข้อมูล "
        "และเงื่อนไขที่ผู้ใช้เลือกในระบบ",
        styles["TH_Small"]
    ))

    # =================================================
    # PAGE 2 - TREND AND AGE
    # =================================================

    story.append(PageBreak())

    story.append(para(
        "หน้า 2 · แนวโน้มและกลุ่มอายุ",
        styles["TH_Title"]
    ))

    story.append(para(
        f"เปรียบเทียบข้อมูลย้อนหลัง 5 ปี | พื้นที่: {area}",
        styles["TH_Subtitle"]
    ))

    story.append(para(
        "แนวโน้มจำนวนผู้ป่วยรายเดือน",
        styles["TH_Heading"]
    ))

    if trend_df is not None and not trend_df.empty:

        story.append(
            TrendLineChart(trend_df)
        )

        story.append(para(
            "กราฟแสดงแนวโน้มผู้ป่วยรายเดือน แยกตามโรค "
            "จากข้อมูลย้อนหลังที่มีในระบบ",
            styles["TH_Small"]
        ))

    else:

        story.append(para(
            "ไม่พบข้อมูลแนวโน้มย้อนหลัง",
            styles["TH_Normal"]
        ))

    story.append(Spacer(1, 12))

    story.append(para(
        "แจกแจงจำนวนผู้ป่วยตามกลุ่มอายุ",
        styles["TH_Heading"]
    ))

    ages = age_df.copy() if age_df is not None else pd.DataFrame()

    if ages.empty:

        ages = pd.DataFrame({
            "age_group": AGE_ORDER,
            "cases": [0] * len(AGE_ORDER)
        })

    else:

        ages = ages.groupby(
            "age_group",
            as_index=False
        )["cases"].sum()

        ages["_order"] = ages["age_group"].apply(
            lambda x: AGE_ORDER.index(x)
            if x in AGE_ORDER else 999
        )

        ages = ages.sort_values("_order").drop(
            columns="_order"
        )

    story.append(AgeBarChart(ages))

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
        [280, 210]
    ))

    # =================================================
    # PAGE 3 - FORECAST
    # =================================================

    story.append(PageBreak())

    story.append(para(
        "หน้า 3 · การคาดการณ์",
        styles["TH_Title"]
    ))

    story.append(para(
        f"คาดการณ์ผู้ป่วยเดือนถัดไป | พื้นที่: {area}",
        styles["TH_Subtitle"]
    ))

    predictions = (
        forecast_df.copy()
        if forecast_df is not None
        else pd.DataFrame()
    )

    if not predictions.empty:

        if "cases" not in predictions.columns:
            predictions["cases"] = 0

        if "disease" in predictions.columns:

            predictions = (
                predictions.groupby(
                    "disease",
                    as_index=False
                )["cases"].sum()
            )

    else:

        predictions = pd.DataFrame({
            "disease": DISEASES,
            "cases": [0] * len(DISEASES)
        })

    story.append(para(
        "จำนวนผู้ป่วยคาดการณ์แยกรายโรค",
        styles["TH_Heading"]
    ))

    forecast_data = [
        ["ลำดับ", "โรค", "จำนวนคาดการณ์ (ราย)"]
    ]

    for i, row in enumerate(predictions.itertuples(), 1):

        forecast_data.append([
            i,
            row.disease,
            f"{int(row.cases):,}"
        ])

    story.append(make_table(
        forecast_data,
        styles,
        [55, 280, 155]
    ))

    total_forecast = int(
        predictions["cases"].fillna(0).sum()
    )

    story.append(Spacer(1, 15))

    story.append(para(
        f"รวมจำนวนผู้ป่วยคาดการณ์: {total_forecast:,} ราย",
        styles["TH_Heading"]
    ))

    story.append(para(
        "ข้อเสนอแนะในการเฝ้าระวัง",
        styles["TH_Heading"]
    ))

    recommendations = [
        "1. ติดตามสถานการณ์โรคที่มีจำนวนผู้ป่วยคาดการณ์สูง "
        "และจัดลำดับความสำคัญในการเฝ้าระวัง",

        "2. ประสานหน่วยงานสาธารณสุขในพื้นที่ "
        "เพื่อตรวจสอบข้อมูลและติดตามการเปลี่ยนแปลงของจำนวนผู้ป่วย",

        "3. ตรวจสอบความครบถ้วนและความถูกต้องของข้อมูล "
        "ก่อนนำผลการคาดการณ์ไปใช้ประกอบการวางแผน",

        "4. ทบทวนผลการคาดการณ์ร่วมกับข้อมูลผู้ป่วยจริง "
        "เมื่อมีการปรับปรุงข้อมูลรอบถัดไป"
    ]

    for item in recommendations:

        story.append(para(
            item,
            styles["TH_Recommendation"]
        ))

    story.append(Spacer(1, 15))

    story.append(para(
        "ข้อจำกัด: ผลการคาดการณ์เป็นค่าประมาณจากข้อมูลที่มีในระบบ "
        "ไม่ใช่คำพยากรณ์ทางระบาดวิทยา "
        "และควรใช้ร่วมกับการประเมินสถานการณ์จริง",
        styles["TH_Small"]
    ))

    # =================================================
    # BUILD
    # =================================================

    doc.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer
    )

    return buffer.getvalue()
