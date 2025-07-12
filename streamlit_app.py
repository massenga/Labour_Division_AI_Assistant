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
        #st.markdown(f"### [Click here to search TanzLII for Similar cases to '{query}']({search_url})")

#with tab2:
    #st.header("Search for Similar Cases on TanzLII")
    #query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    #if query:
        #search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        #st.markdown(
            #f"<small>[Click here to search TanzLII for Similar cases to '{query}']({search_url})</small>",
            #unsafe_allow_html=True
        #)

def fetch_search_results(query, max_cases=6):
    # Prepare URL (replace spaces with +)
    search_url = f"https://tanzlii.org/search/?suggestion=&q={query.replace(' ', '+')}#gsc.tab=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Find judgment links and titles from search results
    # TanzLII search results contain <a> tags with class 'gs-title' for links
    cases = []
    for a in soup.select('a.gs-title')[:max_cases]:
        href = a.get('href')
        title = a.get_text(strip=True)
        if href and title and href.startswith('/'):
            full_link = 'https://tanzlii.org' + href
            cases.append({"title": title, "link": full_link})

    return cases

def fetch_case_details(case_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(case_url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Attempt to extract date - usually in <div class="judgment-details"> or similar
    date = "Date not found"
    date_div = soup.find('div', class_='judgment-details')
    if date_div:
        # Often contains date text, let's extract something that looks like a date
        import re
        date_match = re.search(r'\d{1,2} \w+ \d{4}', date_div.text)
        if date_match:
            date = date_match.group()

    # For summary/outcome, try to get first paragraph of the judgment text
    summary = "Summary not found"
    # Judgments are often inside <div class="judgment-body"> or <div id="body">
    body_div = soup.find('div', class_='judgment-body') or soup.find('div', id='body')
    if body_div:
        paragraphs = body_div.find_all('p')
        if paragraphs:
            summary = paragraphs[0].get_text(strip=True)[:500]  # first 500 chars as snippet

    # Duration and Appeal are complex and may require deeper NLP or manual extraction
    duration = "N/A"
    appeal = "N/A"

    return {
        "date": date,
        "summary": summary,
        "duration": duration,
        "appeal": appeal
    }

with st.sidebar:
    st.title("TanzLII Judgment Search")

tab1, tab2 = st.tabs(["Search", "Results"])

with tab1:
    st.header("Search TanzLII for Judgments")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

with tab2:
    if not query:
        st.info("Please enter a description to search.")
    else:
        st.markdown(f"<p style='font-size: 0.85rem;'><a href='https://tanzlii.org/search/?suggestion=&q={query.replace(' ', '+')}#gsc.tab=0' target='_blank'>🔎 View full search results on TanzLII</a></p>", unsafe_allow_html=True)

        with st.spinner("Fetching cases..."):
            cases = fetch_search_results(query)

        if not cases:
            st.warning("No cases found.")
        else:
            st.subheader(f"Top {len(cases)} Judgments:")

            for idx, case in enumerate(cases):
                with st.expander(f"{idx+1}. {case['title']}"):
                    details = fetch_case_details(case["link"])
                    st.markdown(f"""
                    📅 **Date:** {details['date']}  
                    📄 **Summary (snippet):** {details['summary']}  
                    ⏳ **Duration:** {details['duration']}  
                    🔁 **Appeal:** {details['appeal']}  
                    🔗 [View Full Judgment]({case['link']})
                    """, unsafe_allow_html=True)

