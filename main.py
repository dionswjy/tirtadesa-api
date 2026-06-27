import easyocr
import shutil
import os
import re
import random
import time
import smtplib

from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Base, Pelanggan as PelangganModel, User as UserModel, Meter as MeterModel, CatatMeter as CatatMeterModel, Tagihan as TagihanModel, Komplain as KomplainModel, PemasanganBaru as PemasanganBaruModel
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

def serialize_model(instance):
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }


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

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    role: str = "pelanggan"

class UserUpdate(BaseModel):
    role: str

class UserEdit(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

class PelangganCreate(BaseModel):
    nama: str
    alamat: str
    no_meter: str
    kategori: str
    no_hp: str
    nik: str
    status_pelanggan: str
    jenis_pelanggan: str

class MeterCreate(BaseModel):
    pelanggan_id: int
    no_meter: str
    status_meter: str
    alamat_lokasi: str

class MeterUpdate(BaseModel):
    pelanggan_id: Optional[int] = None
    no_meter: Optional[str] = None
    status_meter: Optional[str] = None
    alamat_lokasi: Optional[str] = None

class CatatMeterCreate(BaseModel):
    meter_id: int
    bulan: str
    petugas_nama: str
    angka_meter_lalu: float
    angka_meter_kini: float
    penggunaan_m3: float

class CatatMeterUpdate(BaseModel):
    meter_id: Optional[int] = None
    bulan: Optional[str] = None
    petugas_nama: Optional[str] = None
    angka_meter_lalu: Optional[float] = None
    angka_meter_kini: Optional[float] = None
    penggunaan_m3: Optional[float] = None

class TagihanCreate(BaseModel):
    meter_id: int
    bulan: str
    penggunaan_m3: float
    total_tagihan: float
    status_pembayaran: str

class TagihanUpdate(BaseModel):
    meter_id: Optional[int] = None
    bulan: Optional[str] = None
    penggunaan_m3: Optional[float] = None
    total_tagihan: Optional[float] = None
    status_pembayaran: Optional[str] = None

class KomplainCreate(BaseModel):
    pelanggan_id: int
    judul: str
    deskripsi: str

class KomplainUpdate(BaseModel):
    pelanggan_id: Optional[int] = None
    judul: Optional[str] = None
    deskripsi: Optional[str] = None
    status: Optional[str] = None

class PemasanganBaruCreate(BaseModel):
    nama: str
    nik: str
    no_hp: str
    alamat: str
    jenis_pelanggan: str

class PemasanganBaruUpdate(BaseModel):
    nama: Optional[str] = None
    nik: Optional[str] = None
    no_hp: Optional[str] = None
    alamat: Optional[str] = None
    jenis_pelanggan: Optional[str] = None
    status: Optional[str] = None


class PelangganUpdate(BaseModel):
    nama: Optional[str] = None
    alamat: Optional[str] = None
    no_meter: Optional[str] = None
    kategori: Optional[str] = None
    no_hp: Optional[str] = None
    nik: Optional[str] = None
    status_pelanggan: Optional[str] = None
    jenis_pelanggan: Optional[str] = None


class MeterCreate(BaseModel):
    pelanggan_id: int
    no_meter: str
    status_meter: str
    alamat_lokasi: str


class CatatMeterCreate(BaseModel):
    meter_id: int
    bulan: str
    petugas_nama: str
    angka_meter_lalu: float
    angka_meter_kini: float
    penggunaan_m3: float


class TagihanCreate(BaseModel):
    meter_id: int
    bulan: str
    penggunaan_m3: float
    total_tagihan: float
    status_pembayaran: str


class KomplainCreate(BaseModel):
    pelanggan_id: int
    judul: str
    deskripsi: str


class PemasanganBaruCreate(BaseModel):
    nama: str
    nik: str
    no_hp: str
    alamat: str
    jenis_pelanggan: str


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


def verify_admin(
    payload: dict = Depends(verify_token)
):
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Akses admin diperlukan"
        )

    return payload


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

@app.post("/auth/login")
def admin_login(
    data: LoginData,
    db: Session = Depends(get_db)
):
    return login(data, db)


@app.get("/admin/dashboard")
def dashboard(
    db: Session = Depends(get_db)
):
    total_pelanggan = db.query(PelangganModel).count()
    total_meter = db.query(MeterModel).count()
    komplain_baru = db.query(KomplainModel).filter(KomplainModel.status == "pending").count()
    pengajuan_pemasangan_baru = db.query(PemasanganBaruModel).filter(PemasanganBaruModel.status == "pending").count()
    tagihan_belum_lunas = db.query(TagihanModel).filter(TagihanModel.status_pembayaran == "belum_lunas").count()

    return {
        "total_pelanggan": total_pelanggan,
        "total_meter": total_meter,
        "komplain_baru": komplain_baru,
        "pengajuan_pemasangan_baru": pengajuan_pemasangan_baru,
        "tagihan_belum_lunas": tagihan_belum_lunas
    }

@app.post("/admin/pelanggan")
def admin_tambah_pelanggan(
    data: PelangganCreate,
    db: Session = Depends(get_db)
):
    pelanggan = PelangganModel(
        nama=data.nama,
        alamat=data.alamat,
        no_meter=data.no_meter,
        kategori=data.kategori,
        no_hp=data.no_hp,
        nik=data.nik,
        status_pelanggan=data.status_pelanggan,
        jenis_pelanggan=data.jenis_pelanggan
    )

    db.add(pelanggan)
    db.commit()
    db.refresh(pelanggan)

    return serialize_model(pelanggan)


@app.post("/admin/user", dependencies=[Depends(verify_admin)])
def admin_create_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(UserModel).filter(
        UserModel.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email sudah terdaftar"
        )

    hashed_password = pwd_context.hash(data.password)

    user = UserModel(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password=hashed_password,
        role=data.role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User berhasil ditambahkan",
        "data": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role
        }
    }


@app.get("/admin/users", dependencies=[Depends(verify_admin)])
def admin_get_users(
    db: Session = Depends(get_db)
):
    users = db.query(UserModel).all()
    return [serialize_model(user) for user in users]


@app.put("/admin/user/{id}/role", dependencies=[Depends(verify_admin)])
def admin_update_user_role(
    id: int,
    data: UserUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.id == id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan"
        )

    user.role = data.role
    db.commit()
    db.refresh(user)

    return {
        "message": "Role user berhasil diubah",
        "data": serialize_model(user)
    }


@app.put("/admin/user/{id}", dependencies=[Depends(verify_admin)])
def admin_edit_user(
    id: int,
    data: UserEdit,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.id == id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan"
        )

    if data.name is not None:
        user.name = data.name
    if data.phone is not None:
        user.phone = data.phone
    if data.role is not None:
        user.role = data.role
    if data.password is not None:
        user.password = pwd_context.hash(data.password)

    db.commit()
    db.refresh(user)

    return {
        "message": "User berhasil diperbarui",
        "data": serialize_model(user)
    }


@app.delete("/admin/user/{id}", dependencies=[Depends(verify_admin)])
def admin_delete_user(
    id: int,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.id == id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan"
        )

    db.delete(user)
    db.commit()

    return {"message": "User berhasil dihapus"}


@app.put("/meter/{id}", dependencies=[Depends(verify_token)])
def update_meter(
    id: int,
    data: MeterUpdate,
    db: Session = Depends(get_db)
):
    meter = db.query(MeterModel).filter(
        MeterModel.id == id
    ).first()

    if not meter:
        raise HTTPException(
            status_code=404,
            detail="Meter tidak ditemukan"
        )

    if data.pelanggan_id is not None:
        meter.pelanggan_id = data.pelanggan_id
    if data.no_meter is not None:
        meter.no_meter = data.no_meter
    if data.status_meter is not None:
        meter.status_meter = data.status_meter
    if data.alamat_lokasi is not None:
        meter.alamat_lokasi = data.alamat_lokasi

    db.commit()
    db.refresh(meter)

    return {
        "message": "Meter berhasil diperbarui",
        "data": serialize_model(meter)
    }


@app.put("/admin/catat-meter/{id}", dependencies=[Depends(verify_token)])
def update_catat_meter(
    id: int,
    data: CatatMeterUpdate,
    db: Session = Depends(get_db)
):
    record = db.query(CatatMeterModel).filter(
        CatatMeterModel.id == id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Catatan meter tidak ditemukan"
        )

    if data.meter_id is not None:
        record.meter_id = data.meter_id
    if data.bulan is not None:
        record.bulan = data.bulan
    if data.petugas_nama is not None:
        record.petugas_nama = data.petugas_nama
    if data.angka_meter_lalu is not None:
        record.angka_meter_lalu = data.angka_meter_lalu
    if data.angka_meter_kini is not None:
        record.angka_meter_kini = data.angka_meter_kini
    if data.penggunaan_m3 is not None:
        record.penggunaan_m3 = data.penggunaan_m3

    db.commit()
    db.refresh(record)

    return {
        "message": "Catatan meter berhasil diperbarui",
        "data": serialize_model(record)
    }


@app.put("/admin/tagihan/{id}", dependencies=[Depends(verify_token)])
def update_tagihan(
    id: int,
    data: TagihanUpdate,
    db: Session = Depends(get_db)
):
    bill = db.query(TagihanModel).filter(
        TagihanModel.id == id
    ).first()

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Tagihan tidak ditemukan"
        )

    if data.meter_id is not None:
        bill.meter_id = data.meter_id
    if data.bulan is not None:
        bill.bulan = data.bulan
    if data.penggunaan_m3 is not None:
        bill.penggunaan_m3 = data.penggunaan_m3
    if data.total_tagihan is not None:
        bill.total_tagihan = data.total_tagihan
    if data.status_pembayaran is not None:
        bill.status_pembayaran = data.status_pembayaran
        bill.tanggal_bayar = datetime.utcnow().isoformat() if data.status_pembayaran == "lunas" else None

    db.commit()
    db.refresh(bill)

    return {
        "message": "Tagihan berhasil diperbarui",
        "data": serialize_model(bill)
    }


@app.put("/admin/komplain/{id}", dependencies=[Depends(verify_token)])
def update_komplain(
    id: int,
    data: KomplainUpdate,
    db: Session = Depends(get_db)
):
    complaint = db.query(KomplainModel).filter(
        KomplainModel.id == id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Komplain tidak ditemukan"
        )

    if data.pelanggan_id is not None:
        complaint.pelanggan_id = data.pelanggan_id
    if data.judul is not None:
        complaint.judul = data.judul
    if data.deskripsi is not None:
        complaint.deskripsi = data.deskripsi
    if data.status is not None:
        complaint.status = data.status

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Komplain berhasil diperbarui",
        "data": serialize_model(complaint)
    }


@app.put("/admin/pemasangan-baru/{id}", dependencies=[Depends(verify_token)])
def update_pemasangan_baru(
    id: int,
    data: PemasanganBaruUpdate,
    db: Session = Depends(get_db)
):
    submission = db.query(PemasanganBaruModel).filter(
        PemasanganBaruModel.id == id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Pengajuan pemasangan tidak ditemukan"
        )

    if data.nama is not None:
        submission.nama = data.nama
    if data.nik is not None:
        submission.nik = data.nik
    if data.no_hp is not None:
        submission.no_hp = data.no_hp
    if data.alamat is not None:
        submission.alamat = data.alamat
    if data.jenis_pelanggan is not None:
        submission.jenis_pelanggan = data.jenis_pelanggan
    if data.status is not None:
        submission.status = data.status

    db.commit()
    db.refresh(submission)

    return {
        "message": "Pengajuan pemasangan berhasil diperbarui",
        "data": serialize_model(submission)
    }

@app.delete("/admin/pelanggan/{id}")
def admin_delete_pelanggan(
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

    return {"message": "Berhasil dihapus"}




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

    return [serialize_model(item) for item in pelanggan]


@app.post("/pelanggan", dependencies=[Depends(verify_token)])
def tambah_pelanggan(
    data: PelangganCreate,
    db: Session = Depends(get_db)
):

    pelanggan_baru = PelangganModel(
        nama=data.nama,
        alamat=data.alamat,
        no_meter=data.no_meter,
        kategori=data.kategori,
        no_hp=data.no_hp,
        nik=data.nik,
        status_pelanggan=data.status_pelanggan,
        jenis_pelanggan=data.jenis_pelanggan
    )

    db.add(pelanggan_baru)
    db.commit()
    db.refresh(pelanggan_baru)

    return {
        "message": "Pelanggan berhasil ditambahkan",
        "data": serialize_model(pelanggan_baru)
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

    if data.nama is not None:
        pelanggan.nama = data.nama
    if data.alamat is not None:
        pelanggan.alamat = data.alamat
    if data.no_meter is not None:
        pelanggan.no_meter = data.no_meter
    if data.kategori is not None:
        pelanggan.kategori = data.kategori
    if data.no_hp is not None:
        pelanggan.no_hp = data.no_hp
    if data.nik is not None:
        pelanggan.nik = data.nik
    if data.status_pelanggan is not None:
        pelanggan.status_pelanggan = data.status_pelanggan
    if data.jenis_pelanggan is not None:
        pelanggan.jenis_pelanggan = data.jenis_pelanggan

    db.commit()
    db.refresh(pelanggan)

    return {
        "message": "Data pelanggan berhasil diperbarui",
        "data": serialize_model(pelanggan)
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


@app.get("/meter", dependencies=[Depends(verify_token)])
def get_meter(db: Session = Depends(get_db)):
    meters = db.query(MeterModel).all()
    return {
        "message": "Data meter berhasil diambil",
        "data": [serialize_model(meter) for meter in meters]
    }


@app.post("/meter", dependencies=[Depends(verify_token)])
def tambah_meter(
    data: MeterCreate,
    db: Session = Depends(get_db)
):
    meter = MeterModel(
        pelanggan_id=data.pelanggan_id,
        no_meter=data.no_meter,
        status_meter=data.status_meter,
        alamat_lokasi=data.alamat_lokasi
    )

    db.add(meter)
    db.commit()
    db.refresh(meter)

    return {
        "message": "Meter berhasil ditambahkan",
        "data": serialize_model(meter)
    }


@app.delete("/meter/{id}", dependencies=[Depends(verify_token)])
def delete_meter(
    id: int,
    db: Session = Depends(get_db)
):
    meter = db.query(MeterModel).filter(
        MeterModel.id == id
    ).first()

    if not meter:
        raise HTTPException(
            status_code=404,
            detail="Meter tidak ditemukan"
        )

    db.delete(meter)
    db.commit()

    return {"message": "Meter berhasil dihapus"}


@app.get("/catat-meter", dependencies=[Depends(verify_token)])
def get_catat_meter(db: Session = Depends(get_db)):
    readings = db.query(CatatMeterModel).all()
    return {
        "message": "Data catat meter berhasil diambil",
        "data": [serialize_model(reading) for reading in readings]
    }


@app.post("/admin/catat-meter", dependencies=[Depends(verify_token)])
def tambah_catat_meter(
    data: CatatMeterCreate,
    db: Session = Depends(get_db)
):
    record = CatatMeterModel(
        meter_id=data.meter_id,
        bulan=data.bulan,
        petugas_nama=data.petugas_nama,
        angka_meter_lalu=data.angka_meter_lalu,
        angka_meter_kini=data.angka_meter_kini,
        penggunaan_m3=data.penggunaan_m3,
        status_verifikasi="pending"
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "Catatan meter berhasil ditambahkan",
        "data": serialize_model(record)
    }


@app.delete("/admin/catat-meter/{id}", dependencies=[Depends(verify_token)])
def delete_catat_meter(
    id: int,
    db: Session = Depends(get_db)
):
    record = db.query(CatatMeterModel).filter(
        CatatMeterModel.id == id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Catatan meter tidak ditemukan"
        )

    db.delete(record)
    db.commit()

    return {"message": "Catatan meter berhasil dihapus"}


@app.get("/admin/tagihan", dependencies=[Depends(verify_token)])
def get_tagihan(db: Session = Depends(get_db)):
    bills = db.query(TagihanModel).all()
    return {
        "message": "Data tagihan berhasil diambil",
        "data": [serialize_model(bill) for bill in bills]
    }


@app.post("/admin/tagihan", dependencies=[Depends(verify_token)])
def tambah_tagihan(
    data: TagihanCreate,
    db: Session = Depends(get_db)
):
    tanggal_bayar = None
    if data.status_pembayaran == "lunas":
        tanggal_bayar = datetime.utcnow().isoformat()

    bill = TagihanModel(
        meter_id=data.meter_id,
        bulan=data.bulan,
        penggunaan_m3=data.penggunaan_m3,
        total_tagihan=data.total_tagihan,
        status_pembayaran=data.status_pembayaran,
        tanggal_bayar=tanggal_bayar
    )

    db.add(bill)
    db.commit()
    db.refresh(bill)

    return {
        "message": "Tagihan berhasil ditambahkan",
        "data": serialize_model(bill)
    }


@app.delete("/admin/tagihan/{id}", dependencies=[Depends(verify_token)])
def delete_tagihan(
    id: int,
    db: Session = Depends(get_db)
):
    bill = db.query(TagihanModel).filter(
        TagihanModel.id == id
    ).first()

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Tagihan tidak ditemukan"
        )

    db.delete(bill)
    db.commit()

    return {"message": "Tagihan berhasil dihapus"}


@app.get("/admin/komplain", dependencies=[Depends(verify_token)])
def get_komplain(db: Session = Depends(get_db)):
    complaints = db.query(KomplainModel).all()
    return {
        "message": "Data komplain berhasil diambil",
        "data": [serialize_model(complaint) for complaint in complaints]
    }


@app.post("/admin/komplain", dependencies=[Depends(verify_token)])
def tambah_komplain(
    data: KomplainCreate,
    db: Session = Depends(get_db)
):
    complaint = KomplainModel(
        pelanggan_id=data.pelanggan_id,
        judul=data.judul,
        deskripsi=data.deskripsi,
        status="pending"
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {
        "message": "Komplain berhasil ditambahkan",
        "data": serialize_model(complaint)
    }


@app.delete("/admin/komplain/{id}", dependencies=[Depends(verify_token)])
def delete_komplain(
    id: int,
    db: Session = Depends(get_db)
):
    complaint = db.query(KomplainModel).filter(
        KomplainModel.id == id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Komplain tidak ditemukan"
        )

    db.delete(complaint)
    db.commit()

    return {"message": "Komplain berhasil dihapus"}


@app.get("/admin/pemasangan-baru", dependencies=[Depends(verify_token)])
def get_pemasangan_baru(db: Session = Depends(get_db)):
    submissions = db.query(PemasanganBaruModel).all()
    return {
        "message": "Data pemasangan baru berhasil diambil",
        "data": [serialize_model(submission) for submission in submissions]
    }


@app.post("/admin/pemasangan-baru", dependencies=[Depends(verify_token)])
def tambah_pemasangan_baru(
    data: PemasanganBaruCreate,
    db: Session = Depends(get_db)
):
    submission = PemasanganBaruModel(
        nama=data.nama,
        nik=data.nik,
        no_hp=data.no_hp,
        alamat=data.alamat,
        jenis_pelanggan=data.jenis_pelanggan,
        status="pending"
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Pengajuan pemasangan berhasil ditambahkan",
        "data": serialize_model(submission)
    }


@app.delete("/admin/pemasangan-baru/{id}", dependencies=[Depends(verify_token)])
def delete_pemasangan_baru(
    id: int,
    db: Session = Depends(get_db)
):
    submission = db.query(PemasanganBaruModel).filter(
        PemasanganBaruModel.id == id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Pengajuan pemasangan tidak ditemukan"
        )

    db.delete(submission)
    db.commit()

    return {"message": "Pengajuan pemasangan berhasil dihapus"}


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