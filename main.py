import easyocr
import shutil
import os
import re
import random
import time
import smtplib

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Base
from models import Pelanggan as PelangganModel
from models import User as UserModel
from passlib.context import CryptContext
from auth import create_access_token, SECRET_KEY, ALGORITHM
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env"),
    override=True
)

otp_store = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

reader = easyocr.Reader(['en'])


class RegisterData(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    otp: str

class SendOTPData(BaseModel):
    email: str

class ResetPasswordData(BaseModel):
    email: str
    otp: str
    new_password: str

class LoginData(BaseModel):
    email: str
    password: str

class PelangganCreate(BaseModel):
    nama: str
    alamat: str
    no_meter: str
    kategori: str


class PelangganUpdate(BaseModel):
    nama: str
    alamat: str
    no_meter: str
    kategori: str


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token tidak valid"
        )

def send_email_otp(to_email: str, otp: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD", "").replace(" ", "")

    print("SMTP EMAIL:", smtp_email)
    print("SMTP PASSWORD ADA:", "YA" if smtp_password else "TIDAK")
    print("PANJANG PASSWORD:", len(smtp_password) if smtp_password else 0)

    if not smtp_email or not smtp_password:
        raise HTTPException(
            status_code=500,
            detail="Konfigurasi email belum lengkap"
        )

    message = EmailMessage()
    message["Subject"] = "Kode OTP Registrasi TirtaDesa"
    message["From"] = smtp_email
    message["To"] = to_email

    message.set_content(
        f"""
Halo,

Kode OTP registrasi TirtaDesa kamu adalah:

{otp}

Kode ini berlaku selama 5 menit.

Jangan berikan kode ini kepada siapa pun.

Terima kasih,
TirtaDesa
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengirim OTP ke email: {str(e)}"
        )


@app.get("/")
def root():
    return {"message": "TirtaDesa API Running"}

@app.post("/send-otp")
def send_otp(
    data: SendOTPData,
    db: Session = Depends(get_db)
):
    otp = str(random.randint(100000, 999999))

    otp_store[data.email] = {
        "otp": otp,
        "expired_at": time.time() + 300
    }

    send_email_otp(data.email, otp)

    return {
        "message": "OTP berhasil dikirim ke email"
    }

@app.post("/forgot-password/send-otp")
def forgot_password_send_otp(
    data: SendOTPData,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Email tidak ditemukan"
        )

    otp = str(random.randint(100000, 999999))

    otp_store[data.email] = {
        "otp": otp,
        "expired_at": time.time() + 300
    }

    send_email_otp(data.email, otp)

    return {
        "message": "OTP reset password berhasil dikirim"
    }

@app.post("/forgot-password/reset")
def reset_password(
        data: ResetPasswordData,
        db: Session = Depends(get_db)
    ):
    otp_data = otp_store.get(data.email)

    if not otp_data:
        raise HTTPException(
            status_code=400,
            detail="OTP belum dikirim"
        )

    if time.time() > otp_data["expired_at"]:
        raise HTTPException(
            status_code=400,
            detail="OTP sudah kadaluarsa"
        )

    if otp_data["otp"] != data.otp:
        raise HTTPException(
            status_code=400,
            detail="OTP salah"
        )

    user = db.query(UserModel).filter(
        UserModel.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Email tidak ditemukan"
        )

    user.password = pwd_context.hash(
        data.new_password
    )

    db.commit()

    del otp_store[data.email]

    return {
        "message": "Password berhasil diubah"
    }

@app.post("/register")
def register(
    data: RegisterData,
    db: Session = Depends(get_db)
):
    otp_data = otp_store.get(data.email)

    if not otp_data:
        raise HTTPException(
            status_code=400,
            detail="OTP belum dikirim"
        )

    if time.time() > otp_data["expired_at"]:
        raise HTTPException(
            status_code=400,
            detail="OTP sudah kadaluarsa"
        )

    if data.otp != otp_data["otp"]:
        raise HTTPException(
            status_code=400,
            detail="Kode OTP salah"
        )
    user_lama = db.query(UserModel).filter(
        UserModel.email == data.email
    ).first()

    if user_lama:
        raise HTTPException(
            status_code=400,
            detail="Email sudah terdaftar"
        )

    hashed_password = pwd_context.hash(data.password)

    user_baru = UserModel(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password=hashed_password,
        role="pelanggan"
    )

    db.add(user_baru)
    db.commit()
    db.refresh(user_baru)

    del otp_store[data.email]

    return {
        "message": "Registrasi berhasil",
        "data": {
            "id": user_baru.id,
            "name": user_baru.name,
            "email": user_baru.email,
            "phone": user_baru.phone,
            "role": user_baru.role
        }
    }


@app.post("/login")
def login(
    data: LoginData,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email atau password salah"
        )

    if not pwd_context.verify(data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Email atau password salah"
        )

    token = create_access_token({
        "sub": user.email,
        "role": user.role
    })

    return {
        "message": "Login berhasil",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role
        }
    }

@app.get("/pelanggan", dependencies=[Depends(verify_token)])
def get_pelanggan(db: Session = Depends(get_db)):

    pelanggan = db.query(PelangganModel).all()

    return {
        "message": "Data pelanggan berhasil diambil",
        "data": pelanggan
    }


@app.post("/pelanggan", dependencies=[Depends(verify_token)])
def tambah_pelanggan(
    data: PelangganCreate,
    db: Session = Depends(get_db)
):

    pelanggan_baru = PelangganModel(
        nama=data.nama,
        alamat=data.alamat,
        no_meter=data.no_meter,
        kategori=data.kategori
    )

    db.add(pelanggan_baru)
    db.commit()
    db.refresh(pelanggan_baru)

    return {
        "message": "Pelanggan berhasil ditambahkan",
        "data": pelanggan_baru
    }


@app.get("/pelanggan/{id}", dependencies=[Depends(verify_token)])
def detail_pelanggan(
    id: int,
    db: Session = Depends(get_db)
):

    pelanggan = db.query(PelangganModel).filter(
        PelangganModel.id == id
    ).first()

    if pelanggan:
        return {
            "message": "Detail pelanggan ditemukan",
            "data": pelanggan
        }

    raise HTTPException(
        status_code=404,
        detail="Pelanggan tidak ditemukan"
    )


@app.put("/pelanggan/{id}", dependencies=[Depends(verify_token)])
def update_pelanggan(
    id: int,
    data: PelangganUpdate,
    db: Session = Depends(get_db)
):

    pelanggan = db.query(PelangganModel).filter(
        PelangganModel.id == id
    ).first()

    if not pelanggan:
        raise HTTPException(
            status_code=404,
            detail="Pelanggan tidak ditemukan"
        )

    pelanggan.nama = data.nama
    pelanggan.alamat = data.alamat
    pelanggan.no_meter = data.no_meter
    pelanggan.kategori = data.kategori

    db.commit()
    db.refresh(pelanggan)

    return {
        "message": "Data pelanggan berhasil diperbarui",
        "data": pelanggan
    }


@app.delete("/pelanggan/{id}", dependencies=[Depends(verify_token)])
def delete_pelanggan(
    id: int,
    db: Session = Depends(get_db)
):

    pelanggan = db.query(PelangganModel).filter(
        PelangganModel.id == id
    ).first()

    if not pelanggan:
        raise HTTPException(
            status_code=404,
            detail="Pelanggan tidak ditemukan"
        )

    db.delete(pelanggan)
    db.commit()

    return {
        "message": "Pelanggan berhasil dihapus"
    }


@app.post("/scan-meter", dependencies=[Depends(verify_token)])
def scan_meter(file: UploadFile = File(...)):

    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)

    file_path = f"{upload_folder}/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    hasil = reader.readtext(file_path, detail=0)

    teks_ocr = " ".join(hasil)

    angka_meter = re.findall(r"\d+", teks_ocr)
    angka_meter = "".join(angka_meter)

    return {
        "message": "OCR berhasil diproses",
        "hasil_teks_ocr": teks_ocr,
        "angka_meter": angka_meter
    }