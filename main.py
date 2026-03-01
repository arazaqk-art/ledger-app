import os
import re
from io import BytesIO
from datetime import datetime

import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import User, Ledger
from auth import verify_password, hash_password
from sms import send_sms

app = FastAPI()

# -----------------------------
# Phone Validation (PK)
# -----------------------------
PHONE_RE = re.compile(r"^\+?\d{10,15}$")

def normalize_phone(p: str) -> str:
    p = (p or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("03") and len(p) == 11 and p[2:].isdigit():
        p = "+92" + p[1:]
    if p.isdigit() and p.startswith("92"):
        p = "+" + p
    return p

def validate_phone(p: str) -> str:
    p = normalize_phone(p)
    if not PHONE_RE.match(p):
        raise HTTPException(status_code=400, detail="Invalid phone. Use +923001234567 or 03001234567")
    return p

# -----------------------------
# Session + DB + Templates
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-super-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_login(request: Request) -> bool:
    return "user" in request.session

def require_admin(request: Request) -> bool:
    return request.session.get("role") == "admin"


# ================= LOGIN =================

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        request.session["user"] = user.username
        request.session["role"] = user.role
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ================= DASHBOARD =================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, q: str = "", db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    query = db.query(Ledger)
    if q.strip():
        s = f"%{q.strip()}%"
        query = query.filter(
            (Ledger.customer_name.ilike(s)) |
            (Ledger.phone.ilike(s)) |
            (Ledger.vehicle_no.ilike(s))
        )

    entries = query.order_by(Ledger.id.desc()).all()

    total_sales = sum(float(e.total or 0) for e in entries)
    total_received = sum(float(e.received or 0) for e in entries)
    total_balance = sum(float(e.balance or 0) for e in entries)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "entries": entries,
        "role": request.session.get("role"),
        "user": request.session.get("user"),
        "q": q,
        "total_sales": total_sales,
        "total_received": total_received,
        "total_balance": total_balance,
    })


# ================= ADD ENTRY =================

@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add")
def add_entry(
    request: Request,
    customer_name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    vehicle_no: str = Form(""),
    source_mine: str = Form(""),
    destination: str = Form(""),
    unit: float = Form(...),
    rate: float = Form(...),
    received: float = Form(...),
    date: str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    phone = validate_phone(phone)

    total = float(unit) * float(rate)
    balance = total - float(received)

    entry = Ledger(
        customer_name=customer_name,
        phone=phone,
        address=address,
        vehicle_no=vehicle_no,
        source_mine=source_mine,
        destination=destination,
        unit=float(unit),
        rate=float(rate),
        total=float(total),
        received=float(received),
        balance=float(balance),
        date=date
    )

    db.add(entry)
    db.commit()

    if balance > 0:
        send_sms(phone, f"Dear {customer_name}, your pending balance is {balance:.2f}")

    return RedirectResponse("/dashboard", status_code=303)


# ================= EDIT ENTRY =================

@app.get("/edit/{entry_id}", response_class=HTMLResponse)
def edit_page(entry_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    entry = db.query(Ledger).filter(Ledger.id == entry_id).first()
    if not entry:
        return RedirectResponse("/dashboard", status_code=303)

        return templates.TemplateResponse("add_entry.html", {"request": request})

@app.post("/edit/{entry_id}")
def edit_entry(
    entry_id: int,
    request: Request,
    customer_name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    vehicle_no: str = Form(""),
    source_mine: str = Form(""),
    destination: str = Form(""),
    unit: float = Form(...),
    rate: float = Form(...),
    received: float = Form(...),
    date: str = Form(...),
    db: Session = Depends(get_db)
):
    entry.source_mine = source_mine
    entry.destination = destination

    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    entry = db.query(Ledger).filter(Ledger.id == entry_id).first()
    if not entry:
        return RedirectResponse("/dashboard", status_code=303)

    phone = validate_phone(phone)

    total = float(unit) * float(rate)
    balance = total - float(received)

    entry.customer_name = customer_name
    entry.phone = phone
    entry.address = address
    entry.vehicle_no = vehicle_no
    entry.unit = float(unit)
    entry.rate = float(rate)
    entry.total = float(total)
    entry.received = float(received)
    entry.balance = float(balance)
    entry.date = date

    db.commit()
    return RedirectResponse("/dashboard", status_code=303)


# ================= DELETE (ADMIN ONLY) =================

@app.get("/delete/{entry_id}")
def delete_entry(entry_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    if not require_admin(request):
        return RedirectResponse("/dashboard", status_code=303)

    entry = db.query(Ledger).filter(Ledger.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse("/dashboard", status_code=303)


# ================= STAFF (ADMIN ONLY) =================

@app.get("/staff", response_class=HTMLResponse)
def staff_page(request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)
    if not require_admin(request):
        return RedirectResponse("/dashboard", status_code=303)

    users = db.query(User).order_by(User.id.desc()).all()
    return templates.TemplateResponse("staff.html", {
        "request": request,
        "users": users
    })

@app.post("/staff/create")
def staff_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    db: Session = Depends(get_db)
):
    if not require_login(request) or not require_admin(request):
        return RedirectResponse("/dashboard", status_code=303)

    username = username.strip().lower()

    if role not in ("admin", "staff"):
        role = "staff"

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        return RedirectResponse("/staff", status_code=303)

    db.add(User(username=username, password_hash=hash_password(password), role=role))
    db.commit()
    return RedirectResponse("/staff", status_code=303)


# ================= EXCEL EXPORT =================

@app.get("/export/excel")
def export_excel(request: Request, q: str = "", db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    query = db.query(Ledger)
    if q.strip():
        s = f"%{q.strip()}%"
        query = query.filter(
            (Ledger.customer_name.ilike(s)) |
            (Ledger.phone.ilike(s)) |
            (Ledger.vehicle_no.ilike(s))
        )

    entries = query.order_by(Ledger.id.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ledger"
   # Header
    ws.append([
    "ID", "Customer", "Phone", "Address", "Vehicle",
    "Mine", "Destination",
    "Unit", "Rate", "Total", "Received", "Balance", "Date"
])

# Rows
    for e in entries:
      ws.append([
        int(e.id),
        str(e.customer_name or ""),
        str(e.phone or ""),
        str(e.address or ""),
        str(e.vehicle_no or ""),
        str(getattr(e, "source_mine", "") or ""),
        str(getattr(e, "destination", "") or ""),
        float(e.unit or 0),
        float(e.rate or 0),
        float(e.total or 0),
        float(e.received or 0),
        float(e.balance or 0),
        str(e.date or ""),
    ])

    
    

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = f"ledger_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ================= PDF INVOICE =================

@app.get("/invoice/{entry_id}")
def invoice_pdf(entry_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/", status_code=303)

    e = db.query(Ledger).filter(Ledger.id == entry_id).first()
    if not e:
        return RedirectResponse("/dashboard", status_code=303)

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    w, h = A4

    y = h - 60
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, "INVOICE")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Invoice ID: {e.id}")
    y -= 18
    c.drawString(50, y, f"Date: {e.date}")
    y -= 28

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Customer")
    y -= 18
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Name: {e.customer_name}")
    y -= 16
    c.drawString(50, y, f"Phone: {e.phone}")
    y -= 16
    c.drawString(50, y, f"Address: {e.address or '-'}")
    y -= 16
    c.drawString(50, y, f"Vehicle No: {e.vehicle_no or '-'}")
    y -= 28

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Billing")
    y -= 18
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Unit: {float(e.unit or 0):.2f}")
    y -= 16
    c.drawString(50, y, f"Rate: {float(e.rate or 0):.2f}")
    y -= 16
    c.drawString(50, y, f"Total: {float(e.total or 0):.2f}")
    y -= 16
    c.drawString(50, y, f"Received: {float(e.received or 0):.2f}")
    y -= 16
    c.drawString(50, y, f"Balance: {float(e.balance or 0):.2f}")
    y -= 30

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, "Thank you for your business.")
    c.showPage()
    c.save()

    bio.seek(0)
    filename = f"invoice_{e.id}.pdf"
    return StreamingResponse(
        bio,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )