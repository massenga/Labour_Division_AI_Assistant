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
def fetch_pdf_summaries_from_search(search_query, max_pdfs=6, debug=False):
    search_url = f"https://tanzlii.org/search/?q={search_query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            if debug:
                print(f"Failed to fetch search results. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Get all case links from search page
        case_links = []
        for tag in soup.select("h5.card-title a"):
            href = tag.get("href")
            if href and href.startswith("/akn/"):
                case_links.append(urljoin(search_url, href))
                if len(case_links) >= max_pdfs:
                    break

        if debug:
            print(f"Found {len(case_links)} case links.")

        # From each case page, find the PDF link
        pdf_cases = []
        for case_url in case_links:
            case_resp = requests.get(case_url, headers=headers)
            if case_resp.status_code != 200:
                continue

            case_soup = BeautifulSoup(case_resp.text, "html.parser")
            pdf_tag = case_soup.find("a", string="Download", href=True)

            if pdf_tag:
                pdf_url = urljoin(case_url, pdf_tag["href"])
                pdf_cases.append(pdf_url)

                if debug:
                    print(f"Found PDF: {pdf_url}")

            if len(pdf_cases) >= max_pdfs:
                break

        if not pdf_cases:
            if debug:
                print("❌ No PDF judgments found for the given query.")
            return []

        # Summarize PDFs
        results = []
        for pdf_url in pdf_cases:
            try:
                pdf_resp = requests.get(pdf_url)
                pdf_resp.raise_for_status()

                reader = PdfReader(BytesIO(pdf_resp.content))
                text = ""
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"

                if not text.strip():
                    summary = "⚠️ No extractable text found in PDF."
                else:
                    prompt = (
                        "Summarize the following labour court judgment into 5 key points: "
                        "1) cause of dispute, 2) legal reasoning, 3) final ruling, "
                        "4) cited laws, and 5) potential impact or precedent.\n\n"
                        f"{text[:3000]}"
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

                results.append({
                    "pdf_url": pdf_url,
                    "summary": summary
                })

            except Exception as e:
                results.append({
                    "pdf_url": pdf_url,
                    "summary": f"❌ Error processing PDF: {e}"
                })

        return results

    except Exception as e:
        if debug:
            print(f"Unexpected error: {e}")
        return []


with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if query:
        search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        st.markdown(
            f"<small>[Click here to search TanzLII for Similar cases to '{query}']({search_url})</small>",
            unsafe_allow_html=True
        )

        with st.spinner("Fetching and summarizing PDF judgments... this may take a while"):
            cases = fetch_and_summarize_pdfs(query, max_cases=6)

        if cases:
            for idx, case in enumerate(cases, start=1):
                st.subheader(f"Case {idx}: {case['title']}")
                st.markdown(f"[Download PDF]({case['pdf_url']})", unsafe_allow_html=True)
                st.write(case["summary"])
        else:
            st.warning("No PDF judgments found for the given query. Try a broader keyword.")
