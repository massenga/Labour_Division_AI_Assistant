import streamlit as st
from PyPDF2 import PdfReader
import openai

# Set your OpenAI API key from Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

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
                summary = response.choices[0].message.content
                st.subheader("Summary")
                st.write(summary)
            except Exception as e:
                st.error(f"Error while summarizing: {e}")
else:
    st.write("Please upload a PDF file to extract and summarize text.")
