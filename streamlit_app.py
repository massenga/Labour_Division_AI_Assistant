import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup
import feedparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin
from io import BytesIO

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
def fetch_download_links_selenium(query, max_links=5):
    base_url = "https://tanzlii.org"
    search_url = f"{base_url}/search/?q={query.replace(' ', '+')}"
    
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=opts)
        driver.get(search_url)
        driver.implicitly_wait(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
    except Exception as e:
        return [f"❌ Error: {str(e)}"]

    links = []
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "download":
            full = urljoin(base_url, a["href"])
            links.append(full)
            if len(links) >= max_links:
                break

    return links if links else ["Still not working"]

with tab2:
    st.header("Search TanzLII Download Links (First 5)")

    query = st.text_input("Enter legal search query (e.g. 'wrongful termination')")

    if query:
        with st.spinner("Searching and extracting download links..."):
            links = fetch_download_links_selenium(query)

        if links and isinstance(links[0], str) and links[0].startswith("http"):
            for i, link in enumerate(links, 1):
                st.markdown(f"**Link {i}:** [Download Judgment]({link})", unsafe_allow_html=True)
        else:
            st.warning(links[0])  # show error or "No download links found"
