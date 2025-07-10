import os
import re
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup

# Load OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

st.title("Labour Division AI Assistant")
tab1, tab2 = st.tabs(["📄 Judgment Summarization", "🔍 Similar Case Retrieval"])

# --- Use Case 1: Summarization ---
with tab1:
    st.header("Upload a Judgment PDF to Summarize")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file:
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
with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if st.button("Find Similar Judgments"):
        with st.spinner("Scraping multiple pages from TanzLII and filtering results..."):
            try:
                base_url = "https://tanzlii.org"
                judgments_base = f"{base_url}/judgments/TZHCLD"
                headers = {"User-Agent": "Mozilla/5.0"}
                max_pages = 10  # scrape up to 10 pages (~100 judgments)
                collected_cases = []

                # Normalize query to lower for filtering
                query_lower_words = set(word.lower() for word in re.findall(r'\w+', query))

                for page_num in range(max_pages):
                    url = f"{judgments_base}?page={page_num}"
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        st.warning(f"Failed to fetch page {page_num+1}, status code {resp.status_code}")
                        break
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cases = soup.select("div.view-content .views-row")
                    if not cases:
                        # No more pages
                        break

                    for case in cases:
                        title_tag = case.select_one(".title a")
                        summary_tag = case.select_one(".field-content")
                        if not title_tag:
                            continue
                        title = title_tag.text.strip()
                        summary = summary_tag.text.strip() if summary_tag else ""
                        link = base_url + title_tag['href']

                        # Filter locally by query keywords in title or summary
                        title_words = set(word.lower() for word in re.findall(r'\w+', title))
                        summary_words = set(word.lower() for word in re.findall(r'\w+', summary))
                        if query_lower_words & (title_words | summary_words):
                            collected_cases.append((title, link))
                            if len(collected_cases) >= 6:
                                break
                    if len(collected_cases) >= 6:
                        break

                if not collected_cases:
                    st.warning("No similar cases found matching your query in recent judgments.")
                else:
                    st.subheader("Similar Judgments Found")
                    for title, link in collected_cases:
                        # Optional: Fetch a snippet about the outcome (best effort)
                        snippet = ""
                        try:
                            case_resp = requests.get(link, headers=headers, timeout=10)
                            if case_resp.status_code == 200:
                                case_soup = BeautifulSoup(case_resp.text, "html.parser")
                                outcome_candidates = case_soup.find_all(string=re.compile(r'(outcome|decision|result|ruling)', re.I))
                                if outcome_candidates:
                                    parent_text = outcome_candidates[0].parent.get_text(strip=True)
                                    snippet = f" **(Excerpt: {parent_text[:150]}...)**"
                        except Exception:
                            pass
                        st.markdown(f"- [{title}]({link}){snippet}")

            except Exception as e:
                st.error(f"Error during scraping or processing: {e}")
