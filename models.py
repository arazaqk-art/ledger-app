from sqlalchemy import Column, Integer, String, Float
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin / staff

class Ledger(Base):
    __tablename__ = "ledger"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    vehicle_no = Column(String, nullable=True)
    
    source_mine = Column(String, nullable=True)
    destination = Column(String, nullable=True)

    unit = Column(Float, default=0)
    rate = Column(Float, default=0)
    total = Column(Float, default=0)
    received = Column(Float, default=0)
    balance = Column(Float, default=0)
    date = Column(String, nullable=False)