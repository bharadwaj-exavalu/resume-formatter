import streamlit as st
import requests
from pathlib import Path

# --- Page config (MUST be first) ---
st.set_page_config(page_title="Resume Formatter", page_icon="📄", layout="wide")

# --- Top bar: logo on the right using columns ---
col1, col2, col3 = st.columns([6, 1, 1])
with col3:
    st.image("logo.png", width=150)

st.markdown("", unsafe_allow_html=True)

# --- Sidebar: Powered by Claude ---
with st.sidebar:
    st.markdown(
        "Powered by",
        unsafe_allow_html=True
    )
    st.image("claude_logo.png", width=120)
    st.divider()
    st.markdown("#### How it works")
    st.markdown("""
    1. 📤 Upload a resume (PDF or DOCX)
    2. 🤖 Claude extracts and structures the content
    3. 📄 Downloads in Exavalu format
    """)

# --- Main content ---
st.title("📄 Exavalu Resume Formatter")
st.write("Upload a resume and get it formatted in the Exavalu template.")

uploaded_file = st.file_uploader("Upload Resume", type=["pdf", "docx"])

if uploaded_file:
    if st.button("Format Resume", type="primary"):
        with st.spinner("Processing... this may take 30-60 seconds"):
            response = requests.post(
                "http://localhost:8000/upload",
                files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            )

        if response.status_code == 200:
            st.success("✅ Done! Your formatted resume is ready.")
            st.download_button(
                label="⬇️ Download Formatted Resume",
                data=response.content,
                file_name=uploaded_file.name.replace(".pdf", "_EV_Format.docx").replace(".docx", "_EV_Format.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.error(f"Something went wrong: {response.status_code}")
            st.write(response.text)