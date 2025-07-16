import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup
import feedparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote_plus, urljoin
from io import BytesIO
from playwright.sync_api import sync_playwright

# Load OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

# App Title
st.title("Labour Division AI Assistant")

# Tabs
tab1, tab2 = st.tabs(["📄 Judgment Summarization", "🔍 Similar Case Retrieval"])

# --- Use Case 1: Summarization ---
with tab1:
    st.header("Upload a Judgment PDF to Summarize")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file is not None:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"

        st.subheader("Extracted Text")
        st.write(text)

        if st.button("Summarize Judgment"):
            with st.spinner("Summarizing..."):
                try:
                    prompt = (
                        "Summarize the following labour court judgment into 5 key points. "
                        "The summary must include: 1) cause of dispute, 2) legal reasoning, "
                        "3) final ruling, 4) cited laws, and 5) potential impact or precedent.\n\n"
                        f"{text}"
                    )

                    response = openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a legal assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.4
                    )
                    summary = response.choices[0].message.content
                    st.subheader("Summary")
                    st.write(summary)
                except openai.error.RateLimitError:
                    st.error("OpenAI quota exceeded. Please check your billing.")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Please upload a PDF to summarize.")

# --- Use Case 2: Similar Case Retrieval ---

def generate_search_url(search_query):
    base_url = "https://tanzlii.org"
    encoded_query = quote_plus(search_query)
    search_url = f"{base_url}/search/?suggestion=&q={encoded_query}#gsc.tab=0"
    site_url = search_url.read()
    extracted_links = re.findall('"((http)s?://.*?)"', str(site_url))
    return extracted_links

with tab2:
    st.header("Generate TanzLII Search URL")
    query = st.text_input("Enter case description (e.g., 'termination of employment')")

    if query:
        with st.spinner("Generating search link..."):
            search_url = generate_search_url(query)

        st.markdown("### 🔗 TanzLII Search URL:")
        st.markdown(f"[{search_url}]({search_url})", unsafe_allow_html=True)
