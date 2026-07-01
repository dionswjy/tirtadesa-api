from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from database import Base


class Pelanggan(Base):
    __tablename__ = "pelanggan"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    nama = Column(String(100))
    alamat = Column(Text)
    no_meter = Column(String(50))
    kategori = Column(String(50))
    no_hp = Column(String(20))
    nik = Column(String(50))
    status_pelanggan = Column(String(50))
    jenis_pelanggan = Column(String(50))


class Meter(Base):
    __tablename__ = "meter"

    id = Column(Integer, primary_key=True, index=True)
    pelanggan_id = Column(Integer)
    no_meter = Column(String(50))
    status_meter = Column(String(50))
    alamat_lokasi = Column(Text)


class CatatMeter(Base):
    __tablename__ = "catat_meter"

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer)
    bulan = Column(String(20))
    petugas_nama = Column(String(100))
    angka_meter_lalu = Column(Float)
    angka_meter_kini = Column(Float)
    penggunaan_m3 = Column(Float)
    status_verifikasi = Column(String(50), default="pending")


class Tagihan(Base):
    __tablename__ = "tagihan"

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer)
    bulan = Column(String(20))
    penggunaan_m3 = Column(Float)
    total_tagihan = Column(Float)
    status_pembayaran = Column(String(50))
    tanggal_bayar = Column(String(50), nullable=True)


class Komplain(Base):
    __tablename__ = "komplain"

    id = Column(Integer, primary_key=True, index=True)
    pelanggan_id = Column(Integer)
    judul = Column(String(200))
    deskripsi = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class PemasanganBaru(Base):
    __tablename__ = "pemasangan_baru"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100))
    nik = Column(String(50))
    no_hp = Column(String(20))
    alamat = Column(Text)
    jenis_pelanggan = Column(String(50))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    password = Column(String(255))
    role = Column(String(50), default="pelanggan")