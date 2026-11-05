
import streamlit as st
import pandas as pd
import altair as alt
import base64
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

from modules.data import load_all, DISEASES, AGE_ORDER, REGIONS, MONTHS
from modules.auth import login_gate, logout_button
from modules.analysis import (
    monthly_trend, age_summary, next_month_forecast, kpi_summary
)
from modules.db import (
    save_survey_record, list_recipients, save_recipient,
    delete_recipient, load_survey_records
)
from modules.reporting import build_pdf
from modules.line_oa import send_line_message
from modules.drive import upload_pdf_to_drive


# =====================================================
# 1. PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="T-DTAF | ระบบวิเคราะห์แนวโน้มและคาดการณ์โรค",
    page_icon="📊",
    layout="wide"
)


# =====================================================
# 2. CSS DESIGN - PROTOTYPE
# =====================================================

st.markdown("""
<style>

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

[data-testid="stSidebar"] {
    background: #f3f6fa;
}

.hero {
    padding: 22px 25px;
    border-radius: 14px;
    background: linear-gradient(120deg,#123b5d,#1d628f);
    color: white;
    margin-bottom: 22px;
}

.hero h1 {
    color: white;
    margin: 0;
    font-size: 30px;
}

.hero p {
    color: #d5e6f2;
    margin: 5px 0 0;
    font-size: 13px;
}

h2 {
    color: #173f61;
    font-weight: 700;
}

h3 {
    color: #214b6d;
    font-size: 17px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 13px;
}

.kpi-card {
    padding: 18px;
    border-radius: 12px;
    min-height: 125px;
    margin-bottom: 10px;
    border: 1px solid rgba(0,0,0,.04);
}

.kpi-card small {
    display: block;
    font-size: 13px;
    color: #567188;
}

.kpi-card strong {
    display: block;
    font-size: 29px;
    margin: 9px 0 3px;
    font-weight: 750;
}

.kpi-card span {
    font-size: 12px;
    color: #718395;
}

.kpi-blue {
    background: #eaf3ff;
}

.kpi-blue strong {
    color: #174e80;
}

.kpi-red {
    background: #fff0f1;
}

.kpi-red strong {
    color: #b84d5a;
}

.kpi-gold {
    background: #fff7e5;
}

.kpi-gold strong {
    color: #946000;
}

.kpi-green {
    background: #edf8f1;
}

.kpi-green strong {
    color: #26734d;
}

.section-note {
    color: #718395;
    font-size: 12px;
}

.age-summary-card {
    background: #f3f7fb;
    border: 1px solid #dce7f0;
    border-radius: 10px;
    padding: 12px 14px;
    min-height: 66px;
    margin-bottom: 8px;
}

.age-summary-card .age-label {
    color: #294b67;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 2px;
}

.age-summary-card .age-value {
    color: #17649a;
    font-size: 20px;
    font-weight: 800;
    line-height: 1.15;
}

.age-summary-card .age-unit {
    color: #718395;
    font-size: 11px;
    margin-left: 3px;
}

div[data-testid="stSelectbox"] label {
    color: #526b80;
    font-weight: 600;
}

div[data-testid="stDataFrame"] {
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. HEADER
# =====================================================

st.markdown("""
<div class="hero">
    <h1>T-DTAF</h1>
    <p>THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM</p>
</div>
""", unsafe_allow_html=True)


# =====================================================
# 4. LOAD DATA
# =====================================================

hist, forecast, simulation = load_all()

ALL_DISEASES = ["ทุกโรค"] + DISEASES

YEAR_OPTIONS = sorted(
    set(hist.year_be.unique().tolist())
    | set(forecast.year_be.unique().tolist())
    | set(simulation.year_be.unique().tolist()),
    reverse=True
)

if not YEAR_OPTIONS:
    YEAR_OPTIONS = [2569, 2568, 2567, 2566, 2565]


# =====================================================
# 5. MENU
# =====================================================

pages = [
    "ภาพรวมสถานการณ์โรค",
    "วิเคราะห์แนวโน้มและคาดการณ์",
    "บันทึกข้อมูลทีมสำรวจ",
    "รายงานประจำเดือน",
    "จัดการผู้รับรายงาน"
]

page = st.sidebar.radio("เมนูหลัก", pages)

st.sidebar.caption(
    "ข้อมูลสังเคราะห์/จำลอง ต้องไม่ใช้แทนสถิติจริง"
)

if page in [
    "บันทึกข้อมูลทีมสำรวจ",
    "รายงานประจำเดือน",
    "จัดการผู้รับรายงาน"
]:
    role = {
        "บันทึกข้อมูลทีมสำรวจ": "INPUT",
        "รายงานประจำเดือน": "REPORT",
        "จัดการผู้รับรายงาน": "ADMIN"
    }[page]

    if not login_gate(role):
        st.stop()

    logout_button(role)


# =====================================================
# 6. COMMON FUNCTIONS
# =====================================================

def get_year_data(year):

    if year in hist.year_be.values:
        return hist[hist.year_be == year].copy()

    if year in forecast.year_be.values:
        return forecast[forecast.year_be == year].copy()

    if year in simulation.year_be.values:
        return simulation[simulation.year_be == year].copy()

    return pd.DataFrame()


def filter_data(df, area, disease, month=None):

    if df.empty:
        return df.copy()

    result = df.copy()

    if area != "ภาพรวมประเทศไทย":
        result = result[
            result["health_region"] == area
        ]

    if disease != "ทุกโรค":
        result = result[
            result["disease"] == disease
        ]

    if month is not None and month != 0:
        result = result[
            result["month"] == month
        ]

    return result


def show_kpi(label, value, unit, color):

    st.markdown(f"""
    <div class="kpi-card {color}">
        <small>{label}</small>
        <strong>{value}</strong>
        <span>{unit}</span>
    </div>
    """, unsafe_allow_html=True)


def format_number(value):

    return f"{int(value):,}"


# =====================================================
# 7. OVERVIEW - ภาพรวมสถานการณ์โรค
# =====================================================

if page == "ภาพรวมสถานการณ์โรค":

    st.subheader("ภาพรวมสถานการณ์โรค")

    st.caption(
        "สรุปสถานการณ์ผู้ป่วยและข้อมูลโรคที่เฝ้าระวังในประเทศไทย"
    )

    # ---------- FILTER CARD ----------

    with st.container(border=True):

        st.markdown("### ตัวกรองข้อมูล")

        c1, c2, c3, c4 = st.columns(4)

        area = c1.selectbox(
            "พื้นที่",
            ["ภาพรวมประเทศไทย"] + REGIONS,
            key="ov_area"
        )

        year = c2.selectbox(
            "ปี พ.ศ.",
            YEAR_OPTIONS,
            index=0,
            key="ov_year"
        )

        month = c3.selectbox(
            "เดือน",
            [0] + list(range(1, 13)),
            format_func=lambda x:
                "ทุกเดือน" if x == 0 else MONTHS[x-1],
            key="ov_month"
        )

        disease = c4.selectbox(
            "โรค",
            ALL_DISEASES,
            key="ov_disease"
        )

    # ---------- FILTER DATA ----------

    source = get_year_data(year)

    view = filter_data(
        source,
        area,
        disease,
        month
    )

    # ---------- KPI CALCULATION ----------

    total_cases = int(view["cases"].sum()) if not view.empty else 0

    disease_count = view["disease"].nunique() if not view.empty else 0

    month_count = view["month"].nunique() if not view.empty else 0

    # Latest month based on filtered dataset
    if not view.empty:

        latest_month = int(view["month"].max())

        latest_total = int(
            view[view["month"] == latest_month]["cases"].sum()
        )

        previous_month = latest_month - 1

        if previous_month >= 1:

            previous_total = int(
                source[
                    (source["month"] == previous_month)
                    & (
                        (source["health_region"] == area)
                        if area != "ภาพรวมประเทศไทย"
                        else True
                    )
                    & (
                        (source["disease"] == disease)
                        if disease != "ทุกโรค"
                        else True
                    )
                ]["cases"].sum()
            )

        else:
            previous_total = 0

    else:

        latest_total = 0
        previous_total = 0

    if previous_total > 0:

        change = (
            (latest_total - previous_total)
            / previous_total
        ) * 100

        change_text = f"{change:+.1f}%"

        change_direction = (
            "เพิ่มขึ้น" if change > 0
            else "ลดลง" if change < 0
            else "คงที่"
        )

    else:

        change_text = "-"
        change_direction = "ไม่มีข้อมูลเปรียบเทียบ"

    # ---------- KPI CARDS ----------

    st.markdown("### สรุปสถานการณ์")

    st.caption("ข้อมูลตามเงื่อนไขที่เลือก")

    cols = st.columns(4)

    with cols[0]:
        show_kpi(
            "ผู้ป่วยสะสม",
            format_number(total_cases),
            "ราย",
            "kpi-blue"
        )

    with cols[1]:
        show_kpi(
            "ผู้ป่วยเดือนล่าสุด",
            format_number(latest_total),
            "ราย",
            "kpi-red"
        )

    with cols[2]:
        show_kpi(
            "เปลี่ยนแปลงจากเดือนก่อน",
            change_text,
            change_direction,
            "kpi-gold"
        )

    with cols[3]:
        show_kpi(
            "โรคที่ติดตาม",
            f"{disease_count} โรค",
            f"{month_count} เดือน",
            "kpi-green"
        )

    # ---------- DISEASE TABLE ----------

    with st.container(border=True):

        st.markdown("### จำนวนผู้ป่วยแยกตามโรค")

        if not view.empty:

            summary = (
                view.groupby("disease", as_index=False)["cases"]
                .sum()
                .sort_values("cases", ascending=False)
            )

            summary.columns = [
                "โรค",
                "จำนวนผู้ป่วย (ราย)"
            ]

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("ไม่พบข้อมูลตามเงื่อนไขที่เลือก")

    # ---------- BAR CHART ----------

    if not view.empty:

        st.markdown("### กราฟจำนวนผู้ป่วย")

        chart_data = (
            view.groupby("disease")["cases"]
            .sum()
            .sort_values(ascending=False)
        )

        st.bar_chart(chart_data)

    st.caption(
        "หมายเหตุ: ข้อมูล Historical และ Forecast "
        "ต้องตรวจสอบแหล่งที่มาก่อนนำไปใช้อ้างอิง"
    )


# =====================================================
# 8. ANALYSIS - วิเคราะห์แนวโน้มและคาดการณ์
# =====================================================

elif page == "วิเคราะห์แนวโน้มและคาดการณ์":

    st.subheader("วิเคราะห์แนวโน้มและคาดการณ์")

    st.caption(
        "เปรียบเทียบข้อมูลย้อนหลัง วิเคราะห์กลุ่มอายุ "
        "และคาดการณ์ผู้ป่วยเดือนถัดไป"
    )

    # ---------- ANALYSIS FILTER ----------

    with st.container(border=True):

        st.markdown("### ตัวกรองการวิเคราะห์")

        c1, c2, c3, c4 = st.columns(4)

        mode = c1.selectbox(
            "รูปแบบการวิเคราะห์",
            [
                "เปรียบเทียบย้อนหลัง 5 ปี",
                "ดูเฉพาะปีที่เลือก"
            ],
            key="analysis_mode"
        )

        disease = c2.selectbox(
            "เลือกโรค",
            ALL_DISEASES,
            key="analysis_disease"
        )

        area = c3.selectbox(
            "เขตสุขภาพ",
            ["ภาพรวมประเทศไทย"] + REGIONS,
            key="analysis_area"
        )

        selected_year = c4.selectbox(
            "เลือกปี พ.ศ.",
            YEAR_OPTIONS,
            index=0,
            key="analysis_year"
        )

    # ---------- SELECT ANALYSIS DATA ----------

    if mode == "เปรียบเทียบย้อนหลัง 5 ปี":

        analysis_data = hist.copy()

        if not analysis_data.empty:

            # แปลงเลขเดือนให้เป็นตัวเลขก่อน เพื่อให้เรียงตามปฏิทินเสมอ
            trend_source = analysis_data.copy()
            month_lookup = {name: i + 1 for i, name in enumerate(MONTHS)}
            trend_source["month_num"] = trend_source["month"].apply(
                lambda value: month_lookup.get(str(value).strip(), value)
            )
            trend_source["month_num"] = pd.to_numeric(
                trend_source["month_num"], errors="coerce"
            )
            trend_source = trend_source.dropna(subset=["month_num"])
            trend_source["month_num"] = trend_source["month_num"].astype(int)
            trend_source = trend_source[
                trend_source["month_num"].between(1, 12)
            ]

            trend = (
                trend_source
                .groupby(
                    ["year_be", "month_num"],
                    as_index=False
                )["cases"]
                .sum()
            )

            # คงรูปแบบกราฟเส้นเดิมไว้ และบังคับให้แกนเดือนเรียง 1–12
            trend_pivot = trend.pivot(
                index="month_num",
                columns="year_be",
                values="cases"
            ).reindex(range(1, 13), fill_value=0).fillna(0)

            trend_pivot.index = [
                MONTHS[month_no - 1] for month_no in trend_pivot.index
            ]
            trend_pivot.index.name = "เดือน"

            st.line_chart(
                trend_pivot,
                use_container_width=True
            )

            st.caption(
                "กราฟแสดงแนวโน้มจำนวนผู้ป่วยรายเดือน "
                "จำแนกตามปีที่เลือก เรียงเดือนมกราคมถึงธันวาคม"
            )

        else:

            st.info("ไม่มีข้อมูลสำหรับสร้างกราฟ")


    # ---------- AGE ANALYSIS + FORECAST ----------

    col_age, col_forecast = st.columns([1.2, 0.8])

    # ---------- AGE ANALYSIS ----------

    with col_age:

        with st.container(border=True):

            st.markdown("### วิเคราะห์ผู้ป่วยตามกลุ่มอายุ")
            st.caption("แสดงจำนวนผู้ป่วยแยกตามกลุ่มอายุในรูปแบบการ์ด")

            if not analysis_data.empty and "age_group" in analysis_data.columns:

                ages = (
                    analysis_data
                    .groupby("age_group", as_index=False)["cases"]
                    .sum()
                )

                ages["age_group"] = pd.Categorical(
                    ages["age_group"],
                    categories=AGE_ORDER,
                    ordered=True
                )
                ages = ages.sort_values("age_group")

                age_values = {
                    str(row["age_group"]): int(row["cases"])
                    for _, row in ages.iterrows()
                    if pd.notna(row["age_group"])
                }

                for i in range(0, len(AGE_ORDER), 2):

                    age_cols = st.columns(2)

                    for col, age_label in zip(
                        age_cols,
                        AGE_ORDER[i:i + 2]
                    ):

                        value = age_values.get(age_label, 0)

                        with col:
                            st.markdown(
                                f"""
                                <div class="age-summary-card">
                                    <div class="age-label">{age_label}</div>
                                    <div class="age-value">
                                        {value:,}<span class="age-unit">ราย</span>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                st.caption(
                    "หมายเหตุ: แสดงตามกลุ่มอายุที่มีอยู่ในฐานข้อมูลปัจจุบัน "
                    "ซึ่งแบ่งเป็น 6 กลุ่มอายุ"
                )

            else:

                st.info("ไม่พบข้อมูลสำหรับวิเคราะห์กลุ่มอายุ")

    # ---------- FORECAST ----------

    with col_forecast:

        with st.container(border=True):

            st.markdown("### คาดการณ์ผู้ป่วยเดือนถัดไป")

            forecast_source = pd.concat(
                [hist, forecast],
                ignore_index=True
            )

            if area != "ภาพรวมประเทศไทย":

                forecast_source = forecast_source[
                    forecast_source.health_region == area
                ]

            if disease != "ทุกโรค":

                forecast_diseases = [disease]

            else:

                forecast_diseases = DISEASES

            forecast_rows = []

            for d in forecast_diseases:

                pred = next_month_forecast(
                    forecast_source,
                    d
                )

                forecast_rows.append({
                    "โรค": d,
                    "คาดการณ์ (ราย)": pred["cases"]
                })

            forecast_table = pd.DataFrame(
                forecast_rows
            )

            if not forecast_table.empty:

                st.dataframe(
                    forecast_table,
                    use_container_width=True,
                    hide_index=True
                )

                forecast_total = int(
                    forecast_table["คาดการณ์ (ราย)"].sum()
                )

                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        padding:15px 0;
                    ">
                        <b>รวมคาดการณ์</b>
                        <strong style="
                            font-size:25px;
                            color:#17649a;
                        ">
                            {forecast_total:,} ราย
                        </strong>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.info("ไม่พบข้อมูลสำหรับคาดการณ์")

            st.caption(
                "ค่าคาดการณ์เป็นการประมาณเชิงสถิติอย่างง่าย "
                "ไม่ใช่คำพยากรณ์ทางระบาดวิทยา"
            )

# 9. SURVEY INPUT - บันทึกข้อมูลทีมสำรวจ
# =====================================================

elif page == "บันทึกข้อมูลทีมสำรวจ":

    st.subheader("บันทึกข้อมูลทีมสำรวจ")
    st.caption(
        "แบบฟอร์มบันทึกจำนวนผู้ป่วยรายเดือนเข้าสู่ฐานข้อมูลกลาง"
    )

    # ---------- SURVEY INFORMATION ----------

    with st.container(border=True):

        st.markdown("### ข้อมูลการสำรวจ")

        c1, c2 = st.columns(2)

        year = c1.selectbox(
            "ปี พ.ศ.",
            list(range(2564, 2571)),
            index=5,
            key="survey_year"
        )

        month = c2.selectbox(
            "เดือน",
            list(range(1, 13)),
            format_func=lambda x: MONTHS[x - 1],
            key="survey_month"
        )

        c3, c4 = st.columns(2)

        region = c3.selectbox(
            "เขตสุขภาพ",
            REGIONS,
            key="survey_region"
        )

        disease = c4.selectbox(
            "โรค",
            DISEASES,
            key="survey_disease"
        )

    # ---------- CASES BY AGE GROUP ----------

    st.markdown(" ")

    with st.container(border=True):

        st.markdown("### จำนวนผู้ป่วยจำแนกตามกลุ่มอายุ")

        age_values = {}

        # แสดงช่องกรอก 2 คอลัมน์ ตาม Prototype
        for i in range(0, len(AGE_ORDER), 2):

            col1, col2 = st.columns(2)

            for col, age in zip(
                [col1, col2],
                AGE_ORDER[i:i + 2]
            ):

                with col:

                    age_values[age] = st.number_input(
                        age,
                        min_value=0,
                        value=0,
                        step=1,
                        key=f"survey_cases_{i}_{age}"
                    )

        total_cases = sum(age_values.values())

        st.markdown("---")

        total_col1, total_col2 = st.columns([2, 1])

        with total_col1:
            st.markdown("### รวมผู้ป่วย")

        with total_col2:
            st.markdown(
                f"""
                <div style="
                    text-align:right;
                    color:#17649b;
                    font-size:25px;
                    font-weight:700;
                    padding-top:4px;
                ">
                    {total_cases:,} ราย
                </div>
                """,
                unsafe_allow_html=True
            )

        st.caption(
            "กรอกจำนวนเต็มตั้งแต่ 0 ขึ้นไป "
            "ห้ามกรอกข้อมูลระบุตัวบุคคล"
        )

        note = st.text_area(
            "หมายเหตุ/แหล่งข้อมูล",
            placeholder="ระบุแหล่งข้อมูลหรือรายละเอียดเพิ่มเติม",
            key="survey_source_note"
        )

        save_clicked = st.button(
            "บันทึกข้อมูล",
            type="primary",
            key="save_survey_button"
        )

        if save_clicked:

            if total_cases <= 0:

                st.error(
                    "กรุณากรอกจำนวนผู้ป่วยอย่างน้อย 1 ราย"
                )

            else:

                saved_count = 0
                failed_ages = []

                # บันทึกแยก 1 รายการต่อ 1 กลุ่มอายุ
                # เพื่อให้ข้อมูลนำไปวิเคราะห์กลุ่มอายุได้
                for age, count in age_values.items():

                    record = {
                        "year_be": int(year),
                        "month": int(month),
                        "disease": disease,
                        "health_region": region,
                        "age_group": age,
                        "cases": int(count),
                        "source_note": note
                    }

                    result = save_survey_record(record)

                    if result:
                        saved_count += 1
                    else:
                        failed_ages.append(age)

                if not failed_ages:

                    st.success(
                        f"บันทึกข้อมูลสำเร็จ "
                        f"รวมผู้ป่วย {total_cases:,} ราย "
                        f"({saved_count} กลุ่มอายุ)"
                    )

                    st.rerun()

                else:

                    st.error(
                        f"บันทึกสำเร็จ {saved_count} จาก "
                        f"{len(age_values)} กลุ่มอายุ"
                    )

                    st.warning(
                        "กลุ่มอายุที่บันทึกไม่สำเร็จ: "
                        + ", ".join(failed_ages)
                    )

    # ---------- SURVEY HISTORY ----------

    st.markdown(" ")
    st.markdown("## ประวัติการบันทึก")

    rec = load_survey_records()

    if not rec.empty:

        st.dataframe(
            rec,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("ยังไม่มีประวัติการบันทึก")


# =====================================================
# 10. MONTHLY REPORT - รายงานประจำเดือน
# =====================================================

elif page == "รายงานประจำเดือน":

    st.subheader("รายงานประจำเดือน")
    st.caption(
        "สร้างรายงาน PDF 3 หน้า ประกอบด้วยภาพรวมสถานการณ์ "
        "แนวโน้มย้อนหลัง 5 ปี และการคาดการณ์ผู้ป่วยเดือนถัดไป"
    )

    # ------------------------------------------
    # 1. REPORT FILTERS
    # ------------------------------------------

    with st.container(border=True):

        st.markdown("### กำหนดรายงาน")

        c1, c2 = st.columns(2)

        year = c1.selectbox(
            "ปี พ.ศ.",
            [2564, 2565, 2566, 2567, 2568, 2569, 2570],
            index=5,
            key="report_year"
        )

        month = c2.selectbox(
            "เดือนรายงาน",
            list(range(1, 13)),
            format_func=lambda x: MONTHS[x - 1],
            key="report_month"
        )

        area = st.selectbox(
            "พื้นที่รายงาน",
            ["ประเทศไทย"] + REGIONS,
            key="report_area"
        )

        include_forecast = st.checkbox(
            "รวมข้อมูลคาดการณ์/จำลองปี 2569",
            value=False,
            key="report_include_forecast"
        )

    # ------------------------------------------
    # 2. PDF STRUCTURE PREVIEW
    # ------------------------------------------

    st.markdown("### โครงสร้างรายงาน PDF")

    preview_cols = st.columns(3)
    preview_cols[0].info(
        "**หน้า 1**\n\nภาพรวมสถานการณ์ตามพื้นที่ที่เลือก\nสรุปผู้ป่วยครบ 6 โรค"
    )
    preview_cols[1].info(
        "**หน้า 2**\n\nแนวโน้มข้อมูลย้อนหลัง 5 ปี\nจำนวนผู้ป่วยแยกตามกลุ่มอายุ"
    )
    preview_cols[2].info(
        "**หน้า 3**\n\nคาดการณ์ผู้ป่วยเดือนถัดไปแยกรายโรค\nพร้อมข้อเสนอแนะ"
    )

    # ------------------------------------------
    # 3. CREATE THREE-PAGE PDF
    # ------------------------------------------

    if st.button(
        "สร้างรายงาน PDF 3 หน้า",
        type="primary",
        use_container_width=True,
        key="create_monthly_report"
    ):

        try:
            # PAGE 1: DATA FOR THE SELECTED REPORT MONTH
            if year < 2569:
                report_source = hist.copy()
            else:
                report_source = forecast.copy()

            if not report_source.empty:
                report_source = report_source[
                    report_source["year_be"] == year
                ]
                report_source = report_source[
                    report_source["month"] == month
                ]

            if include_forecast and year == 2569 and not simulation.empty:
                simulation_source = simulation[
                    (simulation["year_be"] == year)
                    & (simulation["month"] == month)
                ].copy()
                report_source = pd.concat(
                    [report_source, simulation_source],
                    ignore_index=True
                )

            if area != "ประเทศไทย" and not report_source.empty:
                report_source = report_source[
                    report_source["health_region"] == area
                ]

            # PREVIOUS MONTH: used for the month-on-month comparison on page 1.
            previous_year = year if month > 1 else year - 1
            previous_month = month - 1 if month > 1 else 12
            if previous_year <= 2568:
                previous_base = hist.copy()
            else:
                previous_base = forecast.copy()
            previous_source = previous_base.copy()
            if not previous_source.empty:
                previous_source = previous_source[
                    (previous_source["year_be"] == previous_year)
                    & (previous_source["month"] == previous_month)
                ].copy()
            if area != "ประเทศไทย" and not previous_source.empty:
                previous_source = previous_source[
                    previous_source["health_region"] == area
                ].copy()

            # PAGE 2: HISTORICAL DATA, LAST FIVE AVAILABLE YEARS
            historical_source = hist.copy()

            if area != "ประเทศไทย" and not historical_source.empty:
                historical_source = historical_source[
                    historical_source["health_region"] == area
                ]

            if not historical_source.empty:
                available_years = sorted(
                    pd.to_numeric(
                        historical_source["year_be"], errors="coerce"
                    ).dropna().unique().tolist()
                )
                available_years = [y for y in available_years if y <= year][-5:]
                historical_source = historical_source[
                    historical_source["year_be"].isin(available_years)
                ].copy()

            # PAGE 3: FORECAST ALL SIX DISEASES FOR THE NEXT MONTH
            forecast_source = hist.copy()

            if area != "ประเทศไทย" and not forecast_source.empty:
                forecast_source = forecast_source[
                    forecast_source["health_region"] == area
                ]

            forecast_rows = []
            for disease_name in DISEASES:
                try:
                    prediction = next_month_forecast(
                        forecast_source,
                        disease_name
                    )
                    forecast_rows.append({
                        "disease": disease_name,
                        "cases": max(0, int(prediction.get("cases", 0)))
                    })
                except Exception as forecast_error:
                    st.warning(
                        f"ไม่สามารถคาดการณ์ {disease_name}: {forecast_error}"
                    )
                    forecast_rows.append({
                        "disease": disease_name,
                        "cases": 0
                    })

            forecast_data = pd.DataFrame(
                forecast_rows,
                columns=["disease", "cases"]
            )

            if report_source.empty:
                st.warning(
                    "ไม่พบข้อมูลตามปี เดือน และพื้นที่ที่เลือก "
                    "โปรดตรวจสอบข้อมูลก่อนสร้างรายงาน"
                )
            else:
                # The current modules/reporting.py accepts historical_df
                # and forecast_df. It derives age distribution from historical_df.
                if year < 2569:
                    source_label = "ฐานข้อมูลผู้ป่วยย้อนหลัง (hist)"
                else:
                    source_label = "ชุดข้อมูลคาดการณ์ปี 2569 (forecast)"
                    if include_forecast:
                        source_label += " และข้อมูลจำลอง (simulation)"

                # Include provenance notes when the source files provide them.
                if "source_note" in report_source.columns:
                    notes = [
                        str(x).strip()
                        for x in report_source["source_note"].dropna().unique().tolist()
                        if str(x).strip()
                    ]
                    if notes:
                        source_label += " | " + "; ".join(notes[:2])

                historical_source_label = "ฐานข้อมูลผู้ป่วยย้อนหลัง (hist)"
                if "source_note" in historical_source.columns:
                    history_notes = [
                        str(x).strip()
                        for x in historical_source["source_note"].dropna().unique().tolist()
                        if str(x).strip()
                    ]
                    if history_notes:
                        historical_source_label += " | " + "; ".join(history_notes[:2])

                generated_at = datetime.now(ZoneInfo("Asia/Bangkok"))

                pdf = build_pdf(
                    df=report_source,
                    area=area,
                    title="รายงานวิเคราะห์แนวโน้มและคาดการณ์โรค",
                    historical_df=historical_source,
                    forecast_df=forecast_data,
                    previous_df=previous_source,
                    report_month=month,
                    report_year=year,
                    source_label=source_label,
                    historical_source_label=historical_source_label,
                    generated_at=generated_at
                )

                st.session_state["last_pdf"] = pdf
                st.session_state["last_pdf_name"] = (
                    f"T-DTAF_Report_{year}_{month:02d}.pdf"
                )
                st.session_state["last_pdf_area"] = area
                st.session_state["last_pdf_year"] = year
                st.session_state["last_pdf_month"] = month
                st.success("สร้างรายงาน PDF 3 หน้าเรียบร้อยแล้ว")

        except Exception as error:
            st.error(f"สร้างรายงาน PDF ไม่สำเร็จ: {error}")

    # ------------------------------------------
    # 4. PREVIEW AND DOWNLOAD PDF
    # ------------------------------------------

    if "last_pdf" in st.session_state:
        st.divider()
        st.markdown("### ตัวอย่างรายงานก่อนดาวน์โหลด")
        pdf_base64 = base64.b64encode(st.session_state["last_pdf"]).decode("utf-8")
        pdf_preview_html = f'''
            <iframe
                src="data:application/pdf;base64,{pdf_base64}"
                width="100%" height="760"
                style="border:1px solid #d7e1ea;border-radius:10px;"
                type="application/pdf">
            </iframe>
        '''
        components.html(pdf_preview_html, height=780, scrolling=True)

    if "last_pdf" in st.session_state:
        st.divider()
        st.markdown("### ดาวน์โหลดรายงาน")
        st.download_button(
            "ดาวน์โหลดรายงาน PDF",
            data=st.session_state["last_pdf"],
            file_name=st.session_state["last_pdf_name"],
            mime="application/pdf",
            use_container_width=True,
            key="download_monthly_pdf"
        )
        st.caption(
            f"พื้นที่: {st.session_state.get('last_pdf_area', 'ไม่ระบุ')} | "
            f"เดือน: {MONTHS[st.session_state.get('last_pdf_month', month) - 1]} | "
            f"ปี พ.ศ. {st.session_state.get('last_pdf_year', year)}"
        )

    # ------------------------------------------
    # 5. AUTO SELECT RECIPIENTS AND SEND THROUGH LINE OA
    # ------------------------------------------

    if "last_pdf" in st.session_state:
        st.divider()
        st.markdown("### การส่งรายงานผ่าน LINE OA")

        report_area = st.session_state.get("last_pdf_area", area)
        st.markdown(f"**พื้นที่ของรายงาน:** {report_area}")

        # list_recipients() returns active recipients from the database.
        active_recipients = list_recipients()
        if not isinstance(active_recipients, list):
            active_recipients = []

        selected_recipients = []
        for recipient in active_recipients:
            name = str(recipient.get("name", "")).strip()
            line_id = str(recipient.get("line_id", "")).strip()
            if not name or not line_id:
                continue

            if report_area == "ประเทศไทย":
                # National reports go to BOTH national teams:
                # Epidemiology and Infection Control (IC).
                is_epidemiology = (
                    "ระบาดวิทยา" in name
                    or "ทีมระบาด" in name
                )

                is_infection_control = (
                    "ควบคุมการติดเชื้อ" in name
                    or "ทีม IC" in name
                    or "(IC)" in name
                    or " IC" in name
                )

                if is_epidemiology or is_infection_control:
                    selected_recipients.append(recipient)

            else:
                # Regional reports go to the administrator group
                # whose recipient name contains the selected health region.
                if report_area in name:
                    selected_recipients.append(recipient)

        # Remove duplicate LINE IDs before displaying/sending.
        unique_recipients = {}
        for recipient in selected_recipients:
            unique_recipients[recipient["line_id"]] = recipient
        selected_recipients = list(unique_recipients.values())

        if report_area == "ประเทศไทย":
            st.info(
                "กลุ่มผู้รับที่ระบบเลือกอัตโนมัติ: "
                "ทีมระบาดวิทยา และทีมควบคุมการติดเชื้อ (IC)"
            )
        else:
            st.info(
                f"กลุ่มผู้รับที่ระบบเลือกอัตโนมัติ: ผู้รับผิดชอบ{report_area}"
            )

        st.markdown(f"**จำนวนผู้รับ: {len(selected_recipients)} ราย**")

        if selected_recipients:
            recipient_preview = pd.DataFrame([
                {
                    "ลำดับ": index + 1,
                    "ชื่อผู้รับ/หน่วยงาน": recipient.get("name", "-"),
                    "LINE ID": recipient.get("line_id", "-")
                }
                for index, recipient in enumerate(selected_recipients)
            ])
            st.dataframe(
                recipient_preview,
                use_container_width=True,
                hide_index=True
            )

            confirm_key = (
                "confirm_report_send_"
                + str(st.session_state.get("last_pdf_name", "report"))
                + "_"
                + str(report_area).replace(" ", "_")
            )
            confirmed = st.checkbox(
                "ฉันตรวจสอบรายชื่อผู้รับและยืนยันการส่งรายงานแล้ว",
                key=confirm_key
            )


            if st.button(
                "ยืนยันส่ง PDF ผ่าน LINE OA",
                type="primary",
                use_container_width=True,
                disabled=not confirmed,
                key="send_monthly_report_line"
            ):
                try:
                    # 1. อ่าน APP_PUBLIC_URL
                    # รองรับทั้ง Secrets ระดับหลักและภายใน [passwords]
                    dashboard = (
                        st.secrets.get("APP_PUBLIC_URL", "")
                        or st.secrets.get(
                            "passwords", {}
                        ).get("APP_PUBLIC_URL", "")
                    )

                    dashboard = str(dashboard).strip().rstrip("/")

                    if not dashboard:
                        st.error(
                            "ไม่พบ APP_PUBLIC_URL "
                            "กรุณาตรวจสอบ Streamlit Secrets"
                        )

                    else:
                        # 2. อัปโหลด PDF ไป Supabase Storage
                        with st.spinner(
                            "กำลังอัปโหลดรายงาน PDF ไปยัง Supabase..."
                        ):
                            pdf_url = upload_pdf_to_drive(
                                st.session_state["last_pdf"],
                                st.session_state["last_pdf_name"]
                            )

                        if not pdf_url:
                            st.error(
                                "อัปโหลด PDF ไปยัง Supabase Storage ไม่สำเร็จ "
                                "กรุณาตรวจสอบการเชื่อมต่อ Supabase"
                            )

                        else:
                            # 3. เตรียมข้อความ LINE OA
                            sent = 0
                            failed = 0

                            message = (
                                "T-DTAF รายงานประจำเดือน\n"
                                f"พื้นที่: {report_area}\n"
                                f"PDF: {pdf_url}\n"
                                f"Dashboard: {dashboard}"
                            )

                            # 4. ส่งรายงานให้ผู้รับที่เลือกไว้
                            for recipient in selected_recipients:
                                try:
                                    result = send_line_message(
                                        recipient["line_id"],
                                        message
                                    )

                                    if result:
                                        sent += 1
                                    else:
                                        failed += 1

                                except Exception:
                                    failed += 1

                            # 5. แสดงผลการส่ง
                            if failed == 0:
                                st.success(
                                    f"ส่งรายงานสำเร็จ {sent} ราย"
                                )

                                st.markdown(
                                    f"[เปิดดูรายงาน PDF]({pdf_url})"
                                )

                            else:
                                st.warning(
                                    f"ส่งสำเร็จ {sent} ราย "
                                    f"และส่งไม่สำเร็จ {failed} ราย"
                                )

                                st.markdown(
                                    f"[เปิดดูรายงาน PDF]({pdf_url})"
                                )

                except Exception as error:
                    st.error(
                        f"เกิดข้อผิดพลาดในการส่งรายงาน: {error}"
                    )


# =====================================================
# 11. RECIPIENT MANAGEMENT
# =====================================================

elif page == "จัดการผู้รับรายงาน":

    st.subheader("จัดการผู้รับรายงาน")
    st.caption(
        "การจับคู่ผู้รับอัตโนมัติ: รายงานประเทศไทยส่งให้ "
        "'ทีมระบาดวิทยา' และ 'ทีมควบคุมการติดเชื้อ (IC)' "
        "ส่วนรายงานเขตสุขภาพส่งให้กลุ่มผู้บริหารของเขตที่เลือก "
        "เช่น 'ผู้บริหารเขตสุขภาพที่ 1' "
        "กรุณากรอก LINE User ID หรือ Group ID ให้ถูกต้อง"
    )

    with st.form("recipient"):

        name = st.text_input(
            "ชื่อผู้รับ/หน่วยงาน"
        )

        line_id = st.text_input(
            "LINE User ID หรือ Group ID"
        )

        active = st.checkbox(
            "เปิดใช้งาน",
            value=True
        )

        saved = st.form_submit_button(
            "เพิ่มผู้รับ"
        )

    if saved:

        if not name or not line_id:

            st.error("กรุณากรอกชื่อและ LINE ID")

        elif save_recipient(
            name,
            line_id,
            active
        ):

            st.success("บันทึกผู้รับแล้ว")

        else:

            st.error(
                "บันทึกไม่สำเร็จ โปรดตรวจสอบ Supabase"
            )

    recs = list_recipients()

    if recs:

        st.dataframe(
            pd.DataFrame(recs),
            use_container_width=True,
            hide_index=True
        )
    else:

        st.info("ยังไม่มีรายชื่อผู้รับรายงาน")


# =====================================================
# 12. FOOTER
# =====================================================

st.markdown("---")

st.caption(
    "T-DTAF | THAILAND DISEASE TREND ANALYSIS "
    "& FORECASTING SYSTEM"
)
