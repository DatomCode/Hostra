from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./hostra.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    role = Column(String)
    area = Column(String, nullable=True)
    wallet_balance = Column(Float, default=0.0)
    is_id_verified = Column(Boolean, default=False)
    sleep_schedule = Column(String, nullable=True)
    noise_tolerance = Column(String, nullable=True)
    cleanliness = Column(String, nullable=True)
    profile_picture = Column(String, default="/images/default_avatar.png")
    phone_number = Column(String, nullable=True)

class Listing(Base):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True, index=True)
    landlord_id = Column(Integer, ForeignKey("users.id"))
    address = Column(String)
    area = Column(String)
    price = Column(String)
    landlord_claims = Column(Text)
    image_path = Column(String)
    status = Column(String, default="pending")
    strike_count = Column(Integer, default=0)

class VerificationReport(Base):
    __tablename__ = "verification_reports"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    verifier_id = Column(Integer, ForeignKey("users.id"))
    gemma_verdict = Column(String)
    gemma_reason = Column(String)
    submitted_photos = Column(Text)
    matched_claims = Column(Text)
    mismatched_claims = Column(Text)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    tenant_id = Column(Integer, ForeignKey("users.id"))
    landlord_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)
    is_split = Column(Boolean, default=False)

class RoommatePair(Base):
    __tablename__ = "roommate_pairs"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    is_read = Column(Boolean, default=False)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    transcribed_text = Column(Text)
    sentiment = Column(String)
    gemma_summary = Column(String)
    rating = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class MaintenanceReport(Base):
    __tablename__ = "maintenance_reports"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    tenant_id = Column(Integer, ForeignKey("users.id"))
    description = Column(Text)
    image_path = Column(String)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()