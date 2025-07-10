import streamlit as st
from PyPDF2 import PdfReader
import openai

# Load OpenAI API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("PDF Summarizer")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    pdf_reader = PdfReader(uploaded_file)
    full_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    st.header("Extracted Text")
    st.write(full_text[:1000] + "...")  # show a preview of first 1000 chars

    if st.button("Summarize PDF"):
        with st.spinner("Summarizing..."):
            try:
                # Call OpenAI's Chat Completion API for summarization
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"Please summarize this text briefly:\n{full_text}"}
                    ],
                    max_tokens=300,
                    temperature=0.5,
                )
                summary = response['choices'][0]['message']['content']
                st.subheader("Summary")
                st.write(summary)
            except Exception as e:
                st.error(f"Error while summarizing: {e}")

else:
    st.write("Please upload a PDF file to extract and summarize its content.")
