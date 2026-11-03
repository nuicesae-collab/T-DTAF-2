from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable
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
    "THSarabun-BoldItalic": FONT_DIR / "THSarabunNew BoldItalic.ttf",
}


def register_thai_fonts():
    """Register TH Sarabun New fonts bundled in assets/fonts."""
    for font_name, font_path in FONT_FILES.items():
        if not font_path.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์ฟอนต์ {font_name}: {font_path}"
            )

        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

    pdfmetrics.registerFontFamily(
        "THSarabun",
        normal="THSarabun",
        bold="THSarabun-Bold",
        italic="THSarabun-Italic",
        boldItalic="THSarabun-BoldItalic",
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
    colors.HexColor("#36A6A6"),
]


# =====================================================
# 3. PDF STYLES
# =====================================================

def get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TH_Title",
        fontName="THSarabun-Bold",
        fontSize=21,
        leading=25,
        alignment=TA_LEFT,
        textColor=NAVY,
        spaceAfter=3,
    ))

    styles.add(ParagraphStyle(
        name="TH_Subtitle",
        fontName="THSarabun",
        fontSize=13,
        leading=16,
        textColor=GREY,
        spaceAfter=7,
    ))

    styles.add(ParagraphStyle(
        name="TH_Heading",
        fontName="THSarabun-Bold",
        fontSize=17,
        leading=20,
        textColor=NAVY,
        spaceBefore=3,
        spaceAfter=5,
    ))

    styles.add(ParagraphStyle(
        name="TH_Normal",
        fontName="THSarabun",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#263648"),
    ))

    styles.add(ParagraphStyle(
        name="TH_Small",
        fontName="THSarabun",
        fontSize=10.5,
        leading=13,
        textColor=GREY,
    ))

    styles.add(ParagraphStyle(
        name="TH_Table",
        fontName="THSarabun",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#263648"),
    ))

    styles.add(ParagraphStyle(
        name="TH_TableBold",
        fontName="THSarabun-Bold",
        fontSize=12,
        leading=14,
        textColor=WHITE,
    ))

    styles.add(ParagraphStyle(
        name="TH_Recommendation",
        fontName="THSarabun",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#263648"),
        leftIndent=7,
        spaceAfter=3,
    ))

    return styles


def para(value, style):
    return Paragraph(escape(str(value)), style)


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
        rows.append([para(value, current_style) for value in row])

    table = Table(
        rows,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_BLUE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return table


# =====================================================
# 5. TREND LINE CHART
# =====================================================

class TrendLineChart(Flowable):
    def __init__(self, df, width=525, height=145):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv

        required = {"period", "disease", "cases"}
        if self.df.empty or not required.issubset(self.df.columns):
            c.setFont("THSarabun", 13)
            c.setFillColor(GREY)
            c.drawString(20, self.height / 2, "ไม่มีข้อมูลแนวโน้ม")
            return

        pivot = self.df.pivot_table(
            index="period",
            columns="disease",
            values="cases",
            aggfunc="sum",
        ).fillna(0).sort_index()

        periods = [str(x) for x in pivot.index]
        diseases = list(pivot.columns)

        left, right = 48, self.width - 12
        bottom, top = 35, self.height - 14
        plot_width = right - left
        plot_height = top - bottom

        max_value = max(float(pivot.max().max()), 1) * 1.15
        step = plot_width / (len(periods) - 1) if len(periods) > 1 else 0

        # Grid and Y-axis labels
        c.setFont("THSarabun", 9)
        for i in range(5):
            value = max_value * i / 4
            y = bottom + plot_height * i / 4
            c.setStrokeColor(GRID)
            c.setLineWidth(0.4)
            c.line(left, y, right, y)
            c.setFillColor(GREY)
            c.drawRightString(left - 5, y - 3, f"{value:,.0f}")

        # X-axis labels
        label_step = max(1, len(periods) // 7)
        for i, period in enumerate(periods):
            if i % label_step == 0 or i == len(periods) - 1:
                x = left + i * step if len(periods) > 1 else left
                c.setFillColor(GREY)
                c.saveState()
                c.translate(x, bottom - 7)
                c.rotate(35)
                c.drawString(0, 0, period[:12])
                c.restoreState()

        # Disease lines
        for disease_index, disease in enumerate(diseases):
            color = CHART_COLORS[disease_index % len(CHART_COLORS)]
            values = pivot[disease].tolist()
            points = []

            for i, value in enumerate(values):
                x = left + i * step if len(values) > 1 else left
                y = bottom + (float(value) / max_value) * plot_height
                points.append((x, y))

            c.setStrokeColor(color)
            c.setLineWidth(1.5)

            if len(points) > 1:
                path = c.beginPath()
                path.moveTo(*points[0])
                for point in points[1:]:
                    path.lineTo(*point)
                c.drawPath(path)

            for x, y in points:
                c.setFillColor(color)
                c.circle(x, y, 1.8, fill=1, stroke=0)

        # Compact legend (two rows if needed)
        c.setFont("THSarabun", 9)
        legend_x = left
        legend_y = 9

        for i, disease in enumerate(diseases):
            if i == 3:
                legend_x = left
                legend_y = -2

            color = CHART_COLORS[i % len(CHART_COLORS)]
            c.setFillColor(color)
            c.circle(legend_x, legend_y + 3, 2.5, fill=1, stroke=0)
            c.setFillColor(GREY)
            label = str(disease)
            c.drawString(legend_x + 6, legend_y, label[:18])
            legend_x += 155


# =====================================================
# 6. AGE BAR CHART
# =====================================================

class AgeBarChart(Flowable):
    def __init__(self, df, width=525):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        # Dynamic height: one compact row per age group.
        self.row_height = 12
        self.height = max(35, len(self.df) * self.row_height + 8)
        self.width = width

    def draw(self):
        c = self.canv

        if self.df.empty:
            c.setFont("THSarabun", 12)
            c.setFillColor(GREY)
            c.drawString(10, self.height / 2, "ไม่มีข้อมูลกลุ่มอายุ")
            return

        left = 95
        right = self.width - 48
        top = self.height - 5
        max_value = max(float(self.df["cases"].max()), 1)

        c.setFont("THSarabun", 9.5)

        for i, row in enumerate(self.df.itertuples()):
            y = top - (i + 1) * self.row_height
            value = max(0, float(row.cases))
            bar_width = (right - left) * value / max_value

            c.setFillColor(NAVY)
            c.roundRect(left, y + 1, max(bar_width, 0.5), 7, 2, fill=1, stroke=0)

            c.setFillColor(GREY)
            c.drawRightString(left - 6, y + 1, str(row.age_group))
            c.drawString(
                min(left + bar_width + 4, right - 35),
                y + 1,
                f"{int(value):,}",
            )


# =====================================================
# 7. FOOTER
# =====================================================

def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(35, 28, A4[0] - 35, 28)

    canvas.setFont("THSarabun", 9)
    canvas.setFillColor(GREY)
    canvas.drawString(
        35, 16,
        "T-DTAF | THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM",
    )
    canvas.drawRightString(A4[0] - 35, 16, f"Page {doc.page}")
    canvas.restoreState()


# =====================================================
# 8. DATA PREPARATION HELPERS
# =====================================================

def prepare_age_data(age_df):
    ages = age_df.copy() if age_df is not None else pd.DataFrame()

    if ages.empty:
        return pd.DataFrame({
            "age_group": AGE_ORDER,
            "cases": [0] * len(AGE_ORDER),
        })

    if not {"age_group", "cases"}.issubset(ages.columns):
        return pd.DataFrame({
            "age_group": AGE_ORDER,
            "cases": [0] * len(AGE_ORDER),
        })

    ages["cases"] = pd.to_numeric(ages["cases"], errors="coerce").fillna(0)
    ages = ages.groupby("age_group", as_index=False)["cases"].sum()

    order_map = {name: i for i, name in enumerate(AGE_ORDER)}
    ages["_order"] = ages["age_group"].map(order_map).fillna(999)
    ages = ages.sort_values("_order").drop(columns="_order")

    # Include missing age groups as zero.
    master = pd.DataFrame({"age_group": AGE_ORDER})
    ages = master.merge(ages, on="age_group", how="left")
    ages["cases"] = ages["cases"].fillna(0).astype(int)
    return ages


def prepare_forecast_data(forecast_df):
    predictions = (
        forecast_df.copy()
        if forecast_df is not None
        else pd.DataFrame()
    )

    if predictions.empty or not {"disease", "cases"}.issubset(predictions.columns):
        predictions = pd.DataFrame({
            "disease": DISEASES,
            "cases": [0] * len(DISEASES),
        })
    else:
        predictions["cases"] = pd.to_numeric(
            predictions["cases"], errors="coerce"
        ).fillna(0)
        predictions = predictions.groupby(
            "disease", as_index=False
        )["cases"].sum()

        master = pd.DataFrame({"disease": DISEASES})
        predictions = master.merge(
            predictions, on="disease", how="left"
        )
        predictions["cases"] = predictions["cases"].fillna(0)

    predictions["cases"] = predictions["cases"].clip(lower=0).astype(int)
    return predictions


# =====================================================
# 9. BUILD THREE-PAGE PDF
# =====================================================

def build_pdf(
    df,
    area,
    title,
    trend_df=None,
    age_df=None,
    forecast_df=None,
    report_month=None,
    report_year=None,
):
    register_thai_fonts()
    styles = get_styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=30,
        bottomMargin=38,
        title="T-DTAF Disease Report",
        author="T-DTAF",
    )

    story = []

    # Report period
    month_text = ""
    if report_month is not None:
        try:
            month_number = int(report_month)
            if 1 <= month_number <= 12:
                month_text = MONTHS[month_number - 1]
        except (TypeError, ValueError):
            month_text = ""

    if month_text and report_year is not None:
        period_text = f"{month_text} พ.ศ. {report_year}"
    else:
        period_text = str(title)

    # Prepare overview data and show all six diseases.
    source = df.copy() if df is not None else pd.DataFrame()
    if (
        not source.empty
        and {"disease", "cases"}.issubset(source.columns)
    ):
        source["cases"] = pd.to_numeric(
            source["cases"], errors="coerce"
        ).fillna(0)
        summary = source.groupby(
            "disease", as_index=False
        )["cases"].sum()
    else:
        summary = pd.DataFrame(columns=["disease", "cases"])

    disease_master = pd.DataFrame({"disease": DISEASES})
    summary = disease_master.merge(
        summary, on="disease", how="left"
    )
    summary["cases"] = summary["cases"].fillna(0).astype(int)
    summary = summary.sort_values("cases", ascending=False)
    total_cases = int(summary["cases"].sum())

    # =================================================
    # PAGE 1 — OVERVIEW
    # =================================================

    story.append(para("หน้า 1 · ภาพรวมสถานการณ์", styles["TH_Title"]))
    story.append(para(
        f"รายงานสถานการณ์โรค 6 โรค | {period_text}",
        styles["TH_Subtitle"],
    ))
    story.append(para(f"พื้นที่รายงาน: {area}", styles["TH_Heading"]))

    story.append(para(
        f"จำนวนผู้ป่วยรวมทั้ง 6 โรค: {total_cases:,} ราย",
        styles["TH_Heading"],
    ))

    overview_data = [["ลำดับ", "โรค", "จำนวนผู้ป่วย (ราย)"]]
    for i, row in enumerate(summary.itertuples(), 1):
        overview_data.append([i, row.disease, f"{row.cases:,}"])

    story.append(make_table(
        overview_data, styles, [55, 280, 155]
    ))
    story.append(Spacer(1, 12))
    story.append(para("สรุปสถานการณ์", styles["TH_Heading"]))

    if total_cases > 0:
        top_disease = summary.iloc[0]
        story.append(para(
            f"โรคที่มีจำนวนผู้ป่วยสูงสุดในพื้นที่และช่วงเวลาที่เลือก "
            f"คือ {top_disease['disease']} "
            f"จำนวน {int(top_disease['cases']):,} ราย",
            styles["TH_Normal"],
        ))
    else:
        story.append(para(
            "ไม่พบข้อมูลผู้ป่วยในช่วงเวลาและพื้นที่ที่เลือก",
            styles["TH_Normal"],
        ))

    story.append(Spacer(1, 10))
    story.append(para(
        "หมายเหตุ: รายงานนี้สรุปตามพื้นที่ ปี และเดือนที่ผู้ใช้เลือก "
        "โปรดตรวจสอบแหล่งข้อมูลก่อนนำไปใช้อ้างอิง",
        styles["TH_Small"],
    ))

    # Force page 2 to start on a new page.
    story.append(PageBreak())

    # =================================================
    # PAGE 2 — TREND AND AGE
    # =================================================

    story.append(para(
        "หน้า 2 · แนวโน้มและกลุ่มอายุ",
        styles["TH_Title"],
    ))
    story.append(para(
        f"เปรียบเทียบข้อมูลย้อนหลัง 5 ปี | พื้นที่: {area}",
        styles["TH_Subtitle"],
    ))

    story.append(para(
        "แนวโน้มจำนวนผู้ป่วยรายเดือน",
        styles["TH_Heading"],
    ))

    if trend_df is not None and not trend_df.empty:
        story.append(TrendLineChart(trend_df, height=145))
        story.append(para(
            "กราฟแสดงแนวโน้มผู้ป่วยรายเดือนแยกตามโรค "
            "จากข้อมูลย้อนหลังที่มีในระบบ",
            styles["TH_Small"],
        ))
    else:
        story.append(para(
            "ไม่พบข้อมูลแนวโน้มย้อนหลังในพื้นที่ที่เลือก",
            styles["TH_Normal"],
        ))

    story.append(Spacer(1, 5))
    story.append(para(
        "จำนวนผู้ป่วยจำแนกตามกลุ่มอายุ",
        styles["TH_Heading"],
    ))

    ages = prepare_age_data(age_df)
    story.append(AgeBarChart(ages))

    age_table = [["กลุ่มอายุ", "จำนวนผู้ป่วย (ราย)"]]
    for row in ages.itertuples():
        age_table.append([row.age_group, f"{int(row.cases):,}"])

    story.append(make_table(
        age_table, styles, [280, 210]
    ))

    # Force page 3 to start on a new page.
    story.append(PageBreak())

    # =================================================
    # PAGE 3 — FORECAST AND RECOMMENDATIONS
    # =================================================

    story.append(para(
        "หน้า 3 · การคาดการณ์",
        styles["TH_Title"],
    ))
    story.append(para(
        f"คาดการณ์ผู้ป่วยเดือนถัดไป | พื้นที่: {area}",
        styles["TH_Subtitle"],
    ))

    predictions = prepare_forecast_data(forecast_df)

    story.append(para(
        "จำนวนผู้ป่วยคาดการณ์แยกรายโรค",
        styles["TH_Heading"],
    ))

    forecast_table = [["ลำดับ", "โรค", "จำนวนคาดการณ์ (ราย)"]]
    for i, row in enumerate(predictions.itertuples(), 1):
        forecast_table.append([
            i, row.disease, f"{int(row.cases):,}"
        ])

    story.append(make_table(
        forecast_table, styles, [55, 280, 155]
    ))

    total_forecast = int(predictions["cases"].sum())
    story.append(Spacer(1, 10))
    story.append(para(
        f"รวมจำนวนผู้ป่วยคาดการณ์: {total_forecast:,} ราย",
        styles["TH_Heading"],
    ))

    story.append(para(
        "ข้อเสนอแนะในการเฝ้าระวัง",
        styles["TH_Heading"],
    ))

    recommendations = [
        "1. ติดตามโรคที่มีจำนวนผู้ป่วยคาดการณ์สูง "
        "และจัดลำดับความสำคัญในการเฝ้าระวัง",

        "2. ประสานหน่วยงานสาธารณสุขในพื้นที่ "
        "เพื่อตรวจสอบข้อมูลและติดตามการเปลี่ยนแปลงของจำนวนผู้ป่วย",

        "3. ตรวจสอบความครบถ้วนและความถูกต้องของข้อมูล "
        "ก่อนนำผลการคาดการณ์ไปใช้ประกอบการวางแผน",

        "4. ทบทวนผลการคาดการณ์ร่วมกับข้อมูลผู้ป่วยจริง "
        "เมื่อมีการปรับปรุงข้อมูลรอบถัดไป",
    ]

    for item in recommendations:
        story.append(para(item, styles["TH_Recommendation"]))

    story.append(Spacer(1, 8))
    story.append(para(
        "ข้อจำกัด: ผลการคาดการณ์เป็นค่าประมาณจากข้อมูลที่มีในระบบ "
        "ไม่ใช่คำพยากรณ์ทางระบาดวิทยา "
        "ควรใช้ร่วมกับการประเมินสถานการณ์จริง",
        styles["TH_Small"],
    ))

    # Build all three pages with page number footer.
    doc.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    return buffer.getvalue()
