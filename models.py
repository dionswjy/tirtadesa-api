from sqlalchemy import Column, Integer, String, Text
from database import Base


class Pelanggan(Base):
    __tablename__ = "pelanggan"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100))
    alamat = Column(Text)
    no_meter = Column(String(50))
    kategori = Column(String(50))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    password = Column(String(255))
    role = Column(String(50), default="pelanggan")