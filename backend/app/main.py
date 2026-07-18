import os
import json
import shutil
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Body # Add Body here
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

# IMPORT UPDATED TO RoommatePair
from .database import get_db, User, Listing, VerificationReport, Transaction, RoommatePair, Notification, Review, MaintenanceReport, SessionLocal
load_dotenv()
try:
    client = genai.Client()
except Exception as e:
    print("Warning: Gemma API Client failed to initialize. Check your .env file.")

MODEL_ID = "gemma-4-31b-it" 

os.makedirs("uploads", exist_ok=True)

# ... (all your imports and setup remain the same) ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "david@student.lautech.edu.ng").first():
            print("Seeding database with wealthy test students...")
            
            landlord1 = User(email="babaojo@email.com", password="password123", name="Baba Ojo", role="landlord")
            landlord2 = User(email="iyaniola@email.com", password="password123", name="Iya Niola", role="landlord")
            
            # Everyone gets ₦500,000 to test payments
            wallet_start = 500000.0
            
            student2 = User(email="david@student.lautech.edu.ng", password="password123", name="David O.", role="student", area="UnderG", is_id_verified=True, sleep_schedule="Night Owl", noise_tolerance="High", cleanliness="Medium", wallet_balance=wallet_start)
            student3 = User(email="amina@student.lautech.edu.ng", password="password123", name="Amina Y.", role="student", area="UnderG", is_id_verified=True, sleep_schedule="Early Bird", noise_tolerance="Low", cleanliness="High", wallet_balance=wallet_start)
            student4 = User(email="chuks@student.lautech.edu.ng", password="password123", name="Chuks E.", role="student", area="Adenike", is_id_verified=True, sleep_schedule="Night Owl", noise_tolerance="High", cleanliness="Low", wallet_balance=wallet_start)
            student5 = User(email="tunde@student.lautech.edu.ng", password="password123", name="Tunde B.", role="student", area="Stadium", is_id_verified=True, sleep_schedule="Flexible", noise_tolerance="Medium", cleanliness="Medium", wallet_balance=wallet_start)
            
            db.add_all([landlord1, landlord2, student2, student3, student4, student5])
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

            # ... (dummy reviews seeding logic remains the same) ...
            reviews_to_add = []
            for lst in listings:
                reviews_to_add.append(Review(listing_id=lst.id, user_id=student2.id, transcribed_text="Great place!", sentiment="positive", gemma_summary="Good", rating=5))
                reviews_to_add.append(Review(listing_id=lst.id, user_id=student3.id, transcribed_text="It is okay.", sentiment="neutral", gemma_summary="Average", rating=3))
                reviews_to_add.append(Review(listing_id=lst.id, user_id=student4.id, transcribed_text="Leaky roof.", sentiment="negative", gemma_summary="Bad roof", rating=2))
            db.add_all(reviews_to_add)
            db.commit()
    finally:
        db.close()
    yield

# ... (rest of your routes) ...



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
    if price_val is None:
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
        
    cleaned = str(price_val).lower().replace("₦", "").replace(",", "").strip()
    multiplier = 1.0
    if 'k' in cleaned:
        multiplier = 1000.0
        cleaned = cleaned.replace('k', '')
    elif 'm' in cleaned:
        multiplier = 1000000.0
        cleaned = cleaned.replace('m', '')
        
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
    
    # We add wallet_balance=500000.0 here so they start with cash!
    new_user = User(
        email=email, 
        password=password, 
        name=name, 
        role=role, 
        area=area, 
        is_id_verified=False,
        wallet_balance=500000.0 
    )
    db.add(new_user)
    db.commit()
    return {"success": True, "token": f"token_{new_user.email}"}

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

@app.post("/contract/translate")
def translate_contract(image: UploadFile = File(...), user: User = Depends(get_current_user)):
    try:
        image_data = Image.open(image.file)
        prompt = """You are an expert campus tenancy lawyer. Analyze this image of a rental contract. 
        Translate this legal agreement document layout into three simple, straightforward pieces for a student user. 
        Look intentionally for hidden fees, sudden curfews, utility traps, unfair upkeep liability rules, alongside standard reasonable clauses.
        
        You MUST respond exclusively using a JSON block containing exactly these three specific fields:
        1. 'plain_summary': A brief, honest paragraph summarizing what this lease segments mean in normal plain vocabulary.
        2. 'red_flags': A simple array list of strings showing unfair rules, traps, or unexpected expenses.
        3. 'fair_clauses': A simple array list of strings showcasing the safe, standard, completely balanced legal terms.
        """
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[image_data, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        return {
            "success": True, 
            "plain_summary": ai_data.get("plain_summary", "No clear breakdown summary could be generated."),
            "red_flags": ai_data.get("red_flags", []),
            "fair_clauses": ai_data.get("fair_clauses", [])
        }
    except Exception as e:
        return {"raw_result": {"verdict": "error", "detail": str(e)}}

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

@app.get("/notifications")
def get_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(Notification).filter(Notification.user_id == user.id).all()
    return {"notifications": [{"id": n.id, "message": n.message, "is_read": n.is_read} for n in notes]}

# --- ROOMMATE API (Independent of properties) ---
class RoommateRequestReq(BaseModel):
    roommate_id: int

@app.post("/roommate/request")
def send_roommate_request(req: RoommateRequestReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pair = RoommatePair(sender_id=user.id, receiver_id=req.roommate_id, status="pending")
    db.add(pair)
    db.add(Notification(user_id=req.roommate_id, message=f"🤝 {user.name} wants to be your roommate! Head to your dashboard to respond."))
    db.commit()
    return {"success": True}

@app.get("/roommate/requests")
def get_roommate_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    received = db.query(RoommatePair).filter(RoommatePair.receiver_id == user.id, RoommatePair.status == "pending").all()
    sent = db.query(RoommatePair).filter(RoommatePair.sender_id == user.id, RoommatePair.status == "pending").all()
    
    def format_req(inv, is_inbox):
        other_user = db.query(User).filter(User.id == (inv.sender_id if is_inbox else inv.receiver_id)).first()
        return {
            "id": inv.id,
            "sender_name": other_user.name if is_inbox else None,
            "receiver_name": other_user.name if not is_inbox else None
        }

    return {
        "received": [format_req(i, True) for i in received],
        "sent": [format_req(i, False) for i in sent]
    }

class AnswerInviteRequest(BaseModel):
    action: str 

@app.post("/roommate/requests/{invite_id}/answer")
def answer_roommate_request(invite_id: int, req: AnswerInviteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.query(RoommatePair).filter(RoommatePair.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    if req.action == "accept":
        invite.status = "accepted"
        db.add(Notification(user_id=invite.sender_id, message=f"✅ {user.name} accepted your roommate request! You can now split rent together."))
    else:
        invite.status = "declined"
        
    db.commit()
    return {"success": True}

# --- SMART ESCROW API ---
class EscrowPayRequest(BaseModel):
    listing_id: int
    is_split: bool = False

@app.post("/escrow/pay")
def pay_escrow(req: EscrowPayRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing: raise HTTPException(status_code=404, detail="Listing not found")
    
    numeric_price = parse_price(listing.price)
    amount_to_pay = (numeric_price / 2.0) if req.is_split else numeric_price
    
    if user.wallet_balance < amount_to_pay:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
    user.wallet_balance -= amount_to_pay
    
    transaction = Transaction(
        listing_id=listing.id, tenant_id=user.id, landlord_id=listing.landlord_id,
        status="held", is_split=req.is_split
    )
    db.add(transaction)
    
    # Smart Roommate Split Logic
    if req.is_split:
        roommate_pair = db.query(RoommatePair).filter(RoommatePair.status == "accepted", (RoommatePair.sender_id == user.id) | (RoommatePair.receiver_id == user.id)).first()
        roommate_id = roommate_pair.receiver_id if roommate_pair.sender_id == user.id else roommate_pair.sender_id
        
        # Did the roommate already pay?
        roommate_tx = db.query(Transaction).filter(Transaction.listing_id == listing.id, Transaction.tenant_id == roommate_id, Transaction.status == "held").first()
        
        if roommate_tx:
            db.add(Notification(user_id=roommate_id, message=f"🎉 {user.name} just paid their half for {listing.address}! The house is now fully secured in escrow."))
            db.add(Notification(user_id=listing.landlord_id, message=f"💰 Full rent secured in escrow for {listing.address} by roommates!"))
        else:
            db.add(Notification(user_id=roommate_id, message=f"🔔 {user.name} just paid their half of the rent for {listing.address}! Go to the property page to pay your half and secure the house."))

    db.commit()
    return {"success": True, "message": "Payment locked in escrow successfully"}


@app.get("/escrow/listing/{listing_id}")
def check_escrow(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Does the user have an accepted roommate?
    roommate_pair = db.query(RoommatePair).filter(
        RoommatePair.status == "accepted",
        (RoommatePair.sender_id == user.id) | (RoommatePair.receiver_id == user.id)
    ).first()

    has_roommate = False
    roommate_name = None
    roommate_id = None
    roommate_tx = None

    if roommate_pair:
        has_roommate = True
        roommate_id = roommate_pair.receiver_id if roommate_pair.sender_id == user.id else roommate_pair.sender_id
        roommate_user = db.query(User).filter(User.id == roommate_id).first()
        roommate_name = roommate_user.name if roommate_user else "Your Roommate"
        
        # 2. Did the roommate already pay their half?
        roommate_tx = db.query(Transaction).filter(
            Transaction.listing_id == listing_id, 
            Transaction.tenant_id == roommate_id, 
            Transaction.status.in_(["held", "released"])
        ).order_by(Transaction.id.desc()).first()

    # 3. Did the current user pay?
    my_tx = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == user.id).order_by(Transaction.id.desc()).first()

    # 4. The Grand Logic Decoder
    display_status = "unpaid"
    
    if my_tx and my_tx.status in ["held", "released"]:
        if my_tx.is_split:
            if roommate_tx:
                display_status = my_tx.status # Fully funded (Held or Released)
            else:
                display_status = "waiting_for_roommate" # You paid, waiting for them
        else:
            display_status = my_tx.status # You paid full
    elif not my_tx or my_tx.status == "refunded":
        if roommate_tx:
            display_status = "roommate_paid" # They paid, waiting for you!
        else:
            display_status = "unpaid" # Nobody paid

    return {
        "success": True, 
        "status": display_status,
        "has_roommate": has_roommate,
        "roommate_name": roommate_name,
        "tx_id": my_tx.id if my_tx else None
    }

@app.post("/escrow/{tx_id}/confirm-move-in")
def confirm_move_in(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    listing_id = tx.listing_id
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if tx.is_split:
        roommate_pair = db.query(RoommatePair).filter(RoommatePair.status == "accepted", (RoommatePair.sender_id == user.id) | (RoommatePair.receiver_id == user.id)).first()
        if roommate_pair:
            partner_id = roommate_pair.receiver_id if roommate_pair.sender_id == user.id else roommate_pair.sender_id
            partner_tx = db.query(Transaction).filter(Transaction.listing_id == listing_id, Transaction.tenant_id == partner_id, Transaction.status == "held").first()
            if partner_tx:
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
    return {"success": True}

@app.post("/escrow/{tx_id}/refund")
def refund_escrow(tx_id: int, req: RefundRequest = Body(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ... rest of your code stays the same
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx or tx.tenant_id != user.id: raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.status != "held": raise HTTPException(status_code=400, detail="Only held funds can be refunded")
        
    listing = db.query(Listing).filter(Listing.id == tx.listing_id).first()
    numeric_price = parse_price(listing.price)
    amount_to_refund = (numeric_price / 2.0) if tx.is_split else numeric_price

    user.wallet_balance += amount_to_refund
    tx.status = "refunded"
    
    if tx.is_split:
        roommate_pair = db.query(RoommatePair).filter(RoommatePair.status == "accepted", (RoommatePair.sender_id == user.id) | (RoommatePair.receiver_id == user.id)).first()
        if roommate_pair:
            partner_id = roommate_pair.receiver_id if roommate_pair.sender_id == user.id else roommate_pair.sender_id
            partner_tx = db.query(Transaction).filter(Transaction.listing_id == listing.id, Transaction.tenant_id == partner_id, Transaction.status == "held").first()
            if partner_tx:
                partner = db.query(User).filter(User.id == partner_id).first()
                if partner:
                    partner.wallet_balance += amount_to_refund
                    partner_tx.status = "refunded"
                    db.add(Notification(user_id=partner.id, message=f"⚠️ Your roommate rejected the house ({listing.address}). Your half of the rent has been fully refunded to your wallet."))

    new_review = Review(listing_id=listing.id, user_id=user.id, transcribed_text=req.reason, sentiment="negative", gemma_summary="Tenant rejected property", rating=1)
    db.add(new_review)
    db.add(Notification(user_id=listing.landlord_id, message=f"❌ The tenant rejected {listing.address} and was refunded. Reason: {req.reason}"))
    db.commit()
    return {"success": True, "message": "Funds refunded securely."}

# Reviews, Maintenance, Roommate Matching remain exactly identical...
@app.post("/reviews/{listing_id}")
def submit_review(listing_id: int, req: ReviewRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing: raise HTTPException(status_code=404, detail="Listing not found")
    prompt = f"Analyze this student review: '{req.transcribed_text}'. Return a JSON object with 'sentiment' (must be exactly 'positive', 'negative', or 'neutral') and 'gemma_summary' (a concise 3 to 5 word summary)."
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=[prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        sentiment = ai_data.get('sentiment', 'neutral')
        gemma_summary = ai_data.get('gemma_summary', 'Student review')
    except Exception:
        sentiment = 'neutral'
        gemma_summary = 'Student review'
    new_review = Review(listing_id=listing_id, user_id=user.id, transcribed_text=req.transcribed_text, sentiment=sentiment, gemma_summary=gemma_summary, rating=req.rating)
    db.add(new_review)
    db.commit()
    return {"success": True}

@app.get("/reviews/{listing_id}")
def get_reviews(listing_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.listing_id == listing_id).all()
    if not reviews: return {"overall_summary": "No reviews yet for this property.", "reviews": []}
    sentiments = [r.sentiment for r in reviews]
    pos_count = sentiments.count('positive')
    overall = "Mostly positive student feedback." if pos_count >= len(sentiments) / 2 else "Mixed student feedback."
    formatted_reviews = [{"sentiment": r.sentiment, "rating": r.rating, "transcribed_text": r.transcribed_text, "gemma_summary": r.gemma_summary, "timestamp": r.timestamp.strftime("%Y-%m-%d") if r.timestamp else "Recent"} for r in reviews]
    return {"overall_summary": overall, "reviews": formatted_reviews}

@app.post("/roommate/profile")
def submit_roommate_profile(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prompt = f"Analyze this student's lifestyle note: '{body.get('lifestyle_note')}'. Extract their traits into a JSON object with exactly these keys: 'sleep_schedule', 'noise_tolerance', and 'cleanliness'."
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=[prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        user.sleep_schedule = ai_data.get("sleep_schedule", "Unknown")
        user.noise_tolerance = ai_data.get("noise_tolerance", "Unknown")
        user.cleanliness = ai_data.get("cleanliness", "Unknown")
        db.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Gemma reasoning failed")

@app.get("/roommate/matches")
def get_roommate_matches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.sleep_schedule: return {"matches": []}
    other_students = db.query(User).filter(User.role == "student", User.id != user.id).all()
    candidates = [{"id": s.id, "name": s.name, "sleep": s.sleep_schedule, "noise": s.noise_tolerance, "clean": s.cleanliness} for s in other_students if s.sleep_schedule]
    if not candidates: return {"matches": []}
    prompt = f"""You are a smart roommate matchmaker. The current student has these traits: Sleep: {user.sleep_schedule}, Noise: {user.noise_tolerance}, Cleanliness: {user.cleanliness}. Here are potential roommates: {json.dumps(candidates)} Compare them. Return a JSON object containing a list called 'matches'. For each match, provide: 'id' (integer), 'name' (string), 'score' (integer from 1 to 3, 3 being a perfect match), 'reason' (short string), and 'summary' (short string). Sort by the highest score first."""
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=[prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        matches = []
        for m in ai_data.get("matches", []):
            candidate = next((c for c in candidates if c["id"] == m["id"]), None)
            if candidate:
                m["traits"] = {"sleep_schedule": candidate["sleep"], "noise_tolerance": candidate["noise"], "cleanliness": candidate["clean"]}
                matches.append(m)
        return {"matches": matches}
    except Exception as e:
        return {"matches": []}

@app.post("/listings/{listing_id}/maintenance")
def submit_maintenance(listing_id: int, description: str = Form(...), image: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_path = f"uploads/maintenance_{image.filename}"
    with open(file_path, "wb") as buffer: shutil.copyfileobj(image.file, buffer)
    report = MaintenanceReport(listing_id=listing_id, tenant_id=user.id, description=description, image_path=f"/{file_path}", status="pending")
    db.add(report)
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing: db.add(Notification(user_id=listing.landlord_id, message=f"⚠️ Maintenance reported for {listing.address}: {description}"))
    db.commit()
    return {"success": True}

@app.post("/listings/{listing_id}/repair-audit")
def repair_audit(listing_id: int, image: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_data = Image.open(image.file)
        prompt = """Look at this image of a plumbing or house repair. Has the issue been fixed, or does it look broken/dirty? Reply in JSON with 'verdict' ('approved' or 'rejected') and 'reason'."""
        response = client.models.generate_content(model=MODEL_ID, contents=[image_data, prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        if ai_data.get('verdict') != 'approved': raise HTTPException(status_code=400, detail=ai_data.get('reason'))
        report = db.query(MaintenanceReport).filter(MaintenanceReport.listing_id == listing_id, MaintenanceReport.status == "pending").first()
        if report:
            report.status = "resolved"
            db.commit()
        return {"success": True, "verdict": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))