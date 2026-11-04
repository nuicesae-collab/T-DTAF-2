
import streamlit as st
import uuid
import os

def upload_pdf_to_drive(pdf_bytes, filename):
    """
    Upload PDF to Supabase Private Storage
    and return Signed URL for inline viewing.
    """

    try:
        from supabase import create_client

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

        supabase = create_client(url, str(key).strip())

        bucket = "tdtaf-reports"

        filename = os.path.basename(filename)

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        file_path = f"reports/{uuid.uuid4().hex}_{filename}"

        # Upload PDF ให้เปิดดูผ่าน Browser ได้
        supabase.storage.from_(bucket).upload(
            file_path,
            pdf_bytes,
            {
                "content-type": "application/pdf",
                "content-disposition": "inline",
                "cache-control": "3600",
                "upsert": "false"
            }
        )

        # สร้าง Signed URL อายุ 7 วัน
        result = supabase.storage.from_(bucket).create_signed_url(
            file_path,
            604800
        )

        signed_url = (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )

        if not signed_url:
            st.error("อัปโหลดสำเร็จ แต่สร้าง PDF URL ไม่สำเร็จ")
            return None

        if signed_url.startswith("/"):
            signed_url = url.rstrip("/") + signed_url

        return signed_url

    except Exception as e:
        st.error(f"Supabase Storage Error: {e}")
        return None
