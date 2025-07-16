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
import re

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

import re
import requests
from requests_html import HTMLSession

def fetch_links_with_js(search_query):
    base_url = "https://tanzlii.org"
    encoded_query = quote_plus(search_query)
    search_url = f"{base_url}/search/?suggestion=&q={encoded_query}#gsc.tab=0"

    session = HTMLSession()
    r = session.get(search_url)
    r.html.render(sleep=2)  # render JS, wait 2 seconds

    # Extract links that start with /akn/tz/judgment
    links = []
    for a in r.html.find('a'):
        href = a.attrs.get('href', '')
        if href.startswith('/akn/tz/judgment'):
            full_url = urljoin(base_url, href)
            links.append(full_url)

    return search_url, links

with st.sidebar:
    st.header("TanzLII JS Search")
    query = st.text_input("Enter search query")

    if query:
        with st.spinner("Rendering JS and fetching links..."):
            search_url, links = fetch_links_with_js(query)

        st.markdown(f"### Search URL\n[{search_url}]({search_url})")

        if links:
            st.markdown("### Extracted Judgment Links")
            for i, link in enumerate(links, 1):
                st.markdown(f"{i}. [{link}]({link})")
        else:
            st.info("No judgment links found.")
