import streamlit as st
def upload_pdf_to_drive(pdf_bytes,filename):
    """Requires Google Drive service-account JSON in Streamlit Secrets [gdrive]."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        from io import BytesIO
        cfg=dict(st.secrets["gdrive"])
        creds=service_account.Credentials.from_service_account_info(cfg,scopes=["https://www.googleapis.com/auth/drive.file"])
        service=build("drive","v3",credentials=creds)
        meta={"name":filename,"mimeType":"application/pdf"}
        folder=st.secrets.get("GDRIVE_FOLDER_ID","")
        if folder: meta["parents"]=[folder]
        f=service.files().create(body=meta,media_body=MediaIoBaseUpload(BytesIO(pdf_bytes),mimetype="application/pdf"),fields="id,webViewLink").execute()
        return f.get("webViewLink")
    except Exception as e:
        st.error(f"Google Drive ยังไม่พร้อม: {e}")
        return None
