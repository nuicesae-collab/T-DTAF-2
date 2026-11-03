import streamlit as st
import pandas as pd
from pathlib import Path
DATA=Path(__file__).resolve().parents[1]/"data"
DISEASES=["โรคมือเท้าปาก","โรคไข้เลือดออก","โรคปอดบวม","โรคไข้หวัดใหญ่","โรคลมแดด","โรคอุจจาระร่วงเฉียบพลัน"]
AGE_ORDER=["0–4 ปี","5–14 ปี","15–24 ปี","25–44 ปี","45–64 ปี","65 ปีขึ้นไป"]
REGIONS=[f"เขตสุขภาพที่ {i}" for i in range(1,14)]
MONTHS=["มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน","กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]
@st.cache_data
def _read(name):
    p=DATA/f"{name}.csv"
    if not p.exists(): return pd.DataFrame(columns=["year_be","month","month_name_th","disease","health_region","age_group","data_status","source_note","cases"])
    d=pd.read_csv(p)
    if "sex" in d.columns: d=d.drop(columns=["sex"])
    d["cases"]=pd.to_numeric(d["cases"],errors="coerce").fillna(0).astype(int)
    return d
def load_all(): return _read("historical"),_read("forecast"),_read("simulation")
