import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup
import io

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


def fetch_and_summarize_cases(query, max_cases=6):
    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = soup.select('.gsc-webResult')

    cases = []
    for result in results[:max_cases]:
        title_el = result.select_one('.gs-title a')
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        link = title_el['href']

        # Get case page to find PDF link
        case_page = requests.get(link, headers=headers)
        if case_page.status_code != 200:
            continue
        case_soup = BeautifulSoup(case_page.text, 'html.parser')

        # Find first PDF link
        pdf_link = None
        for a in case_soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                if href.startswith('/'):
                    pdf_link = 'https://tanzlii.org' + href
                elif href.startswith('http'):
                    pdf_link = href
                else:
                    pdf_link = link.rsplit('/', 1)[0] + '/' + href
                break

        if not pdf_link:
            continue

        # Download PDF and extract text
        pdf_resp = requests.get(pdf_link, headers=headers)
        if pdf_resp.status_code != 200:
            continue
        pdf_bytes = io.BytesIO(pdf_resp.content)
        reader = PdfReader(pdf_bytes)
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
        if not full_text.strip():
            continue

        # Summarize with OpenAI
        prompt = (
            "Summarize the following labour court judgment into 5 key points, including: "
            "1) cause of dispute, 2) legal reasoning, 3) final ruling, "
            "4) cited laws, and 5) potential impact or precedent.\n\n"
            f"{full_text}"
        )
        try:
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
        except Exception as e:
            summary = f"Error summarizing judgment: {e}"

        # Extract date if available
        date_el = case_soup.find('time') or case_soup.find(class_='date')
        date_text = date_el.get_text(strip=True) if date_el else "Date not found"

        cases.append({
            "title": title,
            "link": link,
            "date": date_text,
            "summary": summary,
        })

    return cases


# --- Streamlit Tab 2 UI ---
with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if query:
        with st.spinner("Fetching and summarizing cases..."):
            cases = fetch_and_summarize_cases(query)

        search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        st.markdown(f"<small>[Click here to search TanzLII for '{query}']({search_url})</small>", unsafe_allow_html=True)

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
            st.warning("No matching summaries available. Try a broader keyword.")
