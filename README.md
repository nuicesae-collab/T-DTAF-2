# T-DTAF
THAILAND DISEASE TREND ANALYSIS & FORECASTING SYSTEM

ระบบต้นแบบ Streamlit สำหรับรวบรวม วิเคราะห์แนวโน้ม คาดการณ์ และจัดทำรายงานข้อมูล 6 โรค

## เมนู
1. ภาพรวมสถานการณ์โรค — สาธารณะ
2. วิเคราะห์แนวโน้มและคาดการณ์ — สาธารณะ
3. บันทึกข้อมูลทีมสำรวจ — ต้องใช้รหัสผ่าน
4. รายงานประจำเดือน — ต้องใช้รหัสผ่าน
5. จัดการผู้รับรายงาน — ต้องใช้รหัสผ่านผู้ดูแล

## ข้อมูล
- `data/historical.csv` พ.ศ. 2564–2568
- `data/forecast.csv` พ.ศ. 2569
- `data/simulation.csv` พ.ศ. 2569
- ข้อมูลเพศถูกตัดออกและจำนวนชาย/หญิงในไฟล์ Forecast/Simulation ถูกรวมเป็นยอดรวมต่อกลุ่มอายุ
- Historical เป็นข้อมูลสังเคราะห์ ไม่ใช่สถิติจริงจากกรมควบคุมโรค
- Forecast/Simulation เป็นข้อมูลสังเคราะห์/จำลอง

## เริ่มใช้งานในเครื่อง
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ด้วย Streamlit Community Cloud
1. Push ไฟล์ทั้งหมดไป GitHub
2. ไปที่ https://share.streamlit.io/
3. เลือก repository `T-DTAF` และไฟล์หลัก `app.py`
4. ตั้งค่า Secrets ตามตัวอย่าง `secrets.toml.example` (อย่าอัปโหลด secrets จริงลง GitHub)

## ตั้งค่า Supabase
1. สร้างโปรเจกต์ Supabase
2. เปิด SQL Editor แล้วรัน `sql/schema.sql`
3. นำ Project URL และ key ไปใส่ใน Streamlit Secrets

## ข้อควรทราบก่อนใช้จริง
- ต้องตั้งรหัสผ่าน 3 ชุดใน Secrets
- ต้องตั้ง LINE Messaging API Channel Access Token
- ต้องตั้ง Google Drive Service Account และแชร์โฟลเดอร์ปลายทางให้ Service Account
- ต้องตั้ง `APP_PUBLIC_URL` เป็น URL Streamlit ที่ Deploy แล้ว
- กำหนดสิทธิ์ Supabase RLS และทดสอบความปลอดภัยก่อนใส่ข้อมูลจริง
- LINE OA ส่งลิงก์ PDF และ Dashboard; ไม่ได้แนบ PDF เป็นไฟล์ในข้อความนี้
- ระบบนี้เป็นต้นแบบ ต้องทดสอบและตรวจสอบความถูกต้องก่อนใช้งานจริงในหน่วยงาน

## แบบเว็บไซต์เดิม
ไฟล์ `design_reference/index 3(1).html` เก็บไว้เป็นต้นแบบอ้างอิงหน้าตาเว็บไซต์เดิม การทำ UI ใน Streamlit เป็นการสร้างใหม่ด้วย Python; ต้องปรับรายละเอียดภาพ/เลย์เอาต์เทียบกับไฟล์ต้นแบบก่อนเปิดใช้งานจริง
