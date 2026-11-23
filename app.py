import os
import secrets
from flask import Flask, jsonify, render_template_string, request, redirect, url_for
from dotenv import load_dotenv
from database import init_db, get_patient_by_token, add_patient

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# تهيئة قاعدة البيانات عند بدء التشغيل
init_db()

EMERGENCY_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أمان ميديكا - بطاقة طوارئ</title>
    <style>
        body {
            font-family: Tahoma, Arial, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 20px;
            color: #1f2937;
        }
        .card {
            max-width: 520px;
            margin: 30px auto;
            background: #ffffff;
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
            border-top: 6px solid #dc2626;
        }
        .badge {
            display: inline-block;
            background: #fee2e2;
            color: #b91c1c;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        h1 {
            margin: 0 0 18px 0;
            font-size: 22px;
        }
        .row {
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px solid #f1f5f9;
        }
        .label {
            font-size: 13px;
            color: #6b7280;
            margin-bottom: 4px;
        }
        .value {
            font-size: 17px;
            font-weight: bold;
        }
        .blood {
            color: #dc2626;
            font-size: 20px;
        }
        .alert-box {
            background: #fff7ed;
            border: 1px solid #fdba74;
            padding: 12px;
            border-radius: 8px;
            color: #9a3412;
        }
        .not-found {
            text-align: center;
            color: #b91c1c;
        }
    </style>
</head>
<body>
    <div class="card">
        {% if patient %}
            <div class="badge"> بطاقة طوارئ طبية - أمان ميديكل</div>
            <h1>{{ patient.full_name }}</h1>

            <div class="row">
                <div class="label">فصيلة الدم</div>
                <div class="value blood">{{ patient.blood_type }}</div>
            </div>

            <div class="row">
                <div class="label">الحالات الطبية / الحساسيات / الأدوية</div>
                <div class="alert-box">{{ patient.medical_conditions }}</div>
            </div> 

            <div class="row">
                <div class="label">جهة الاتصال للطوارئ</div>
                <div class="value">{{ patient.emergency_contact }}</div>
            </div> {% if patient.emergency_contact %}
<div style="margin-top: 12px; margin-bottom: 16px;">
  <a href="tel:{{ patient.emergency_contact | replace(' ', '') | replace('-', '') }}"
     style="display: block; width: 100%; box-sizing: border-box; background-color: #d93025; color: #ffffff;
            text-align: center; padding: 14px 16px; border-radius: 10px;
            text-decoration: none; font-weight: bold; font-size: 17px;">
    📞 اتصال مباشر بجهة الطوارئ ({{ patient.emergency_contact }})
  </a>
</div>
{% endif %}

            <div class="row" style="border-bottom: none; margin-bottom: 0;">
                <div class="label">رمز البطاقة (NFC Token)</div>
                <div class="value" style="font-size: 14px; color: #4b5563;">{{ patient.nfc_token }}</div>
            </div>
        {% else %}
            <div class="not-found">
                <h2>لم يتم العثور على سجل طبي</h2>
                <p>الرمز <strong>{{ token }}</strong> غير مسجل في النظام حالياً.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Aman Medical NFC Emergency API",
        "usage": "افتح الرابط /nfc/<token> لعرض بطاقة الطوارئ"
    })


@app.route("/nfc/<nfc_token>")
def view_patient_by_nfc(nfc_token: str):
    patient = get_patient_by_token(nfc_token)
    return render_template_string(EMERGENCY_PAGE_TEMPLATE, patient=patient, token=nfc_token)


@app.route("/api/nfc/<nfc_token>")
def api_patient_by_nfc(nfc_token: str):
    patient = get_patient_by_token(nfc_token)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(patient)

ADD_PATIENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أمان ميديكل - إضافة مريض</title>
    <style>
        body {
            font-family: Tahoma, Arial, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 20px;
            color: #1f2937;
        }
        .card {
            max-width: 520px;
            margin: 25px auto;
            background: #ffffff;
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
            border-top: 6px solid #0f766e;
        }
        h1 {
            margin: 0 0 18px 0;
            font-size: 21px;
        }
        .field {
            margin-bottom: 14px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: bold;
            font-size: 14px;
        }
        input, textarea, select {
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-family: inherit;
            font-size: 14px;
        }
        textarea {
            min-height: 80px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #0f766e;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            background: #115e59;
        }
        .error {
            background: #fee2e2;
            color: #b91c1c;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 14px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>إضافة سجل مريض جديد</h1>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            
                <input type="text" name="nfc_token" placeholder=" او اتركه فارغا للتوليد التلقائي مثال: AMAN-101" required>
            </div>
            <div class="field">
                <label>الاسم الكامل</label>
                <input type="text" name="full_name" placeholder="مثال: خالد عبدالله" required>
            </div>
            <div class="field">
                <label>فصيلة الدم</label>
                <select name="blood_type" required>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                </select>
            </div>
            <div class="field">
                <label>الحالات الطبية / الحساسيات / الأدوية (سيتم تشفيرها)</label>
                <textarea name="medical_conditions" placeholder="مثال: حساسية بنسلين - سكري النوع الثاني" required></textarea>
            </div>
            <div class="field">
                <label>جهة الاتصال للطوارئ</label>
                <input type="text" name="emergency_contact" placeholder="مثال: أخوه الوالد الاقارب - 0500000000" required>
            </div>
            <button type="submit">حفظ وتشفير البيانات</button>
        </form>
    </div>
</body>
</html>
"""
def generate_nfc_token(prefix: str = "AMAN", length: int = 6) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        token = f"{prefix}-{code}"
        if not get_patient_by_token(token):
            return token

@app.route("/add", methods=["GET", "POST"])
def create_patient():
    if request.method == "POST":
        nfc_token = generate_nfc_token()
        full_name = request.form.get("full_name", "").strip()
        blood_type = request.form.get("blood_type", "").strip()
        medical_conditions = request.form.get("medical_conditions", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()

        try:
            add_patient(
                nfc_token=nfc_token,
                full_name=full_name,
                blood_type=blood_type,
                medical_conditions=medical_conditions,
                emergency_contact=emergency_contact,
            )
            return redirect(url_for("view_patient_by_nfc", nfc_token=nfc_token))
        except Exception as e:
            return render_template_string(
                ADD_PATIENT_TEMPLATE,
                error=f"تعذر حفظ البيانات: {e}",
            )

    return render_template_string(ADD_PATIENT_TEMPLATE, error=None)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
