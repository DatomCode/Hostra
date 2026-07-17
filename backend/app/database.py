from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./hostra.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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
    
class Listing(Base):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True, index=True)
    landlord_id = Column(Integer, ForeignKey("users.id"))
    address = Column(String)
    area = Column(String)
    price = Column(String)
    landlord_claims = Column(String)
    image_path = Column(String)
    status = Column(String, default="pending") 
    
class VerificationReport(Base):
    __tablename__ = "verification_reports"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    verifier_id = Column(Integer, ForeignKey("users.id"))
    gemma_verdict = Column(String)
    gemma_reason = Column(Text)
    submitted_photos = Column(String) 
    matched_claims = Column(String) 
    mismatched_claims = Column(String) 
    
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    tenant_id = Column(Integer, ForeignKey("users.id"))
    landlord_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="held") # held, released
    is_split = Column(Boolean, default=False)

class SplitInvite(Base):
    __tablename__ = "split_invites"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))
    status = Column(String, default="pending") # pending, accepted, declined

# Add this model to your existing database.py
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()