import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup

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
#with tab2:
    #st.header("Search for Similar Cases on TanzLII")
    #query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    #if query:
        #search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        #st.markdown(
            #f"<small>[Click here to search TanzLII for Similar cases to '{query}']({search_url})</small>",
            #unsafe_allow_html=True
        #)
from playwright.sync_api import sync_playwright

# Your Playwright scraper function
def scrape_tanzlii_cases(query, max_cases=6):
    search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}#gsc.tab=0"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url)

        # Wait for results container to load
        page.wait_for_selector('.gsc-webResult')

        search_results = page.query_selector_all('.gsc-webResult')
        for result in search_results[:max_cases]:
            title_el = result.query_selector('.gs-title a')
            if not title_el:
                continue
            title = title_el.inner_text()
            link = title_el.get_attribute('href')

            # Visit judgment page and scrape summary if possible
            page.goto(link)
            try:
                page.wait_for_selector('.judgment-body, .content, .judgment', timeout=5000)
            except:
                pass

            # Extract summary/outcome - heuristic selectors
            summary = None
            for sel in ['.judgment-body p', '.content p', '.judgment p']:
                el = page.query_selector(sel)
                if el:
                    summary = el.inner_text()
                    break

            # Extract date if possible
            date = None
            date_el = page.query_selector('time, .date, .judgment-date')
            if date_el:
                date = date_el.inner_text()

            results.append({
                "title": title,
                "link": link,
                "summary": summary if summary else "Summary not found",
                "date": date if date else "Date not found",
            })

            # Return to search results page
            page.goto(search_url)
            page.wait_for_selector('.gsc-webResult')

        browser.close()
    return results


# --- Use Case 2: Similar Case Retrieval ---
with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if query:
        search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        st.markdown(
            f"<small>[Click here to search TanzLII for Similar cases to '{query}']({search_url})</small>",
            unsafe_allow_html=True
        )

        if st.button("Fetch and Summarize Cases"):
            with st.spinner("Fetching cases from TanzLII..."):
                try:
                    cases = scrape_tanzlii_cases(query)
                    if cases:
                        st.subheader("Top Matching Cases:")
                        for case in cases:
                            st.markdown(f"""
                            <div style='font-size: 0.85rem; line-height: 1.5; margin-bottom: 1.5em;'>
                                <strong><a href="{case['link']}" target="_blank">{case['title']}</a></strong><br>
                                📅 <strong>Date:</strong> {case['date']}<br>
                                📄 <strong>Summary:</strong> {case['summary']}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No cases found for the given query.")
                except Exception as e:
                    st.error(f"Error fetching cases: {e}")

