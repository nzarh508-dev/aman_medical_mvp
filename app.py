import os
import re
import secrets
import string
from flask import Flask, render_template_string, request, redirect, url_for

# تأكد أن ملف database.py يحتوي على هذه الدوال بنفس الأسماء
from database import init_db, add_patient, get_patient_by_token

app = __Flask__(__name__)
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
    body { font-family: Tahoma, Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #0f172a; }
    .container { max-width: 600px; margin: auto; background: #fff; padding: 24px; border-radius: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
    h1 { margin-top: 0; font-size: 22px; color: #0f172a; }
    .section { border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 16px; background: #f8fafc; }
    .section-title { font-weight: bold; margin-bottom: 10px; color: #0f4c81; }
    label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: bold; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 12px; font-family: inherit; }
    textarea { min-height: 70px; resize: vertical; }
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

        <label>العمر</label>
        <input type="number" name="age" min="0" max="130" placeholder="مثال: 25" />

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
        <input type="tel" name="contact1_phone" placeholder="05xxxxxxxx" required />
      </div>

      <div class="section">
        <div class="section-title">جهة اتصال الطوارئ 2 (اختياري)</div>
        <label>الاسم أو صلة القرابة</label>
        <input type="text" name="contact2_name" placeholder="مثال: الزوجة / الابن / قريب" />

        <label>رقم الجوال</label>
        <input type="tel" name="contact2_phone" placeholder="05xxxxxxxx" />
      </div>

      <button type="submit">حفظ وإنشاء بطاقة NFC</button>
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
    .header { background: #0b1c1c; color: #fff; padding: 18px; border-radius: 14px; margin-bottom: 10px; }
    .header h1 { margin: 0 0 6px 0; font-size: 22px; }
    .token { font-size: 13px; opacity: 0.9; }
    .notice { background: #fffbeb; border-right: 4px solid #d97706; color: #78350f; padding: 12px 14px; border-radius: 10px; font-size: 13px; line-height: 1.6; margin-bottom: 12px; }
    .identity-row { display: flex; gap: 12px; margin-bottom: 12px; }
    .identity-box { flex: 1; background: #fff; border-radius: 12px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .age-box { min-width: 110px; flex: 0 0 auto; text-align: center; }
    .box { background: #fff; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .box-alert { border-right: 4px solid #dc2626; }
    .label { font-size: 13px; color: #64748b; margin-bottom: 6px; font-weight: bold; }
    .value { font-size: 18px; font-weight: bold; white-space: pre-line; }
    .contact-relation { font-size: 14px; color: #0f172a; font-weight: bold; margin-bottom: 6px; }
    .contact-phone { font-size: 19px; font-weight: bold; color: #0f172a; margin-bottom: 10px; direction: ltr; text-align: right; }
    .call-btn { display: inline-block; text-decoration: none; background: #15803d; color: #fff; padding: 10px 16px; border-radius: 8px; font-weight: bold; }
    .call-btn:hover { background: #166534; }
    .not-found { background: #fff; padding: 24px; border-radius: 12px; text-align: center; border-top: 4px solid #dc2626; }
  </style>
</head>
<body>
  <div class="wrap">
    {% if not found %}
      <div class="not-found">
        <h2>لم يتم العثور على سجل طبي</h2>
        <p>غير مسجل في النظام حالياً ({{ token }})</p>
      </div>
    {% else %}
      <div class="header">
        <h1>بطاقة حالات الطوارئ</h1>
        <div class="token">رمز البطاقة: {{ token }}</div>
      </div>

      <div class="notice">
        <strong>تنبيه:</strong> يجب استخدام هذه البطاقة في الحالات الطارئة تحت إشراف ولي الأمر أو الجهات المختصة للمساعدة في الحالات الطارئة.
      </div>

      <div class="identity-row">
        <div class="identity-box">
          <div class="label">الاسم</div>
          <div class="value">{{ patient.full_name }}</div>
        </div>
        <div class="identity-box age-box">
          <div class="label">العمر</div>
          <div class="value">{{ age_text }}</div>
        </div>
      </div>

      <div class="box">
        <div class="label">فصيلة الدم</div>
        <div class="value">{{ patient.blood_type or "غير محدد" }}</div>
      </div>
      <div class="box box-alert">
        <div class="label">الحساسيات</div>
        <div class="value">{{ allergies_text }}</div>
      </div>

      <div class="box">
        <div class="label">الأمراض المزمنة</div>
        <div class="value">{{ chronic_text }}</div>
      </div>

      {% for c in emergency_contacts %}
        <div class="box">
          <div class="label">{{ c.badge_label }}</div>
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
        "service": "Aman Medica NFC Emergency API",
        "status": "ok",
        "add_patient": "/add",
        "emergency_card": "/nfc/<token>",
    }


@app.route("/add", methods=["GET", "POST"])
def create_patient():
    if request.method == "POST":
        nfc_token = generate_nfc_token()
        full_name = request.form.get("full_name", "").strip()
        age = request.form.get("age", "").strip()
        blood_type = request.form.get("blood_type", "").strip()
        allergies = request.form.get("allergies", "").strip() or "لا يوجد"
        medical_conditions = request.form.get("medical_conditions", "").strip() or "لا يوجد"

        c1_name = request.form.get("contact1_name", "").strip()
        c1_phone = request.form.get("contact1_phone", "").strip()
        c2_name = request.form.get("contact2_name", "").strip()
        c2_phone = request.form.get("contact2_phone", "").strip()

        emergency_contact = pack_emergency_contacts(c1_name, c1_phone, c2_name, c2_phone)
        age_line = f"العمر: {age}" if age else ""
        merged_parts = [p for p in [age_line, f"الحساسيات: {allergies}", f"الأمراض المزمنة: {medical_conditions}"] if p]
        merged_conditions = "\n".join(merged_parts)

        try:
            add_patient(
                nfc_token=nfc_token,
                full_name=full_name,
                blood_type=blood_type,
                medical_conditions=merged_conditions,
                emergency_contact=emergency_contact,
            )
        except TypeError:
            # توافق احتياطي في حال كانت دالة add_patient تستخدم أسماء معاملات قديمة
            add_patient(
                nfc_token,
                full_name,
                blood_type,
                merged_conditions,
                emergency_contact,
            )
        except Exception as e:
            return render_template_string(ADD_PATIENT_HTML, error=f"تعذر حفظ البيانات: {e}"), 500

        return redirect(url_for("view_patient_by_nfc", token=nfc_token))

    return render_template_string(ADD_PATIENT_HTML, error=None)


@app.route("/nfc/<token>")
def view_patient_by_nfc(token):
    patient = get_patient_by_token(token)
    if not patient:
        return render_template_string(NFC_CARD_HTML, found=False, token=token)

    raw_conditions = patient.get("medical_conditions", "") if isinstance(patient, dict) else ""
    raw_contacts = patient.get("emergency_contact", "") if isinstance(patient, dict) else ""
    raw_age = patient.get("age", "") if isinstance(patient, dict) else ""

    age_text = str(raw_age).strip() if str(raw_age).strip() else "غير محدد"
    allergies_text = "لا يوجد"
    chronic_text = raw_conditions or "لا يوجد"

    lines = [ln.strip() for ln in str(raw_conditions).splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("العمر:") and age_text == "غير محدد":
            age_text = ln.replace("العمر:", "", 1).strip() or "غير محدد"
        elif ln.startswith("الحساسيات:"):
            allergies_text = ln.replace("الحساسيات:", "", 1).strip() or "لا يوجد"
        elif ln.startswith("الأمراض المزمنة:"):
            chronic_text = ln.replace("الأمراض المزمنة:", "", 1).strip() or "لا يوجد"
    if chronic_text == raw_conditions and lines:
        filtered = [ln for ln in lines if not ln.startswith(("العمر:", "الحساسيات:", "الأمراض المزمنة:"))]
        chronic_text = "\n".join(filtered) if filtered else "لا يوجد"

    user_contacts = parse_emergency_contacts(raw_contacts)
    emergency_contacts = []
    for idx, c in enumerate(user_contacts, start=1):
        emergency_contacts.append({
            "badge_label": f"جهة اتصال الطوارئ {idx}",
            "relation": c["relation"],
            "phone": c["phone"],
            "tel_href": c["tel_href"],
        })

    emergency_contacts.extend([
        {
            "badge_label": "الجهة الرسمية 1 - الإسعاف",
            "relation": "الإسعاف (الهلال الأحمر السعودي)",
            "phone": "997",
            "tel_href": "997",
        },
        {
            "badge_label": "الجهة الرسمية 2 - الشرطة / الطوارئ الموحدة",
            "relation": "الشرطة / الطوارئ الموحدة (911 أو 999)",
            "phone": "911",
            "tel_href": "911",
        },
    ])

    return render_template_string(
        NFC_CARD_HTML,
        found=True,
        token=token,
        patient=patient,
        age_text=age_text,
        allergies_text=allergies_text,
        chronic_text=chronic_text,
        emergency_contacts=emergency_contacts,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
