import streamlit as st
from supabase import create_client
def client():
    try:
        return create_client(st.secrets["supabase"]["url"],st.secrets["supabase"]["key"])
    except Exception:
        return None
def save_survey_record(d):
    c=client()
    if not c: return False
    try: c.table("survey_records").insert(d).execute(); return True
    except Exception as e: st.error(str(e)); return False
def load_survey_records():
    c=client()
    if not c: return __import__("pandas").DataFrame()
    try:
        r=c.table("survey_records").select("*").order("created_at",desc=True).limit(500).execute()
        return __import__("pandas").DataFrame(r.data)
    except Exception: return __import__("pandas").DataFrame()
def list_recipients():
    c=client()
    if not c: return []
    try: return c.table("line_recipients").select("*").eq("active",True).execute().data
    except Exception: return []
def save_recipient(name,line_id,active):
    c=client()
    if not c: return False
    try: c.table("line_recipients").insert({"name":name,"line_id":line_id,"active":active}).execute(); return True
    except Exception as e: st.error(str(e)); return False
def delete_recipient(row_id):
    c=client()
    if not c: return False
    try: c.table("line_recipients").delete().eq("id",row_id).execute(); return True
    except Exception: return False
