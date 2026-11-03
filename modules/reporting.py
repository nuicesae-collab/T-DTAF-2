from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable, KeepTogether
)

from .data import AGE_ORDER, DISEASES, MONTHS

NAVY = colors.HexColor('#174B75')
BLUE = colors.HexColor('#2878A8')
PALE = colors.HexColor('#EAF3FA')
LIGHT = colors.HexColor('#F4F7FA')
GREY = colors.HexColor('#64748B')
GRID = colors.HexColor('#D7E1EA')
GREEN = colors.HexColor('#EAF6EF')
RED = colors.HexColor('#FCECEC')
ORANGE = colors.HexColor('#FFF4DF')
LINE_COLORS = [
    colors.HexColor('#2878A8'), colors.HexColor('#D8892B'),
    colors.HexColor('#3B9A72'), colors.HexColor('#8B70B5'),
    colors.HexColor('#D35F70'), colors.HexColor('#2A9D9A')
]


def _register_fonts():
    """Prefer TH Sarabun New; it includes Thai and Western numerals."""
    root = Path(__file__).resolve().parent.parent
    font_dir = root / 'assets' / 'fonts'
    files = {
        'TDTafThai': font_dir / 'THSarabunNew.ttf',
        'TDTafThai-Bold': font_dir / 'THSarabunNew Bold.ttf',
        'TDTafThai-Italic': font_dir / 'THSarabunNew Italic.ttf',
        'TDTafThai-BoldItalic': font_dir / 'THSarabunNew BoldItalic.ttf',
    }
    # NotoLoopedThai is retained as a fallback for installations that only
    # contain the two Noto files. TH Sarabun New is preferred for full digits.
    if not files['TDTafThai'].exists() or not files['TDTafThai-Bold'].exists():
        files = {
            'TDTafThai': font_dir / 'NotoLoopedThai-Regular.ttf',
            'TDTafThai-Bold': font_dir / 'NotoLoopedThai-Bold.ttf',
        }
    for name, path in files.items():
        if not path.exists():
            raise FileNotFoundError(
                f'ไม่พบไฟล์ฟอนต์ {path.name} กรุณาวางฟอนต์ TH Sarabun New '
                'หรือ NotoLoopedThai ไว้ใน assets/fonts/'
            )
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        'TDTafThai', normal='TDTafThai', bold='TDTafThai-Bold',
        italic='TDTafThai-Italic' if 'TDTafThai-Italic' in files else 'TDTafThai',
        boldItalic='TDTafThai-BoldItalic' if 'TDTafThai-BoldItalic' in files else 'TDTafThai-Bold'
    )
    return 'TDTafThai', 'TDTafThai-Bold'


def _styles():
    regular, bold = _register_fonts()
    return {
        'title': ParagraphStyle('TTitleV2', fontName=bold, fontSize=17, leading=21,
                                textColor=NAVY, spaceAfter=3),
        'subtitle': ParagraphStyle('TSubV2', fontName=regular, fontSize=8.5, leading=11,
                                   textColor=GREY, spaceAfter=6),
        'section': ParagraphStyle('TSecV2', fontName=bold, fontSize=12, leading=15,
                                  textColor=NAVY, spaceBefore=5, spaceAfter=5),
        'body': ParagraphStyle('TBodyV2', fontName=regular, fontSize=8.5, leading=12,
                               textColor=colors.HexColor('#243447'), spaceAfter=3),
        'small': ParagraphStyle('TSmallV2', fontName=regular, fontSize=7, leading=9,
                                textColor=GREY),
        'table': ParagraphStyle('TTableV2', fontName=regular, fontSize=7.5, leading=9,
                                textColor=colors.HexColor('#243447')),
        'table_bold': ParagraphStyle('TTableBoldV2', fontName=bold, fontSize=7.5, leading=9,
                                     textColor=colors.white),
        'kpi': ParagraphStyle('TKpiV2', fontName=bold, fontSize=16, leading=18,
                              textColor=NAVY, alignment=TA_CENTER),
        'kpi_label': ParagraphStyle('TKpiLabelV2', fontName=regular, fontSize=7.5, leading=9,
                                    textColor=GREY, alignment=TA_CENTER),
        'callout': ParagraphStyle('TCalloutV2', fontName=regular, fontSize=8, leading=11,
                                  textColor=colors.HexColor('#243447'), leftIndent=5),
    }


def _p(value, style):
    return Paragraph(escape(str(value)), style)


def _num(value):
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def _fmt(value):
    return f'{_num(value):,}'


def _pct(value):
    try:
        return f'{float(value):+.1f}%'
    except (TypeError, ValueError):
        return '—'


def _month_label(month, year):
    try:
        return f'{MONTHS[int(month) - 1]} พ.ศ. {int(year)}'
    except Exception:
        return 'ไม่ระบุช่วงเวลา'


def _next_period(month, year):
    try:
        m, y = int(month), int(year)
        if m == 12:
            m, y = 1, y + 1
        else:
            m += 1
        return _month_label(m, y)
    except Exception:
        return 'เดือนถัดไป'


def _area_filter(frame, area):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    out = frame.copy()
    if area != 'ประเทศไทย' and 'health_region' in out.columns:
        out = out[out['health_region'].astype(str) == str(area)]
    return out


def _disease_totals(frame):
    if not isinstance(frame, pd.DataFrame) or frame.empty or not {'disease', 'cases'}.issubset(frame.columns):
        totals = pd.DataFrame(columns=['disease', 'cases'])
    else:
        work = frame.copy()
        work['cases'] = pd.to_numeric(work['cases'], errors='coerce').fillna(0)
        totals = work.groupby('disease', as_index=False)['cases'].sum()
    known = list(DISEASES) if DISEASES else totals.get('disease', pd.Series(dtype=str)).tolist()
    mapping = dict(zip(totals.get('disease', []), totals.get('cases', [])))
    return pd.DataFrame({'disease': known, 'cases': [_num(mapping.get(d, 0)) for d in known]})


def _table(rows, widths, header=True, font_size=None):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    commands = [
        ('GRID', (0, 0), (-1, -1), 0.35, GRID),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [('BACKGROUND', (0, 0), (-1, 0), NAVY)]
        if len(rows) > 1:
            commands.append(('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]))
    table.setStyle(TableStyle(commands))
    return table


def _cell(text, styles, bold=False):
    return _p(text, styles['table_bold'] if bold else styles['table'])


class AnnualTrendChart(Flowable):
    """Readable monthly line chart with year-only x-axis labels."""
    def __init__(self, frame, width=500, height=142, regular_font='TDTafThai'):
        super().__init__()
        self.frame = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
        self.width, self.height, self.font = width, height, regular_font

    def draw(self):
        c = self.canv
        required = {'year_be', 'month', 'disease', 'cases'}
        if self.frame.empty or not required.issubset(self.frame.columns):
            c.setFont(self.font, 9)
            c.setFillColor(GREY)
            c.drawString(8, self.height / 2, 'ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแนวโน้มรายเดือน')
            return
        d = self.frame.copy()
        d['year_be'] = pd.to_numeric(d['year_be'], errors='coerce')
        d['month'] = pd.to_numeric(d['month'], errors='coerce')
        d['cases'] = pd.to_numeric(d['cases'], errors='coerce').fillna(0)
        d = d.dropna(subset=['year_be', 'month'])
        d['year_be'] = d['year_be'].astype(int)
        d['month'] = d['month'].astype(int)
        years = sorted(d['year_be'].unique().tolist())[-5:]
        d = d[d['year_be'].isin(years)]
        monthly = d.groupby(['year_be', 'month', 'disease'], as_index=False)['cases'].sum()
        periods = sorted(set(zip(monthly['year_be'].tolist(), monthly['month'].tolist())))
        diseases = list(DISEASES) if DISEASES else sorted(monthly['disease'].unique().tolist())
        lookup = {(int(r.year_be), int(r.month), r.disease): float(r.cases)
                  for r in monthly.itertuples()}
        if not periods:
            return
        left, right, bottom, top = 42, self.width - 12, 31, self.height - 12
        plot_w, plot_h = right - left, top - bottom
        ymax = max(1.0, max(lookup.values(), default=1.0)) * 1.12
        c.setFont(self.font, 7)
        for i in range(5):
            value = ymax * i / 4
            y = bottom + plot_h * i / 4
            c.setStrokeColor(GRID)
            c.setLineWidth(0.45)
            c.line(left, y, right, y)
            c.setFillColor(GREY)
            c.drawRightString(left - 5, y - 2, f'{value:,.0f}')
        xs = [left + plot_w * i / max(1, len(periods) - 1) for i in range(len(periods))]
        # Label only January of each year to keep the timeline uncluttered.
        for i, (year, month) in enumerate(periods):
            if month == 1 or i == 0:
                c.setFillColor(GREY)
                c.drawCentredString(xs[i], bottom - 12, str(year))
        for j, disease in enumerate(diseases):
            vals = [lookup.get((year, month, disease), 0.0) for year, month in periods]
            pts = [(xs[i], bottom + (v / ymax) * plot_h) for i, v in enumerate(vals)]
            color = LINE_COLORS[j % len(LINE_COLORS)]
            c.setStrokeColor(color)
            c.setFillColor(color)
            c.setLineWidth(1.35)
            if len(pts) > 1:
                path = c.beginPath()
                path.moveTo(*pts[0])
                for pt in pts[1:]:
                    path.lineTo(*pt)
                c.drawPath(path)
            for x, y in pts:
                c.circle(x, y, 1.5, fill=1, stroke=0)
        # Two-row legend, placed below the x-axis.
        legend_y = 14
        col_w = (self.width - 20) / 3
        for j, disease in enumerate(diseases[:6]):
            row, col = divmod(j, 3)
            x = 12 + col * col_w
            y = legend_y - row * 10
            color = LINE_COLORS[j % len(LINE_COLORS)]
            c.setFillColor(color)
            c.circle(x, y + 2, 2.3, fill=1, stroke=0)
            c.setFillColor(GREY)
            c.setFont(self.font, 6.5)
            c.drawString(x + 5, y, str(disease)[:27])


class AgeBarChart(Flowable):
    def __init__(self, age_frame, width=500, height=91, regular_font='TDTafThai'):
        super().__init__()
        self.frame = age_frame.copy() if isinstance(age_frame, pd.DataFrame) else pd.DataFrame()
        self.width, self.height, self.font = width, height, regular_font

    def draw(self):
        if self.frame.empty:
            return
        c = self.canv
        d = self.frame.copy()
        maxv = max(1, float(pd.to_numeric(d['cases'], errors='coerce').fillna(0).max()))
        left, right = 80, self.width - 48
        row_h = min(14, (self.height - 5) / max(1, len(d)))
        c.setFont(self.font, 7)
        for i, row in enumerate(d.itertuples()):
            y = self.height - (i + 1) * row_h + 2
            val = _num(row.cases)
            bar_w = (right - left) * val / maxv
            c.setFillColor(NAVY)
            c.roundRect(left, y, bar_w, 7, 2, fill=1, stroke=0)
            c.setFillColor(GREY)
            c.drawRightString(left - 5, y + 1, str(row.age_group)[:14])
            c.drawString(min(right + 4, left + bar_w + 4), y + 1, _fmt(val))


def _page_chrome(canvas, doc):
    regular, bold = _register_fonts()
    canvas.saveState()
    # Consistent running header
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 10 * mm, A4[0], 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(bold, 8)
    canvas.drawString(18 * mm, A4[1] - 6.6 * mm, 'T-DTAF | รายงานวิเคราะห์สถานการณ์โรค')
    # Footer with page number
    canvas.setStrokeColor(GRID)
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.setFillColor(GREY)
    canvas.setFont(regular, 6.5)
    canvas.drawString(18 * mm, 9.5 * mm, 'T-DTAF | Thailand Disease Trend Analysis & Forecasting System')
    canvas.drawRightString(A4[0] - 18 * mm, 9.5 * mm, f'หน้า {doc.page} จาก 3')
    canvas.restoreState()


def _annual_age_summary(history):
    if history.empty or not {'age_group', 'cases'}.issubset(history.columns):
        return pd.DataFrame(columns=['age_group', 'cases'])
    age = history.copy()
    age['cases'] = pd.to_numeric(age['cases'], errors='coerce').fillna(0)
    grouped = age.groupby('age_group', as_index=False)['cases'].sum()
    order = {v: i for i, v in enumerate(AGE_ORDER)}
    grouped['_order'] = grouped['age_group'].map(order).fillna(999)
    return grouped.sort_values('_order').drop(columns='_order')


def _trend_text(history, styles):
    if history.empty or not {'year_be', 'cases'}.issubset(history.columns):
        return _p('ยังไม่มีข้อมูลเพียงพอสำหรับสรุปแนวโน้มรายปี', styles['body'])
    d = history.copy()
    d['year_be'] = pd.to_numeric(d['year_be'], errors='coerce')
    d['cases'] = pd.to_numeric(d['cases'], errors='coerce').fillna(0)
    annual = d.dropna(subset=['year_be']).groupby('year_be')['cases'].sum().sort_index()
    if len(annual) < 2:
        return _p('มีข้อมูลไม่ครบ 2 ปี จึงยังไม่สามารถเปรียบเทียบแนวโน้มระหว่างปีได้', styles['body'])
    first_year, last_year = int(annual.index[0]), int(annual.index[-1])
    first, last = float(annual.iloc[0]), float(annual.iloc[-1])
    if first > 0:
        change = (last - first) / first * 100
        direction = 'เพิ่มขึ้น' if change > 0 else ('ลดลง' if change < 0 else 'ทรงตัว')
        sentence = f'ยอดผู้ป่วยรวมเปลี่ยนจาก { _fmt(first) } รายในปี {first_year} เป็น {_fmt(last)} รายในปี {last_year} หรือ{direction} {_pct(change)}'
    else:
        sentence = f'ยอดผู้ป่วยรวมในปี {first_year} เท่ากับ 0 ราย และปี {last_year} เท่ากับ {_fmt(last)} ราย'
    return _p(sentence + ' เมื่อเทียบระหว่างปีแรกและปีล่าสุดที่มีข้อมูลในช่วงรายงาน', styles['body'])


def _recommendation(disease):
    name = str(disease)
    if 'ไข้หวัดใหญ่' in name:
        return 'ติดตามการป่วยเป็นกลุ่มก้อนในสถานศึกษา สถานดูแลผู้สูงอายุ และชุมชน พร้อมสื่อสารการป้องกันโรคทางเดินหายใจ'
    if 'ปอดบวม' in name:
        return 'ติดตามผู้ป่วยกลุ่มเสี่ยงและการเข้ารับบริการด้วยอาการทางเดินหายใจ ประสานหน่วยบริการเมื่อพบการเพิ่มขึ้นผิดปกติ'
    if 'อุจจาระร่วง' in name:
        return 'เฝ้าระวังผู้ป่วยที่มีอาการคล้ายกันในพื้นที่เดียวกัน ตรวจสอบแหล่งน้ำและอาหารร่วมกับหน่วยงานที่เกี่ยวข้อง'
    if 'มือเท้าปาก' in name:
        return 'ติดตามการป่วยในศูนย์เด็กเล็กและสถานศึกษา เน้นการคัดกรองอาการและการทำความสะอาดสิ่งแวดล้อม'
    if 'ไข้เลือดออก' in name:
        return 'ติดตามผู้ป่วยรายพื้นที่และสำรวจแหล่งเพาะพันธุ์ยุงลาย ประสานการควบคุมพาหะตามมาตรการของพื้นที่'
    if 'ลมแดด' in name:
        return 'ติดตามกลุ่มเสี่ยงในช่วงอากาศร้อน สื่อสารการหลีกเลี่ยงความร้อนและการสังเกตอาการเจ็บป่วยจากความร้อน'
    return 'ติดตามการเปลี่ยนแปลงของผู้ป่วยรายพื้นที่และตรวจสอบข้อมูลกับหน่วยบริการก่อนกำหนดมาตรการ'


def build_pdf(
    df,
    area,
    title,
    historical_df=None,
    forecast_df=None,
    previous_df=None,
    report_month=None,
    report_year=None,
    source_label='ฐานข้อมูลที่ระบบใช้งาน',
    historical_source_label='ฐานข้อมูลย้อนหลังที่ระบบโหลด',
    generated_at=None,
):
    """Build a fixed three-page Thai PDF report."""
    styles = _styles()
    selected = _area_filter(df, area)
    history = _area_filter(historical_df, area) if historical_df is not None else selected.copy()
    future = _area_filter(forecast_df, area) if forecast_df is not None else pd.DataFrame()
    previous = _area_filter(previous_df, area) if previous_df is not None else pd.DataFrame()
    regular, _ = _register_fonts()
    if generated_at is None:
        generated_at = datetime.now().strftime('%d/%m/%Y %H:%M')
    elif isinstance(generated_at, datetime):
        generated_at = generated_at.strftime('%d/%m/%Y %H:%M')
    report_period = _month_label(report_month, report_year)
    next_period = _next_period(report_month, report_year)
    previous_period = _month_label(
        12 if int(report_month or 1) == 1 else int(report_month or 1) - 1,
        int(report_year or 0) - 1 if int(report_month or 1) == 1 else int(report_year or 0)
    )
    meta = f'พื้นที่: {area} | ช่วงรายงาน: {report_period} | จัดทำ: {generated_at} น.'

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=f'T-DTAF - {title}', author='T-DTAF'
    )
    story = []

    # PAGE 1: OVERVIEW + MONTH-ON-MONTH COMPARISON
    story += [
        _p('หน้า 1 · ภาพรวมสถานการณ์', styles['title']),
        _p(f'{title} | {meta}', styles['subtitle']),
        _p('จำนวนผู้ป่วยรวมแยกตามโรค', styles['section']),
    ]
    current_totals = _disease_totals(selected)
    previous_totals = _disease_totals(previous)
    total_current = _num(current_totals['cases'].sum())
    total_previous = _num(previous_totals['cases'].sum())
    total_change = ((total_current - total_previous) / total_previous * 100) if total_previous else None
    kpi_rows = [[
        _p(_fmt(total_current), styles['kpi']),
        _p(_fmt(total_previous), styles['kpi']),
        _p(_pct(total_change) if total_change is not None else 'ไม่มีฐานเปรียบเทียบ', styles['kpi'])
    ], [
        _p('ผู้ป่วยเดือนรายงาน (ราย)', styles['kpi_label']),
        _p(f'ผู้ป่วยเดือนก่อน ({previous_period})', styles['kpi_label']),
        _p('เปลี่ยนแปลงจากเดือนก่อน', styles['kpi_label'])
    ]]
    kpi = Table(kpi_rows, colWidths=[doc.width / 3] * 3)
    kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PALE),
        ('BOX', (0, 0), (-1, -1), 0.5, GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story += [kpi, Spacer(1, 7)]
    rows = [[_cell('โรค', styles, True), _cell('ผู้ป่วย (ราย)', styles, True),
             _cell('สัดส่วน', styles, True), _cell('เดือนก่อน', styles, True),
             _cell('เปลี่ยนแปลง', styles, True)]]
    prev_map = dict(zip(previous_totals['disease'], previous_totals['cases']))
    for r in current_totals.itertuples():
        share = (r.cases / total_current * 100) if total_current else 0
        old = _num(prev_map.get(r.disease, 0))
        delta = r.cases - old
        delta_pct = ((delta / old) * 100) if old else None
        rows.append([
            _cell(r.disease, styles), _cell(_fmt(r.cases), styles),
            _cell(f'{share:.1f}%', styles), _cell(_fmt(old), styles),
            _cell(_pct(delta_pct) if delta_pct is not None else ('ใหม่/ไม่มีฐาน' if r.cases else '—'), styles)
        ])
    story.append(_table(rows, [doc.width * .30, doc.width * .15, doc.width * .15, doc.width * .17, doc.width * .23]))
    if not selected.empty and total_current:
        top = current_totals.sort_values('cases', ascending=False).head(3)
        top_text = 'อันดับโรคที่พบมาก: ' + ' | '.join(
            f'{r.disease} {_fmt(r.cases)} ราย ({r.cases / total_current * 100:.1f}%)'
            for r in top.itertuples() if r.cases > 0
        )
        story += [Spacer(1, 7), _p(top_text, styles['body'])]
    else:
        story += [Spacer(1, 7), _p('ไม่พบข้อมูลผู้ป่วยในช่วงเวลาที่เลือก', styles['body'])]
    story += [
        Spacer(1, 5),
        _p(f'แหล่งข้อมูล: {source_label}', styles['small']),
        _p('หมายเหตุ: สัดส่วนคำนวณจากจำนวนผู้ป่วยรวมของ 6 โรคในเดือนรายงาน ส่วนการเปลี่ยนแปลงคำนวณเทียบกับเดือนก่อนหน้า หากไม่มีข้อมูลเดือนก่อนจะแสดงว่าไม่มีฐานเปรียบเทียบ', styles['small']),
        PageBreak()
    ]

    # PAGE 2: FIVE-YEAR TREND + AGE GROUP ANALYSIS
    story += [
        _p('หน้า 2 · แนวโน้มและกลุ่มอายุ', styles['title']),
        _p(f'พื้นที่: {area} | จัดทำ: {generated_at} น. | แหล่งข้อมูล: {historical_source_label}', styles['subtitle']),
    ]
    if history.empty:
        story.append(_p('ไม่มีข้อมูลย้อนหลังสำหรับแสดงแนวโน้มและกลุ่มอายุ', styles['body']))
        age = pd.DataFrame(columns=['age_group', 'cases'])
        years = []
    else:
        h = history.copy()
        if 'year_be' in h.columns:
            h['year_be'] = pd.to_numeric(h['year_be'], errors='coerce')
            all_years = sorted(h['year_be'].dropna().astype(int).unique().tolist())
            years = all_years[-5:]
            h = h[h['year_be'].isin(years)]
        else:
            years = []
        story += [
            _p('แนวโน้มจำนวนผู้ป่วยรายเดือนย้อนหลัง 5 ปี แยกตามโรค', styles['section']),
            AnnualTrendChart(h, width=doc.width, height=142, regular_font=regular),
            _p('กราฟแสดงข้อมูลรายเดือนตลอดช่วง 5 ปี โดยระบุปี พ.ศ. บนแกนเวลาเฉพาะจุดเริ่มต้นของแต่ละปี และแสดงจำนวนผู้ป่วย (ราย) บนแกนตั้ง', styles['small']),
            Spacer(1, 3),
            _p('บทวิเคราะห์แนวโน้ม', styles['section']),
            _trend_text(h, styles),
        ]
        age = _annual_age_summary(h)
    year_span = f'{years[0]}–{years[-1]}' if years else 'ไม่พบปีข้อมูล'
    story += [
        Spacer(1, 4),
        _p(f'จำนวนผู้ป่วยจำแนกตามกลุ่มอายุ (ข้อมูลสะสมช่วงปี พ.ศ. {year_span})', styles['section'])
    ]
    if age.empty:
        story.append(_p('ไม่มีข้อมูลกลุ่มอายุ หรือชุดข้อมูลไม่มีคอลัมน์ age_group', styles['body']))
    else:
        story.append(AgeBarChart(age, width=doc.width, height=88, regular_font=regular))
        age_rows = [[_cell('กลุ่มอายุ', styles, True), _cell('จำนวนผู้ป่วย (ราย)', styles, True)]]
        age_rows += [[_cell(r.age_group, styles), _cell(_fmt(r.cases), styles)] for r in age.itertuples()]
        story.append(_table(age_rows, [doc.width * .52, doc.width * .48]))
        top_age = age.sort_values('cases', ascending=False).iloc[0]
        total_age = _num(age['cases'].sum())
        share_age = (_num(top_age['cases']) / total_age * 100) if total_age else 0
        story += [Spacer(1, 4), _p(
            f'กลุ่มอายุที่พบผู้ป่วยมากที่สุดคือ {top_age["age_group"]} '
            f'{_fmt(top_age["cases"])} ราย ({share_age:.1f}% ของยอดรวมตามกลุ่มอายุ)', styles['body'])]
    story += [
        Spacer(1, 4),
        _p('ข้อควรพิจารณา: การสรุปแนวโน้มเป็นการเปรียบเทียบจำนวนที่บันทึกในฐานข้อมูล ไม่ได้ปรับตามขนาดประชากรหรือความครบถ้วนของการรายงาน', styles['small']),
        PageBreak()
    ]

    # PAGE 3: NEXT MONTH FORECAST VS SELECTED MONTH
    story += [
        _p('หน้า 3 · การคาดการณ์และข้อเสนอแนะ', styles['title']),
        _p(f'พื้นที่: {area} | เดือนปัจจุบัน: {report_period} | เดือนคาดการณ์: {next_period}', styles['subtitle']),
        _p(f'จัดทำ: {generated_at} น. | แหล่งข้อมูล: {source_label}', styles['small']),
        Spacer(1, 5),
        _p('เปรียบเทียบจำนวนผู้ป่วยเดือนรายงานกับค่าคาดการณ์เดือนถัดไป', styles['section'])
    ]
    current_map = dict(zip(current_totals['disease'], current_totals['cases']))
    pred_totals = _disease_totals(future)
    rows = [[_cell('โรค', styles, True), _cell(f'จริง {report_period}', styles, True),
             _cell(f'คาดการณ์ {next_period}', styles, True), _cell('เปลี่ยนแปลง', styles, True)]]
    for r in pred_totals.itertuples():
        current = _num(current_map.get(r.disease, 0))
        delta = r.cases - current
        delta_pct = (delta / current * 100) if current else None
        rows.append([
            _cell(r.disease, styles), _cell(_fmt(current), styles), _cell(_fmt(r.cases), styles),
            _cell(_pct(delta_pct) if delta_pct is not None else ('ไม่มีฐาน' if r.cases else '—'), styles)
        ])
    story.append(_table(rows, [doc.width * .31, doc.width * .21, doc.width * .24, doc.width * .24]))
    total_pred = _num(pred_totals['cases'].sum())
    total_delta = total_pred - total_current
    total_delta_pct = (total_delta / total_current * 100) if total_current else None
    story += [
        Spacer(1, 7),
        _p(f'รวมคาดการณ์เดือน {next_period}: {_fmt(total_pred)} ราย', styles['section']),
        _p(f'เทียบกับเดือนรายงาน: {_pct(total_delta_pct) if total_delta_pct is not None else "ไม่มีฐานเปรียบเทียบ"}', styles['body']),
        _p('ข้อเสนอแนะเฉพาะโรค', styles['section'])
    ]
    positive = pred_totals[pred_totals['cases'] > 0].sort_values('cases', ascending=False)
    if positive.empty:
        story.append(_p('ยังไม่มีค่าคาดการณ์ที่มากกว่า 0 ควรตรวจสอบข้อมูลนำเข้าและทบทวนแบบจำลองก่อนใช้วางแผน', styles['body']))
    else:
        for r in positive.itertuples():
            story.append(_p(f'{r.disease} ({_fmt(r.cases)} ราย): {_recommendation(r.disease)}', styles['body']))
    story += [
        Spacer(1, 5),
        _p('ข้อจำกัด: ค่าคาดการณ์เป็นค่าประมาณจากข้อมูลและวิธีการที่ระบบได้รับ ไม่ใช่การยืนยันการระบาด ควรตรวจสอบกับข้อมูลผู้ป่วยจริงและผู้รับผิดชอบในพื้นที่ก่อนตัดสินใจ', styles['small']),
    ]

    doc.build(story, onFirstPage=_page_chrome, onLaterPages=_page_chrome)
    return buf.getvalue()
