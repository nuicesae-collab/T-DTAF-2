
import streamlit as st
import uuid
import os


def upload_pdf_to_drive(pdf_bytes, filename):
    """
    Upload PDF to Supabase Storage (Private Bucket)
    and return a temporary Signed URL.
    """

    try:
        from supabase import create_client

        # 1. อ่านค่าการเชื่อมต่อ Supabase
        config = st.secrets["supabase"]

        url = str(config["url"]).strip()

        key = (
            config.get("service_role_key")
            or config.get("key")
            or config.get("secret_key")
        )

        if not url or not key:
            st.error("กรุณาตรวจสอบ Supabase URL และ Key")
            return None

        # 2. เชื่อมต่อ Supabase
        supabase = create_client(url, str(key).strip())

        # 3. กำหนด Bucket
        bucket = "tdtaf-reports"

        # 4. ตั้งชื่อไฟล์ไม่ให้ซ้ำกัน
        filename = os.path.basename(filename)

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        file_path = f"reports/{uuid.uuid4().hex}_{filename}"

        # 5. อัปโหลด PDF
        supabase.storage.from_(bucket).upload(
            file_path,
            pdf_bytes,
            {
                "content-type": "application/pdf",
                "upsert": "false"
            }
        )

        # 6. สร้าง Signed URL อายุ 7 วัน
        result = supabase.storage.from_(bucket).create_signed_url(
            file_path,
            604800
        )

        # 7. ส่ง URL กลับไปให้ระบบ LINE OA
        signed_url = (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )

        if not signed_url:
            st.error("อัปโหลดสำเร็จ แต่สร้างลิงก์ PDF ไม่สำเร็จ")
            return None

        if signed_url.startswith("/"):
            signed_url = url.rstrip("/") + signed_url

        return signed_url

    except Exception as e:
        st.error(f"Supabase Storage Error: {e}")
        return None
