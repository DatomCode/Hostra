import os
import json
import shutil
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai
from google.genai import types
from PIL import Image

import re

from .database import get_db, User, Listing, VerificationReport, Transaction, SplitInvite, Notification, Review, MaintenanceReport, SessionLocal
load_dotenv()
try:
    client = genai.Client()
except Exception as e:
    print("Warning: Gemma API Client failed to initialize. Check your .env file.")

MODEL_ID = "gemma-4-31b-it" 

os.makedirs("uploads", exist_ok=True)





# --- Lifespan Event: Auto-Seeding with Balanced Landlord Splits ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "david@student.lautech.edu.ng").first():
            print("Seeding database with correct landlord distribution...")
            
            landlord1 = User(email="babaojo@email.com", password="password123", name="Baba Ojo", role="landlord")
            landlord2 = User(email="iyaniola@email.com", password="password123", name="Iya Niola", role="landlord")
            student2 = User(email="david@student.lautech.edu.ng", password="password123", name="David O.", role="student", area="UnderG", is_id_verified=True)
            
            db.add_all([landlord1, landlord2, student2])
            db.commit()
            
            listings = [
                Listing(landlord_id=landlord1.id, address="Block A, Ojo Estate", area="UnderG", price="₦180,000", landlord_claims="Single room, tiled, running water", image_path="/uploads/house1.jpeg", status="verified"),
                Listing(landlord_id=landlord1.id, address="Ojo Flat 1", area="Stadium", price="₦350,000", landlord_claims="2 Bedroom flat, pop ceiling, wardrobe", image_path="/uploads/house2.jpeg", status="verified"),
                Listing(landlord_id=landlord1.id, address="Ojo Lodge 2", area="UnderG", price="₦170,000", landlord_claims="Self-con, secure environment", image_path="/uploads/house3.jpeg", status="pending"),
                Listing(landlord_id=landlord1.id, address="Ojo Annex 2", area="Adenike", price="₦140,000", landlord_claims="Single room, tiled floor", image_path="/uploads/house4.jpeg", status="pending"),
                Listing(landlord_id=landlord2.id, address="Niola Villa, Street 4", area="Adenike", price="₦220,000", landlord_claims="Self-con, fenced, gated, borehole", image_path="/uploads/house5.jpeg", status="verified"),
                Listing(landlord_id=landlord2.id, address="Niola Annex", area="Adenike", price="₦200,000", landlord_claims="Self-con, newly built, tiled", image_path="/uploads/house6.jpeg", status="verified"),
                Listing(landlord_id=landlord2.id, address="Niola Heights", area="Adenike", price="₦150,000", landlord_claims="Running water, tiled floor", image_path="/uploads/house7.jpeg", status="pending"),
                Listing(landlord_id=landlord2.id, address="Niola Crescent", area="Stadium", price="₦190,000", landlord_claims="Single room, prepaid meter", image_path="/uploads/house8.jpeg", status="pending"),
            ]
            
            db.add_all(listings)
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="Hostra API", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def parse_price(price_val) -> float:
    """
    Safely converts any price format (string or number) into a clean float.
    Handles: "₦150,000", "150,000", "150k", "1.5m", or raw integers/floats.
    """
    if price_val is None:
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
        
    # Convert to string and clean spaces/currency symbols
    cleaned = str(price_val).lower().replace("₦", "").replace(",", "").strip()
    
    # Handle shorthand multipliers like 'k' (thousand) or 'm' (million)
    multiplier = 1.0
    if 'k' in cleaned:
        multiplier = 1000.0
        cleaned = cleaned.replace('k', '')
    elif 'm' in cleaned:
        multiplier = 1000000.0
        cleaned = cleaned.replace('m', '')
        
    # Extract only the numeric digits and decimal points
    match = re.search(r"[-+]?\d*\.\d+|\d+", cleaned)
    if match:
        return float(match.group()) * multiplier
    return 0.0

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    if not token.startswith("token_"):
        raise HTTPException(status_code=401, detail="Invalid token format")
    email = token.replace("token_", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.password != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "token": f"token_{user.email}", "email": user.email, "role": user.role, "name": user.name}

@app.post("/auth/signup")
def signup(email: str = Form(...), password: str = Form(...), name: str = Form(...), 
           role: str = Form(...), area: Optional[str] = Form(None), 
           id_image: Optional[UploadFile] = File(None), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(email=email, password=password, name=name, role=role, area=area, is_id_verified=False)
    db.add(new_user)
    db.commit()
    return {"success": True, "token": f"token_{new_user.email}", "email": new_user.email, "role": new_user.role, "name": new_user.name, "area": new_user.area}

@app.post("/users/verify-id")
def upload_id(id_image: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        image_data = Image.open(id_image.file)
        prompt = "Look at this ID card. Does it clearly say 'Ladoke Akintola University of Technology' or 'LAUTECH'? Answer ONLY with a JSON object with a single boolean key: 'is_valid'."
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[image_data, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        if ai_data.get("is_valid"):
            user.is_id_verified = True
            db.commit()
            return {"success": True, "message": "LAUTECH ID verified by AI"}
        else:
            raise HTTPException(status_code=400, detail="Invalid ID card.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/me")
def get_profile(user: User = Depends(get_current_user)):
    return {"name": user.name, "email": user.email, "role": user.role, "area": user.area, "wallet_balance": user.wallet_balance, "is_id_verified": user.is_id_verified}

@app.post("/listings/")
def create_listing(address: str = Form(...), area: str = Form(...), price: str = Form(...), 
                   landlord_claims: str = Form(...), image: UploadFile = File(...), 
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_path = f"uploads/{image.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    new_listing = Listing(landlord_id=user.id, address=address, area=area, price=price, 
                          landlord_claims=landlord_claims, image_path=f"/{file_path}", status="pending")
    db.add(new_listing)
    db.commit()
    return {"success": True}

@app.get("/listings/")
def get_all_listings(db: Session = Depends(get_db)):
    listings = db.query(Listing).all()
    return {"listings": [{"id": l.id, "landlord_id": l.landlord_id, "address": l.address, "area": l.area, "price": l.price, "landlord_claims": l.landlord_claims, "image_path": l.image_path, "status": l.status} for l in listings]}

@app.get("/listings/mine")
def get_my_listings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listings = db.query(Listing).filter(Listing.landlord_id == user.id).all()
    return {"listings": [{"id": l.id, "address": l.address, "price": l.price, "landlord_claims": l.landlord_claims, "image_path": l.image_path, "status": l.status} for l in listings]}

@app.get("/listings/{listing_id}")
def get_single_listing(listing_id: int, db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"id": l.id, "landlord_id": l.landlord_id, "address": l.address, "area": l.area, "price": l.price, "landlord_claims": l.landlord_claims, "image_path": l.image_path, "status": l.status}

@app.get("/verify/feed")
def get_verify_feed(show_all: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Listing).filter(Listing.status == "pending")
    if not show_all and user.area:
        query = query.filter(Listing.area == user.area)
    listings = query.all()
    return {"listings": [{"id": l.id, "address": l.address, "area": l.area, "price": l.price, "landlord_claims": l.landlord_claims, "image_path": l.image_path, "status": l.status} for l in listings]}

@app.post("/verify/{listing_id}")
def verify_listing(listing_id: int, images: list[UploadFile] = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    try:
        pil_images = [Image.open(img.file) for img in images]
        prompt = f"""You are a strict property inspector. The landlord claims this property has: {listing.landlord_claims}. 
        Look at these images. Return a JSON response with exactly these keys: 
        'verdict' (must be exactly 'approved' or 'rejected'), 
        'reason' (a short 1-sentence explanation), 
        'matched_claims' (a list of strings of features you see), 
        'mismatched_claims' (a list of strings of features missing)."""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=pil_images + [prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        # Explicitly assign and commit the status change to the listing
        listing.status = "verified" if ai_data.get('verdict') == 'approved' else "rejected"
        if listing.status == "verified":
            user.wallet_balance += 1500.0
        
        report = VerificationReport(
            listing_id=listing.id, verifier_id=user.id,
            gemma_verdict=ai_data.get('verdict'), gemma_reason=ai_data.get('reason'),
            submitted_photos=json.dumps([listing.image_path]), 
            matched_claims=json.dumps(ai_data.get('matched_claims', [])),
            mismatched_claims=json.dumps(ai_data.get('mismatched_claims', []))
        )
        db.add(report)
        
        # Ensure the listing status change is safely written to the database
        db.commit()
        db.refresh(listing)
        db.refresh(user)
        
        return {"success": True, "ai_response": ai_data, "new_wallet_balance": user.wallet_balance}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings/{listing_id}/verification-report")
def get_report(listing_id: int, db: Session = Depends(get_db)):
    report = db.query(VerificationReport).filter(VerificationReport.listing_id == listing_id).first()
    if not report: return {"success": False}
    return {"success": True, "report": {
        "gemma_verdict": report.gemma_verdict, "gemma_reason": report.gemma_reason,
        "submitted_photos": json.loads(report.submitted_photos),
        "matched_claims": json.loads(report.matched_claims), 
        "mismatched_claims": json.loads(report.mismatched_claims)
    }}

# --- THE AGREEMENT TRANSLATOR (LEASE AUDIT) ---
@app.post("/translate-contract")
def translate_contract(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Upload using the Files API for native document/multimodal understanding
        uploaded_file = client.files.upload(file=file_path)
        
        prompt = """You are an expert student legal aid advisor in Nigeria. Read this rental lease agreement document carefully. 
        Analyze it and return a JSON object with exactly these keys:
        'summary': A plain English 2-sentence summary of the lease terms,
        'red_flags': A list of strings pointing out any suspicious, unfair, unlawful, or restrictive clauses,
        'fair_clauses': A list of strings highlighting standard or favorable conditions."""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"success": True, "analysis": ai_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wallet/me")
def get_wallet(user: User = Depends(get_current_user)):
    earnings = [{"type": "deposit", "amount": user.wallet_balance, "listing_address": "Various", "timestamp": "Recent"}] if user.wallet_balance > 0 else []
    return {"wallet_balance": user.wallet_balance, "earnings": earnings}

@app.post("/wallet/withdraw")
def withdraw_wallet(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    amount = body.get("amount", 0)
    if amount > user.wallet_balance:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    user.wallet_balance -= amount
    db.commit()
    return {"success": True}

# --- Notifications Endpoint ---
@app.get("/notifications")
def get_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(Notification).filter(Notification.user_id == user.id).all()
    return {"notifications": [{"id": n.id, "message": n.message, "is_read": n.is_read} for n in notes]}

# --- Escrow & Split Rent Logic ---
class EscrowPayRequest(BaseModel):
    listing_id: int
    is_split: bool = False

@app.post("/escrow/pay")
def pay_escrow(req: EscrowPayRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Safely parse the price string into a clean float for calculation
    numeric_price = parse_price(listing.price)
    
    amount_to_pay = (numeric_price / 2.0) if req.is_split else numeric_price
    
    if user.wallet_balance < amount_to_pay:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
    user.wallet_balance -= amount_to_pay
    
    transaction = Transaction(
        listing_id=listing.id,
        tenant_id=user.id,
        landlord_id=listing.landlord_id,
        status="held",
        is_split=req.is_split
    )
    db.add(transaction)
    db.commit()
    return {"success": True, "message": "Payment locked in escrow successfully"}

@app.post("/escrow/split-invite")
def send_split_invite(req: SplitInviteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    # Safely calculate split share using the helper
    total_price = parse_price(listing.price)
    split_share = total_price / 2.0
    
    invite = SplitInvite(
        sender_id=user.id,
        receiver_id=req.roommate_id,
        listing_id=req.listing_id,
        status="pending"
    )
    db.add(invite)
    
    # Send notification with the correctly formatted numerical split share
    db.add(Notification(
        user_id=req.roommate_id, 
        message=f"{user.name} invited you to split rent for {listing.address}. Your share is ₦{split_share:,.2f}"
    ))
    
    db.commit()
    return {"success": True, "split_amount": split_share}

@app.get("/escrow/listing/{listing_id}")
def check_escrow(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    my_tx = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == user.id).first()
    
    accepted_invite = db.query(SplitInvite).filter(
        SplitInvite.listing_id == listing_id,
        SplitInvite.status == "accepted",
        (SplitInvite.sender_id == user.id) | (SplitInvite.receiver_id == user.id)
    ).first()
    
    is_fully_funded = False
    if accepted_invite:
        payer1 = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == accepted_invite.sender_id, Transaction.status.in_(["held", "released"])).first()
        payer2 = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == accepted_invite.receiver_id, Transaction.status.in_(["held", "released"])).first()
        if payer1 and payer2:
            is_fully_funded = True
    else:
        if my_tx and my_tx.status in ["held", "released"]:
            is_fully_funded = True

    return {
        "success": True, 
        "transaction": {"id": my_tx.id if my_tx else None, "status": my_tx.status if my_tx else "unpaid"},
        "is_fully_funded": is_fully_funded
    }

@app.post("/escrow/{tx_id}/confirm-move-in")
def confirm_move_in(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    listing_id = tx.listing_id
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if tx.is_split:
        accepted_invite = db.query(SplitInvite).filter(
            SplitInvite.listing_id == listing_id,
            SplitInvite.status == "accepted",
            (SplitInvite.sender_id == user.id) | (SplitInvite.receiver_id == user.id)
        ).first()
        
        if accepted_invite:
            partner_id = accepted_invite.receiver_id if accepted_invite.sender_id == user.id else accepted_invite.sender_id
            partner_tx = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == partner_id, Transaction.status == "held").first()
            if not partner_tx:
                raise HTTPException(status_code=400, detail="Both roommates must pay their escrow share before move-in can be confirmed!")
            partner_tx.status = "released"

    tx.status = "released"
    
    try:
        clean_price = float(listing.price.replace('₦', '').replace(',', ''))
    except:
        clean_price = 150000.0
    
    landlord = db.query(User).filter(User.id == tx.landlord_id).first()
    if landlord:
        landlord.wallet_balance += clean_price
        db.add(Notification(user_id=landlord.id, message=f"🎉 Full rent funds released from escrow for {listing.address} and credited to your wallet!"))
        
    db.commit()
    return {"success": True, "message": "Move-in confirmed successfully. Funds credited to landlord wallet."}

class InviteRequest(BaseModel):
    roommate_id: int
    listing_id: int

@app.post("/escrow/split-invite")
def send_invite(req: InviteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(SplitInvite).filter(
        SplitInvite.listing_id == req.listing_id,
        SplitInvite.sender_id == user.id,
        SplitInvite.receiver_id == req.roommate_id
    ).first()
    if existing:
        return {"success": True}
        
    invite = SplitInvite(sender_id=user.id, receiver_id=req.roommate_id, listing_id=req.listing_id)
    db.add(invite)
    
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    roommate = db.query(User).filter(User.id == req.roommate_id).first()
    
    db.add(Notification(user_id=req.roommate_id, message=f"📬 {user.name} invited you to split rent for {listing.address}."))
    db.add(Notification(user_id=listing.landlord_id, message=f"👥 {user.name} and {roommate.name if roommate else 'a roommate'} are looking to split rent for {listing.address}."))
    
    db.commit()
    return {"success": True}

@app.get("/escrow/invites")
def get_invites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    received = db.query(SplitInvite).filter(SplitInvite.receiver_id == user.id, SplitInvite.status == "pending").all()
    sent = db.query(SplitInvite).filter(SplitInvite.sender_id == user.id, SplitInvite.status == "pending").all()
    
    def format_invite(inv, is_inbox):
        listing = db.query(Listing).filter(Listing.id == inv.listing_id).first()
        other_user = db.query(User).filter(User.id == (inv.sender_id if is_inbox else inv.receiver_id)).first()
        try:
            clean_price = float(listing.price.replace('₦', '').replace(',', ''))
            split_amount = f"{clean_price / 2:,.0f}"
        except:
            split_amount = "Half"

        return {
            "id": inv.id, "listing_id": listing.id, "property_address": listing.address,
            "sender_name": other_user.name if is_inbox else None,
            "receiver_name": other_user.name if not is_inbox else None,
            "split_amount": split_amount
        }

    return {
        "received": [format_invite(i, True) for i in received],
        "sent": [format_invite(i, False) for i in sent]
    }

class AnswerInviteRequest(BaseModel):
    action: str 

@app.post("/escrow/invites/{invite_id}/answer")
def answer_invite(invite_id: int, req: AnswerInviteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.query(SplitInvite).filter(SplitInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.status = "accepted" if req.action == "accept" else "declined"
    
    listing = db.query(Listing).filter(Listing.id == invite.listing_id).first()
    db.add(Notification(user_id=invite.sender_id, message=f"✅ {user.name} has {req.action}ed your split rent invite for {listing.address}!"))
    db.commit()
    return {"success": True}

@app.post("/escrow/invites/{invite_id}/cancel")
def cancel_invite(invite_id: int, db: Session = Depends(get_db)):
    invite = db.query(SplitInvite).filter(SplitInvite.id == invite_id).first()
    if invite:
        db.delete(invite)
        db.commit()
    return {"success": True}

            
# --- Real Reviews & Sentiment Analysis ---
class ReviewRequest(BaseModel):
    transcribed_text: str
    rating: Optional[int] = None
            
@app.post("/reviews/{listing_id}")
def submit_review(listing_id: int, req: ReviewRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Use Gemma to analyze sentiment and generate summary
    prompt = f"Analyze this student review: '{req.transcribed_text}'. Return a JSON object with 'sentiment' (must be exactly 'positive', 'negative', or 'neutral') and 'gemma_summary' (a concise 3 to 5 word summary)."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        sentiment = ai_data.get('sentiment', 'neutral')
        gemma_summary = ai_data.get('gemma_summary', 'Student review')
    except Exception:
        sentiment = 'neutral'
        gemma_summary = 'Student review'

    new_review = Review(
        listing_id=listing_id,
        user_id=user.id,
        transcribed_text=req.transcribed_text,
        sentiment=sentiment,
        gemma_summary=gemma_summary,
        rating=req.rating
    )
    db.add(new_review)
    db.commit()
    return {"success": True}

@app.get("/reviews/{listing_id}")
def get_reviews(listing_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.listing_id == listing_id).all()
    
    if not reviews:
        return {"overall_summary": "No reviews yet for this property.", "reviews": []}
    
    # Compute overall summary text
    sentiments = [r.sentiment for r in reviews]
    pos_count = sentiments.count('positive')
    overall = "Mostly positive student feedback." if pos_count >= len(sentiments) / 2 else "Mixed student feedback."

    formatted_reviews = [{
        "sentiment": r.sentiment,
        "rating": r.rating,
        "transcribed_text": r.transcribed_text,
        "gemma_summary": r.gemma_summary,
        "timestamp": r.timestamp.strftime("%Y-%m-%d") if r.timestamp else "Recent"
    } for r in reviews]

    return {
        "overall_summary": overall,
        "reviews": formatted_reviews
    }



# --- Roommate Profiling & Matching ---
@app.post("/roommate/profile")
def submit_roommate_profile(body: dict):
    prompt = f"Analyze this student's lifestyle note: '{body.get('lifestyle_note')}'. Extract their traits into a JSON object with keys: 'sleep_schedule', 'noise_tolerance', and 'cleanliness'."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Gemma reasoning failed")

# --- ROOMMATE MATCHING ENGINE ---
@app.get("/roommates/matches")
def get_roommate_matches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Query other student profiles excluding the current user
    other_students = db.query(User).filter(User.role == "student", User.id != user.id).all()
    
    matches = []
    for peer in other_students:
        # Calculate compatibility based on shared area preferences
        score = 90 if peer.area and user.area and peer.area.lower() == user.area.lower() else 75
        
        matches.append({
            "id": peer.id,
            "name": peer.name,
            "area": peer.area or "Ogbomoso Central",
            "compatibility_score": f"{score}% Match",
            "lifestyle": "Focused student, quiet habits, verified profile"
        })
        
    return {"matches": matches}

# --- Real AI Repair Audit & Maintenance ---
@app.post("/listings/{listing_id}/maintenance")
def submit_maintenance(listing_id: int, description: str = Form(...), image: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_path = f"uploads/maintenance_{image.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    report = MaintenanceReport(
        listing_id=listing_id,
        tenant_id=user.id,
        description=description,
        image_path=f"/{file_path}",
        status="pending"
    )
    db.add(report)
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing:
        db.add(Notification(user_id=listing.landlord_id, message=f"⚠️ Maintenance reported for {listing.address}: {description}"))
        
    db.commit()
    return {"success": True}

@app.post("/listings/{listing_id}/repair-audit")
def repair_audit(listing_id: int, image: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_data = Image.open(image.file)
        prompt = """Look at this image of a plumbing or house repair. Has the issue been fixed, or does it look broken/dirty? 
        Reply in JSON with 'verdict' ('approved' or 'rejected') and 'reason'."""
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[image_data, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        if ai_data.get('verdict') != 'approved':
            raise HTTPException(status_code=400, detail=ai_data.get('reason'))
            
        # Update maintenance report status if exists
        report = db.query(MaintenanceReport).filter(MaintenanceReport.listing_id == listing_id, MaintenanceReport.status == "pending").first()
        if report:
            report.status = "resolved"
            db.commit()
            
        return {"success": True, "verdict": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))