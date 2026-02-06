import streamlit as st
from streamlit_option_menu import option_menu
import firebase_admin
from firebase_admin import credentials, firestore
import base64
from datetime import datetime
from PIL import Image
import io

# 1. Page Configuration
st.set_page_config(page_title="360 Skin Clinic ERP", layout="wide", page_icon="🏥")

# --- CSS (Supiri Dark UI) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117 !important; }
    div[data-testid="metric-container"] { background-color: #1e293b !important; padding: 25px !important; border-radius: 15px !important; text-align: center; border: 1px solid #334155; }
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    .info-card, .profile-section, .invoice-item { background-color: #1e293b !important; padding: 20px !important; border-radius: 12px !important; border-left: 8px solid #10b981 !important; color: #ffffff !important; margin-bottom: 15px !important; }
    .data-card { background-color: #0f172a !important; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #334155; }
    .label { color: #94a3b8; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }
    .value { color: #ffffff; font-size: 1.1rem; }
    .stButton>button { background-color: #2563eb !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. Firebase Connection (Using Secrets for Security)
if not firebase_admin._apps:
    try:
        # Streamlit Cloud Secrets වලින් දත්ත කියවීම
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Firebase Configuration Error: {e}")
db = firestore.client()

# --- [HELPERS] ---
def encode_image(uploaded_file):
    """ඡායාරූපය Compress කර Base64 බවට පත් කරයි."""
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()
    return None

# --- [SESSION STATES] ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None 
if 'selected_patient' not in st.session_state: st.session_state.selected_patient = None

# ==========================================
# 🏥 CLINICAL PORTAL LOGIC
# ==========================================
def run_clinical_portal():
    with st.sidebar:
        selected = option_menu(None, ["New Patient", "Search Client", "Billing"], 
                              icons=["person-plus-fill", "search-heart", "receipt-cutoff"], 
                              default_index=0, styles={"nav-link-selected": {"background-color": "#2563eb"}})
        if st.button("🚪 Logout Portal"):
            st.session_state.logged_in = False; st.session_state.user_role = None; st.rerun()

    if selected == "New Patient":
        st.title("➕ New Patient Registration")
        with st.form("p_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name, ph = c1.text_input("Full Name*"), c1.text_input("Mobile*")
            age, gen = c2.number_input("Age", 0, 120), c2.selectbox("Gender", ["Male", "Female", "Other"])
            ad, sym, tr = st.text_area("Address"), st.text_area("Symptoms"), st.text_area("History")
            st.markdown("### 📸 Case Photos")
            col_img1, col_img2 = st.columns(2)
            img_b = col_img1.file_uploader("Before", type=['jpg','png','jpeg'])
            img_a = col_img2.file_uploader("After", type=['jpg','png','jpeg'])
            if st.form_submit_button("Register Patient"):
                if name and ph:
                    data = {"name":name, "phone":ph, "age":age, "gender":gen, "address":ad, "symptoms":sym, "treatments":tr}
                    if img_b: data["before_img"] = encode_image(img_b)
                    if img_a: data["after_img"] = encode_image(img_a)
                    db.collection("patients").document(ph).set(data); st.success("Created!")

    elif selected == "Search Client":
        if st.session_state.selected_patient:
            p = st.session_state.selected_patient
            if st.button("⬅️ Back to Search List"): st.session_state.selected_patient = None; st.rerun()
            st.markdown(f'<div class="info-card"><h1>👤 Patient Profile: {p["name"]}</h1><p>Contact: {p["phone"]}</p></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="data-card"><div class="label">Age</div><div class="value">{p.get("age")} Years</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="data-card"><div class="label">Gender</div><div class="value">{p.get("gender")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="data-card"><div class="label">Address</div><div class="value">{p.get("address", "N/A")}</div></div>', unsafe_allow_html=True)
            with c2:
                st.info(f"**Symptoms:**\n\n{p.get('symptoms', 'None')}")
                st.warning(f"**History:**\n\n{p.get('treatments', 'None')}")
            
            # --- Photos Section (Download & Upload) ---
            st.markdown("---")
            ci1, ci2 = st.columns(2)
            for key, col, label in [("before_img", ci1, "BEFORE"), ("after_img", ci2, "AFTER")]:
                with col:
                    st.markdown(f"**{label}**")
                    if p.get(key):
                        img_bytes = base64.b64decode(p[key])
                        st.image(img_bytes, use_container_width=True)
                        st.caption(f"📏 Size: {len(img_bytes)/1024:.1f} KB")
                        st.download_button(f"📥 Download {label}", img_bytes, f"{p['phone']}_{label.lower()}.jpg", "image/jpeg")
                    else: st.info(f"No {label.lower()} photo.")
                    with st.expander(f"⬆️ Update {label} Photo"):
                        new_img = st.file_uploader(f"Choose {label}", type=['jpg','jpeg','png'], key=f"up_{key}")
                        if new_img and st.button(f"Save New {label}"):
                            db.collection("patients").document(p['phone']).update({key: encode_image(new_img)})
                            st.success("Updated!"); st.rerun()
        else:
            q = st.text_input("Search Patient Phone")
            if q:
                res = db.collection("patients").where("phone", ">=", q).where("phone", "<=", q + "\uf8ff").stream()
                for doc in res:
                    d = doc.to_dict(); c_i, c_b = st.columns([4, 1])
                    c_i.markdown(f'<div class="info-card"><b>{d["name"]}</b> ({d["phone"]})</div>', unsafe_allow_html=True)
                    if c_b.button("View Profile", key=d['phone']): st.session_state.selected_patient = d; st.rerun()

    elif selected == "Billing":
        st.title("💰 Billing Portal")
        sq = st.text_input("Find Patient")
        if sq:
            res = db.collection("patients").where("phone", ">=", sq).where("phone", "<=", sq + "\uf8ff").stream()
            p_list = [f"{d.to_dict()['name']} - {d.to_dict()['phone']}" for d in res]
            if p_list:
                sel = st.selectbox("Select Patient", ["-- Select --"] + p_list)
                if sel != "-- Select --":
                    p_n, p_ph = sel.split(" - ")
                    with st.form("b_form"):
                        fee, disc = st.number_input("Amount", 0), st.number_input("Discount", 0)
                        if st.form_submit_button("Generate Bill"):
                            db.collection("bills").add({"name":p_n, "phone":p_ph, "total":fee-disc, "date":datetime.now()}); st.success("Saved!")

# ==========================================
# 📊 MONITOR PORTAL LOGIC
# ==========================================
def run_monitor_portal():
    st.sidebar.title("📊 Monitor Panel")
    if st.sidebar.button("🚪 Logout Monitor"):
        st.session_state.logged_in = False; st.session_state.user_role = None; st.rerun()
    st.title("📈 Business Intelligence")
    bills = db.collection("bills").order_by("date", direction="DESCENDING").get()
    m1, m2 = st.columns(2)
    m1.metric("Registered Patients", len(db.collection("patients").get()))
    m2.metric("Total Revenue", f"Rs. {sum([b.to_dict().get('total', 0) for b in bills]):,.2f}")
    st.subheader("📑 Recent Transactions")
    for b in bills:
        d = b.to_dict()
        st.markdown(f'<div class="invoice-item">{d.get("name")} | <span style="float:right; color:#10b981;">Rs. {d.get("total"):,.2f}</span></div>', unsafe_allow_html=True)

# ==========================================
# 🚀 ROUTING & LOGIN LOGIC
# ==========================================
if st.session_state.user_role is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.image("360logo.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center; color: white;'>360 Skin Clinic Management</h2>", unsafe_allow_html=True)
        cx, cy = st.columns(2)
        if cx.button("🏥 Clinical Portal", use_container_width=True): st.session_state.user_role = 'cashier'; st.rerun()
        if cy.button("📊 Monitoring Portal", use_container_width=True): st.session_state.user_role = 'monitor'; st.rerun()

elif not st.session_state.logged_in:
    st.markdown(f"<h2 style='text-align: center; color: white;'>🔐 {st.session_state.user_role.capitalize()} Login</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if st.session_state.user_role == 'cashier' and u == "cashier" and p == "360pass": st.session_state.logged_in = True; st.rerun()
                elif st.session_state.user_role == 'monitor' and u == "admin" and p == "owner360": st.session_state.logged_in = True; st.rerun()
                else: st.error("Incorrect details!")
        if st.button("⬅️ Back"): st.session_state.user_role = None; st.rerun()
else:
    if st.session_state.user_role == 'cashier': run_clinical_portal()
    else: run_monitor_portal()
