
import streamlit as st
import pandas as pd

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

            available_years = sorted(
                analysis_data.year_be.unique()
            )[-5:]

            analysis_data = analysis_data[
                analysis_data.year_be.isin(available_years)
            ]

    else:

        analysis_data = get_year_data(selected_year)

    analysis_data = filter_data(
        analysis_data,
        area,
        disease
    )

    # ---------- TREND CHART ----------

    st.markdown("### แนวโน้มจำนวนผู้ป่วยรายเดือน")

    with st.container(border=True):

        if mode == "เปรียบเทียบย้อนหลัง 5 ปี":

            st.caption("เปรียบเทียบข้อมูลย้อนหลัง 5 ปี")

        else:

            st.caption(f"ข้อมูลปี พ.ศ. {selected_year}")

        if not analysis_data.empty:

            trend = (
                analysis_data
                .groupby(
                    ["year_be", "month"],
                    as_index=False
                )["cases"]
                .sum()
            )

            trend_pivot = trend.pivot(
                index="month",
                columns="year_be",
                values="cases"
            ).fillna(0)

            trend_pivot = trend_pivot.reindex(
                range(1, 13),
                fill_value=0
            )

            trend_pivot.index = [
                MONTHS[m-1] for m in trend_pivot.index
            ]

            trend_pivot.index.name = "เดือน"

            st.line_chart(
                trend_pivot,
                use_container_width=True
            )

            st.caption(
                "กราฟแสดงแนวโน้มจำนวนผู้ป่วยรายเดือน "
                "จำแนกตามปีที่เลือก"
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

    c1, c2 = st.columns(2)

    year = c1.selectbox(
        "ปี พ.ศ.",
        [2564, 2565, 2566, 2567, 2568, 2569, 2570],
        index=5
    )

    month = c2.selectbox(
        "เดือน",
        list(range(1, 13)),
        format_func=lambda x: MONTHS[x-1]
    )

    area = st.selectbox(
        "พื้นที่รายงาน",
        ["ประเทศไทย"] + REGIONS
    )

    include_forecast = st.checkbox(
        "รวมข้อมูลคาดการณ์/จำลองปี 2569",
        value=False
    )

    if st.button(
        "สร้างรายงาน PDF",
        type="primary"
    ):

        df = (
            hist[hist.year_be == year]
            if year < 2569
            else forecast[forecast.year_be == year]
        )

        if include_forecast and year == 2569:

            df = pd.concat(
                [
                    df,
                    simulation[simulation.year_be == year]
                ],
                ignore_index=True
            )

        df = df[df.month == month]

        if area != "ประเทศไทย":

            df = df[df.health_region == area]

        if df.empty:

            st.warning("ไม่พบข้อมูลตามเงื่อนไข")

        else:

            pdf = build_pdf(
                df,
                area,
                f"รายงานประจำเดือน {MONTHS[month-1]} {year}"
            )

            st.session_state["last_pdf"] = pdf

            st.session_state["last_pdf_name"] = (
                f"T-DTAF_{year}_{month:02d}.pdf"
            )

            st.download_button(
                "ดาวน์โหลดรายงาน PDF",
                pdf,
                file_name=st.session_state["last_pdf_name"],
                mime="application/pdf"
            )

            st.success("สร้าง PDF แล้ว")

    st.markdown("### รายงานผลวิเคราะห์แนวโน้ม")
    st.caption(
        "สร้าง PDF สรุปแนวโน้มข้อมูลย้อนหลัง โดยเลือกพื้นที่รายงานด้านบน"
    )

    if st.button(
        "สร้าง PDF ผลวิเคราะห์แนวโน้ม",
        key="create_analysis_pdf"
    ):

        analysis_pdf_data = hist.copy()

        if area != "ประเทศไทย":
            analysis_pdf_data = analysis_pdf_data[
                analysis_pdf_data["health_region"] == area
            ]

        if analysis_pdf_data.empty:
            st.warning("ไม่พบข้อมูลย้อนหลังสำหรับสร้างรายงานผลวิเคราะห์")
        else:
            analysis_pdf = build_pdf(
                analysis_pdf_data,
                area,
                "ผลวิเคราะห์แนวโน้มข้อมูลย้อนหลัง"
            )

            st.session_state["last_analysis_pdf"] = analysis_pdf
            st.session_state["last_analysis_pdf_name"] = (
                f"T-DTAF_Analysis_{year}_{month:02d}.pdf"
            )

            st.download_button(
                "ดาวน์โหลด PDF ผลวิเคราะห์แนวโน้ม",
                analysis_pdf,
                file_name=st.session_state["last_analysis_pdf_name"],
                mime="application/pdf",
                key="download_analysis_pdf"
            )
            st.success("สร้าง PDF ผลวิเคราะห์แล้ว")

    if "last_pdf" in st.session_state:

        if st.button("ส่ง PDF และลิงก์ Dashboard ผ่าน LINE OA"):

            drive_url = upload_pdf_to_drive(
                st.session_state["last_pdf"],
                st.session_state["last_pdf_name"]
            )

            dashboard = st.secrets.get(
                "APP_PUBLIC_URL",
                ""
            )

            if not drive_url:

                st.error(
                    "อัปโหลด PDF ไป Google Drive ไม่สำเร็จ "
                    "หรือยังไม่ได้ตั้งค่า Drive"
                )

            elif not dashboard:

                st.error(
                    "กรุณาตั้งค่า APP_PUBLIC_URL "
                    "ใน Streamlit Secrets"
                )

            else:

                recipients = list_recipients()

                sent = 0

                for rec in recipients:

                    if (
                        rec.get("line_id")
                        and send_line_message(
                            rec["line_id"],
                            f"T-DTAF รายงานประจำเดือน\n"
                            f"PDF: {drive_url}\n"
                            f"Dashboard: {dashboard}"
                        )
                    ):

                        sent += 1

                st.success(
                    f"ส่ง LINE สำเร็จ {sent}/{len(recipients)} ราย"
                )


# =====================================================
# 11. RECIPIENT MANAGEMENT
# =====================================================

elif page == "จัดการผู้รับรายงาน":

    st.subheader("จัดการผู้รับรายงาน")

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

