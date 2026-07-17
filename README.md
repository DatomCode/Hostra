# Hostra 🏠⚡

> **Student-Powered Off-Campus Housing Verification & Escrow Platform**
> *Built for the Gemma 4 Hackathon Sprint (Campus Infrastructure Track).*

---

## 📖 Overview

Every semester, thousands of university students (such as those at LAUTECH in Ogbomoso) face a high-risk off-campus rental market plagued by fraudulent agents, unverified property claims, fake photos, and hidden legal traps in lease agreements.

**Hostra** solves this trust deficit by combining **Gemma 4's advanced multimodal intelligence**, secure financial escrow, and student-powered physical verification workflows into a single, cohesive ecosystem.

---

## 🚀 Core Features

1. **Multimodal Property Verification (`verifier.html`)**
   - Student verifiers physically inspect apartments in areas like UnderG and Adenike, uploading live site photos.
   - **Gemma 4 AI Audit:** Streams images directly to the Gemma model alongside the landlord's original claims (e.g., running water, tiled floors) to generate a strict JSON verdict (`approved`/`rejected`) with specific matched and mismatched claims.
   - Approved properties instantly unlock on the student feed and reward verifiers with wallet credits.

2. **AI Lease Agreement Translator (`contract.html`)**
   - Students can upload complex rental agreements or document scans.
   - **Gemma 4 Legal Analysis:** Translates legal jargon into plain-English summaries, highlighting **🚩 Red Flags & Hidden Traps** (such as unlawful fees or unreasonable curfews) versus **✅ Fair Clauses**.

3. **Secure Escrow & Split-Rent System**
   - Eliminates upfront cash loss to fraudulent agents. Rent payments are locked safely in an internal escrow wallet and released upon move-in confirmation.
   - **Roommate Matching Engine:** Allows students to find compatible peers based on lifestyle preferences and send automated split-rent invites.


---

## 🛠️ Technical Architecture

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite (`hostra.db`), Passlib (bcrypt password hashing).
- **AI Engine:** Google GenAI SDK powered by Gemma 4 multimodal vision and structured JSON generation (`response_mime_type="application/json"`).
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla with asynchronous fetch APIs and modular routing).

---

## 📁 Project Structure

```text
hostra/
│
├── backend/
│   ├── main.py                  # FastAPI application & API routes
│   ├── database.py              # SQLAlchemy models & DB configuration
│   └── uploads/                 # Storage for inspection & maintenance photos
│
├── frontend/
│   ├── css/                     # Global styles
│   ├── js/                      # API client wrapper & state management
│   ├── index.html               # Landing page
│   ├── login.html                # Authentication portal
│   ├── student-dashboard.html    # Main student housing feed
│   ├── verifier.html             # Verifier inspection workflow
│   └── contract.html             # AI Lease Agreement Translator
│
└── requirements.txt              # Python dependencies
```

---

## ⚙️ Setup & Installation Instructions

Follow these step-by-step instructions to set up, configure, and run Hostra locally on your machine.

### Step 1: Clone the Repository

Open your terminal or command prompt and clone the project repository:

```bash
git clone https://github.com/your-username/hostra.git
cd hostra
```

### Step 2: Set Up the Python Virtual Environment

Create and activate an isolated virtual environment to manage dependencies cleanly:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (Command Prompt / PowerShell):
venv\Scripts\activate

# Activate on macOS / Linux:
source venv/bin/activate
```

### Step 3: Install Required Dependencies

Install all required backend and AI libraries listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

> **Note:** Ensure your `requirements.txt` contains `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `passlib`, `bcrypt`, `pillow`, and `google-genai`.

### Step 4: Configure Environment Variables

Hostra relies on Google's GenAI SDK to interact with Gemma 4 models. Set your API key in your environment variables:

**On Windows (Command Prompt):**
```dos
set GEMINI_API_KEY=your_actual_api_key_here
```

**On Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_actual_api_key_here"
```

**On macOS / Linux:**
```bash
export GEMINI_API_KEY="your_actual_api_key_here"
```

### Step 5: Start the Backend FastAPI Server

Navigate into your project root and start the server with auto-reload enabled using Uvicorn:

```bash
uvicorn backend.main:app --reload
```

The FastAPI backend server will launch and run locally at `http://127.0.0.1:8000`. You can access the interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

### Step 6: Launch the Frontend

Open the `frontend/` folder in your code editor (such as VS Code) and serve the frontend files using a local development server like Live Server, or open `index.html` directly in your browser.

---

## 🔌 Key API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register a new user (Student, Landlord, or Verifier) with secure bcrypt password hashing. |
| `POST` | `/auth/login` | Authenticate user credentials and return session tokens. |
| `GET` | `/verify/feed` | Fetch pending property listings filtered by location area. |
| `POST` | `/verify/{listing_id}` | Upload site inspection photos for Gemma 4 multimodal audit. |
| `POST` | `/translate-contract` | Upload and analyze lease agreements for hidden clauses and red flags. |
| `POST` | `/escrow/pay` | Securely lock rent funds in escrow. |
| `GET` | `/roommates/matches` | Retrieve compatible student roommate matches in your area. |
