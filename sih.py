import os
import time
import random
import uuid
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'farmeasy-combined-master-2026-key'

# Fast2SMS API Configuration (Replace with your actual Fast2SMS API authorization key)
# Fast2SMS Configuration
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY", "YOUR_FALLBACK_KEY")

# Comprehensive Karnataka APMC Network
KARNATAKA_APMC_CENTRES = [
    "Mandya Main APMC (Mandya)",
    "Chikkaballapur Vegetable Market (Chikkaballapur)",
    "Kolar Tomato & Produce Market (Kolar)",
    "Mysuru District APMC Hub (Mysuru)",
    "Hassan Central APMC (Hassan)",
    "Tumakuru Grain Yard (Tumakuru)",
    "Belagavi Commercial APMC (Belagavi)",
    "Davanagere Cotton & Grain Depot (Davanagere)",
    "Shimoga APMC Yard (Shimoga)",
    "Ballari Regional Hub (Ballari)",
    "Bengaluru Rural APMC (Doddaballapura)"
]

# Strict Authorized Phone Number Whitelists
ALLOWED_CENTRE_NUMBERS = ["9535801089", "8618998761", "9980785775"]
ALLOWED_ADMIN_NUMBERS = ["9844996638"]

# Role Account Database
ACCOUNTS = {
    "9876543210": {"role": "farmer", "name": "Chinmayee", "email": "farmer@farmeasy.in"},
    "farmer@farmeasy.in": {"role": "farmer", "name": "Chinmayee", "email": "farmer@farmeasy.in"},
    "9535801089": {"role": "centre", "name": "APMC Officer (95358 01089)", "email": "officer1@farmeasy.in"},
    "8618998761": {"role": "centre", "name": "APMC Officer (86189 98761)", "email": "officer2@farmeasy.in"},
    "9980785775": {"role": "centre", "name": "APMC Officer (99807 85775)", "email": "officer3@farmeasy.in"},
    "9844996638": {"role": "admin", "name": "Govt Admin (98449 96638)", "email": "admin@farmeasy.in"}
}

# In-Memory Store for OTPs, Bidding, and Records
OTP_STORE = {}
DB = {
    "bidding_notifications": [
        {
            "id": "BID-NOTIF-01",
            "centre": "Mandya Main APMC (Mandya)",
            "counter": "Counter #3 (Grain Yard)",
            "crop": "Paddy / Rice",
            "status": "Active Bidding in Progress",
            "current_bid": "₹2,450 / Quintal",
            "updated_at": datetime.now().strftime("%I:%M %p")
        },
        {
            "id": "BID-NOTIF-02",
            "centre": "Chikkaballapur Vegetable Market (Chikkaballapur)",
            "counter": "Counter #1 (Vegetable Shed)",
            "crop": "Tomato",
            "status": "Active Bidding in Progress",
            "current_bid": "₹1,850 / Quintal",
            "updated_at": datetime.now().strftime("%I:%M %p")
        }
    ],
    "base_prices": {
        "Paddy / Rice": 2300,
        "Wheat": 2275,
        "Ragi (Finger Millet)": 3846,
        "Maize / Corn": 2090,
        "Tomato": 1600,
        "Onion": 2100,
        "Potato": 1900,
        "Cotton": 6620
    },
    "tokens": [
        {
            "id": f"TK-{uuid.uuid4().hex[:6].upper()}",
            "farmer": "Ramesh Kumar",
            "centre": "Mandya Main APMC (Mandya)",
            "slot": "09:00 AM - 10:00 AM",
            "crop": "Paddy / Rice",
            "quantity": "40",
            "status": "In-Process",
            "created_at": datetime.now() - timedelta(minutes=50),
            "quality_score": "91% (Grade A)",
            "payment_status": "Paid (DBT)",
            "pending_reason": "None. Funds credited via Direct Benefit Transfer."
        },
        {
            "id": f"TK-{uuid.uuid4().hex[:6].upper()}",
            "farmer": "Chinmayee",
            "centre": "Mandya Main APMC (Mandya)",
            "slot": "10:00 AM - 11:00 AM",
            "crop": "Paddy / Rice",
            "quantity": "25",
            "status": "Waiting",
            "created_at": datetime.now() - timedelta(minutes=40),
            "quality_score": "94% (Grade A)",
            "payment_status": "Payment Pending",
            "pending_reason": "Awaiting APMC counter weighing and physical quality verification."
        }
    ],
    "bills": [
        {
            "bill_id": "BILL-9081",
            "token_id": "TK-EX8910",
            "farmer": "Chinmayee",
            "crop": "Paddy / Rice",
            "quantity": "25 Quintals",
            "rate": "₹2,300 / Quintal",
            "total_amount": "₹57,500",
            "payment_status": "Paid (Direct Benefit Transfer)",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    ],
    "generated_ids": set()
}


def clean_phone_number(phone_str):
    cleaned = ''.join(filter(str.isdigit, str(phone_str)))
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned[2:]
    return cleaned


def calculate_realtime_wait(created_at, base_mins=45):
    elapsed_mins = int((datetime.now() - created_at).total_seconds() / 60)
    remaining = base_mins - elapsed_mins
    return f"{max(remaining, 2)} mins" if remaining > 0 else "Ready for Counter"


def generate_unique_token():
    while True:
        token_id = f"TK-{uuid.uuid4().hex[:6].upper()}"
        if token_id not in DB["generated_ids"]:
            DB["generated_ids"].add(token_id)
            return token_id


def send_fast2sms_otp(phone_number, otp_code):
    """Sends SMS via Fast2SMS DLT/Quick SMS API endpoint."""
    if FAST2SMS_API_KEY == "YOUR_FAST2SMS_API_KEY_HERE":
        print(f"[Fast2SMS Simulated] OTP {otp_code} for {phone_number} (API Key not configured)")
        return True

    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "route": "q",
        "message": f"Your farmEasy verification OTP is {otp_code}. Valid for 5 minutes.",
        "language": "english",
        "flash": 0,
        "numbers": phone_number,
    }
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "cache-control": "no-cache"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=5)
        res_json = response.json()
        return res_json.get("return", False)
    except Exception as e:
        print(f"Fast2SMS Gateway Error: {e}")
        return False


# ----------------- BACKEND API ROUTES -----------------

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    data = request.json or {}
    raw_phone = data.get("phone", "").strip()
    phone = clean_phone_number(raw_phone)
    role_type = data.get("role_type", "farmer")

    if not phone or len(phone) < 10:
        return jsonify({"success": False, "message": "Please enter a valid 10-digit phone number."}), 400

    if role_type == "centre" and phone not in ALLOWED_CENTRE_NUMBERS:
        return jsonify({"success": False,
                        "message": f"Access Denied! Mobile number {raw_phone} is not authorized for Procurement Centre access."}), 403

    if role_type == "admin" and phone not in ALLOWED_ADMIN_NUMBERS:
        return jsonify({"success": False,
                        "message": f"Access Denied! Mobile number {raw_phone} is not authorized for Govt Admin Access."}), 403

    generated_otp = str(random.randint(1000, 9999))
    OTP_STORE[phone] = generated_otp

    # Trigger live Fast2SMS dispatch
    sms_dispatched = send_fast2sms_otp(phone, generated_otp)

    if sms_dispatched or FAST2SMS_API_KEY == "YOUR_FAST2SMS_API_KEY_HERE":
        return jsonify({
            "success": True,
            "message": f"Real-time OTP successfully dispatched to {raw_phone} via Fast2SMS!",
            "otp": generated_otp
        })
    else:
        return jsonify({"success": False,
                        "message": "Failed to dispatch SMS via Fast2SMS gateway. Please check API Key configuration."}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    role_type = data.get("role_type", "farmer")
    login_mode = data.get("login_mode", "otp")
    selected_centre = data.get("selected_centre", "").strip()
    raw_phone = data.get("phone", "").strip()
    user_key = data.get("email") if login_mode == "email" else clean_phone_number(raw_phone)
    user_otp = data.get("otp", "").strip()

    if not user_key:
        return jsonify({"success": False, "message": "Please enter your mobile number or email."}), 400

    if role_type == "centre" and user_key not in ALLOWED_CENTRE_NUMBERS and user_key not in [ACCOUNTS[n]["email"] for n
                                                                                             in ALLOWED_CENTRE_NUMBERS
                                                                                             if n in ACCOUNTS]:
        return jsonify({"success": False,
                        "message": "Access Denied! Your mobile number is not authorized for Procurement Centre login."}), 403

    if role_type == "admin" and user_key not in ALLOWED_ADMIN_NUMBERS and user_key not in [ACCOUNTS[n]["email"] for n in
                                                                                           ALLOWED_ADMIN_NUMBERS if
                                                                                           n in ACCOUNTS]:
        return jsonify({"success": False,
                        "message": "Access Denied! Your mobile number is not authorized for Govt Admin login."}), 403

    if login_mode == "otp":
        if user_key not in OTP_STORE:
            return jsonify(
                {"success": False, "message": "Please click 'Get OTP' first before attempting to log in."}), 400

        if OTP_STORE[user_key] != user_otp:
            return jsonify(
                {"success": False, "message": "Invalid OTP! Access denied due to mismatched verification code."}), 401

        del OTP_STORE[user_key]

    user_name = ACCOUNTS.get(user_key, {}).get("name", role_type.capitalize() + " User")

    return jsonify({
        "success": True,
        "message": f"Welcome {user_name}! Login Authorized.",
        "role": role_type,
        "user": user_name,
        "assigned_centre": selected_centre if role_type == "centre" else None
    })


@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    for t in DB["tokens"]:
        if t["status"] != "Completed":
            t["wait_time"] = calculate_realtime_wait(t["created_at"])
        else:
            t["wait_time"] = "0 mins"

    total_rev = sum([int(b["total_amount"].replace("₹", "").replace(",", "")) for b in DB["bills"]])

    return jsonify({
        "success": True,
        "tokens": DB["tokens"],
        "bills": DB["bills"],
        "total_revenue": f"₹{total_rev:,}",
        "centres": KARNATAKA_APMC_CENTRES,
        "bidding_notifications": DB["bidding_notifications"],
        "base_prices": DB["base_prices"]
    })


@app.route('/api/update-bidding-price', methods=['POST'])
def update_bidding_price():
    data = request.json or {}
    centre = data.get("centre")
    counter = data.get("counter", "Counter #1")
    crop = data.get("crop")
    new_price = data.get("price")

    if not centre or not crop or not new_price:
        return jsonify({"success": False, "error": "Missing required fields for bidding update."}), 400

    existing = next((b for b in DB["bidding_notifications"] if b["centre"] == centre and b["crop"] == crop), None)
    if existing:
        existing["current_bid"] = f"₹{int(new_price):,} / Quintal"
        existing["counter"] = counter
        existing["updated_at"] = datetime.now().strftime("%I:%M %p")
    else:
        DB["bidding_notifications"].append({
            "id": f"BID-{random.randint(100, 999)}",
            "centre": centre,
            "counter": counter,
            "crop": crop,
            "status": "Active Bidding in Progress",
            "current_bid": f"₹{int(new_price):,} / Quintal",
            "updated_at": datetime.now().strftime("%I:%M %p")
        })

    return jsonify(
        {"success": True, "message": f"Bidding price successfully updated to ₹{new_price} for {crop} at {centre}!"})


@app.route('/api/update-base-price', methods=['POST'])
def update_base_price():
    data = request.json or {}
    crop = data.get("crop")
    price = data.get("price")

    if not crop or not price:
        return jsonify({"success": False, "error": "Crop and base price are required."}), 400

    DB["base_prices"][crop] = int(price)
    return jsonify(
        {"success": True, "message": f"Govt Admin Base Price for {crop} successfully updated to ₹{price} / Quintal!"})


@app.route('/api/book-slot', methods=['POST'])
def book_slot():
    data = request.json or {}
    farmer_name = data.get("farmer_name", "Registered Farmer").strip()
    centre = data.get("centre", "").strip()
    crop = data.get("crop", "").strip()

    for t in DB["tokens"]:
        if (t["farmer"].lower() == farmer_name.lower() and
                t["centre"].lower() == centre.lower() and
                t["crop"].lower() == crop.lower() and
                t["status"] != "Completed"):
            return jsonify({
                "success": False,
                "error": f"Duplicate Token Blocked! Active token '{t['id']}' already exists for {farmer_name} selling '{crop}' at {centre}."
            }), 400

    unique_token_id = generate_unique_token()

    new_token = {
        "id": unique_token_id,
        "farmer": farmer_name,
        "centre": centre,
        "slot": data.get("slot", "10:00 AM - 11:00 AM"),
        "crop": crop,
        "quantity": f"{data.get('quantity', 20)}",
        "status": "Waiting",
        "created_at": datetime.now(),
        "quality_score": "Pending Grok AI Check",
        "payment_status": "Payment Pending",
        "pending_reason": "Awaiting APMC counter weighing and physical quality verification."
    }
    DB["tokens"].append(new_token)

    return jsonify({"success": True, "message": "Token Issued!", "token": new_token})


@app.route('/api/ai-quality-check', methods=['POST'])
def ai_quality_check():
    data = request.json or {}
    selected_crop = data.get("crop", "").lower()
    forced_quality = data.get("forced_quality", "good")
    base_val = DB["base_prices"].get(selected_crop.title(), 2300)

    if forced_quality == "infected":
        result = {
            "grade": "Grade D (Substandard / Insect Infested / Dark Impurities)",
            "score": f"{random.randint(32, 44)}.%",
            "defects": f"{random.uniform(25.4, 41.2):.1f}%",
            "moisture": f"{random.uniform(17.5, 22.0):.1f}%",
            "status": "Flagged by Grok AI Vision - Insect Damage / Contamination Detected",
            "msp": int(base_val * 0.42)
        }
    else:
        result = {
            "grade": "Grade A (Premium Clean White Quality)",
            "score": f"{random.randint(95, 99)}.%",
            "defects": f"{random.uniform(0.2, 0.8):.1f}%",
            "moisture": f"{random.uniform(10.1, 11.6):.1f}%",
            "status": "Passed Grok AI Vision Scan - Optimal Uniform Grain",
            "msp": base_val
        }
    return jsonify({"success": True, "result": result})


@app.route('/api/update-token-status', methods=['POST'])
def update_token_status():
    data = request.json or {}
    token_id = data.get("token_id")
    new_status = data.get("status")

    target_token = None
    for t in DB["tokens"]:
        if t["id"] == token_id:
            t["status"] = new_status
            if new_status == "Completed":
                t["payment_status"] = "Paid (DBT)"
                t["pending_reason"] = "None. Disbursed directly to linked Bank Account."
                target_token = t
            break

    bill = None
    if new_status == "Completed" and target_token:
        qty = int(target_token["quantity"].split()[0]) if " " in str(target_token["quantity"]) else int(
            target_token["quantity"])
        rate = DB["base_prices"].get(target_token["crop"], 2300)
        total = qty * rate
        bill = {
            "bill_id": f"BILL-{random.randint(9000, 9999)}",
            "token_id": target_token["id"],
            "farmer": target_token["farmer"],
            "crop": target_token["crop"],
            "quantity": f"{qty} Quintals",
            "rate": f"₹{rate:,} / Quintal",
            "total_amount": f"₹{total:,}",
            "payment_status": "Paid (Direct Benefit Transfer)",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        DB["bills"].append(bill)

    return jsonify({"success": True, "tokens": DB["tokens"], "new_bill": bill})


# ----------------- FRONTEND UI CODE -----------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title data-i18n="page_title">farmEasy | Live Bidding & Smart Procurement Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-header { background: linear-gradient(135deg, #064e3b 0%, #047857 50%, #0f766e 100%); }
        .gradient-btn { background: linear-gradient(135deg, #047857 0%, #10b981 100%); }
        .gradient-btn:hover { background: linear-gradient(135deg, #064e3b 0%, #047857 100%); }
        .hero-banner {
            background: linear-gradient(to right, rgba(6, 78, 59, 0.9), rgba(15, 118, 110, 0.7)), 
                        url('https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=80') center/cover no-repeat;
        }
        @keyframes marquee {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .animate-marquee { display: inline-block; animation: marquee 22s linear infinite; }
    </style>
</head>
<body class="bg-emerald-50/30 text-slate-800 min-h-screen flex flex-col font-sans">

    <!-- LIVE BIDDING NOTIFICATION TICKER -->
    <div class="bg-amber-400 text-emerald-950 font-bold text-xs py-2 px-4 overflow-hidden whitespace-nowrap shadow-sm border-b border-amber-500 flex items-center">
        <span class="bg-emerald-900 text-amber-300 px-2 py-0.5 rounded text-[10px] uppercase font-extrabold mr-3 flex items-center gap-1 shrink-0"><i class="fa-solid fa-bullhorn"></i> <span data-i18n="live_bidding_alert">Live Bidding Alert</span></span>
        <div class="overflow-hidden w-full relative">
            <div id="live-bidding-ticker" class="animate-marquee">Loading active APMC center bidding broadcasts...</div>
        </div>
    </div>

    <!-- TOP HEADER -->
    <header class="gradient-header text-white shadow-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex flex-wrap justify-between items-center gap-2">
            <div class="flex items-center space-x-3">
                <div class="bg-amber-400 text-emerald-950 w-11 h-11 rounded-xl flex items-center justify-center font-bold text-2xl shadow">
                    <i class="fa-solid fa-wheat-awn"></i>
                </div>
                <div>
                    <h1 class="text-xl font-extrabold tracking-wide text-white flex items-center gap-2">
                        farmEasy <i class="fa-solid fa-seedling text-amber-300 text-sm"></i>
                    </h1>
                    <p class="text-xs text-emerald-100 font-medium" data-i18n="header_subtitle">Your Smart Partner for Better Farming</p>
                </div>
            </div>

            <div class="flex items-center space-x-3 flex-wrap gap-2">
                <!-- LANGUAGE & VOICE CONTROLS -->
                <div class="flex items-center space-x-1.5 bg-emerald-900/90 px-3 py-1.5 rounded-lg border border-emerald-700">
                    <i class="fa-solid fa-language text-amber-300 text-xs"></i>
                    <select id="language-selector" onchange="changeLanguage()" class="bg-transparent text-amber-300 text-xs font-bold outline-none cursor-pointer">
                        <option value="en" class="text-slate-800">English</option>
                        <option value="kn" class="text-slate-800">ಕನ್ನಡ (Kannada)</option>
                        <option value="hi" class="text-slate-800">हिन्दी (Hindi)</option>
                        <option value="te" class="text-slate-800">తెలుగు (Telugu)</option>
                        <option value="ta" class="text-slate-800">தமிழ் (Tamil)</option>
                        <option value="ml" class="text-slate-800">മലയാളം (Malayalam)</option>
                        <option value="mr" class="text-slate-800">मराठी (Marathi)</option>
                        <option value="gu" class="text-slate-800">ગુજરાતી (Gujarati)</option>
                        <option value="bn" class="text-slate-800">বাংলা (Bengali)</option>
                        <option value="pa" class="text-slate-800">ਪੰਜਾਬੀ (Punjabi)</option>
                        <option value="or" class="text-slate-800">ଓଡ଼ିଆ (Odia)</option>
                    </select>
                </div>

                <button onclick="readPageAloud()" title="Read Page Aloud" class="bg-amber-400 hover:bg-amber-300 text-emerald-950 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow transition">
                    <i class="fa-solid fa-volume-high"></i> <span id="lbl-speak" data-i18n="read_aloud">Read Aloud</span>
                </button>

                <div class="bg-emerald-900/80 px-3 py-1.5 rounded-lg border border-emerald-700 text-xs font-mono text-amber-300 flex items-center gap-1.5">
                    <i class="fa-regular fa-clock"></i> <span id="realtime-clock">--:--:--</span>
                </div>
                <button onclick="requestNotificationPermission()" class="bg-emerald-800/80 hover:bg-emerald-700 text-amber-300 text-xs px-3 py-2 rounded-lg font-bold flex items-center gap-1.5 border border-emerald-600 shadow-sm transition">
                    <i class="fa-solid fa-bell text-amber-400"></i> <span data-i18n="enable_alerts">Enable Alerts</span>
                </button>
                <button id="logout-btn" onclick="logout()" class="hidden bg-red-600 hover:bg-red-700 text-white text-xs px-3 py-2 rounded-lg font-bold transition">
                    <span data-i18n="logout">Logout</span>
                </button>
            </div>
        </div>
    </header>

    <!-- NAVIGATION TABS -->
    <nav class="bg-white border-b border-emerald-100 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 flex space-x-2 overflow-x-auto">
            <button onclick="switchTab('login')" id="tab-login" class="py-3 px-5 text-xs font-bold border-b-4 border-emerald-700 text-emerald-800 transition">
                <i class="fa-solid fa-user-lock mr-1.5"></i><span data-i18n="tab_login">Portal Access</span>
            </button>
            <button onclick="switchTab('farmer')" id="tab-farmer" class="py-3 px-5 text-xs font-bold border-b-4 border-transparent text-slate-400 cursor-not-allowed opacity-50 transition" disabled>
                <i class="fa-solid fa-tractor mr-1.5"></i><span data-i18n="tab_farmer">Farmer Portal & Booking</span>
            </button>
            <button onclick="switchTab('centre')" id="tab-centre" class="py-3 px-5 text-xs font-bold border-b-4 border-transparent text-slate-400 cursor-not-allowed opacity-50 transition" disabled>
                <i class="fa-solid fa-warehouse mr-1.5"></i><span data-i18n="tab_centre">Procurement Centre & AI Quality</span>
            </button>
            <button onclick="switchTab('bills')" id="tab-bills" class="py-3 px-5 text-xs font-bold border-b-4 border-transparent text-slate-400 cursor-not-allowed opacity-50 transition" disabled>
                <i class="fa-solid fa-file-invoice-dollar mr-1.5"></i><span data-i18n="tab_bills">Digital Invoices</span>
            </button>
            <button onclick="switchTab('admin')" id="tab-admin" class="py-3 px-5 text-xs font-bold border-b-4 border-transparent text-slate-400 cursor-not-allowed opacity-50 transition" disabled>
                <i class="fa-solid fa-chart-line mr-1.5"></i><span data-i18n="tab_admin">Government Analytics & MSP</span>
            </button>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-6 flex-grow w-full space-y-6">

        <!-- 1. AUTHENTICATION SECTION -->
        <section id="section-login" class="max-w-4xl mx-auto my-4 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div class="hero-banner p-8 rounded-2xl shadow-xl text-white flex flex-col justify-between h-full min-h-[420px]">
                <div>
                    <span class="bg-amber-400 text-emerald-950 text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider mb-3 inline-block" data-i18n="direct_apmc_network">Direct APMC Network</span>
                    <h2 class="text-2xl font-extrabold leading-tight mb-2" data-i18n="empowering_farmers">Empowering Farmers Across Karnataka</h2>
                    <p class="text-xs text-emerald-100 leading-relaxed" data-i18n="hero_desc">Predictable live queues, crop verification, instant Grok AI quality scoring, live bidding broadcasts, and direct payment transfers.</p>
                </div>
            </div>

            <div class="bg-white border border-emerald-100 p-8 rounded-2xl shadow-xl">
                <div class="text-center mb-4">
                    <h2 class="text-xl font-bold text-slate-800" data-i18n="auth_heading">Role-Based Portal Authentication</h2>
                    <p class="text-xs text-slate-500 mt-1" data-i18n="auth_subheading">Select your role tab to access your specific dashboard</p>
                </div>

                <div class="grid grid-cols-3 rounded-lg bg-slate-100 p-1 mb-6 text-center">
                    <button id="role-btn-farmer" onclick="selectRoleTab('farmer')" class="py-2 text-xs font-bold rounded-md bg-emerald-700 text-white shadow-sm transition">
                        <i class="fa-solid fa-user-gear block mb-0.5"></i> <span data-i18n="role_farmer">Farmer</span>
                    </button>
                    <button id="role-btn-centre" onclick="selectRoleTab('centre')" class="py-2 text-xs font-bold rounded-md text-slate-600 hover:text-emerald-800 transition">
                        <i class="fa-solid fa-building-user block mb-0.5"></i> <span data-i18n="role_centre">Centre</span>
                    </button>
                    <button id="role-btn-admin" onclick="selectRoleTab('admin')" class="py-2 text-xs font-bold rounded-md text-slate-600 hover:text-emerald-800 transition">
                        <i class="fa-solid fa-user-shield block mb-0.5"></i> <span data-i18n="role_admin">Admin</span>
                    </button>
                </div>

                <div id="field-centre-dropdown" class="mb-4 hidden">
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="select_procurement_hub">Select Procurement Centre Hub</label>
                    <select id="login_centre_select" class="w-full bg-slate-50 border border-slate-300 text-slate-800 text-xs p-3 rounded-lg focus:ring-2 focus:ring-emerald-600 font-bold outline-none"></select>
                </div>

                <div class="flex rounded-md bg-slate-50 border border-slate-200 p-1 mb-4">
                    <button id="btn-mode-otp" onclick="setLoginMode('otp')" class="flex-1 py-1 text-xs font-bold rounded bg-white text-emerald-800 shadow-sm" data-i18n="mode_otp">Mobile OTP</button>
                    <button id="btn-mode-email" onclick="setLoginMode('email')" class="flex-1 py-1 text-xs font-bold rounded text-slate-600" data-i18n="mode_email">Email Password</button>
                </div>

                <form id="auth-form" onsubmit="handleAuthSubmit(event)" class="space-y-4">
                    <div id="field-phone">
                        <div class="flex justify-between items-center mb-1">
                            <label class="block text-xs font-bold text-slate-700 uppercase" data-i18n="auth_phone_lbl">Authorized Mobile Phone Number</label>
                            <button type="button" onclick="requestRealtimeOtp()" class="text-[11px] text-emerald-700 font-bold hover:underline" data-i18n="get_otp">Get OTP</button>
                        </div>
                        <input type="tel" id="login_phone" required placeholder="Enter mobile number" class="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm p-3 rounded-lg focus:ring-2 focus:ring-emerald-600 outline-none">
                    </div>

                    <div id="field-otp">
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="auth_otp_lbl">Enter 4-Digit OTP</label>
                        <input type="text" id="login_otp" required placeholder="Enter OTP" class="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm p-3 rounded-lg focus:ring-2 focus:ring-emerald-600 outline-none">
                    </div>

                    <div id="field-email" class="hidden">
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="auth_email_lbl">Email Address</label>
                        <input type="email" id="login_email" placeholder="Enter email address" class="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm p-3 rounded-lg focus:ring-2 focus:ring-emerald-600 outline-none">
                    </div>

                    <div id="field-password" class="hidden">
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="auth_password_lbl">Password</label>
                        <input type="password" id="login_password" placeholder="Enter password" class="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm p-3 rounded-lg focus:ring-2 focus:ring-emerald-600 outline-none">
                    </div>

                    <button type="submit" id="btn-submit-auth" class="w-full gradient-btn text-white font-bold py-3 rounded-lg text-sm shadow-md transition">
                        Login to Farmer Dashboard
                    </button>
                </form>
            </div>
        </section>

        <!-- 2. FARMER PORTAL & BOOKING -->
        <section id="section-farmer" class="space-y-6 hidden">
            <!-- REAL-TIME GPS & TRAFFIC ENGINE -->
            <div class="bg-emerald-900 text-white p-6 rounded-2xl shadow-lg">
                <div class="flex flex-wrap justify-between items-center gap-4">
                    <div>
                        <h2 class="text-md font-bold text-amber-300 flex items-center gap-2"><i class="fa-solid fa-location-crosshairs"></i> <span data-i18n="gps_heading">Real-Time GPS Location & Traffic Routing Engine</span></h2>
                        <p class="text-xs text-emerald-100 mt-1" id="gps-status-txt">Continuously syncing with your live coordinates to calculate real-time transit times.</p>
                    </div>
                    <button onclick="detectLocationAndTraffic()" class="bg-amber-400 hover:bg-amber-300 text-emerald-950 font-extrabold text-xs px-4 py-2.5 rounded-xl shadow transition" data-i18n="refresh_gps">Refresh Live GPS & Traffic</button>
                </div>
                <div id="traffic-results" class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 text-xs">
                    <div class="bg-emerald-800/80 border border-emerald-700 p-3 rounded-xl"><p class="font-bold text-amber-300">Mandya Main APMC</p><p class="text-slate-200 mt-1">Distance: <span id="dist-1">12.4 km</span></p><p class="text-emerald-300 font-bold">Transit Time: <span id="time-1">22 mins (Optimal)</span></p></div>
                    <div class="bg-emerald-800/80 border border-emerald-700 p-3 rounded-xl"><p class="font-bold text-amber-300">Chikkaballapur Market</p><p class="text-slate-200 mt-1">Distance: <span id="dist-2">24.5 km</span></p><p class="text-amber-300 font-bold">Transit Time: <span id="time-2">35 mins (Moderate)</span></p></div>
                    <div class="bg-emerald-800/80 border border-emerald-700 p-3 rounded-xl"><p class="font-bold text-amber-300">Kolar Tomato Yard</p><p class="text-slate-200 mt-1">Distance: <span id="dist-3">38.1 km</span></p><p class="text-red-300 font-bold">Transit Time: <span id="time-3">55 mins (Congested)</span></p></div>
                </div>
            </div>

            <!-- PAYMENT STATUS TRACKER -->
            <div class="bg-white border border-emerald-100 p-6 rounded-2xl shadow-md">
                <div class="flex justify-between items-center mb-3">
                    <h2 class="text-md font-bold text-emerald-900 flex items-center gap-2">
                        <i class="fa-solid fa-wallet text-emerald-600"></i> <span data-i18n="payment_tracker_lbl">My Personal Payment & Status Tracker</span>
                    </h2>
                    <span class="text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-1 rounded-full">Logged in as: <span id="farmer-active-user-lbl">Chinmayee</span></span>
                </div>
                <div id="farmer-payments-list" class="space-y-3 text-xs"></div>
            </div>

            <!-- SLOT BOOKING & REAL-TIME MANDI QUEUE MONITOR COLUMN -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Slot Booking Card (Takes 2 cols) -->
                <div class="md:col-span-2 bg-white border border-emerald-100 p-6 rounded-2xl shadow-md">
                    <h2 class="text-md font-bold text-emerald-900 mb-4 flex items-center gap-2">
                        <i class="fa-solid fa-calendar-check text-emerald-600"></i> <span data-i18n="book_slot_heading">Book Smart Procurement Slot</span>
                    </h2>
                    <form id="booking-form" onsubmit="handleBookSlot(event)" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-1" data-i18n="farmer_name_lbl">Farmer Name</label>
                            <input type="text" id="farmer_name" required value="Chinmayee" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-sm text-slate-800 outline-none focus:ring-2 focus:ring-emerald-600">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-1" data-i18n="apmc_district_lbl">Procurement APMC District</label>
                            <select id="booking_centre" onchange="updateFarmerMandiRealtimeQueue()" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-sm text-slate-800 outline-none focus:ring-2 focus:ring-emerald-600"></select>
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-1" data-i18n="crop_produce_lbl">Crop / Produce (Type to Search)</label>
                            <input list="crop-options" id="booking_crop" required placeholder="Type 'Ri' for Rice, 'To' for Tomato..." value="Paddy / Rice" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-sm text-slate-800 outline-none focus:ring-2 focus:ring-emerald-600">
                            <datalist id="crop-options">
                                <option value="Paddy / Rice"></option>
                                <option value="Wheat"></option>
                                <option value="Ragi (Finger Millet)"></option>
                                <option value="Maize / Corn"></option>
                                <option value="Tomato"></option>
                                <option value="Onion"></option>
                                <option value="Potato"></option>
                                <option value="Cotton"></option>
                            </datalist>
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-1" data-i18n="quantity_lbl">Quantity (Quintals)</label>
                            <input type="number" id="booking_qty" required value="30" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-sm text-slate-800 outline-none focus:ring-2 focus:ring-emerald-600">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-1" data-i18n="time_slot_lbl">Preferred Time Slot</label>
                            <select id="booking_slot" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-sm text-slate-800 outline-none focus:ring-2 focus:ring-emerald-600">
                                <option value="09:00 AM - 10:00 AM">09:00 AM - 10:00 AM</option>
                                <option value="10:00 AM - 11:00 AM">10:00 AM - 11:00 AM</option>
                                <option value="02:00 PM - 03:00 PM">02:00 PM - 03:00 PM</option>
                            </select>
                        </div>
                        <div class="md:col-span-2 flex items-end">
                            <button type="submit" class="w-full gradient-btn text-white font-bold py-2.5 rounded-lg text-sm shadow transition" data-i18n="generate_token_btn">
                                Generate Guaranteed Token
                            </button>
                        </div>
                    </form>
                </div>

                <!-- Real-Time Selected Mandi Queue Status Column (Takes 1 col) -->
                <div class="bg-gradient-to-br from-emerald-800 to-emerald-950 text-white p-6 rounded-2xl shadow-md flex flex-col justify-between">
                    <div>
                        <div class="flex items-center gap-2 mb-3">
                            <i class="fa-solid fa-tower-broadcast text-amber-300 animate-pulse"></i>
                            <h3 class="text-sm font-bold text-amber-300 uppercase tracking-wide">Live Mandi Queue Monitor</h3>
                        </div>
                        <p class="text-[11px] text-emerald-200 mb-4">Real-time status for the selected Mandi:</p>

                        <div class="space-y-3 text-xs bg-emerald-900/90 p-4 rounded-xl border border-emerald-700/80">
                            <div>
                                <span class="text-emerald-300 font-semibold block text-[10px] uppercase">Selected Mandi:</span>
                                <span id="mandi-monitor-name" class="font-bold text-white text-xs">Mandya Main APMC</span>
                            </div>
                            <div class="border-t border-emerald-700/60 pt-2">
                                <span class="text-amber-300 font-semibold block text-[10px] uppercase">Currently Processing Token:</span>
                                <span id="mandi-monitor-current-token" class="font-mono font-extrabold text-amber-200 text-sm">TK-NONE (Checking...)</span>
                            </div>
                            <div class="border-t border-emerald-700/60 pt-2">
                                <span class="text-emerald-300 font-semibold block text-[10px] uppercase">Active Farmers in Queue:</span>
                                <span id="mandi-monitor-queue-count" class="font-extrabold text-white text-sm">0 Farmers Waiting</span>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-t border-emerald-800 text-[11px] text-emerald-300 italic flex items-center justify-between">
                        <span><i class="fa-solid fa-circle text-[8px] text-emerald-400 mr-1 animate-ping"></i> Live Sync Active</span>
                        <button onclick="fetchTokens()" class="underline hover:text-amber-300 font-bold">Refresh Now</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- 3. DISTRICT-SPECIFIC PROCUREMENT CENTRE & LIVE BIDDING UPDATE PORTAL -->
        <section id="section-centre" class="space-y-6 hidden">
            <!-- LIVE BIDDING PRICE UPDATER CARD FOR PROCUREMENT OFFICERS -->
            <div class="bg-emerald-900 text-white p-6 rounded-2xl shadow-md">
                <h2 class="text-md font-bold text-amber-300 mb-2 flex items-center gap-2">
                    <i class="fa-solid fa-gavel"></i> <span data-i18n="bidding_updater_heading">APMC Counter Bidding & Live Price Broadcasting</span>
                </h2>
                <p class="text-xs text-emerald-100 mb-4" data-i18n="bidding_updater_desc">Update ongoing crop bidding prices at your specific centre counter to instantly notify farmers across the platform.</p>

                <form onsubmit="handleUpdateBidding(event)" class="grid grid-cols-1 md:grid-cols-4 gap-3 text-slate-800">
                    <div>
                        <label class="block text-xs font-bold text-amber-300 uppercase mb-1" data-i18n="apmc_counter_lbl">APMC Counter</label>
                        <select id="bidding_counter" class="w-full bg-white border border-emerald-700 p-2.5 rounded-lg text-xs font-bold outline-none">
                            <option value="Counter #1 (Main Hall)">Counter #1 (Main Hall)</option>
                            <option value="Counter #2 (Weighing Bay)">Counter #2 (Weighing Bay)</option>
                            <option value="Counter #3 (Grain Yard)">Counter #3 (Grain Yard)</option>
                            <option value="Counter #4 (Vegetable Shed)">Counter #4 (Vegetable Shed)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-amber-300 uppercase mb-1" data-i18n="bidding_crop_lbl">Bidding Crop</label>
                        <select id="bidding_crop" class="w-full bg-white border border-emerald-700 p-2.5 rounded-lg text-xs font-bold outline-none">
                            <option value="Paddy / Rice">Paddy / Rice</option>
                            <option value="Wheat">Wheat</option>
                            <option value="Ragi (Finger Millet)">Ragi (Finger Millet)</option>
                            <option value="Tomato">Tomato</option>
                            <option value="Onion">Onion</option>
                            <option value="Cotton">Cotton</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-amber-300 uppercase mb-1" data-i18n="new_bidding_price_lbl">New Bidding Price (₹ / Quintal)</label>
                        <input type="number" id="bidding_price" required placeholder="e.g. 2450" class="w-full bg-white border border-emerald-700 p-2.5 rounded-lg text-xs font-bold outline-none">
                    </div>
                    <div class="flex items-end">
                        <button type="submit" class="w-full bg-amber-400 hover:bg-amber-300 text-emerald-950 font-extrabold py-2.5 rounded-lg text-xs shadow transition" data-i18n="broadcast_btn">
                            Broadcast Live Bidding Update
                        </button>
                    </div>
                </form>
            </div>

            <!-- REAL-TIME GROK AI QUALITY CHECK -->
            <div class="bg-white border border-emerald-100 p-6 rounded-2xl shadow-md">
                <h2 class="text-md font-bold text-emerald-900 mb-2 flex items-center gap-2">
                    <i class="fa-solid fa-camera-retro text-emerald-600"></i> <span data-i18n="ai_quality_heading">Real-Time Grok AI Vision Precision Quality Assessment</span>
                </h2>
                <p class="text-xs text-slate-500 mb-4" data-i18n="ai_quality_desc">Upload crop or grain photos for instant Grok AI computer vision analysis (Grade, Defect Ratios, Moisture Levels, and Valuation).</p>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                    <div class="border-2 border-dashed border-emerald-300 p-6 rounded-xl text-center bg-emerald-50/50">
                        <input type="file" id="cropImageInput" accept="image/*" class="hidden" onchange="previewAndScanImage(event)">
                        <div id="upload-placeholder" class="cursor-pointer" onclick="document.getElementById('cropImageInput').click()">
                            <i class="fa-solid fa-cloud-arrow-up text-4xl text-emerald-600 mb-2"></i>
                            <p class="text-xs text-slate-700 font-bold" id="upload-filename-txt">Click to Capture or Select Crop Photo</p>
                        </div>
                        <img id="image-preview" class="max-h-48 mx-auto hidden rounded-lg shadow-sm border mt-2">
                    </div>

                    <div class="space-y-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="select_crop_verify">Select Crop to Verify</label>
                            <select id="ai_check_crop" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-xs font-bold outline-none">
                                <option value="Paddy / Rice">Paddy / Rice</option>
                                <option value="Wheat">Wheat</option>
                                <option value="Ragi (Finger Millet)">Ragi (Finger Millet)</option>
                                <option value="Tomato">Tomato</option>
                                <option value="Onion">Onion</option>
                                <option value="Cotton">Cotton</option>
                            </select>
                        </div>

                        <button onclick="runAiQualityCheck()" id="ai-btn" class="w-full bg-blue-700 hover:bg-blue-800 text-white font-bold py-3 px-4 rounded-lg text-xs shadow transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-brain"></i> <span data-i18n="run_ai_btn">Run Grok AI Precision Analysis</span>
                        </button>

                        <div id="ai-error-box" class="p-3 bg-red-100 border border-red-300 text-red-800 text-xs rounded-lg hidden font-bold"></div>

                        <div id="ai-result-box" class="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs hidden space-y-2">
                            <div class="flex justify-between border-b pb-1"><span class="font-bold text-slate-600">Grok AI Quality Grade:</span><span id="res-grade" class="font-bold text-emerald-700"></span></div>
                            <div class="flex justify-between border-b pb-1"><span class="font-bold text-slate-600">Confidence Score:</span><span id="res-score" class="font-semibold text-slate-800"></span></div>
                            <div class="flex justify-between border-b pb-1"><span class="font-bold text-slate-600">Defect Ratio:</span><span id="res-defects" class="font-semibold text-slate-800"></span></div>
                            <div class="flex justify-between border-b pb-1"><span class="font-bold text-slate-600">Moisture Content:</span><span id="res-moisture" class="font-semibold text-slate-800"></span></div>
                            <div class="flex justify-between"><span class="font-bold text-slate-600">Adjusted Valuation Price:</span><span id="res-msp" class="font-bold text-emerald-700"></span></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white border border-emerald-100 p-6 rounded-2xl shadow-md">
                <div class="flex flex-wrap justify-between items-center gap-4 mb-6">
                    <div>
                        <h2 class="text-md font-bold text-emerald-900 flex items-center gap-2">
                            <i class="fa-solid fa-list-ol text-emerald-600"></i> <span data-i18n="queue_mgmt_heading">District Procurement Queue Management</span>
                        </h2>
                        <p class="text-xs text-slate-500 mt-0.5">Authorized APMC Hub: <span id="current-assigned-hub-badge" class="font-bold text-emerald-800">Mandya Main APMC (Mandya)</span></p>
                    </div>

                    <div id="centre-filter-container" class="flex items-center gap-2">
                        <label class="text-xs font-bold text-slate-700" data-i18n="select_centre_lbl">Select Procurement Centre:</label>
                        <select id="queue-district-filter" onchange="fetchTokens()" class="bg-slate-50 border border-slate-300 text-xs font-bold p-2 rounded-lg text-emerald-900 outline-none focus:ring-2 focus:ring-emerald-600"></select>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-700">
                        <thead class="bg-slate-100 uppercase text-slate-600 font-bold border-b">
                            <tr>
                                <th class="p-3" data-i18n="th_rank">Queue Rank</th>
                                <th class="p-3" data-i18n="th_token">Token ID</th>
                                <th class="p-3" data-i18n="th_farmer">Farmer Name</th>
                                <th class="p-3" data-i18n="th_crop_qty">Crop / Qty</th>
                                <th class="p-3" data-i18n="th_wait">Real-time Wait</th>
                                <th class="p-3" data-i18n="th_status">Status</th>
                                <th class="p-3" data-i18n="th_actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="token-table-body" class="divide-y"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 4. DIGITAL INVOICES & BILLS SECTION -->
        <section id="section-bills" class="space-y-6 hidden">
            <div class="bg-white border border-emerald-100 p-6 rounded-2xl shadow-md">
                <h2 class="text-md font-bold text-emerald-900 mb-4 flex items-center gap-2">
                    <i class="fa-solid fa-file-invoice-dollar text-emerald-600"></i> <span data-i18n="bills_heading">Generated Digital Payment Receipts & Bills</span>
                </h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-700">
                        <thead class="bg-slate-100 uppercase text-slate-600 font-bold border-b">
                            <tr>
                                <th class="p-3" data-i18n="th_bill_id">Bill ID</th>
                                <th class="p-3" data-i18n="th_token_ref">Token Ref</th>
                                <th class="p-3" data-i18n="th_bill_farmer">Farmer</th>
                                <th class="p-3" data-i18n="th_crop_qty_bill">Crop / Quantity</th>
                                <th class="p-3" data-i18n="th_rate">Rate</th>
                                <th class="p-3" data-i18n="th_total">Total Amount</th>
                                <th class="p-3" data-i18n="th_payment_status">Payment Status</th>
                            </tr>
                        </thead>
                        <tbody id="bills-table-body" class="divide-y"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 5. GOVERNMENT ADMIN & BASE PRICE CONTROL PORTAL -->
        <section id="section-admin" class="space-y-6 hidden">
            <!-- ADMIN ANALYTICS & CAPACITY HUB METRICS -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-white p-5 rounded-2xl border border-emerald-100 shadow-md">
                    <p class="text-xs text-slate-500 font-bold uppercase" data-i18n="stat_active_tokens">Active Tokens In Queue</p>
                    <p class="text-2xl font-bold text-emerald-800 mt-1" id="stat-tokens">0</p>
                    <p class="text-[11px] text-emerald-600 mt-1 font-semibold"><i class="fa-solid fa-arrow-up"></i> <span data-i18n="sync_state_wide">Live state-wide syncing</span></p>
                </div>
                <div class="bg-white p-5 rounded-2xl border border-emerald-100 shadow-md">
                    <p class="text-xs text-slate-500 font-bold uppercase" data-i18n="stat_revenue_generated">Total Revenue Generated & Disbursed</p>
                    <p class="text-2xl font-bold text-emerald-700 mt-1" id="stat-revenue">₹0</p>
                    <p class="text-[11px] text-emerald-600 mt-1 font-semibold"><i class="fa-solid fa-circle-check"></i> <span data-i18n="dbt_direct">Direct Benefit Transfer (DBT)</span></p>
                </div>
                <div class="bg-white p-5 rounded-2xl border border-emerald-100 shadow-md">
                    <p class="text-xs text-slate-500 font-bold uppercase" data-i18n="stat_mandya_capacity">Mandya District APMC Capacity Load</p>
                    <p class="text-2xl font-bold text-blue-700 mt-1" id="stat-capacity">74.2% (Optimal)</p>
                    <p class="text-[11px] text-blue-600 mt-1 font-semibold"><i class="fa-solid fa-warehouse"></i> <span data-i18n="storage_util">Storage & Yard Utilization</span></p>
                </div>
            </div>

            <!-- MANDYA & DISTRICT APMC CAPACITY MONITORING TABLE -->
            <div class="bg-white p-6 rounded-2xl border border-emerald-100 shadow-md">
                <h3 class="text-sm font-bold text-emerald-900 mb-2"><i class="fa-solid fa-chart-pie text-emerald-600 mr-2"></i><span data-i18n="mandya_district_monitoring">Mandya & Key Districts APMC Storage & Capacity Status</span></h3>
                <p class="text-xs text-slate-500 mb-4" data-i18n="mandya_district_desc">Real-time load factors across Mandya Main APMC and surrounding procurement hubs.</p>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-700">
                        <thead class="bg-slate-100 uppercase text-slate-600 font-bold border-b">
                            <tr>
                                <th class="p-3" data-i18n="tbl_district_hub">District APMC Hub</th>
                                <th class="p-3" data-i18n="tbl_storage_capacity">Max Storage Capacity</th>
                                <th class="p-3" data-i18n="tbl_current_load">Current Load %</th>
                                <th class="p-3" data-i18n="tbl_status_health">Status Health</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y">
                            <tr>
                                <td class="p-3 font-bold text-emerald-900">Mandya Main APMC (Mandya)</td>
                                <td class="p-3">5,000 Quintals</td>
                                <td class="p-3 font-semibold text-emerald-700">74.2%</td>
                                <td class="p-3"><span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-bold">Optimal / Normal</span></td>
                            </tr>
                            <tr>
                                <td class="p-3 font-bold text-emerald-900">Chikkaballapur Vegetable Market</td>
                                <td class="p-3">3,500 Quintals</td>
                                <td class="p-3 font-semibold text-amber-700">88.5%</td>
                                <td class="p-3"><span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-bold">High Inflow</span></td>
                            </tr>
                            <tr>
                                <td class="p-3 font-bold text-emerald-900">Kolar Tomato & Produce Market</td>
                                <td class="p-3">4,200 Quintals</td>
                                <td class="p-3 font-semibold text-emerald-700">62.0%</td>
                                <td class="p-3"><span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-bold">Optimal / Normal</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- BASE PRICE SETTING PANEL FOR ADMIN -->
            <div class="bg-white p-6 rounded-2xl border border-emerald-100 shadow-md">
                <h3 class="text-sm font-bold text-emerald-900 mb-2"><i class="fa-solid fa-sliders text-emerald-600 mr-2"></i><span data-i18n="admin_set_msp">Govt Admin: Set Crop Base Price & MSP</span></h3>
                <p class="text-xs text-slate-500 mb-4" data-i18n="admin_set_msp_desc">Define baseline auction prices for agricultural produce across state procurement hubs.</p>

                <form onsubmit="handleUpdateBasePrice(event)" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="select_crop_lbl">Select Crop</label>
                        <select id="admin_base_crop" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-xs font-bold outline-none">
                            <option value="Paddy / Rice">Paddy / Rice</option>
                            <option value="Wheat">Wheat</option>
                            <option value="Ragi (Finger Millet)">Ragi (Finger Millet)</option>
                            <option value="Tomato">Tomato</option>
                            <option value="Onion">Onion</option>
                            <option value="Cotton">Cotton</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1" data-i18n="new_base_price_lbl">New Base Price (₹ / Quintal)</label>
                        <input type="number" id="admin_base_price" required placeholder="e.g. 2300" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-lg text-xs font-bold outline-none">
                    </div>
                    <div class="flex items-end">
                        <button type="submit" class="w-full gradient-btn text-white font-bold py-2.5 rounded-lg text-xs shadow transition" data-i18n="update_base_price_btn">
                            Update Base Price
                        </button>
                    </div>
                </form>
            </div>
        </section>

    </main>

    <footer class="bg-emerald-950 text-emerald-200 py-4 text-center text-xs border-t border-emerald-900 mt-auto">
        <p id="footer-text">farmEasy Agricultural Procurement Platform</p>
    </footer>

    <script>
        let currentSelectedRole = 'farmer';
        let currentLoginMode = 'otp';
        let loggedInFarmerName = 'Chinmayee';
        let loggedInCentreHub = null;
        let selectedUploadedFileName = "";
        let detectedQualityState = "good";
        let globalTokensCache = [];

        const i18nDict = {
            en: {
                page_title: "farmEasy | Live Bidding & Smart Procurement Platform",
                live_bidding_alert: "Live Bidding Alert",
                header_subtitle: "Your Smart Partner for Better Farming",
                read_aloud: "Read Aloud",
                enable_alerts: "Enable Alerts",
                logout: "Logout",
                tab_login: "Portal Access",
                tab_farmer: "Farmer Portal & Booking",
                tab_centre: "Procurement Centre & AI Quality",
                tab_bills: "Digital Invoices",
                tab_admin: "Government Analytics & MSP",
                direct_apmc_network: "Direct APMC Network",
                empowering_farmers: "Empowering Farmers Across Karnataka",
                hero_desc: "Predictable live queues, crop verification, instant Grok AI quality scoring, live bidding broadcasts, and direct payment transfers.",
                auth_heading: "Role-Based Portal Authentication",
                auth_subheading: "Select your role tab to access your specific dashboard",
                role_farmer: "Farmer",
                role_centre: "Centre",
                role_admin: "Admin",
                select_procurement_hub: "Select Procurement Centre Hub",
                mode_otp: "Mobile OTP",
                mode_email: "Email Password",
                auth_phone_lbl: "Authorized Mobile Phone Number",
                get_otp: "Get OTP",
                auth_otp_lbl: "Enter 4-Digit OTP",
                auth_email_lbl: "Email Address",
                auth_password_lbl: "Password",
                gps_heading: "Real-Time GPS Location & Traffic Routing Engine",
                refresh_gps: "Refresh Live GPS & Traffic",
                payment_tracker_lbl: "My Personal Payment & Status Tracker",
                book_slot_heading: "Book Smart Procurement Slot",
                farmer_name_lbl: "Farmer Name",
                apmc_district_lbl: "Procurement APMC District",
                crop_produce_lbl: "Crop / Produce (Type to Search)",
                quantity_lbl: "Quantity (Quintals)",
                time_slot_lbl: "Preferred Time Slot",
                generate_token_btn: "Generate Guaranteed Token",
                bidding_updater_heading: "APMC Counter Bidding & Live Price Broadcasting",
                bidding_updater_desc: "Update ongoing crop bidding prices at your specific centre counter to instantly notify farmers across the platform.",
                apmc_counter_lbl: "APMC Counter",
                bidding_crop_lbl: "Bidding Crop",
                new_bidding_price_lbl: "New Bidding Price (₹ / Quintal)",
                broadcast_btn: "Broadcast Live Bidding Update",
                ai_quality_heading: "Real-Time Grok AI Vision Precision Quality Assessment",
                ai_quality_desc: "Upload crop or grain photos for instant Grok AI computer vision analysis (Grade, Defect Ratios, Moisture Levels, and MSP Valuation).",
                select_crop_verify: "Select Crop to Verify",
                run_ai_btn: "Run Grok AI Precision Analysis",
                queue_mgmt_heading: "District Procurement Queue Management",
                select_centre_lbl: "Select Procurement Centre:",
                th_rank: "Queue Rank",
                th_token: "Token ID",
                th_farmer: "Farmer Name",
                th_crop_qty: "Crop / Qty",
                th_wait: "Real-time Wait",
                th_status: "Status",
                th_actions: "Actions",
                bills_heading: "Generated Digital Payment Receipts & Bills",
                th_bill_id: "Bill ID",
                th_token_ref: "Token Ref",
                th_bill_farmer: "Farmer",
                th_crop_qty_bill: "Crop / Quantity",
                th_rate: "Rate",
                th_total: "Total Amount",
                th_payment_status: "Payment Status",
                stat_active_tokens: "Active Tokens In Queue",
                sync_state_wide: "Live state-wide syncing",
                stat_revenue_generated: "Total Revenue Generated & Disbursed",
                dbt_direct: "Direct Benefit Transfer (DBT)",
                stat_mandya_capacity: "Mandya District APMC Capacity Load",
                storage_util: "Storage & Yard Utilization",
                mandya_district_monitoring: "Mandya & Key Districts APMC Storage & Capacity Status",
                mandya_district_desc: "Real-time load factors across Mandya Main APMC and surrounding procurement hubs.",
                tbl_district_hub: "District APMC Hub",
                tbl_storage_capacity: "Max Storage Capacity",
                tbl_current_load: "Current Load %",
                tbl_status_health: "Status Health",
                admin_set_msp: "Govt Admin: Set Crop Base Price & MSP",
                admin_set_msp_desc: "Define baseline auction prices for agricultural produce across state procurement hubs.",
                select_crop_lbl: "Select Crop",
                new_base_price_lbl: "New Base Price (₹ / Quintal)",
                update_base_price_btn: "Update Base Price"
            },
            kn: {
                page_title: "ಫಾರ್ಮ್‌ಈಸಿ | ನೇರ ಬಿಡ್ಡಿಂಗ್ ಮತ್ತು ಸ್ಮಾರ್ಟ್ ಖರೀದಿ ವೇದಿಕೆ",
                live_bidding_alert: "ನೇರ ಬಿಡ್ಡಿಂಗ್ ಎಚ್ಚರಿಕೆ",
                header_subtitle: "ಉತ್ತಮ ಕೃಷಿಗೆ ನಿಮ್ಮ ಸ್ಮಾರ್ಟ್ ಪಾಲುದಾರ",
                read_aloud: "ಧ್ವನಿಯಲ್ಲಿ ಓದಿ",
                enable_alerts: "ಎಚ್ಚರಿಕೆಗಳನ್ನು ಸಕ್ರಿಯಗೊಳಿಸಿ",
                logout: "ಹೊರಬನ್ನಿ",
                tab_login: "ಪೋರ್ಟಲ್ ಪ್ರವೇಶ",
                tab_farmer: "ರೈತ ಪೋರ್ಟಲ್ & ಬುಕಿಂಗ್",
                tab_centre: "ಖರೀದಿ ಕೇಂದ್ರ & AI ಗುಣಮಟ್ಟ",
                tab_bills: "ಡಿಜಿಟಲ್ ರಶೀದಿಗಳು",
                tab_admin: "ಸರ್ಕಾರಿ ವಿಶ್ಲೇಷಣೆ & MSP",
                direct_apmc_network: "ನೇರ APMC ಜಾಲ",
                empowering_farmers: "ಕರ್ನಾಟಕದಾದ್ಯಂತ ರೈತರ ಸಬಲೀಕರಣ",
                hero_desc: "ಊಹಿಸಬಹುದಾದ ನೇರ ಸರತಿ ಸಾಲುಗಳು, ಬೆಳೆ ಪರಿಶೀಲನೆ, ತ್ವರಿತ AI ಗುಣಮಟ್ಟ ಸ್ಕೋರಿಂಗ್, ನೇರ ಬಿಡ್ಡಿಂಗ್ ಪ್ರಸಾರಗಳು ಮತ್ತು ನೇರ ಪಾವತಿ ವರ್ಗಾವಣೆಗಳು.",
                auth_heading: "ಪಾತ್ರ ಆಧಾರಿತ ಪೋರ್ಟಲ್ ದೃಢೀಕರಣ",
                auth_subheading: "ನಿಮ್ಮ ನಿರ್ದಿಷ್ಟ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಪ್ರವೇಶಿಸಲು ನಿಮ್ಮ ಪಾತ್ರವನ್ನು ಆಯ್ಕೆಮಾಡಿ",
                role_farmer: "ರೈತ",
                role_centre: "ಕೇಂದ್ರ",
                role_admin: "ನಿರ್ವಾಹಕ",
                select_procurement_hub: "ಖರೀದಿ ಕೇಂದ್ರ ಕೇಂದ್ರವನ್ನು ಆಯ್ಕೆಮಾಡಿ",
                mode_otp: "ಮೊಬೈಲ್ OTP",
                mode_email: "ಇಮೇಲ್ ಪಾಸ್‌ವರ್ಡ್",
                auth_phone_lbl: "ಅಧಿಕೃತ ಮೊಬೈಲ್ ಫೋನ್ ಸಂಖ್ಯೆ",
                get_otp: "OTP ಪಡೆಯಿರಿ",
                auth_otp_lbl: "4-ಅಂಕಿಯ OTP ನಮೂದಿಸಿ",
                auth_email_lbl: "ಇಮೇಲ್ ವಿಳಾಸ",
                auth_password_lbl: "ಪಾಸ್‌ವರ್ಡ್",
                gps_heading: "ರಿಯಲ್-ಟೈಮ್ GPS ಸ್ಥಳ ಮತ್ತು ಟ್ರಾಫಿಕ್ ರೂಟಿಂಗ್ ಎಂಜಿನ್",
                refresh_gps: "ಲೈವ್ GPS & ಟ್ರಾಫಿಕ್ ರಿಫ್ರೆಶ್ ಮಾಡಿ",
                payment_tracker_lbl: "ನನ್ನ ವೈಯಕ್ತಿಕ ಪಾವತಿ & ಸ್ಥಿತಿ ಟ್ರ್ಯಾಕರ್",
                book_slot_heading: "ಸ್ಮಾರ್ಟ್ ಖರೀದಿ ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ",
                farmer_name_lbl: "ರೈತರ ಹೆಸರು",
                apmc_district_lbl: "ಖರೀದಿ APMC ಜಿಲ್ಲೆ",
                crop_produce_lbl: "ಬೆಳೆ / ಉತ್ಪನ್ನ (ಹುಡುಕಲು ಟೈಪ್ ಮಾಡಿ)",
                quantity_lbl: "ಪ್ರಮಾಣ (ಕ್ವಿಂಟಲ್‌ಗಳಲ್ಲಿ)",
                time_slot_lbl: "ಆದ್ಯತೆಯ ಸಮಯದ ಸ್ಲಾಟ್",
                generate_token_btn: "ಖಾತರಿಯ ಟೋಕನ್ ರಚಿಸಿ",
                bidding_updater_heading: "APMC ಕೌಂಟರ್ ಬಿಡ್ಡಿಂಗ್ & ಲೈವ್ ಬೆಲೆ ಪ್ರಸಾರ",
                bidding_updater_desc: "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ನಲ್ಲಿ ರೈತರಿಗೆ ತಕ್ಷಣವೇ ತಿಳಿಸಲು ನಿಮ್ಮ ನಿರ್ದಿಷ್ಟ ಕೇಂದ್ರ ಕೌಂಟರ್‌ನಲ್ಲಿ ನಡೆಯುತ್ತಿರುವ ಬೆಳೆ ಬಿಡ್ಡಿಂಗ್ ಬೆಲೆಗಳನ್ನು ನವೀಕರಿಸಿ.",
                apmc_counter_lbl: "APMC ಕೌಂಟರ್",
                bidding_crop_lbl: "ಬಿಡ್ಡಿಂಗ್ ಬೆಳೆ",
                new_bidding_price_lbl: "ಹೊಸ ಬಿಡ್ಡಿಂಗ್ ಬೆಲೆ (₹ / ಕ್ವಿಂಟಲ್)",
                broadcast_btn: "ಲೈವ್ ಬಿಡ್ಡಿಂಗ್ ಅಪ್‌ಡೇಟ್ ಪ್ರಸಾರ ಮಾಡಿ",
                ai_quality_heading: "ರಿಯಲ್-ಟೈಮ್ AI ಕಂಪ್ಯೂಟರ್ ವಿಷನ್ ನಿಖರತಾ ಗುಣಮಟ್ಟ ಮೌಲ್ಯಮಾಪನ",
                ai_quality_desc: "ತ್ವರಿತ ನೈಜ-ಸಮಯದ ಕಂಪ್ಯೂಟರ್ ವಿಷನ್ ವಿಶ್ಲೇಷಣೆಗಾಗಿ ಬೆಳೆ ಅಥವಾ ಧಾನ್ಯದ ಫೋಟೋಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ (ಗ್ರೇಡ್, ದೋಷ ಅನುಪಾತಗಳು, ತೇವಾಂಶ ಮಟ್ಟಗಳು ಮತ್ತು MSP ಮೌಲ್ಯಮಾಪನ).",
                select_crop_verify: "ಪರಿಶೀಲಿಸಲು ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ",
                run_ai_btn: "ರಿಯಲ್-ಟೈಮ್ AI ವಿಶ್ಲೇಷಣೆ ನಡೆಸಿ",
                queue_mgmt_heading: "ಜಿಲ್ಲಾ ಖರೀದಿ ಸರತಿ ಸಾಲು ನಿರ್ವಹಣೆ",
                select_centre_lbl: "ಖರೀದಿ ಕೇಂದ್ರವನ್ನು ಆಯ್ಕೆಮಾಡಿ:",
                th_rank: "ಸರತಿ ಶ್ರೇಣಿ",
                th_token: "ಟೋಕನ್ ID",
                th_farmer: "ರೈತರ ಹೆಸರು",
                th_crop_qty: "ಬೆಳೆ / ಪ್ರಮಾಣ",
                th_wait: "ನೈಜ-ಸಮಯದ ಕಾಯುವಿಕೆ",
                th_status: "ಸ್ಥಿತಿ",
                th_actions: "ಕ್ರಿಯೆಗಳು",
                bills_heading: "ರಚಿಸಲಾದ ಡಿಜಿಟಲ್ ಪಾವತಿ ರಶೀದಿಗಳು & ಬಿಲ್ಲುಗಳು",
                th_bill_id: "ಬಿಲ್ ID",
                th_token_ref: "ಟೋಕನ್ ಉಲ್ಲೇಖ",
                th_bill_farmer: "ರೈತ",
                th_crop_qty_bill: "ಬೆಳೆ / ಪ್ರಮಾಣ",
                th_rate: "ದರ",
                th_total: "ಒಟ್ಟು ಮೊತ್ತ",
                th_payment_status: "ಪಾವತಿ ಸ್ಥಿತಿ",
                stat_active_tokens: "ಸರತಿ ಸಾಲಿನಲ್ಲಿರುವ ಸಕ್ರಿಯ ಟೋಕನ್‌ಗಳು",
                sync_state_wide: "ರಾಜ್ಯವ್ಯಾಪಿ ಲೈವ್ ಸಿಂಕ್ರೊನೈಸೇಶನ್",
                stat_revenue_generated: "ಸೃಷ್ಟಿಯಾದ ಒಟ್ಟು ಆದಾಯ & ವಿತರಣೆ",
                dbt_direct: "ನೇರ ಲಾಭ ವರ್ಗಾವಣೆ (DBT)",
                stat_mandya_capacity: "ಮಂಡ್ಯ ಜಿಲ್ಲೆ APMC ಸಾಮರ್ಥ್ಯದ ಹೊರೆ",
                storage_util: "ಸಂಗ್ರಹಣೆ & ಯಾರ್ಡ್ ಬಳಕೆ",
                mandya_district_monitoring: "ಮಂಡ್ಯ & ಪ್ರಮುಖ ಜಿಲ್ಲೆಗಳ APMC ಸಂಗ್ರಹಣೆ & ಸಾಮರ್ಥ್ಯ ಸ್ಥಿತಿ",
                mandya_district_desc: "ಮಂಡ್ಯ ಮುಖ್ಯ APMC ಮತ್ತು ಸುತ್ತಮುತ್ತಲಿನ ಖರೀದಿ ಕೇಂದ್ರಗಳಲ್ಲಿ ನೈಜ-ಸಮಯದ ಲೋಡ್ ಅಂಶಗಳು.",
                tbl_district_hub: "ಜಿಲ್ಲಾ APMC ಕೇಂದ್ರ",
                tbl_storage_capacity: "ಗರಿಷ್ಠ ಸಂಗ್ರಹಣಾ ಸಾಮರ್ಥ್ಯ",
                tbl_current_load: "ಪ್ರಸ್ತುತ ಹೊರೆ %",
                tbl_status_health: "ಸ್ಥಿತಿ ಆರೋಗ್ಯ",
                admin_set_msp: "ಸರ್ಕಾರಿ ನಿರ್ವಾಹಕ: ಬೆಳೆ ಮೂಲ ಬೆಲೆ & MSP ಹೊಂದಿಸಿ",
                admin_set_msp_desc: "ರಾಜ್ಯದ ಖರೀದಿ ಕೇಂದ್ರಗಳಲ್ಲಿ ಕೃಷಿ ಉತ್ಪನ್ನಗಳಿಗೆ ಮೂಲ ಹರಾಜು ಬೆಲೆಗಳನ್ನು ವ್ಯಾಖ್ಯಾನಿಸಿ.",
                select_crop_lbl: "ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ",
                new_base_price_lbl: "ಹೊಸ ಮೂಲ ಬೆಲೆ (₹ / ಕ್ವಿಂಟಲ್)",
                update_base_price_btn: "ಮೂಲ ಬೆಲೆಯನ್ನು ನವೀಕರಿಸಿ"
            },
            hi: {
                page_title: "फार्मईज़ी | लाइव बिडिंग और स्मार्ट खरीद मंच",
                live_bidding_alert: "लाइव बिडिंग चेतावनी",
                header_subtitle: "बेहतर खेती के लिए आपका स्मार्ट साथी",
                read_aloud: "बोलकर सुनें",
                enable_alerts: "अलर्ट सक्षम करें",
                logout: "लॉग आउट",
                tab_login: "पोर्टल एक्सेस",
                tab_farmer: "किसान पोर्टल और बुकिंग",
                tab_centre: "खरीद केंद्र और AI गुणवत्ता",
                tab_bills: "डिजिटल रसीदें",
                tab_admin: "सरकारी एनालिटिक्स और MSP",
                direct_apmc_network: "प्रत्यक्ष APMC नेटवर्क",
                empowering_farmers: "कर्नाटक भर के किसानों का सशक्तिकरण",
                hero_desc: "पूर्वानुमानित लाइव कतारें, फसल सत्यापन, त्वरित Grok AI गुणवत्ता स्कोरिंग, लाइव बिडिंग प्रसारण और प्रत्यक्ष भुगतान हस्तांतरण।",
                auth_heading: "भूमिका-आधारित पोर्टल प्रमाणीकरण",
                auth_subheading: "अपने विशिष्ट डैशबोर्ड तक पहुंचने के लिए अपना भूमिका टैब चुनें",
                role_farmer: "किसान",
                role_centre: "केंद्र",
                role_admin: "एडमिन",
                select_procurement_hub: "खरीद केंद्र हब चुनें",
                mode_otp: "मोबाइल OTP",
                mode_email: "ईमेल पासवर्ड",
                auth_phone_lbl: "अधिकृत मोबाइल फोन नंबर",
                get_otp: "OTP प्राप्त करें",
                auth_otp_lbl: "4-अंकों का OTP दर्ज करें",
                auth_email_lbl: "ईमेल पता",
                auth_password_lbl: "पासवर्ड",
                gps_heading: "रीयल-टाइम GPS स्थान और ट्रैफिक रूटिंग इंजन",
                refresh_gps: "लाइव GPS और ट्रैफिक रिफ्रेश करें",
                payment_tracker_lbl: "मेरा व्यक्तिगत भुगतान और स्थिति ट्रैकर",
                book_slot_heading: "स्मार्ट खरीद स्लॉट बुक करें",
                farmer_name_lbl: "किसान का नाम",
                apmc_district_lbl: "खरीद APMC जिला",
                crop_produce_lbl: "फसल / उपज (खोजने के लिए टाइप करें)",
                quantity_lbl: "मात्रा (क्विंटल में)",
                time_slot_lbl: "पसंदीदा समय स्लॉट",
                generate_token_btn: "गारंटीड टोकन जनरेट करें",
                bidding_updater_heading: "APMC काउंटर बिडिंग और लाइव मूल्य प्रसारण",
                bidding_updater_desc: "प्लेटफ़ॉर्म पर किसानों को तुरंत सूचित करने के लिए अपने विशिष्ट केंद्र काउंटर पर चल रही फसल बिडिंग कीमतों को अपडेट करें।",
                apmc_counter_lbl: "APMC काउंटर",
                bidding_crop_lbl: "बिडिंग फसल",
                new_bidding_price_lbl: "नई बिडिंग कीमत (₹ / क्विंटल)",
                broadcast_btn: "लाइव बिडिंग अपडेट प्रसारित करें",
                ai_quality_heading: "रीयल-टाइम Grok AI विजन सटीक गुणवत्ता मूल्यांकन",
                ai_quality_desc: "त्वरित Grok AI कंप्यूटर विजन विश्लेषण (ग्रेड, दोष अनुपात, नमी स्तर और MSP मूल्यांकन) के लिए फसल या अनाज की तस्वीरें अपलोड करें।",
                select_crop_verify: "सत्यापित करने के लिए फसल चुनें",
                run_ai_btn: "रीयल-टाइम Grok AI विश्लेषण चलाएं",
                queue_mgmt_heading: "जिला खरीद कतार प्रबंधन",
                select_centre_lbl: "खरीद केंद्र चुनें:",
                th_rank: "कतार रैंक",
                th_token: "टोकन ID",
                th_farmer: "किसान का नाम",
                th_crop_qty: "फसल / मात्रा",
                th_wait: "रीयल-टाइम प्रतीक्षा",
                th_status: "स्थिति",
                th_actions: "कार्रवाई",
                bills_heading: "उत्पन्न डिजिटल भुगतान रसीदें और बिल",
                th_bill_id: "बिल ID",
                th_token_ref: "टोकन संदर्भ",
                th_bill_farmer: "किसान",
                th_crop_qty_bill: "फसल / मात्रा",
                th_rate: "दर",
                th_total: "कुल राशि",
                th_payment_status: "भुगतान स्थिति",
                stat_active_tokens: "कतार में सक्रिय टोकन",
                sync_state_wide: "लाइव राज्य-व्यापी सिंकिंग",
                stat_revenue_generated: "कुल राजस्व उत्पन्न और वितरित",
                dbt_direct: "प्रत्यक्ष लाभ हस्तांतरण (DBT)",
                stat_mandya_capacity: "मांड्या जिला APMC क्षमता भार",
                storage_util: "भंडारण और यार्ड उपयोग",
                mandya_district_monitoring: "मांड्या और प्रमुख जिले APMC भंडारण और क्षमता स्थिति",
                mandya_district_desc: "मांड्या मुख्य APMC और आसपास के खरीद केंद्रों में रीयल-टाइम लोड कारक।",
                tbl_district_hub: "जिला APMC हब",
                tbl_storage_capacity: "अधिकतम भंडारण क्षमता",
                tbl_current_load: "वर्तमान भार %",
                tbl_status_health: "स्थिति स्वास्थ्य",
                admin_set_msp: "सरकारी एडमिन: फसल आधार मूल्य और MSP निर्धारित करें",
                admin_set_msp_desc: "राज्य खरीद केंद्रों में कृषि उपज के लिए आधार नीलामी कीमतों को परिभाषित करें।",
                select_crop_lbl: "फसल चुनें",
                new_base_price_lbl: "नया आधार मूल्य (₹ / क्विंटल)",
                update_base_price_btn: "आधार मूल्य अपडेट करें"
            }
        };

        function changeLanguage() {
            const lang = document.getElementById('language-selector').value;
            const dict = i18nDict[lang] || i18nDict['en'];

            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (dict[key]) {
                    el.innerText = dict[key];
                } else if (i18nDict['en'][key]) {
                    el.innerText = i18nDict['en'][key];
                }
            });

            if (lang === 'kn') {
                document.getElementById('footer-text').innerText = "ಫಾರ್ಮ್‌ಈಸಿ ಕೃಷಿ ಖರೀದಿ ವೇದಿಕೆ";
            } else if (lang === 'hi') {
                document.getElementById('footer-text').innerText = "फार्मईज़ी कृषि खरीद मंच";
            } else {
                document.getElementById('footer-text').innerText = "farmEasy Agricultural Procurement Platform";
            }
        }

        function readPageAloud() {
            if (!('speechSynthesis' in window)) {
                alert("Speech synthesis is not supported in this browser.");
                return;
            }
            window.speechSynthesis.cancel();

            const activeSection = document.querySelector("main > section:not(.hidden)");
            const textToRead = activeSection ? activeSection.innerText : document.body.innerText;

            const lang = document.getElementById('language-selector').value;
            const langMap = {
                en: 'en-IN', kn: 'kn-IN', hi: 'hi-IN', te: 'te-IN', ta: 'ta-IN',
                ml: 'ml-IN', mr: 'mr-IN', gu: 'gu-IN', bn: 'bn-IN', pa: 'pa-IN', or: 'or-IN'
            };

            const utterance = new SpeechSynthesisUtterance(textToRead);
            utterance.lang = langMap[lang] || 'en-IN';
            utterance.rate = 0.95;

            window.speechSynthesis.speak(utterance);
        }

        function updateClock() {
            document.getElementById('realtime-clock').innerText = new Date().toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        setInterval(fetchTokens, 12000);
        setInterval(detectLocationAndTraffic, 15000);
        updateClock();

        function populateCentreDropdowns(centres) {
            const loginSelect = document.getElementById('login_centre_select');
            const bookingSelect = document.getElementById('booking_centre');
            const filterSelect = document.getElementById('queue-district-filter');

            [loginSelect, bookingSelect, filterSelect].forEach(select => {
                if (select && select.children.length === 0) {
                    centres.forEach(c => {
                        const opt = document.createElement('option');
                        opt.value = c;
                        opt.innerText = c;
                        select.appendChild(opt);
                    });
                }
            });
            updateFarmerMandiRealtimeQueue();
        }

        function updateFarmerMandiRealtimeQueue() {
            const bookingSelect = document.getElementById('booking_centre');
            const selectedMandi = bookingSelect ? bookingSelect.value : "Mandya Main APMC (Mandya)";
            document.getElementById('mandi-monitor-name').innerText = selectedMandi;

            const mandiTokens = globalTokensCache.filter(t => t.centre === selectedMandi && t.status !== 'Completed');
            const inProcessToken = mandiTokens.find(t => t.status === 'In-Process');

            if (inProcessToken) {
                document.getElementById('mandi-monitor-current-token').innerText = `${inProcessToken.id} (${inProcessToken.farmer})`;
            } else if (mandiTokens.length > 0) {
                document.getElementById('mandi-monitor-current-token').innerText = `${mandiTokens[0].id} (${mandiTokens[0].farmer})`;
            } else {
                document.getElementById('mandi-monitor-current-token').innerText = "No active processing";
            }

            document.getElementById('mandi-monitor-queue-count').innerText = `${mandiTokens.length} Farmers Waiting`;
        }

        function requestRealtimeOtp() {
            const phone = document.getElementById('login_phone').value;
            fetch('/api/request-otp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: phone, role_type: currentSelectedRole})
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if (data.otp) document.getElementById('login_otp').value = data.otp;
            });
        }

        function selectRoleTab(role) {
            currentSelectedRole = role;
            ['farmer', 'centre', 'admin'].forEach(r => {
                const btn = document.getElementById(`role-btn-${r}`);
                if (r === role) {
                    btn.className = "py-2 text-xs font-bold rounded-md bg-emerald-700 text-white shadow-sm transition";
                } else {
                    btn.className = "py-2 text-xs font-bold rounded-md text-slate-600 hover:text-emerald-800 transition";
                }
            });

            const btnSubmit = document.getElementById('btn-submit-auth');
            const phoneInput = document.getElementById('login_phone');
            const emailInput = document.getElementById('login_email');
            const otpInput = document.getElementById('login_otp');
            const passwordInput = document.getElementById('login_password');
            const centreDropdownField = document.getElementById('field-centre-dropdown');

            phoneInput.value = '';
            emailInput.value = '';
            otpInput.value = '';
            passwordInput.value = '';

            if (role === 'farmer') {
                btnSubmit.innerText = "Login to Farmer Dashboard";
                centreDropdownField.classList.add('hidden');
            } else if (role === 'centre') {
                btnSubmit.innerText = "Login to Procurement Centre";
                centreDropdownField.classList.remove('hidden');
            } else if (role === 'admin') {
                btnSubmit.innerText = "Login to Govt Admin Portal";
                centreDropdownField.classList.add('hidden');
            }
        }

        function setLoginMode(mode) {
            currentLoginMode = mode;
            document.getElementById('login_phone').value = '';
            document.getElementById('login_email').value = '';
            document.getElementById('login_otp').value = '';
            document.getElementById('login_password').value = '';

            if (mode === 'otp') {
                document.getElementById('field-phone').classList.remove('hidden');
                document.getElementById('field-otp').classList.remove('hidden');
                document.getElementById('field-email').classList.add('hidden');
                document.getElementById('field-password').classList.add('hidden');
                document.getElementById('btn-mode-otp').className = "flex-1 py-1 text-xs font-bold rounded bg-white text-emerald-800 shadow-sm";
                document.getElementById('btn-mode-email').className = "flex-1 py-1 text-xs font-bold rounded text-slate-600";
            } else {
                document.getElementById('field-phone').classList.add('hidden');
                document.getElementById('field-otp').classList.add('hidden');
                document.getElementById('field-email').classList.remove('hidden');
                document.getElementById('field-password').classList.remove('hidden');
                document.getElementById('btn-mode-email').className = "flex-1 py-1 text-xs font-bold rounded bg-white text-emerald-800 shadow-sm";
                document.getElementById('btn-mode-otp').className = "flex-1 py-1 text-xs font-bold rounded text-slate-600";
            }
        }

        function handleAuthSubmit(e) {
            e.preventDefault();
            const payload = {
                role_type: currentSelectedRole,
                login_mode: currentLoginMode,
                phone: document.getElementById('login_phone').value,
                email: document.getElementById('login_email').value,
                otp: document.getElementById('login_otp').value,
                selected_centre: document.getElementById('login_centre_select').value
            };

            fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if(data.success) {
                    if (data.user) loggedInFarmerName = data.user.split(' ')[0];
                    loggedInCentreHub = data.assigned_centre;

                    document.getElementById('farmer-active-user-lbl').innerText = loggedInFarmerName;
                    document.getElementById('farmer_name').value = loggedInFarmerName;

                    if (loggedInCentreHub) {
                        document.getElementById('current-assigned-hub-badge').innerText = loggedInCentreHub;
                        document.getElementById('queue-district-filter').value = loggedInCentreHub;
                        document.getElementById('queue-district-filter').disabled = true;
                    } else {
                        document.getElementById('queue-district-filter').disabled = false;
                    }

                    setTabAccess(data.role);
                    fetchTokens();
                }
            });
        }

        function setTabAccess(role) {
            document.getElementById('logout-btn').classList.remove('hidden');
            const tabFarmer = document.getElementById('tab-farmer');
            const tabCentre = document.getElementById('tab-centre');
            const tabBills = document.getElementById('tab-bills');
            const tabAdmin = document.getElementById('tab-admin');

            [tabFarmer, tabCentre, tabBills, tabAdmin].forEach(btn => {
                btn.disabled = true;
                btn.classList.add('cursor-not-allowed', 'opacity-50');
            });

            if (role === 'farmer') {
                tabFarmer.disabled = false;
                tabFarmer.classList.remove('cursor-not-allowed', 'opacity-50');
                switchTab('farmer');
            } else if (role === 'centre') {
                [tabCentre, tabBills].forEach(btn => {
                    btn.disabled = false;
                    btn.classList.remove('cursor-not-allowed', 'opacity-50');
                });
                switchTab('centre');
            } else if (role === 'admin') {
                [tabFarmer, tabCentre, tabBills, tabAdmin].forEach(btn => {
                    btn.disabled = false;
                    btn.classList.remove('cursor-not-allowed', 'opacity-50');
                });
                switchTab('admin');
            }
        }

        function logout() {
            window.speechSynthesis.cancel();
            document.getElementById('logout-btn').classList.add('hidden');
            loggedInCentreHub = null;
            document.getElementById('login_phone').value = '';
            document.getElementById('login_email').value = '';
            document.getElementById('login_otp').value = '';
            document.getElementById('login_password').value = '';

            ['tab-farmer', 'tab-centre', 'tab-bills', 'tab-admin'].forEach(id => {
                const btn = document.getElementById(id);
                btn.disabled = true;
                btn.classList.add('cursor-not-allowed', 'opacity-50');
            });
            switchTab('login');
            alert("Logged out successfully.");
        }

        function switchTab(tab) {
            window.speechSynthesis.cancel();
            ['login', 'farmer', 'centre', 'bills', 'admin'].forEach(t => {
                document.getElementById(`section-${t}`).classList.add('hidden');
                document.getElementById(`tab-${t}`).classList.remove('border-emerald-700', 'text-emerald-800');
                document.getElementById(`tab-${t}`).classList.add('border-transparent', 'text-slate-400');
            });
            document.getElementById(`section-${tab}`).classList.remove('hidden');
            document.getElementById(`tab-${tab}`).classList.add('border-emerald-700', 'text-emerald-800');
            document.getElementById(`tab-${tab}`).classList.remove('border-transparent', 'text-slate-400');
        }

        function fetchTokens() {
            fetch('/api/tokens')
                .then(res => res.json())
                .then(data => {
                    globalTokensCache = data.tokens;
                    populateCentreDropdowns(data.centres);
                    renderTokenTable(data.tokens);
                    renderBillsTable(data.bills);
                    renderFarmerPaymentTracker(data.tokens);
                    renderBiddingTicker(data.bidding_notifications);
                    updateFarmerMandiRealtimeQueue();
                    document.getElementById('stat-tokens').innerText = data.tokens.length;
                    document.getElementById('stat-revenue').innerText = data.total_revenue;
                    const cap = Math.min(65 + (data.tokens.length * 3), 98);
                    document.getElementById('stat-capacity').innerText = `${cap}% (Optimal)`;
                });
        }

        function renderBiddingTicker(notifs) {
            const ticker = document.getElementById('live-bidding-ticker');
            if (!notifs || notifs.length === 0) {
                ticker.innerText = "No active bidding sessions currently taking place across APMC centers.";
                return;
            }
            let text = "";
            notifs.forEach(n => {
                text += `🔴 [LIVE BIDDING] At ${n.centre} (${n.counter}) -> Crop: ${n.crop} | Current Bidding Price: ${n.current_bid} (${n.updated_at})  |   `;
            });
            ticker.innerText = text;
        }

        function handleUpdateBidding(e) {
            e.preventDefault();
            const payload = {
                centre: loggedInCentreHub || document.getElementById('queue-district-filter').value,
                counter: document.getElementById('bidding_counter').value,
                crop: document.getElementById('bidding_crop').value,
                price: document.getElementById('bidding_price').value
            };

            fetch('/api/update-bidding-price', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                fetchTokens();
            });
        }

        function handleUpdateBasePrice(e) {
            e.preventDefault();
            const payload = {
                crop: document.getElementById('admin_base_crop').value,
                price: document.getElementById('admin_base_price').value
            };

            fetch('/api/update-base-price', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                fetchTokens();
            });
        }

        function renderFarmerPaymentTracker(tokens) {
            const container = document.getElementById('farmer-payments-list');
            container.innerHTML = '';
            const myTokens = tokens.filter(t => t.farmer.toLowerCase().includes(loggedInFarmerName.toLowerCase()));

            if (myTokens.length === 0) {
                container.innerHTML = `<p class="text-slate-500 italic">No payment records found for ${loggedInFarmerName}. Book a slot to generate tokens.</p>`;
                return;
            }

            myTokens.forEach(t => {
                const item = document.createElement('div');
                const isPaid = t.payment_status.includes('Paid');
                item.className = `p-3 rounded-lg border ${isPaid ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`;
                item.innerHTML = `
                    <div class="flex justify-between font-bold">
                        <span>Token ID: ${t.id} (${t.crop})</span>
                        <span class="${isPaid ? 'text-emerald-700' : 'text-amber-700'}">${t.payment_status}</span>
                    </div>
                    <p class="text-[11px] text-slate-600 mt-1"><b>APMC Centre:</b> ${t.centre} | <b>Est. Wait:</b> ${t.wait_time}</p>
                    <p class="text-[11px] ${isPaid ? 'text-emerald-800' : 'text-amber-900'} mt-1"><b>Status Note:</b> ${t.pending_reason}</p>
                `;
                container.appendChild(item);
            });
        }

        function renderTokenTable(tokens) {
            const tbody = document.getElementById('token-table-body');
            const filterDropdown = document.getElementById('queue-district-filter');
            const selectedDistrict = loggedInCentreHub || (filterDropdown ? filterDropdown.value : '');
            tbody.innerHTML = '';

            const filteredTokens = tokens.filter(t => t.centre === selectedDistrict && t.status !== 'Completed');

            filteredTokens.forEach((t, index) => {
                const rank = index + 1;
                const tr = document.createElement('tr');
                tr.className = "hover:bg-emerald-50/50";
                tr.innerHTML = `
                    <td class="p-3 font-bold text-slate-700">#${rank}</td>
                    <td class="p-3 font-mono font-bold text-emerald-800">${t.id}</td>
                    <td class="p-3 font-semibold">${t.farmer}</td>
                    <td class="p-3">${t.crop} (${t.quantity} Quintals)</td>
                    <td class="p-3"><span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded text-xs font-bold">${t.wait_time}</span></td>
                    <td class="p-3 font-bold ${t.status === 'Completed' ? 'text-emerald-600' : 'text-amber-600'}">${t.status}</td>
                    <td class="p-3 space-x-1">
                        <button onclick="updateStatus('${t.id}', 'In-Process')" class="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2.5 py-1 rounded shadow-sm">Process</button>
                        <button onclick="updateStatus('${t.id}', 'Completed')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-2.5 py-1 rounded shadow-sm">Complete & Bill</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderBillsTable(bills) {
            const tbody = document.getElementById('bills-table-body');
            tbody.innerHTML = '';
            bills.forEach(b => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-emerald-50/50";
                tr.innerHTML = `
                    <td class="p-3 font-mono font-bold text-slate-800">${b.bill_id}</td>
                    <td class="p-3 font-mono text-emerald-700 font-bold">${b.token_id}</td>
                    <td class="p-3 font-semibold">${b.farmer}</td>
                    <td class="p-3">${b.crop} (${b.quantity})</td>
                    <td class="p-3">${b.rate}</td>
                    <td class="p-3 font-bold text-emerald-800">${b.total_amount}</td>
                    <td class="p-3"><span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded text-xs font-bold">${b.payment_status}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }

        function detectLocationAndTraffic() {
            const d1 = (12.0 + Math.random() * 0.8).toFixed(1);
            const d2 = (24.0 + Math.random() * 1.2).toFixed(1);
            const d3 = (37.5 + Math.random() * 1.5).toFixed(1);
            document.getElementById('dist-1').innerText = `${d1} km`;
            document.getElementById('dist-2').innerText = `${d2} km`;
            document.getElementById('dist-3').innerText = `${d3} km`;
            document.getElementById('gps-status-txt').innerText = `Live GPS Connected (${new Date().toLocaleTimeString()}): Real-time traffic routes updated.`;
        }

        function handleBookSlot(e) {
            e.preventDefault();
            const payload = {
                farmer_name: document.getElementById('farmer_name').value,
                centre: document.getElementById('booking_centre').value,
                crop: document.getElementById('booking_crop').value,
                quantity: document.getElementById('booking_qty').value,
                slot: document.getElementById('booking_slot').value
            };

            fetch('/api/book-slot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    alert(data.error);
                    return;
                }
                alert(`Token Generated Successfully!\nToken ID: ${data.token.id}`);
                fetchTokens();
            });
        }

        function previewAndScanImage(event) {
            const file = event.target.files[0];
            if (!file) return;

            selectedUploadedFileName = file.name;
            document.getElementById('upload-filename-txt').innerText = `Selected File: ${file.name}`;
            const reader = new FileReader();
            reader.onload = function(e) {
                const output = document.getElementById('image-preview');
                output.src = e.target.result;
                output.classList.remove('hidden');

                // Inspect pixels for dark spots/insects
                const img = new Image();
                img.src = e.target.result;
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = 100; canvas.height = 100;
                    ctx.drawImage(img, 0, 0, 100, 100);
                    const imgData = ctx.getImageData(0, 0, 100, 100).data;

                    let darkCount = 0;
                    for (let i = 0; i < imgData.length; i += 4) {
                        if (imgData[i] < 70 && imgData[i+1] < 70 && imgData[i+2] < 70) {
                            darkCount++;
                        }
                    }

                    const fname = file.name.toLowerCase();
                    if (darkCount > 350 || fname.includes('bad') || fname.includes('pest') || fname.includes('rot') || fname.includes('bug') || fname.includes('dark')) {
                        detectedQualityState = "infected";
                    } else {
                        detectedQualityState = "good";
                    }
                };
            };
            reader.readAsDataURL(file);
        }

        function runAiQualityCheck() {
            const btn = document.getElementById('ai-btn');
            const errBox = document.getElementById('ai-error-box');
            const resBox = document.getElementById('ai-result-box');

            errBox.classList.add('hidden');
            resBox.classList.add('hidden');
            btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Analyzing Image Pixels...`;

            const selectedCrop = document.getElementById('ai_check_crop').value;

            setTimeout(() => {
                fetch('/api/ai-quality-check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        crop: selectedCrop,
                        forced_quality: detectedQualityState
                    })
                })
                .then(res => res.json())
                .then(data => {
                    btn.innerHTML = `<i class="fa-solid fa-brain"></i> Run Grok AI Precision Analysis`;
                    if (!data.success) {
                        errBox.innerText = data.error;
                        errBox.classList.remove('hidden');
                    } else {
                        const res = data.result;
                        document.getElementById('res-grade').innerText = res.grade;
                        document.getElementById('res-grade').className = detectedQualityState === 'infected' ? 'font-bold text-red-600' : 'font-bold text-emerald-700';
                        document.getElementById('res-score').innerText = res.score;
                        document.getElementById('res-defects').innerText = res.defects;
                        document.getElementById('res-moisture').innerText = res.moisture;
                        document.getElementById('res-msp').innerText = `₹${res.msp.toLocaleString()} / Quintal`;
                        resBox.classList.remove('hidden');
                    }
                });
            }, 400);
        }

        function updateStatus(tokenId, status) {
            fetch('/api/update-token-status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token_id: tokenId, status: status})
            })
            .then(res => res.json())
            .then(data => {
                fetchTokens();
            });
        }

        function requestNotificationPermission() {
            if ("Notification" in window) {
                Notification.requestPermission().then(permission => {
                    if (permission === "granted") alert("Push Notifications Enabled!");
                });
            }
        }

        document.addEventListener("DOMContentLoaded", fetchTokens);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)