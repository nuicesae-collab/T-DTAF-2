import streamlit as st
import pandas as pd
from modules.data import load_all, DISEASES, AGE_ORDER, REGIONS, MONTHS
from modules.auth import login_gate, logout_button
from modules.analysis import monthly_trend, age_summary, next_month_forecast, kpi_summary
from modules.db import save_survey_record, list_recipients, save_recipient, delete_recipient, load_survey_records
from modules.reporting import build_pdf
from modules.line_oa import send_line_message
from modules.drive import upload_pdf_to_drive

st.set_page_config(page_title="T-DTAF | ระบบวิเคราะห์แนวโน้มและคาดการณ์โรค",page_icon="📊",layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.5rem;max-width:1450px}
[data-testid="stSidebar"]{background:#f1f6fb}
.hero{padding:1.2rem 1.4rem;border-radius:16px;background:linear-gradient(120deg,#123b62,#2676a8);color:white;margin-bottom:1rem}
.hero h1{color:white;margin:0}.hero p{color:#e5f2ff;margin:.3rem 0 0}
.small-note{font-size:.85rem;color:#64748b}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>T-DTAF</h1><p>THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM</p></div>',unsafe_allow_html=True)
hist,forecast,simulation=load_all()
pages=["ภาพรวมสถานการณ์โรค","วิเคราะห์แนวโน้มและคาดการณ์","บันทึกข้อมูลทีมสำรวจ","รายงานประจำเดือน","จัดการผู้รับรายงาน"]
page=st.sidebar.radio("เมนูหลัก",pages)
st.sidebar.caption("ข้อมูลสังเคราะห์/จำลอง ต้องไม่ใช้แทนสถิติจริง")
if page in ["บันทึกข้อมูลทีมสำรวจ","รายงานประจำเดือน","จัดการผู้รับรายงาน"]:
    role={"บันทึกข้อมูลทีมสำรวจ":"INPUT","รายงานประจำเดือน":"REPORT","จัดการผู้รับรายงาน":"ADMIN"}[page]
    if not login_gate(role):
        st.stop()
    logout_button(role)

def area_filter(df):
    opts=["ประเทศไทย"]+REGIONS
    area=st.selectbox("เลือกพื้นที่",opts,key="area_"+page)
    return df if area=="ประเทศไทย" else df[df.health_region==area],area

if page=="ภาพรวมสถานการณ์โรค":
    st.subheader("ภาพรวมสถานการณ์โรค")
    year=st.selectbox("ปีข้อมูล",sorted(hist.year_be.unique().tolist()+[2569]))
    src=hist if year<2569 else forecast
    src=src[src.year_be==year]
    view,area=area_filter(src)
    k=kpi_summary(view)
    cols=st.columns(4)
    for c,(label,val) in zip(cols,[("จำนวนผู้ป่วยรวม",k["cases"]),("จำนวนโรค",k["diseases"]),("จำนวนเดือน",k["months"]),("พื้นที่",area)]):
        c.metric(label,val)
    st.dataframe(view.groupby("disease",as_index=False).cases.sum().sort_values("cases",ascending=False),use_container_width=True,hide_index=True)
    st.bar_chart(view.groupby("disease").cases.sum())
    st.caption("หมายเหตุ: Historical เป็นข้อมูลสังเคราะห์เพื่อทดสอบระบบ ไม่ใช่ข้อมูลจริงจากกรมควบคุมโรค")

elif page=="วิเคราะห์แนวโน้มและคาดการณ์":
    st.subheader("วิเคราะห์แนวโน้มและคาดการณ์")
    st.write("เปรียบเทียบข้อมูลย้อนหลัง วิเคราะห์กลุ่มอายุ และคาดการณ์ผู้ป่วยเดือนถัดไป")
    src,area=area_filter(hist)
    trend=monthly_trend(src)
    st.markdown("#### แนวโน้มผู้ป่วยย้อนหลัง พ.ศ. 2564–2568")
    st.line_chart(trend.pivot(index="period",columns="disease",values="cases").fillna(0))
    disease=st.selectbox("เลือกโรคเพื่อวิเคราะห์กลุ่มอายุ",DISEASES)
    ages=age_summary(src, disease)
    st.markdown("#### วิเคราะห์ตาม 6 กลุ่มอายุ")
    st.bar_chart(ages.set_index("age_group")["cases"])
    st.dataframe(ages,use_container_width=True,hide_index=True)
    st.markdown("#### คาดการณ์จำนวนผู้ป่วยเดือนถัดไป")
    pred=next_month_forecast(src,disease)
    st.metric(f"{disease} · เดือน {pred['month_name']} พ.ศ. {pred['year_be']}",f"{pred['cases']:,} ราย")
    st.caption("เป็นค่าประมาณเชิงสถิติอย่างง่ายจากแนวโน้มข้อมูลย้อนหลัง ไม่ใช่คำพยากรณ์ทางระบาดวิทยา")
    if st.button("สร้าง PDF ผลวิเคราะห์"):
        pdf=build_pdf(src, "ประเทศไทย" if area=="ประเทศไทย" else area, "ผลวิเคราะห์แนวโน้ม")
        st.download_button("ดาวน์โหลด PDF",pdf,file_name="T-DTAF_Analysis.pdf",mime="application/pdf")

elif page=="บันทึกข้อมูลทีมสำรวจ":
    st.subheader("บันทึกข้อมูลทีมสำรวจ")
    with st.form("survey"):
        c1,c2=st.columns(2)
        year=c1.selectbox("ปี พ.ศ.",list(range(2564,2571)),index=5)
        month=c2.selectbox("เดือน",list(range(1,13)),format_func=lambda x:MONTHS[x-1])
        disease=st.selectbox("โรค",DISEASES)
        region=st.selectbox("พื้นที่",REGIONS)
        age=st.selectbox("กลุ่มอายุ",AGE_ORDER)
        cases=st.number_input("จำนวนผู้ป่วยรวม",min_value=0,step=1)
        note=st.text_area("หมายเหตุ/แหล่งข้อมูล")
        ok=st.form_submit_button("บันทึกข้อมูล")
    if ok:
        result=save_survey_record(dict(year_be=year,month=month,disease=disease,health_region=region,age_group=age,cases=int(cases),source_note=note))
        st.success("บันทึกข้อมูลแล้ว" if result else "บันทึกลงฐานข้อมูลไม่สำเร็จ โปรดตรวจสอบ Supabase")
    st.markdown("#### ประวัติการบันทึก")
    rec=load_survey_records()
    if not rec.empty: st.dataframe(rec,use_container_width=True,hide_index=True)

elif page=="รายงานประจำเดือน":
    st.subheader("รายงานประจำเดือน")
    c1,c2=st.columns(2)
    year=c1.selectbox("ปี พ.ศ.",[2564,2565,2566,2567,2568,2569,2570],index=5)
    month=c2.selectbox("เดือน",list(range(1,13)),format_func=lambda x:MONTHS[x-1])
    area=st.selectbox("พื้นที่รายงาน",["ประเทศไทย"]+REGIONS)
    include_forecast=st.checkbox("รวมข้อมูลคาดการณ์/จำลองปี 2569",value=False)
    if st.button("สร้างรายงาน PDF",type="primary"):
        df=hist[hist.year_be==year] if year<2569 else forecast[forecast.year_be==year]
        if include_forecast and year==2569: df=pd.concat([df,simulation[simulation.year_be==year]],ignore_index=True)
        df=df[df.month==month]
        if area!="ประเทศไทย": df=df[df.health_region==area]
        if df.empty: st.warning("ไม่พบข้อมูลตามเงื่อนไข")
        else:
            pdf=build_pdf(df,area,f"รายงานประจำเดือน {MONTHS[month-1]} {year}")
            st.session_state["last_pdf"]=pdf
            st.session_state["last_pdf_name"]=f"T-DTAF_{year}_{month:02d}.pdf"
            st.download_button("ดาวน์โหลดรายงาน PDF",pdf,file_name=st.session_state["last_pdf_name"],mime="application/pdf")
            st.success("สร้าง PDF แล้ว")
    if "last_pdf" in st.session_state:
        if st.button("ส่ง PDF และลิงก์ Dashboard ผ่าน LINE OA"):
            drive_url=upload_pdf_to_drive(st.session_state["last_pdf"],st.session_state["last_pdf_name"])
            dashboard=st.secrets.get("APP_PUBLIC_URL","")
            if not drive_url: st.error("อัปโหลด PDF ไป Google Drive ไม่สำเร็จ หรือยังไม่ได้ตั้งค่า Drive")
            elif not dashboard: st.error("กรุณาตั้งค่า APP_PUBLIC_URL ใน Streamlit Secrets")
            else:
                recipients=list_recipients()
                sent=0
                for rec in recipients:
                    if rec.get("line_id") and send_line_message(rec["line_id"],f"T-DTAF รายงานประจำเดือน\nPDF: {drive_url}\nDashboard: {dashboard}"): sent+=1
                st.success(f"ส่ง LINE สำเร็จ {sent}/{len(recipients)} ราย")

elif page=="จัดการผู้รับรายงาน":
    st.subheader("จัดการผู้รับรายงาน")
    with st.form("recipient"):
        name=st.text_input("ชื่อผู้รับ/หน่วยงาน")
        line_id=st.text_input("LINE User ID หรือ Group ID")
        active=st.checkbox("เปิดใช้งาน",value=True)
        saved=st.form_submit_button("เพิ่มผู้รับ")
    if saved:
        if not name or not line_id: st.error("กรุณากรอกชื่อและ LINE ID")
        elif save_recipient(name,line_id,active): st.success("บันทึกผู้รับแล้ว")
        else: st.error("บันทึกไม่สำเร็จ โปรดตรวจสอบ Supabase")
    recs=list_recipients()
    if recs: st.dataframe(pd.DataFrame(recs),use_container_width=True,hide_index=True)
