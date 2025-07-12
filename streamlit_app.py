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

#with tab2:
    #st.header("Search for Similar Cases on TanzLII")
    #query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    #if query:
        #search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        #st.markdown(f"### [Click here to search TanzLII for '{query}']({search_url})")

# --- Use Case 2: Similar Case Retrieval ---
with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter keywords (e.g., 'unfair termination due to pregnancy')")

    def search_tanzlii_judgments(query, max_pages=5, max_results=6):
        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://tanzlii.org"
        results = []
        query_tokens = set(query.lower().split())

        for page_num in range(max_pages):
            page_url = f"{base_url}/judgments/TZHCLD?page={page_num}"
            resp = requests.get(page_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for case_div in soup.select("div.view-content .views-row"):
                title_tag = case_div.select_one(".title a")
                if not title_tag:
                    continue
                title = title_tag.text.strip()
                title_tokens = set(title.lower().split())
                if query_tokens & title_tokens:
                    link = base_url + title_tag["href"]
                    results.append((title, link))
                    if len(results) >= max_results:
                        return results
        return results

    if st.button("Find Similar Judgments"):
        with st.spinner("Scraping TanzLII for judgments..."):
            matches = search_tanzlii_judgments(query)
            if matches:
                st.subheader("Matching Judgments")
                for title, link in matches:
                    st.markdown(f"- [{title}]({link})")
            else:
                st.warning("No similar cases found. Try more general keywords.")
