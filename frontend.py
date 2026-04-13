import streamlit as st
import requests
import os

# --- Page config (MUST be first) ---
st.set_page_config(page_title="Resume Formatter", page_icon="📄", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Custom CSS ---
st.markdown("""
    <style>
        /* Sidebar background */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ff6b9d 0%, #ff8fab 40%, #ffb3c6 100%);
        }

        /* Sidebar text color */
        [data-testid="stSidebar"] * {
            color: white !important;
        }

        /* Sidebar divider */
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.4) !important;
        }

        /* Main background */
        [data-testid="stAppViewContainer"] {
            background: #f9f9fb;
        }

        /* Card style for upload area */
        .upload-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 24px rgba(255, 107, 157, 0.1);
            border: 1px solid #ffe0ec;
            margin-top: 10px;
        }

        /* Title styling */
        h1 {
            color: #2d2d2d !important;
            font-weight: 700 !important;
        }

        /* Subtitle */
        .subtitle {
            color: #888;
            font-size: 16px;
            margin-bottom: 30px;
        }

        /* Button styling */
        .stButton > button {
            background: linear-gradient(135deg, #ff6b9d, #ff8fab) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 32px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(255, 107, 157, 0.4) !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(255, 107, 157, 0.6) !important;
        }

        /* Download button */
        .stDownloadButton > button {
            background: linear-gradient(135deg, #2d2d2d, #555) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 32px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            background: white;
            border-radius: 12px;
            padding: 10px;
            border: 2px dashed #ff6b9d !important;
        }

        /* Spinner color */
        .stSpinner > div {
            border-top-color: #ff6b9d !important;
        }

        /* Hide streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Header bar with logo only ---
col1, col2 = st.columns([8, 2])
with col2:
    st.image(os.path.join(BASE_DIR, "logo.png"), width=200)

st.markdown("", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("", unsafe_allow_html=True)
    st.image(os.path.join(BASE_DIR, "claude_logo.png"), width=130)
    st.markdown(
        "Powered by Claude AI",
        unsafe_allow_html=True
    )
    st.markdown("", unsafe_allow_html=True)

    st.markdown("#### ✨ How it works")
    st.markdown("", unsafe_allow_html=True)

    st.markdown("📤 **Step 1:** Upload a PDF or DOCX resume")
    st.markdown("", unsafe_allow_html=True)
    st.markdown("🤖 **Step 2:** Claude reads and structures the content")
    st.markdown("", unsafe_allow_html=True)
    st.markdown("📄 **Step 3:** Download in Exavalu format")

    st.markdown("", unsafe_allow_html=True)
    st.markdown(
        "© Exavalu Internal Use Only",
        unsafe_allow_html=True
    )

# --- Main content ---
st.markdown("", unsafe_allow_html=True)
st.title("📄 Resume Formatter")
st.markdown(
    "Upload any resume and instantly get it reformatted in the Exavalu standard template.",
    unsafe_allow_html=True
)

st.markdown("", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drag and drop or browse a resume",
    type=["pdf", "docx"],
    help="Supported formats: PDF, DOCX"
)

if uploaded_file:
    st.markdown(f"✅ File ready: {uploaded_file.name}", unsafe_allow_html=True)
    st.markdown("", unsafe_allow_html=True)

    if st.button("🚀 Format Resume", type="primary"):
        with st.spinner("Claude is reading the resume... this may take 30–60 seconds"):
            response = requests.post(
                "http://localhost:8000/upload",
                files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            )

        if response.status_code == 200:
            st.success("✅ Your formatted resume is ready to download!")
            st.download_button(
                label="⬇️ Download Formatted Resume",
                data=response.content,
                file_name=uploaded_file.name.replace(".pdf", "_EV_Format.docx").replace(".docx", "_EV_Format.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.error(f"❌ Something went wrong: {response.status_code}")
            with st.expander("See error details"):
                st.write(response.text)

st.markdown("", unsafe_allow_html=True)