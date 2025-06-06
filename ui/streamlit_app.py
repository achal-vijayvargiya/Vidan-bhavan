import streamlit as st
from app.api.api_file import getData
import tempfile

st.set_page_config(page_title="Marathi OCR Form Extractor", layout="centered")

st.title("📄 Marathi OCR Data Viewer")

# Upload or paste text
uploaded_file = st.file_uploader("Upload OCR .jpg File", type=["png", "jpg", "jpeg"])



if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix="."+uploaded_file.name.split(".")[-1]) as tmp:
            tmp.write(uploaded_file.read())
            temp_file_path = tmp.name
    data = getData(temp_file_path)
    st.success("✅ Marathi data extracted")

    with st.form("extracted_data_form"):
        st.subheader("📝 Extracted Fields")

        date = st.text_input("📅 Date", value=data.get("date", ""))
        qn = st.text_input("🔢 Question Numbers", value=", ".join(data.get("question_number", [])))
        members = st.text_area("👥 Members Involved", value=", ".join(data.get("members", [])), height=100)
        topics = st.text_area("🧵 Topics", value="\n".join(data.get("topics", [])), height=100)
        answers_by = st.text_input("👨‍💼 Answered By", value=", ".join(data.get("answers_by", [])))

        submit = st.form_submit_button("✅ Confirm")

        if submit:
            st.success("📦 Form submitted! You can now save or export this data.")
else:
    st.info("Upload a `.jpg` file OCR text to begin.")
