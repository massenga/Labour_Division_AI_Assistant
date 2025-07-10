import streamlit as st
from PyPDF2 import PdfReader

st.title("PDF Text Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    st.header("Extracted Text")
    st.write(text)
else:
    st.write("Please upload a PDF file to see the extracted text.")
