# Standard Library Imports
import sqlite3
import os
import json
import base64
import time
from datetime import datetime

# Third-Party Imports for Streamlit, Data & Visualization
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- DATABASE SETUP (Local SQLite Engine) ---
# database initialization for persistent storage of farmers and scans
def init_db():
    conn = sqlite3.connect("kisan_doctor.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Table for Farmer Profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            village TEXT,
            district TEXT,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for Crop Diagnosis Scans linked with Farmer's Phone
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            crop_category TEXT,
            crop_name TEXT,
            disease TEXT,
            severity TEXT,
            treatment TEXT,
            temp REAL,
            condition TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Helper to save or update farmer registration
def save_farmer(name, phone, village, district, state):
    conn = sqlite3.connect("kisan_doctor.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO farmers (name, phone, village, district, state)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                name=excluded.name,
                village=excluded.village,
                district=excluded.district,
                state=excluded.state
        ''', (name, phone, village, district, state))
        conn.commit()
    except Exception as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()

# Helper to log diagnostic scans
def save_scan(phone, category, crop_name, disease, severity, treatment, temp, condition):
    conn = sqlite3.connect("kisan_doctor.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO scans (phone, crop_category, crop_name, disease, severity, treatment, temp, condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (phone, category, crop_name, disease, severity, treatment, temp, condition))
        conn.commit()
    except Exception as e:
        st.error(f"Scan log error: {e}")
    finally:
        conn.close()

# Retrieve all registered farmers (For Admin)
def get_all_farmers():
    conn = sqlite3.connect("kisan_doctor.db")
    df = pd.read_sql_query("SELECT * FROM farmers ORDER BY created_at DESC", conn)
    conn.close()
    return df

# Retrieve all scans with Farmer Name joined (For Admin)
def get_all_scans():
    conn = sqlite3.connect("kisan_doctor.db")
    query = """
        SELECT s.*, f.name as farmer_name, f.village, f.state 
        FROM scans s 
        LEFT JOIN farmers f ON s.phone = f.phone 
        ORDER BY s.timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Retrieve personal history for currently logged-in farmer
def get_farmer_history(phone):
    conn = sqlite3.connect("kisan_doctor.db")
    query = "SELECT * FROM scans WHERE phone = ? ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn, params=(phone,))
    conn.close()
    return df

# Initialize DB on Startup
init_db()

# --- STREAMLIT PAGE INITIALIZATION ---
st.set_page_config(
    page_title="AI Kisan Doctor - Smart Farming",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling & Theme Setup
st.markdown("""
    <style>
    .main {
        background-color: #f4f6f0;
    }
    .header-box {
        background-color: #1b4332;
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
        color: #2d6a4f;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e9f5db !important;
        border-bottom: 3px solid #2d6a4f !important;
    }
    .weather-card {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        margin-bottom: 1.5rem;
    }
    .identity-badge {
        background-color: #0f172a;
        color: #34d399;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        display: inline-block;
        border-left: 5px solid #10b981;
    }
    .profile-card {
        background-color: #e9f5db;
        padding: 1rem;
        border-radius: 10px;
        border-left: 6px solid #2d6a4f;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM DICTIONARY FOR MULTI-LANGUAGE ---
LANG_DICT = {
    "pa": {
        "title": "AI ਕਿਸਾਨ ਡਾਕਟਰ 🩺🌱",
        "subtitle": "ਕਿਸਾਨਾਂ ਲਈ ਵਰਦਾਨ - ਫਸਲਾਂ, ਸਬਜ਼ੀਆਂ, ਫੁੱਲ ਅਤੇ ਫਲਦਾਰ ਬੂਟਿਆਂ ਦੀ ਪਛਾਣ ਤੇ ਸਹੀ ਦਵਾਈ!",
        "reg_title": "ਕਿਸਾਨ ਪ੍ਰੋਫਾਈਲ ਰਜਿਸਟ੍ਰੇਸ਼ਨ",
        "reg_sub": "ਐਪ ਚਲਾਉਣ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਜਾਣਕਾਰੀ ਦਰਜ ਕਰੋ",
        "lbl_name": "ਕਿਸਾਨ ਦਾ ਨਾਮ (Farmer Name)",
        "lbl_phone": "ਮੋਬਾਈਲ ਨੰਬਰ (10-digit Mobile Number)",
        "lbl_village": "ਪਿੰਡ ਦਾ ਨਾਮ (Village)",
        "lbl_district": "ਜ਼ਿਲ੍ਹਾ (District)",
        "lbl_state": "ਸੂਬਾ (State)",
        "btn_register": "ਰਜਿਸਟਰ ਕਰੋ ਅਤੇ ਐਪ ਚਲਾਓ",
        "tab_diagnose": "AI Doctor (ਬਿਮਾਰੀ ਚੈੱਕ)",
        "tab_watering": "Watering & Care (ਪਾਣੀ ਤੇ ਦੇਖਭਾਲ)",
        "tab_history": "ਮੇਰਾ ਪੁਰਾਣਾ ਰਿਕਾਰਡ (My History)",
        "upload_title": "ਫਸਲ ਜਾਂ ਫਲਦਾਰ ਬੂਟੇ ਦੀ ਫੋਟੋ ਲਗਾਓ",
        "btn_analyze": "AI ਡਾਕਟਰ ਦੀ ਸਲਾਹ ਲਵੋ",
        "detected_plant": "ਪਛਾਣਿਆ ਗਿਆ ਪੌਦਾ/ਰੁੱਖ:",
        "disease": "ਬਿਮਾਰੀ ਦਾ ਨਾਮ:",
        "severity": "ਬਿਮਾਰੀ ਦੀ ਹਾਲਤ:",
        "treatment": "ਇਲਾਜ ਅਤੇ ਦਵਾਈ (Pesticide/Medicine Spray):",
        "tips": "ਸਾਵਧਾਨੀਆਂ ਅਤੇ ਟਿਪਸ:",
        "admin_sec": "🔒 Admin Control Panel (ਕਿਸਾਨ ਡਾਟਾ ਬੇਸ)",
        "admin_pass": "ਐਡਮਿਨ ਪਾਸਵਰਡ ਦਰਜ ਕਰੋ:",
        "total_farmers": "ਕੁੱਲ ਰਜਿਸਟਰਡ ਕਿਸਾਨ",
        "total_scans": "ਕੁੱਲ ਫਸਲ ਚੈੱਕਅਪ",
        "change_profile": "ਪ੍ਰੋਫਾਈਲ ਬਦਲੋ / Log Out"
    },
    "hi": {
        "title": "AI किसान डॉक्टर 🩺🌱",
        "subtitle": "किसानों के लिए वरदान - फसलों, सब्जियों, फूलों और फलों के पौधों की पहचान और सटीक उपचार!",
        "reg_title": "किसान प्रोफ़ाइल पंजीकरण",
        "reg_sub": "ऐप का उपयोग करने के लिए कृपया अपनी जानकारी दर्ज करें",
        "lbl_name": "किसान का नाम (Farmer Name)",
        "lbl_phone": "मोबाइल नंबर (10-digit Mobile Number)",
        "lbl_village": "गाँव का नाम (Village)",
        "lbl_district": "जिला (District)",
        "lbl_state": "राज्य (State)",
        "btn_register": "पंजीकरण करें और ऐप शुरू करें",
        "tab_diagnose": "AI डॉक्टर (बीमारी जांच)",
        "tab_watering": "सिंचाई और देखभाल",
        "tab_history": "मेरा पिछला रिकॉर्ड (History)",
        "upload_title": "फसल, सब्जी या पेड़ के फल की फोटो लगाएं",
        "btn_analyze": "AI डॉक्टर की सलाह लें",
        "detected_plant": "पहचाना गया पौधा/पेड़:",
        "disease": "बीमारी का नाम:",
        "severity": "बीमारी की स्थिति:",
        "treatment": "उपचार और दवाएं (Pesticide/Medicine Spray):",
        "tips": "सावधानियां और टिप्स:",
        "admin_sec": "🔒 Admin Control Panel (किसान डेटाबेस)",
        "admin_pass": "एडमिन पासवर्ड दर्ज करें:",
        "total_farmers": "कुल पंजीकृत किसान",
        "total_scans": "कुल फसल जांच",
        "change_profile": "प्रोफ़ाइल बदलें / Log Out"
    },
    "en": {
        "title": "AI Kisan Doctor 🩺🌱",
        "subtitle": "A boon for Farmers - Diagnostics, watering guidance & precise medicine recommendation!",
        "reg_title": "Farmer Profile Registration",
        "reg_sub": "Please enter your profile information to unlock full diagnostic features",
        "lbl_name": "Farmer Name",
        "lbl_phone": "Mobile Number",
        "lbl_village": "Village",
        "lbl_district": "District",
        "lbl_state": "State",
        "btn_register": "Register & Unlock App",
        "tab_diagnose": "AI Doctor (Diagnostics)",
        "tab_watering": "Watering & Care",
        "tab_history": "My History & Records",
        "upload_title": "Upload a picture of Crop, Leaf, Vegetable or Fruit tree",
        "btn_analyze": "Get AI Diagnosis & Solution",
        "detected_plant": "Detected Plant Identity:",
        "disease": "Disease Identified:",
        "severity": "Severity Status:",
        "treatment": "Recommended Remedy & Medicine Spray:",
        "tips": "General Care & Safety Tips:",
        "admin_sec": "🔒 Admin Control Panel (Farmer Database)",
        "admin_pass": "Enter Admin Passcode:",
        "total_farmers": "Total Registered Farmers",
        "total_scans": "Total Crop Checks",
        "change_profile": "Change Profile / Log Out"
    }
}

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&q=80&w=400", use_container_width=True)
    st.markdown("### ⚙️ Language / ਭਾਸ਼ਾ")
    lang_code = st.selectbox(
        "Select App Language:",
        options=["pa", "hi", "en"],
        format_func=lambda x: "ਪੰਜਾਬੀ (Punjabi)" if x == "pa" else ("हिन्दी (Hindi)" if x == "hi" else "English")
    )
    st.markdown("---")
    
    # Simple manual API Key setup in sidebar if environment variable is not set
    st.markdown("### 🔑 API Setup")
    user_api_key = st.text_input("Gemini API Key (Optional Override):", type="password")
    
    st.markdown("---")
    
    # ADMIN GATEWAY to monitor farmer data
    st.markdown(f"### {LANG_DICT[lang_code]['admin_sec']}")
    admin_pass = st.text_input(LANG_DICT[lang_code]['admin_pass'], type="password")
    is_admin = (admin_pass == "admin123")
    if is_admin:
        st.success("Authorized Admin Mode!")

# Apply translation
L = LANG_DICT[lang_code]

# --- APP HEADER DISPLAY ---
st.markdown(f"""
    <div class='header-box'>
        <h1 style='margin:0; font-size:2.5rem; font-weight:800;'>{L['title']}</h1>
        <p style='margin:0.5rem 0 0 0; font-size:1.1rem; opacity:0.9;'>{L['subtitle']}</p>
    </div>
""", unsafe_allow_html=True)

# --- DYNAMIC LOCATION & WEATHER COMPONENT ---
@st.cache_data(ttl=600)
def get_weather_data():
    # Attempting to fetch external IP location. Fallback defaults to Dhanaula, Punjab, India.
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=4).json()
        lat = geo.get("lat", 30.28)
        lon = geo.get("lon", 75.58)
        city = geo.get("city", "Dhanaula")
        region = geo.get("regionName", "Punjab")
        loc_str = f"{city}, {region}, India"
    except Exception:
        lat, lon = 30.28, 75.58
        loc_str = "Dhanaula, Punjab, India"

    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&relative_humidity_2m=true&hourly=relative_humidity_2m"
        res = requests.get(w_url, timeout=4).json()
        current = res.get("current_weather", {})
        temp = Math.round(current.get("temperature", 32)) if 'Math' in globals() else int(current.get("temperature", 32))
        wind = current.get("windspeed", 12)
        
        if temp > 35:
            advice = "Tez Garmi! Fasal nu halka pani shaam nu zroor dvo." if lang_code == 'pa' else ("तेज़ धूप! शाम को हल्की सिंचाई अवश्य करें।" if lang_code == 'hi' else "High temperature! Give a light irrigation in evening.")
        else:
            advice = "Mawsam normal hae. Nami dekh ke srayi kro." if lang_code == 'pa' else ("मौसम अनुकूल है। नमी देखकर सिंचाई करें।" if lang_code == 'hi' else "Normal optimum weather. Irrigate as needed.")
        return loc_str, temp, wind, advice
    except Exception:
        return "Dhanaula, Punjab, India", 31, 10, "Normal optimum weather. Irrigate as needed."

loc_name, weather_temp, weather_wind, weather_advice = get_weather_data()

# Render Weather Widget
st.markdown(f"""
    <div class='weather-card'>
        <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;'>
            <div>
                <span style='font-size:0.9rem; text-transform:uppercase; tracking:1px;'>📍 Live Location Weather</span>
                <h3 style='margin:0; font-size:1.6rem;'>{loc_name}</h3>
                <p style='margin:0.2rem 0; opacity:0.9; font-size:0.9rem;'>Wind: {weather_wind} km/h</p>
            </div>
            <div style='text-align:right;'>
                <span style='font-size:2.5rem; font-weight:900;'>⛅ {weather_temp}°C</span>
                <p style='margin:0; font-size:0.8rem; color:#fef08a; font-weight:bold;'>💡 Advice: {weather_advice}</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)


# --- FARMER REGISTRATION GATEWAY ---
# Session state initialization for logged-in farmer
if "farmer_phone" not in st.session_state:
    st.session_state.farmer_phone = None
if "farmer_name" not in st.session_state:
    st.session_state.farmer_name = None

# Farmer log-in or registration interface
if st.session_state.farmer_phone is None and not is_admin:
    st.markdown(f"### 📋 {L['reg_title']}")
    st.write(L["reg_sub"])
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        f_name = st.text_input(L["lbl_name"], placeholder="e.g. Gurpreet Singh")
        f_phone = st.text_input(L["lbl_phone"], placeholder="e.g. 9876543210", max_chars=10)
    with col_f2:
        f_village = st.text_input(L["lbl_village"], placeholder="e.g. Dhanaula")
        f_district = st.text_input(L["lbl_district"], placeholder="e.g. Barnala")
        f_state = st.text_input(L["lbl_state"], value="Punjab")

    if st.button(L["btn_register"]):
        if not f_name or not f_phone:
            st.error("Name and Mobile Number are required! / ਨਾਮ ਅਤੇ ਮੋਬਾਈਲ ਨੰਬਰ ਜਰੂਰੀ ਹਨ!")
        elif len(f_phone) < 10 or not f_phone.isdigit():
            st.error("Please enter a valid 10-digit mobile number! / ਸਹੀ ਮੋਬਾਈਲ ਨੰਬਰ ਦਰਜ ਕਰੋ!")
        else:
            save_farmer(f_name, f_phone, f_village, f_district, f_state)
            st.session_state.farmer_phone = f_phone
            st.session_state.farmer_name = f_name
            st.success("Registration Successful! Welcome to AI Kisan Doctor.")
            st.rerun()
            
    st.stop()  # Stop execution of dashboard till farmer registers

# If logged-in, show farmer identity card at the top
if st.session_state.farmer_phone is not None:
    st.markdown(f"""
        <div class='profile-card'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <span style='font-size:0.8rem; text-transform:uppercase; color:#1b4332; font-weight:bold;'>Active Farmer Profile</span>
                    <h4 style='margin:0; font-size:1.2rem; color:#1b4332;'>🌾 {st.session_state.farmer_name} ({st.session_state.farmer_phone})</h4>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button(L["change_profile"], key="logout"):
        st.session_state.farmer_phone = None
        st.session_state.farmer_name = None
        st.rerun()


# --- INTERACTIVE USER PORTAL ---
if not is_admin:
    tab1, tab2, tab3 = st.tabs([f"🩺 {L['tab_diagnose']}", f"💧 {L['tab_watering']}", f"📜 {L['tab_history']}"])

    # --- TAB 1: AI DIAGNOSIS ---
    with tab1:
        st.subheader(L["upload_title"])
        
        col_c1, col_c2 = st.columns(2)
        uploaded_image = None
        
        with col_c1:
            st.write("📷 Capture live on field or upload image:")
            input_source = st.radio("Choose Input Method:", ["Upload from Gallery (ਗੈਲਰੀ)", "Take Live Camera Snapshot (ਕੈਮਰਾ)"])
            
            if input_source == "Take Live Camera Snapshot (ਕੈਮਰਾ)":
                uploaded_image = st.camera_input("Scan leaf, fruit or stem picture")
            else:
                uploaded_image = st.file_uploader("Choose Crop Image File", type=["jpg", "jpeg", "png"])
            
            crop_cat = st.selectbox("Category:", ["Crop (ਫਸਲ)", "Vegetable (ਸਬਜ਼ੀ)", "Flower (ਫੁੱਲ)", "Fruit Tree (ਫਲਦਾਰ ਬੂਟਾ)"])
            
        with col_c2:
            st.write("🔍 Image Preview:")
            if uploaded_image is not None:
                st.image(uploaded_image, caption="Uploaded Specimen", use_container_width=True)
                img_bytes = uploaded_image.getvalue()
                base64_specimen = base64.b64encode(img_bytes).decode("utf-8")
            else:
                st.info("Uploaded plant photo preview will display here.")
                base64_specimen = None

        if st.button(L["btn_analyze"]):
            if base64_specimen is None:
                st.error("Please provide a crop/leaf picture first! / ਕਿਰਪਾ ਕਰਕੇ ਫੋਟੋ ਲਗਾਓ!")
            else:
                with st.spinner("AI Kisan Doctor is analyzing... please wait..."):
                    # Use provided override API key or standard injected key
                    api_key = user_api_key if user_api_key else os.environ.get("GEMINI_API_KEY", "")
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
                    
                    system_prompt = f"""You are "AI Kisan Doctor", an expert agricultural botanist.
                    Strictly diagnose the plant image. You must detect the specific crop name and identify diseases.
                    Respond strictly in valid JSON format only. No outer markdown formatting like ```json.
                    JSON Keys structure:
                    {{
                        "cropName": "Exact identified crop/plant name in regional language, e.g. Kanak (Wheat)",
                        "disease": "Specific identified disease name",
                        "severity": "Severity Level (e.g. High / Low / Moderate with reason)",
                        "treatment": "Clear bulleted list of solutions, organic remedies, or standard pesticide sprays with recommended dosage and application technique",
                        "careTips": "Proactive prevention, soil nutrient adjustment, and irrigation tips"
                    }}
                    Translate all JSON value content into the language of code: {lang_code}. Keep chemical names recognizable."""

                    user_prompt = f"Identify this specimen under the category '{crop_cat}'. Provide the complete diagnostics report."

                    payload = {
                        "contents": [{
                            "parts": [
                                { "text": user_prompt },
                                { "inlineData": { "mimeType": "image/jpeg", "data": base64_specimen } }
                            ]
                        }],
                        "systemInstruction": {
                            "parts": [{ "text": system_prompt }]
                        },
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }

                    success = False
                    response_text = ""
                    for attempt in range(5):
                        try:
                            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                            if res.ok:
                                response_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                                success = True
                                break
                        except Exception:
                            pass
                        time.sleep(1 * (attempt + 1))

                    if success:
                        try:
                            report = json.loads(response_text)
                            
                            st.markdown("### 📋 AI Crop Diagnosis Report")
                            
                            # Dynamic identification overlay
                            crop_detected_name = report.get('cropName', 'Unknown')
                            st.markdown(f"""
                                <div class='identity-badge'>
                                    🔎 {L['detected_plant']} {crop_detected_name}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br><br>", unsafe_allow_html=True)
                            
                            # Displaying diagnostic elements beautifully
                            col_out1, col_out2 = st.columns(2)
                            with col_out1:
                                st.markdown(f"#### 🦠 {L['disease']}")
                                st.error(report.get('disease', 'N/A'))
                                
                                st.markdown(f"#### ⚠️ {L['severity']}")
                                st.warning(report.get('severity', 'N/A'))
                                
                            with col_out2:
                                st.markdown(f"#### 💊 {L['treatment']}")
                                st.info(report.get('treatment', 'N/A'))
                                
                                st.markdown(f"#### 💡 {L['tips']}")
                                st.write(report.get('careTips', 'N/A'))
                                
                            # Save scan results dynamically inside SQLite
                            save_scan(
                                phone=st.session_state.farmer_phone,
                                category=crop_cat,
                                crop_name=crop_detected_name,
                                disease=report.get('disease', 'N/A'),
                                severity=report.get('severity', 'N/A'),
                                treatment=report.get('treatment', 'N/A'),
                                temp=weather_temp,
                                condition=loc_name
                            )
                            st.success("Diagnostics saved successfully in your local farming records!")
                            
                        except Exception as e:
                            st.error("Problem decoding AI diagnostic output. Raw response text:")
                            st.code(response_text)
                    else:
                        st.error("AI Doctor Server issue. Please verify your Gemini API key in the sidebar or try again.")

    # --- TAB 2: WATERING & IRRIGATION CALCULATOR ---
    with tab2:
        st.subheader("💧 Smart Irrigation Planner")
        st.write("Identify optimal water intervals based on growth phase and current local weather conditions:")
        
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            crop_irr = st.selectbox("Crop/Tree Type:", ["Wheat (ਕਣਕ)", "Paddy (ਝੋਨਾ)", "Kinnow (ਕਿੰਨੂ)", "Potato (ਆਲੂ)", "Tomato (ਟਮਾਟਰ)", "Cotton", "Flower Crops"])
        with col_w2:
            soil_irr = st.selectbox("Soil Type:", ["Sandy Loam (ਰੇਤਲੀ ਮਿੱਟੀ)", "Clayey (ਚੀਕਣੀ ਮਿੱਟੀ)", "Sandy (ਰੇਤਲੀ)"])
        with col_w3:
            stage_irr = st.selectbox("Growth Stage:", ["Sowing / Initial", "Vegetative Growth", "Flowering / Fruiting", "Maturing / Pre-Harvest"])
            
        if st.button("Calculate Water Requirement"):
            base_days = 9
            if "Sandy" in soil_irr:
                base_days = 5
            elif "Clayey" in soil_irr:
                base_days = 13
                
            # Calibrate dynamically with current live temperature
            if weather_temp > 35:
                base_days = max(3, base_days - 3)
            elif weather_temp < 15:
                base_days = base_days + 4
                
            st.info(f"""
                **📊 Smart Watering Schedule Advice:**
                
                • **Irrigation Interval:** You should irrigate every **{base_days} to {base_days+2} days**.
                • **Stage Warning:** {stage_irr} is highly sensitive to irrigation. Ensure uniform moisture.
                • **Local Temperature Correction:** Corrected for current **{weather_temp}°C** environment.
            """)

    # --- TAB 3: PERSONAL HISTORY RECORDS ---
    with tab3:
        st.subheader("📜 Mere Purane Record (Your Diagnostics History)")
        st.write("Retrieve details of previous disease checks and advice given:")
        
        history_df = get_farmer_history(st.session_state.farmer_phone)
        if len(history_df) == 0:
            st.info("No diagnostic history found. Try scanning a crop leaf in Tab 1!")
        else:
            for idx, row in history_df.iterrows():
                with st.expander(f"🕒 {row['timestamp']} | 🌾 {row['crop_name']} - {row['disease']}"):
                    st.markdown(f"**Crop Type:** {row['crop_category']} | **Weather recorded:** {row['temp']}°C ({row['condition']})")
                    st.markdown(f"**Severity:** {row['severity']}")
                    st.markdown(f"**Medicine Recommendation:**\n{row['treatment']}")


# --- ADMIN CONTROL ROOM (Kisan Data Directory Dashboard) ---
else:
    st.markdown("## 🔒 Admin Management Control Room")
    st.write("Manage farmer registration directories, trace scan analytics, and fetch metrics:")
    
    # Load SQLite Dataframes
    df_farmers = get_all_farmers()
    df_scans = get_all_scans()
    
    # Admin KPI Metrics Dashboard
    col_adm1, col_adm2, col_adm3, col_adm4 = st.columns(4)
    with col_adm1:
        st.metric(L["total_farmers"], len(df_farmers))
    with col_adm2:
        st.metric(L["total_scans"], len(df_scans))
    with col_adm3:
        top_crop = df_scans['crop_name'].mode().iloc[0] if len(df_scans) > 0 else "N/A"
        st.metric("Top Searched Crop", top_crop)
    with col_adm4:
        top_disease = df_scans['disease'].mode().iloc[0] if len(df_scans) > 0 else "N/A"
        st.metric("Most Active Issue", top_disease)
        
    st.markdown("---")
    
    tab_f, tab_s, tab_g = st.tabs(["👥 Kisan Registration Directory", "🔍 Diagnostic Queries Database", "📈 Market & Disease Trends"])
    
    # Admin Sub-Tab 1: Farmer Directory
    with tab_f:
        st.subheader("Active Farmer Registry List")
        st.write("Comprehensive lookup of registered farmers:")
        
        # Search & Filters
        search_term = st.text_input("Search Farmer by Name or Phone Number:")
        filtered_df_f = df_farmers
        if search_term:
            filtered_df_f = df_farmers[
                df_farmers['name'].str.contains(search_term, case=False, na=False) |
                df_farmers['phone'].str.contains(search_term, na=False)
            ]
            
        st.dataframe(filtered_df_f, use_container_width=True)
        
        # CSV Export Feature
        csv_farmers = filtered_df_f.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Registered Farmers List (Excel/CSV)", csv_farmers, "farmers_directory.csv", "text/csv")
        
    # Admin Sub-Tab 2: Scan Database
    with tab_s:
        st.subheader("Diagnostic Scans Log")
        st.write("Comprehensive scan telemetry logs containing crop, disease, severity, and treatments:")
        
        selected_crop = st.multiselect("Filter by Crop:", options=df_scans['crop_name'].unique().tolist())
        filtered_df_s = df_scans
        if selected_crop:
            filtered_df_s = df_scans[df_scans['crop_name'].isin(selected_crop)]
            
        st.dataframe(filtered_df_s, use_container_width=True)
        
        # CSV Export Feature
        csv_scans = filtered_df_s.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Crops Scan Database (Excel/CSV)", csv_scans, "crop_scans_database.csv", "text/csv")

    # Admin Sub-Tab 3: Interactive Analytics Charts
    with tab_g:
        st.subheader("📊 Visual Market Insight Charts")
        
        if len(df_scans) == 0:
            st.info("Not enough telemetry diagnostic data to generate visual analytics yet.")
        else:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("🏆 **Top Crops Looked up by Farmers**")
                crop_counts = df_scans['crop_name'].value_counts().reset_index()
                crop_counts.columns = ['Crop Name', 'Inquiries']
                fig_c = px.bar(crop_counts, x='Crop Name', y='Inquiries', color='Crop Name', color_discrete_sequence=px.colors.qualitative.Dark2)
                st.plotly_chart(fig_c, use_container_width=True)
                
            with col_g2:
                st.write("🎯 **Most Common Disease Threats**")
                disease_counts = df_scans['disease'].value_counts().reset_index()
                disease_counts.columns = ['Disease Name', 'Occurrences']
                fig_d = px.pie(disease_counts, names='Disease Name', values='Occurrences', hole=0.3, color_discrete_sequence=px.colors.sequential.Sunset)
                st.plotly_chart(fig_d, use_container_width=True)
