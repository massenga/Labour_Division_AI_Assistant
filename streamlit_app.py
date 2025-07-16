import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup
import feedparser
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
def fetch_first_5_download_links(search_query):
    base_url = "https://tanzlii.org"
    search_url = f"{base_url}/search/?q={search_query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(search_url, headers=headers)
    except Exception as e:
        return [{"error": f"❌ Request failed: {e}"}]

    if response.status_code != 200:
        return [{"error": f"❌ Failed to fetch search results. Status code: {response.status_code}"}]

    soup = BeautifulSoup(response.text, 'html.parser')
    download_links = []

    for a in soup.find_all('a', href=True):
        if a.get_text(strip=True).lower() == "download":
            full_url = urljoin(base_url, a['href'])
            download_links.append(full_url)
            if len(download_links) == 5:
                break

    if not download_links:
        return [{"message": "No download links found."}]

    return [{"link": url} for url in download_links]

with tab2:
    st.header("First 5 TanzLII Download Links")
    query = st.text_input("Search TanzLII (e.g. 'probation dismissal')")

    if query:
        with st.spinner("Searching TanzLII..."):
            links = fetch_first_5_download_links(query)

        for i, item in enumerate(links, 1):
            if "link" in item:
                st.markdown(f"**Link {i}:** [Download Judgment]({item['link']})", unsafe_allow_html=True)
            elif "error" in item:
                st.error(item["error"])
            elif "message" in item:
                st.info(item["message"])
