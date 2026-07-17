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

from .database import get_db, User, Listing, VerificationReport, Transaction, SplitInvite, Notification, SessionLocal

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

@app.post("/contract/translate")
def translate_contract(image: UploadFile = File(...), user: User = Depends(get_current_user)):
    try:
        image_data = Image.open(image.file)
        prompt = """You are an expert campus tenancy lawyer. Analyze this image of a rental contract. 
        Look specifically for hidden fees, strict curfews, utility traps, or unfair maintenance rules. 
        Translate these legal clauses into short, brutally honest, plain English bullet points for a student. 
        If everything looks standard, return an empty list. 
        Respond in JSON format with a single key 'clauses' which contains a list of strings."""
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[image_data, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        return {"success": True, "clauses": ai_data.get("clauses", [])}
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
    
    existing_tx = db.query(Transaction).filter(
        Transaction.listing_id == req.listing_id, 
        Transaction.tenant_id == user.id
    ).first()
    
    if existing_tx:
        return {"success": True, "message": "Already paid into escrow", "transaction": {"id": existing_tx.id, "status": existing_tx.status}}
    
    tx = Transaction(
        listing_id=listing.id, 
        tenant_id=user.id, 
        landlord_id=listing.landlord_id, 
        is_split=req.is_split,
        status="held"
    )
    db.add(tx)
    
    try:
        clean_price = float(listing.price.replace('₦', '').replace(',', ''))
        share_amt = f"₦{clean_price / 2:,.0f}" if req.is_split else f"₦{clean_price:,.0f}"
    except:
        share_amt = listing.price
        
    db.add(Notification(user_id=listing.landlord_id, message=f"🔔 Student {user.name} has deposited {share_amt} into escrow for {listing.address}."))
    db.commit()
    db.refresh(tx)
    return {"success": True, "transaction": {"id": tx.id, "status": tx.status}}

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

# --- Reviews & Sentiment Analysis ---
class ReviewRequest(BaseModel):
    transcribed_text: str
    rating: int = None
            
@app.post("/reviews/{listing_id}")
def submit_review(listing_id: int, req: ReviewRequest):
    return {"success": True}

@app.get("/reviews/{listing_id}")
def get_reviews(listing_id: int):
    prompt = f"Analyze this fake student review for a hackathon: 'I loved living here, but the landlord locks the gate at 8PM sharp.' Return a JSON object with 'sentiment' (positive, negative, neutral) and 'gemma_summary' (a 3 to 5 word summary)."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text)
        
        return {
            "overall_summary": "Good location, strict rules.",
            "reviews": [{"sentiment": ai_data.get('sentiment', 'neutral'), "rating": 4, "transcribed_text": "I loved living here, but the landlord locks the gate at 8PM sharp.", "gemma_summary": ai_data.get('gemma_summary'), "timestamp": "2026-07-10"}]
        }
    except:
        return {"overall_summary": "Summary unavailable", "reviews": []}

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

@app.get("/roommate/matches")
def get_roommate_matches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    other_students = db.query(User).filter(User.role == "student", User.id != user.id).all()
    matches = []
    for s in other_students:
        matches.append({
            "id": s.id, "name": s.name, "score": 3, 
            "reason": "Both prefer quiet environments.",
            "summary": f"{s.name} matches your student lifestyle.",
            "traits": {"sleep_schedule": "Night Owl", "noise_tolerance": "Low", "cleanliness": "High"}
        })
    return {"matches": matches}

# --- AI Repair Audit & Maintenance ---
@app.post("/listings/{listing_id}/maintenance")
def submit_maintenance(listing_id: int, description: str = Form(...), image: UploadFile = File(...)):
    return {"success": True}

@app.post("/listings/{listing_id}/repair-audit")
def repair_audit(listing_id: int, image: UploadFile = File(...)):
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
        return {"success": True, "verdict": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI Vision processing failed")