
import streamlit as st
import pandas as pd
from supabase import create_client


def client():
    try:
        config = st.secrets["supabase"]
        url = str(config["url"]).strip()

        key = (
            config.get("service_role_key")
            or config.get("key")
            or config.get("secret_key")
        )
        key = str(key).strip() if key else ""

        if not url or not key:
            st.error("กรุณาตรวจสอบ Supabase URL และ Key")
            return None

        return create_client(url, key)

    except Exception as e:
        st.error(f"เชื่อมต่อ Supabase ไม่สำเร็จ: {e}")
        return None


def save_survey_record(d):
    c = client()
    if not c:
        return False
    try:
        c.table("survey_records").insert(d).execute()
        return True
    except Exception as e:
        st.error(f"บันทึกข้อมูลไม่สำเร็จ: {e}")
        return False


def load_survey_records():
    c = client()
    if not c:
        return pd.DataFrame()
    try:
        r = (
            c.table("survey_records")
            .select("*")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        return pd.DataFrame(r.data)
    except Exception as e:
        st.error(f"อ่านข้อมูลไม่สำเร็จ: {e}")
        return pd.DataFrame()


def list_recipients():
    c = client()
    if not c:
        return []

    try:
        response = (
            c.table("line_recipients")
            .select("id, name, line_id, active, created_at")
            .eq("active", True)
            .order("id")
            .execute()
        )
        return response.data or []

    except Exception as e:
        st.error(
            f"อ่านรายชื่อผู้รับจาก Supabase ไม่สำเร็จ: {e}"
        )
        return []


def save_recipient(name, line_id, active):
    c = client()
    if not c:
        return False
    try:
        c.table("line_recipients").insert({
            "name": name,
            "line_id": line_id,
            "active": active
        }).execute()
        return True
    except Exception as e:
        st.error(f"เพิ่มผู้รับไม่สำเร็จ: {e}")
        return False


def delete_recipient(row_id):
    c = client()
    if not c:
        return False
    try:
        c.table("line_recipients").delete().eq(
            "id", row_id
        ).execute()
        return True
    except Exception as e:
        st.error(f"ลบผู้รับไม่สำเร็จ: {e}")
        return False
