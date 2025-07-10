import os
import streamlit as st
from PyPDF2 import PdfReader
import openai

# Load OpenAI API key from environment or Streamlit secrets
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
st.write(f"API key loaded? {'Yes' if openai_api_key else 'No'}")

openai.api_key = openai_api_key

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
                        {"role": "system", "content": "You are a legal assistant AI that summarizes labor court judgments."},
                        {"role": "user", "content": f"""Summarize the following judgment into 5 bullet points focusing on:
1. Cause of dispute
2. Legal reasoning
3. Final ruling
4. Laws or precedents cited
5. Potential impact or implications

Text to summarize:
{text}
"""}
                    ],
                    max_tokens=600,
                    temperature=0.4,
                )
                summary = response.choices[0].message.content
                st.subheader("Summary")
                st.write(summary)
            except Exception as e:
                st.error(f"Error while summarizing: {e}")
else:
    st.write("Please upload a PDF file to extract and summarize text.")
