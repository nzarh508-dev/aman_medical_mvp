import os
import sqlite3
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

DB_NAME = "aman_medical.db"


def get_cipher() -> Fernet:
    """قراءة مفتاح التشفير من البيئة وتجهيز أداة التشفير Fernet."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("لم يتم العثور على ENCRYPTION_KEY في ملف .env")
    return Fernet(key.strip().encode("utf-8"))


def init_db() -> None:
    """إنشاء جدول المرضى في قاعدة البيانات إذا لم يكن موجوداً."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nfc_token TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            blood_type TEXT NOT NULL,
            encrypted_conditions BLOB NOT NULL,
            emergency_contact TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def encrypt_text(plain_text: str) -> bytes:
    """تشفير النص الطبي قبل حفظه في قاعدة البيانات."""
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode("utf-8"))


def decrypt_text(encrypted_data: bytes) -> str:
    """فك تشفير البيانات الطبية عند الحاجة لعرضها."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_data).decode("utf-8")

def get_patient_by_token(nfc_token: str) -> dict | None:
    """جلب بيانات المريض عبر رمز NFC وفك تشفير الحالات الطبية."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nfc_token, full_name, blood_type, encrypted_conditions, emergency_contact
        FROM patients
        WHERE nfc_token = ?
        """,
        (nfc_token,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    conditions_plain = decrypt_text(row["encrypted_conditions"])
    return {
        "id": row["id"],
        "nfc_token": row["nfc_token"],
        "full_name": row["full_name"],
        "blood_type": row["blood_type"],
        "medical_conditions": conditions_plain,
        "emergency_contact": row["emergency_contact"],
    }
def add_patient(
    nfc_token: str,
    full_name: str,
    blood_type: str,
    medical_conditions: str,
    emergency_contact: str,
) -> int:
    """إضافة مريض جديد مع تشفير الحالات الطبية قبل الحفظ."""
    encrypted_conditions = encrypt_text(medical_conditions)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (
            nfc_token, full_name, blood_type, encrypted_conditions, emergency_contact
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (nfc_token, full_name, blood_type, encrypted_conditions, emergency_contact),
    )
    conn.commit()
    patient_id = cursor.lastrowid
    conn.close()
    return patient_id

if __name__ == "__main__":
    init_db()
    sample = "حساسية بنسلين - سكري"
    enc = encrypt_text(sample)
    dec = decrypt_text(enc)
    print("تم إنشاء قاعدة البيانات بنجاح.")
    print("النص المشفر:", enc)
    print("بعد فك التشفير:", dec)