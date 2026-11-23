import os
import re
import secrets
import string
from flask import Flask, render_template_string, request, redirect, url_for

# استيراد دوال قاعدة البيانات والتشفير من ملفات مشروعك
# تأكد أن أسماء الدوال تطابق الموجود في database.py لديك
from database import init_db, add_patient, get_patient_by_token

app = Flask(name)
app.secret_key = os.environ.get("SECRET_KEY", "aman-medica-secret-key")

# تهيئة قاعدة البيانات عند بدء التشغيل
try:
    init_db()
except Exception as e:
    print(f"DB init notice: {e}")


def generate_nfc_token(prefix: str = "AMAN", length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        token = f"{prefix}-{code}"
        if not get_patient_by_token(token):
            return token


def pack_emergency_contacts(c1_name, c1_phone, c2_name, c2_phone):
    lines = []
    for name, phone in [(c1_name, c1_phone), (c2_name, c2_phone)]:
        clean_name = (name or "").strip()
        clean_phone = (phone or "").strip()
        if clean_name or clean_phone:
            lines.append(f"{clean_name or 'جهة اتصال الطوارئ'} | {clean_phone}")
    return "\n".join(lines)


def parse_emergency_contacts(raw_text):
    contacts = []
    if not raw_text:
        return contacts
    for line in str(raw_text).splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            name_part, phone_part = line.split("|", 1)
        else:
            name_part, phone_part = "جهة اتصال الطوارئ", line

        relation = name_part.strip() or "جهة اتصال الطوارئ"
        phone = phone_part.strip()
        tel_href = re.sub(r"[^\d+]", "", phone)
        if phone or relation:
            contacts.append({
                "relation": relation,
                "phone": phone,
                "tel_href": tel_href,
            })
    return contacts


ADD_PATIENT_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>أمان ميديكا - إضافة سجل مريض</title>
  <style>
    body { font-family: Tahoma, Arial, sans-serif; background: #f3f6fa; margin: 0; padding: 20px; color: #1f2937; }
    .container { max-width: 640px; margin: auto; background: #fff; padding: 24px; border-radius: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
    h1 { margin-top: 0; font-size: 22px; color: #0f172a; }
    .section { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin-bottom: 16px; background: #fafbfd; }
    .section-title { font-weight: bold; margin-bottom: 10px; color: #0f4c81; }
    label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: bold; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 12px; font-size: 14px; }
    textarea { min-height: 75px; resize: vertical; }
    button { width: 100%; padding: 12px; background: #0f766e; color: #fff; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; }
    button:hover { background: #115e59; }
    .error { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-bottom: 14px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>إضافة سجل مريض جديد</h1>
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
      <div class="section">
        <div class="section-title">البيانات الأساسية والطبية</div>
        <label>الاسم الكامل</label>
        <input type="text" name="full_name" required />

        <label>فصيلة الدم</label>
        <input type="text" name="blood_type" placeholder="مثال: O+" required />

        <label>الحساسيات</label>
        <textarea name="allergies" placeholder="مثال: حساسية البنسلين أو المكسرات (أو اكتب: لا يوجد)"></textarea>

        <label>الأمراض المزمنة</label>
        <textarea name="medical_conditions" placeholder="مثال: السكري، الضغط، الربو (أو اكتب: لا يوجد)"></textarea>
        </div>

      <div class="section">
        <div class="section-title">جهة اتصال الطوارئ 1</div>
        <label>الاسم أو صلة القرابة</label>
        <input type="text" name="contact1_name" placeholder="مثال: الأب / الأم / الأخ" required />

        <label>رقم الجوال</label>
        <input type="tel" name="contact1_phone" placeholder="مثال: 05XXXXXXXX" required />
      </div>

      <div class="section">
        <div class="section-title">جهة اتصال الطوارئ 2 (اختياري)</div>
        <label>الاسم أو صلة القرابة</label>
        <input type="text" name="contact2_name" placeholder="مثال: الزوجة / الابن / قريب" />

        <label>رقم الجوال</label>
        <input type="tel" name="contact2_phone" placeholder="مثال: 05XXXXXXXX" />
      </div>

      <button type="submit">حفظ وتشفير البيانات</button>
    </form>
  </div>
</body>
</html>
"""


NFC_CARD_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>أمان ميديكا - بطاقة طوارئ</title>
  <style>
    body { font-family: Tahoma, Arial, sans-serif; background: #f1f5f9; margin: 0; padding: 16px; color: #0f172a; }
    .wrap { max-width: 560px; margin: auto; }
    .header { background: #b91c1c; color: #fff; padding: 18px; border-radius: 14px; margin-bottom: 14px; }
    .header h1 { margin: 0 0 6px 0; font-size: 22px; }
    .token { font-size: 13px; opacity: 0.9; }
    .box { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-right: 5px solid #0f766e; }
    .box-alert { border-right-color: #dc2626; }
    .label { font-size: 13px; color: #64748b; margin-bottom: 6px; font-weight: bold; }
    .value { font-size: 18px; font-weight: bold; white-space: pre-line; }
    .contact-relation { font-size: 14px; color: #334155; font-weight: bold; margin-bottom: 4px; }
    .contact-phone { font-size: 19px; font-weight: bold; color: #0f172a; margin-bottom: 10px; direction: ltr; text-align: right; }
    .call-btn { display: inline-block; text-decoration: none; background: #15803d; color: #fff; padding: 10px 16px; border-radius: 8px; font-weight: bold; font-size: 15px; }
    .call-btn:hover { background: #166534; }
    .not-found { background: #fff; padding: 24px; border-radius: 12px; text-align: center; border-top: 4px solid #dc2626; }
  </style>
</head>
<body>
  <div class="wrap">
    {% if not found %}
      <div class="not-found">
        <h2>لم يتم العثور على سجل طبي</h2>
        <p>الرمز {{ token }} غير مسجل في النظام حالياً.</p>
      </div>
    {% else %}
      <div class="header">
        <h1>بطاقة طوارئ - {{ patient.full_name }}</h1>
        <div class="token">رمز البطاقة: {{ token }}</div>
      </div>

      <div class="box">
        <div class="label">فصيلة الدم</div>
        <div class="value">{{ patient.blood_type or "غير محدد" }}</div>
      </div>

      <div class="box box-alert">
        <div class="label">الحساسيات</div>
        <div class="value">{{ patient.allergies or "لا يوجد" }}</div>
      </div>

      <div class="box">
        <div class="label">الأمراض المزمنة</div>
        <div class="value">{{ patient.medical_conditions or "لا يوجد" }}</div>
      </div>

      {% for c in emergency_contacts %}
        <div class="box">
          <div class="label">جهة اتصال الطوارئ {{ loop.index }}</div>
          <div class="contact-relation">{{ c.relation }}</div>
          <div class="contact-phone">{{ c.phone or "غير متوفر" }}</div>
          {% if c.tel_href %}
            <a class="call-btn" href="tel:{{ c.tel_href }}">اتصال مباشر</a>
          {% endif %}
        </div>
      {% endfor %}
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/")
def home():
    return {
        "service": "Aman Medical NFC Emergency API",
        "status": "ok",
        "add_patient": "/add",
        "emergency_card": "/nfc/<token>",
    }


@app.route("/add", methods=["GET", "POST"])
def create_patient():
    if request.method == "POST":
        nfc_token = generate_nfc_token()
        full_name =
        request.form.get("full_name", "").strip()
        blood_type = request.form.get("blood_type", "").strip()
        allergies = request.form.get("allergies", "").strip() or "لا يوجد"
        medical_conditions = request.form.get("medical_conditions", "").strip() or "لا يوجد"

        c1_name = request.form.get("contact1_name", "").strip()
        c1_phone = request.form.get("contact1_phone", "").strip()
        c2_name = request.form.get("contact2_name", "").strip()
        c2_phone = request.form.get("contact2_phone", "").strip()

        emergency_contact = pack_emergency_contacts(c1_name, c1_phone, c2_name, c2_phone)
        merged_conditions = f"الحساسيات: {allergies}\nالأمراض المزمنة: {medical_conditions}"

        try:
            add_patient(
                nfc_token=nfc_token,
                full_name=full_name,
                blood_type=blood_type,
                medical_conditions=merged_conditions,
                emergency_contact=emergency_contact,
            )
            return redirect(url_for("view_patient_by_nfc", token=nfc_token))
        except Exception as e:
            return render_template_string(
                ADD_PATIENT_HTML,
                error=f"حدث خطأ أثناء حفظ البيانات: {e}",
            )

    return render_template_string(ADD_PATIENT_HTML, error=None)


@app.route("/nfc/<token>")
def view_patient_by_nfc(token):
    patient = get_patient_by_token(token)
    if not patient:
        return render_template_string(NFC_CARD_HTML, found=False, token=token)

    raw_conditions = patient.get("medical_conditions", "") if isinstance(patient, dict) else getattr(patient, "medical_conditions", "")
    raw_contacts = patient.get("emergency_contact", "") if isinstance(patient, dict) else getattr(patient, "emergency_contact", "")

    allergies_text = "لا يوجد"
    chronic_text = raw_conditions or "لا يوجد"

    lines = [ln.strip() for ln in str(raw_conditions).splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("الحساسيات:"):
            allergies_text = ln.replace("الحساسيات:", "", 1).strip() or "لا يوجد"
        elif ln.startswith("الأمراض المزمنة:"):
            chronic_text = ln.replace("الأمراض المزمنة:", "", 1).strip() or "لا يوجد"

    patient_view = {
        "full_name": patient.get("full_name", "") if isinstance(patient, dict) else getattr(patient, "full_name", ""),
        "blood_type": patient.get("blood_type", "") if isinstance(patient, dict) else getattr(patient, "blood_type", ""),
        "allergies": allergies_text,
        "medical_conditions": chronic_text,
    }

    contacts = parse_emergency_contacts(raw_contacts)
    return render_template_string(
        NFC_CARD_HTML,
        found=True,
        token=token,
        patient=patient_view,
        emergency_contacts=contacts,
    )


if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
