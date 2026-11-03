import streamlit as st
def login_gate(role):
    cfg=st.secrets.get("passwords",{})
    expected=cfg.get(role,"")
    if not expected:
        st.error(f"ยังไม่ได้ตั้งรหัสผ่านสำหรับ {role} ใน Streamlit Secrets")
        st.info("ผู้ดูแลต้องกำหนด passwords ใน Secrets ก่อนเปิดใช้")
        return False
    key=f"auth_{role}"
    if st.session_state.get(key): return True
    st.markdown("### 🔐 ยืนยันสิทธิ์การเข้าใช้งาน")
    pw=st.text_input("รหัสผ่าน",type="password",key=f"pw_{role}")
    if st.button("เข้าสู่ระบบ",key=f"login_{role}"):
        if pw==expected:
            st.session_state[key]=True
            st.rerun()
        else: st.error("รหัสผ่านไม่ถูกต้อง")
    return False
def logout_button(role):
    if st.sidebar.button("ออกจากระบบ",key=f"logout_{role}"):
        st.session_state.pop(f"auth_{role}",None)
        st.rerun()
