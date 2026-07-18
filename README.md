# Hostra 🏠⚡

> **AI-Verified Student Housing Infrastructure**
> Built for the Build With Gemma Hackathon Sprint (GDGoC LAUTECH) — **Campus Infra for Student** track.

[Live Demo](hostra1.netlify.app) · [Kaggle Writeup](https://www.kaggle.com/competitions/build-with-gemma-gdgoc-lautech/writeups/new-writeup-1784316401597) 

---

## Table of Contents

- [The Problem](#the-problem)
- [How Hostra Solves It](#how-hostra-solves-it)
- [Gemma 4 Integration (30%)](#-gemma-4-integration-30)
- [Innovation & Impact (30%)](#-innovation--impact-30)
- [Functionality (20%)](#-functionality-20)
- [Technical Architecture](#technical-architecture)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [API Reference](#api-reference)
- [Presentation & Writeup (20%)](#-presentation--writeup-20)
- [Known Limitations](#known-limitations)

---

## The Problem

Every semester, students moving to LAUTECH in Ogbomoso step into an off-campus housing market that runs entirely on trust, and that trust keeps getting broken. Agents post listings for houses that don't exist, misrepresent property features, or disappear with deposits before move-in day. By the time a student finds out, the rent is gone and the semester has already started without them.

## How Hostra Solves It

Hostra replaces blind trust with a peer-verified, AI-audited process. A nearby student **Verifier** physically inspects a listed property against the landlord's stated claims and submits live photos. **Gemma 4** checks that evidence and only approves the listing if what's shown genuinely matches what was promised. Only AI-verified listings are ever shown to students browsing for housing, and the evidence behind every badge, not just the badge, is visible to the renter.

---

## 🎯 Gemma 4 Integration (30%)

Gemma 4 is the arbiter at the center of Hostra's trust model, not a bolt-on chatbot. Every AI call uses `response_mime_type="application/json"` to enforce a strict, parseable schema so the backend can act on results programmatically, no free-text guessing.

| Feature | What Gemma 4 Does |
|---|---|
| **Hostel Verification** | Compares a verifier's live inspection photos against the landlord's claims. Returns `matched_claims`, `mismatched_claims`, a `verdict`, and a plain-English `reason`. Drives the listing's approval status directly. |
| **Agreement Translator** | Reads a photographed tenancy agreement and returns a plain-English list of unusual or risky clauses. |
| **Review Scribing** | Analyzes a student's review text and returns a sentiment label and a concise summary; aggregates all reviews for a listing into one overall verdict. |
| **Roommate Matching** | Extracts structured lifestyle traits (sleep schedule, noise tolerance, cleanliness) from a student's note, then ranks and explains compatible matches. |
| **LAUTECH ID Verification** | Reads an uploaded student ID photo and confirms it is a genuine LAUTECH ID before granting verified student status. |

Gemma 4's output directly decides what happens next in the product, whether a listing goes live, whether a clause gets flagged, whether two students get matched, rather than just generating supporting text.

---

## 💡 Innovation & Impact (30%)

- **Peer-led infrastructure, not a corporate inspection team.** Verification is crowdsourced from students who already live near the property, incentivized with real payment for each approved inspection, rather than relying on a company hiring its own inspectors.
- **Evidence over assertion.** Renters can see the actual matched and mismatched claims behind every Verified badge, not just trust a green checkmark, addressing the exact "just take our word for it" problem that makes the current market untrustworthy.
- **A trust loop that pays for itself.** Approved verifications pay the verifying student; declined ones cost the landlord nothing but keep the listing hidden until it's fixed, aligning every party's incentives toward telling the truth.
- **Solves a problem specific to this campus and this moment**, off-campus housing scams are a recurring, well-known pain point for LAUTECH students specifically, not a generic, abstract use case retrofitted onto Gemma.

---

## ✅ Functionality (20%)

Hostra is a full, working prototype, not a static mockup:

- Real user accounts (student, landlord), with role-based access to protected routes.
- A live listings feed, filterable by area, backed by a real SQLite database.
- A working Verifier flow: accept a job, upload real inspection photos, get a real Gemma 4 verdict back, and see the listing status change live.
- A working Agreement Translator, Review system, and Roommate Matching flow, each hitting Gemma 4 live, not a canned response.
- A simulated escrow and wallet system demonstrating the full "pay → hold → confirm move-in → release" loop end to end, clearly labeled as a demo since it isn't connected to a real payment processor.
- Deployed live: backend on Render, frontend on Netlify, reachable without running anything locally.

See [Known Limitations](#known-limitations) below for what's intentionally out of scope or still being verified.

---

## Technical Architecture

- **Backend:** FastAPI (Python), SQLAlchemy over SQLite, token-based authentication with role-based access control.
- **AI Engine:** Gemma 4 via the Google GenAI SDK, structured JSON output enforced on every call.
- **Frontend:** Plain HTML, CSS, and vanilla JavaScript calling the backend as a JSON API, chosen deliberately over a framework for iteration speed within a sprint window.
- **Hosting:** Backend on Render, frontend on Netlify.

## Project Structure

```text
hostra/
│
├── backend/
│   ├── main.py              # FastAPI app, all routes, and Gemma 4 integration
│   ├── database.py          # SQLAlchemy models & DB configuration
│   ├── uploads/              # Storage for listing, ID, and inspection photos
│   └── requirements.txt      # Python dependencies
│
└── frontend/
    ├── css/style.css
    ├── js/
    │   ├── api.js             # Shared API client & session handling
    │   ├── animations.js       # Scroll-reveal and micro-interaction animations
    │   └── dashboard-ui.js      # Shared dashboard behaviors (notifications, invites)
    ├── index.html               # Landing page
    ├── login.html / signup.html # Authentication
    ├── student-dashboard.html    # Verified listings feed + roommate invites
    ├── landlord-dashboard.html   # Landlord's own listings
    ├── landlord.html              # Post a new listing
    ├── verifier.html               # Verifier inspection & AI audit flow
    ├── contract.html                # Agreement Translator
    ├── roommate.html                 # Lifestyle profile & matches
    ├── wallet.html                    # Earnings / escrow wallet
    ├── profile.html                    # Account details
    └── listing-detail.html              # Single listing, evidence, reviews, escrow
```

## Setup & Installation

### Backend (local development)

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```
GEMINI_API_KEY=your_actual_api_key_here
```

Run the server:

```bash
uvicorn app.main:app --reload
```

Backend runs at `http://127.0.0.1:8000`; interactive docs at `http://127.0.0.1:8000/docs`.

### Frontend (local development)

Serve `frontend/` with any local dev server (e.g. VS Code Live Server), or open `index.html` directly. Confirm `API_BASE_URL` in `js/api.js` points to your backend.

### Live Deployment

- **Backend (Render):** Set `GEMINI_API_KEY` in the service's environment variables. Confirm your deployed frontend's origin is listed in `main.py`'s CORS `origins`.
- **Frontend (Netlify):** Confirm `API_BASE_URL` in `js/api.js` points to the live Render URL before deploying.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register a new user (student, landlord). |
| `POST` | `/auth/login` | Authenticate and receive a session token. |
| `GET` | `/users/me` | Get the current user's profile. |
| `POST` | `/users/verify-id` | Gemma checks an uploaded LAUTECH ID photo. |
| `POST` | `/listings/` | Landlord creates a new listing. |
| `GET` | `/listings/` | Fetch all listings. |
| `GET` | `/listings/mine` | Fetch the current landlord's own listings. |
| `GET` | `/listings/{listing_id}` | Fetch a single listing's details. |
| `GET` | `/verify/feed` | Fetch pending listings for verifiers, filtered by area. |
| `POST` | `/verify/{listing_id}` | Submit inspection photos for Gemma 4 to audit against landlord claims. |
| `POST` | `/reviews/{listing_id}` | Submit a review; Gemma scores sentiment. |
| `GET` | `/reviews/{listing_id}` | Fetch all reviews and an aggregated summary. |
| `POST` | `/roommate/profile` | Submit a lifestyle note; Gemma extracts traits. |
| `GET` | `/roommate/matches` | Get AI-ranked roommate matches. |
| `POST` | `/escrow/pay` | Initiate a simulated rent payment, held in escrow. |
| `POST` | `/escrow/{tx_id}/confirm-move-in` | Release held funds to the landlord's wallet. |
| `GET` | `/wallet/me` | View current wallet balance and history. |

Full route list is browsable live at `/docs` on the deployed backend.

---

## 📝 Presentation & Writeup (20%)

- **Kaggle Writeup:** [link] — explains the problem, architecture, Gemma 4 usage, and engineering trade-offs made under sprint constraints.
- **Demo Video:** [link] — walks through the Verifier flow and Agreement Translator live, showing real Gemma 4 output.
- **Live App:** [link] — publicly accessible, no login required to view the landing page and public listings.

---

## Known Limitations

Transparency here is intentional, we'd rather state trade-offs clearly than have them discovered mid-demo:

- **Voice input is transcribed client-side** (Web Speech API) before being sent to Gemma as text, rather than sent as raw audio, due to hosting constraints encountered during the sprint.
- **Escrow and wallet balances are simulated** and clearly labeled as a demo throughout the UI, no real payment processor is connected.
- **Maintenance/repair-audit routes exist on the backend** but the end-to-end tenant-report → landlord-repair → Gemma-audit loop should be re-verified before being demonstrated live.
