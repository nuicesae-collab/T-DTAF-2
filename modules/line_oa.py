import streamlit as st, requests
def send_line_message(to,text):
    token=st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN","")
    if not token: st.error("ยังไม่ได้ตั้ง LINE_CHANNEL_ACCESS_TOKEN");return False
    try:
        r=requests.post("https://api.line.me/v2/bot/message/push",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},json={"to":to,"messages":[{"type":"text","text":text}]},timeout=20)
        return r.ok
    except Exception as e: st.error(str(e));return False
