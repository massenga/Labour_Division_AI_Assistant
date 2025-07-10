import os
import streamlit as st
from PyPDF2 import PdfReader
import openai

# --- START: API key test snippet ---
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
st.write(f"API key loaded? {'Yes' if openai_api_key else 'No'}")

openai.api_key = openai_api_key

try:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}]
    )
    st.write("OpenAI response received:")
    st.write(response.choices[0].message.content)
except Exception as e:
    st.write("Error while calling OpenAI:")
    st.write(e)
# --- END: API key test snippet ---

# Main app title and PDF upload logic
st.title("PDF Summarizer with OpenAI GPT")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    st.header("Extracted Text")
    st.write(text)

    if st.button("Summarize Text"):
        with st.spinner("Summarizing..."):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                        {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
                    ],
                    max_tokens=300,
                    temperature=0.5,
                )
