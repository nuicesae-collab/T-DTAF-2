from io import BytesIO
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
from .data import AGE_ORDER
def build_pdf(df,area,title):
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=28,leftMargin=28,topMargin=30,bottomMargin=30)
    styles=getSampleStyleSheet(); story=[Paragraph("T-DTAF - "+title,styles["Title"]),Paragraph("พื้นที่: "+area,styles["Normal"]),Spacer(1,12)]
    if df.empty: story.append(Paragraph("ไม่พบข้อมูล",styles["Normal"]))
    else:
        summary=df.groupby("disease",as_index=False).cases.sum()
        data=[["โรค","จำนวนผู้ป่วย"]]+[[str(r.disease),f"{int(r.cases):,}"] for r in summary.itertuples()]
        t=Table(data,colWidths=[350,120]);t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#174b75")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("PADDING",(0,0),(-1,-1),6)]));story.append(t)
        story.append(Spacer(1,10))
        ages=df.groupby("age_group",as_index=False).cases.sum()
        data=[["กลุ่มอายุ","จำนวนผู้ป่วย"]]+[[str(r.age_group),f"{int(r.cases):,}"] for r in ages.itertuples()]
        t=Table(data,colWidths=[350,120]);t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#174b75")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("PADDING",(0,0),(-1,-1),6)]));story.append(t)
    story.append(Spacer(1,16));story.append(Paragraph("หมายเหตุ: ตรวจสอบสถานะและแหล่งที่มาของข้อมูลก่อนนำไปใช้อ้างอิง",styles["Italic"]))
    doc.build(story);return buf.getvalue()
