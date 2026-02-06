from PIL import Image
import io
import streamlit as st
from streamlit_option_menu import option_menu
import firebase_admin
from firebase_admin import credentials, firestore
from fpdf import FPDF
import base64
from datetime import datetime
import io

# 1. Page Configuration
st.set_page_config(page_title="360 Skin Clinic ERP", layout="wide", page_icon="🏥")

# --- CSS (UI පිළිවෙළ සහ තද වර්ණ පද්ධතිය) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117 !important; }
    [data-testid="stSidebarContent"] { padding-top: 0rem !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; margin-top: -1rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.1rem !important; padding-top: 0rem !important; }

    /* Dashboard Metrics */
    div[data-testid="metric-container"] {
        background-color: #1e293b !important;
        padding: 25px !important; border-radius: 15px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        border: 1px solid #334155 !important; text-align: center;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 32px !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #cbd5e1 !important; font-size: 16px !important; }

    /* Info Cards & Profile Styling */
    .info-card, .profile-section, .data-card, .invoice-item { 
        background-color: #1e293b !important; padding: 20px !important; 
        border-radius: 12px !important; border-left: 8px solid #10b981 !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important; color: #ffffff !important; margin-bottom: 15px !important;
    }
    .label { color: #94a3b8; font-size: 0.9rem; font-weight: bold; text-transform: uppercase; }
    .value { color: #ffffff; font-size: 1.1rem; font-weight: 500; }
    
    .stButton>button { border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; background-color: #2563eb !important; color: white !important; }
    
    /* Image Box Styling */
    .img-box { border: 2px dashed #334155; border-radius: 10px; padding: 10px; text-align: center; background: #0f172a; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Firebase Connection
if not firebase_admin._apps:
    cred = credentials.Certificate("key.json") 
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'db_unlocked' not in st.session_state: st.session_state.db_unlocked = False
if 'selected_patient' not in st.session_state: st.session_state.selected_patient = None

def encode_image(uploaded_file):
    if uploaded_file is not None:
        # පින්තූරය Open කරගන්න
        img = Image.open(uploaded_file)
        
        # පින්තූරය RGB format එකට හරවන්න (PNG වැනි දේ JPG වලට හරවන්න ලේසියි)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # පින්තූරය මතකයට (Memory) සේව් කරන්න (Compress කරලා)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60, optimize=True) # මෙතන 60 කියන්නේ Quality එක
        
        return base64.b64encode(buffer.getvalue()).decode()
    return None


# --- LOGIN LOGIC ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: white;'>🔐 Clinic System Access</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("main_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter System"):
                if u == "admin" and p == "360pass":
                    st.session_state.logged_in = True; st.rerun()
                else: st.error("Invalid Credentials")
else:
    # Sidebar
    with st.sidebar:
        st.image("360logo.png", use_container_width=True)
        selected = option_menu(menu_title=None, options=["Dashboard", "New Patient", "Search Client", "Billing"], icons=["speedometer2", "person-plus-fill", "search-heart", "receipt-cutoff"], default_index=2, styles={"nav-link-selected": {"background-color": "#2563eb"}})
        if st.button("🚪 Logout System"): st.session_state.logged_in = False; st.session_state.db_unlocked = False; st.rerun()

    # --- PAGES ---

    if selected == "Dashboard":
        if not st.session_state.db_unlocked:
            st.subheader("🔐 Dashboard Security")
            db_pass = st.text_input("Enter Dashboard Password", type="password")
            if st.button("Unlock Dashboard"):
                if db_pass == "owner360": st.session_state.db_unlocked = True; st.rerun()
                else: st.error("Incorrect!")
        else:
            st.title("📊 Financial Overview")
            bills = db.collection("bills").order_by("date", direction=firestore.Query.DESCENDING).get()
            income = sum([b.to_dict().get('total', 0) for b in bills])
            m1, m2, m3 = st.columns(3)
            m1.metric("Registered Patients", len(db.collection("patients").get()))
            m2.metric("Total Revenue", f"Rs. {income:,.2f}")
            m3.metric("System Health", "Optimal ✅")
            if st.button("🔒 Lock Dashboard"): st.session_state.db_unlocked = False; st.rerun()

    elif selected == "New Patient":
        st.title("➕ New Patient Registration")
        with st.form("p_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name, ph = c1.text_input("Patient Full Name*"), c1.text_input("Mobile Number*")
            age, gen = c2.number_input("Age", 0, 120), c2.selectbox("Gender", ["Male", "Female", "Other"])
            address = st.text_area("Home Address")
            sym, tr = st.text_area("Symptoms"), st.text_area("Medical History")
            
            st.markdown("### 📸 Case Photos (Optional)")
            col_img1, col_img2 = st.columns(2)
            img_before = col_img1.file_uploader("Upload Before Photo", type=['jpg', 'png', 'jpeg'])
            # ඡායාරූපය තේරූ විට Preview එකක් පෙන්වීම
            if img_before: col_img1.image(img_before, caption="Selected Before Photo Preview", width=250)
            
            img_after = col_img2.file_uploader("Upload After Photo", type=['jpg', 'png', 'jpeg'])
            # ඡායාරූපය තේරූ විට Preview එකක් පෙන්වීම
            if img_after: col_img2.image(img_after, caption="Selected After Photo Preview", width=250)
            
            if st.form_submit_button("Register Patient Record"):
                if name and ph:
                    data = {"name":name, "phone":ph, "age":age, "gender":gen, "address":address, "symptoms":sym, "treatments":tr}
                    if img_before: data["before_img"] = encode_image(img_before)
                    if img_after: data["after_img"] = encode_image(img_after)
                    
                    db.collection("patients").document(ph).set(data)
                    st.success("Patient Record Created Successfully!")
                else: st.warning("Name and Phone are required.")

    elif selected == "Search Client":
        if st.session_state.selected_patient:
            p = st.session_state.selected_patient
            if st.button("⬅️ Back to Search List"): st.session_state.selected_patient = None; st.rerun()
            
            st.markdown(f"## 👤 Patient Profile: {p['name']}")
            st.markdown(f"**Contact:** {p['phone']}")
            
            st.markdown('<div class="profile-section">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="data-card"><div class="label">Age</div><div class="value">{p.get("age")} Years</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="data-card"><div class="label">Gender</div><div class="value">{p.get("gender")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="data-card"><div class="label">Address</div><div class="value">{p.get("address")}</div></div>', unsafe_allow_html=True)
            with c2:
                st.info(f"#### 🩺 Symptoms\n\n{p.get('symptoms', 'None')}")
                st.warning(f"#### 📜 Medical History\n\n{p.get('treatments', 'None')}")
            
                                    # --- Progress Photos View & Update ---
            st.markdown("---")
            st.markdown("### 📸 Treatment Progress Photos")
            ci1, ci2 = st.columns(2)
            
            with ci1:
                st.markdown("**BEFORE TREATMENT**")
                # 1. පවතින ෆොටෝ එක පෙන්වීම සහ Download කිරීම
                if "before_img" in p and p["before_img"]:
                    img_data = base64.b64decode(p["before_img"])
                    st.image(img_data, use_container_width=True)
                    st.caption(f"📏 Size: {len(img_data)/1024:.1f} KB") # Size පෙන්වීම
                    st.download_button("📥 Download", img_data, f"{p['phone']}_before.jpg", "image/jpeg", key="dl_b")
                else:
                    st.info("No before photo uploaded.")
                
                # 2. අලුතින් Upload කිරීමේ (Update) කොටස
                with st.expander("⬆️ Update Before Photo"):
                    new_b = st.file_uploader("Choose Photo", type=['jpg','png','jpeg'], key="up_b")
                    if new_b:
                        st.image(new_b, width=150, caption="New Preview")
                        if st.button("Save New Before Photo"):
                            # Compress කරලා encode කරනවා
                            encoded_b = encode_image(new_b)
                            db.collection("patients").document(p['phone']).update({"before_img": encoded_b})
                            st.success("Before photo updated!"); st.rerun()

            with ci2:
                st.markdown("**AFTER TREATMENT**")
                # 1. පවතින ෆොටෝ එක පෙන්වීම සහ Download කිරීම
                if "after_img" in p and p["after_img"]:
                    img_data_a = base64.b64decode(p["after_img"])
                    st.image(img_data_a, use_container_width=True)
                    st.caption(f"📏 Size: {len(img_data_a)/1024:.1f} KB") # Size පෙන්වීම
                    st.download_button("📥 Download", img_data_a, f"{p['phone']}_after.jpg", "image/jpeg", key="dl_a")
                else:
                    st.info("No after photo uploaded.")

                # 2. අලුතින් Upload කිරීමේ (Update) කොටස
                with st.expander("⬆️ Update After Photo"):
                    new_a = st.file_uploader("Choose Photo", type=['jpg','png','jpeg'], key="up_a")
                    if new_a:
                        st.image(new_a, width=150, caption="New Preview")
                        if st.button("Save New After Photo"):
                            # Compress කරලා encode කරනවා
                            encoded_a = encode_image(new_a)
                            db.collection("patients").document(p['phone']).update({"after_img": encoded_a})
                            st.success("After photo updated!"); st.rerun()


            
        else:
            st.title("🔍 Directory")
            q = st.text_input("Search Patient Phone", placeholder="07XXXXXXXX")
            if q:
                res = db.collection("patients").where("phone", ">=", q).where("phone", "<=", q + "\uf8ff").stream()
                for doc in res:
                    d = doc.to_dict()
                    col_i, col_b = st.columns([4, 1])
                    col_i.markdown(f'<div class="info-card" style="padding:10px !important;"><b>{d["name"]}</b> ({d["phone"]})</div>', unsafe_allow_html=True)
                    if col_btn := col_b.button("View Profile", key=d['phone']):
                        st.session_state.selected_patient = d; st.rerun()

    elif selected == "Billing":
        st.title("💰 Professional Billing")
        sq = st.text_input("Find Patient")
        if sq:
            res = db.collection("patients").where("phone", ">=", sq).where("phone", "<=", sq + "\uf8ff").stream()
            p_list = [f"{d.to_dict()['name']} - {d.to_dict()['phone']}" for d in res]
            if p_list:
                sel = st.selectbox("Select Patient", ["-- Select --"] + p_list)
                if sel != "-- Select --":
                    p_name, p_phone = sel.split(" - ")
                    st.markdown(f'<div class="info-card"><h4>{p_name}</h4><p>{p_phone}</p></div>', unsafe_allow_html=True)
                    with st.form("b_form"):
                        fee, disc = st.number_input("Amount (Rs.)", 0), st.number_input("Discount", 0)
                        if st.form_submit_button("Generate & Print Invoice"):
                            db.collection("bills").add({"name":p_name, "phone":p_phone, "total":fee-disc, "date":firestore.SERVER_TIMESTAMP})
                            st.success("Invoice Saved Successfully!"); st.balloons()
