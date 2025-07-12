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

def fetch_judgments(query, max_results=6):
    headers = {"User-Agent": "Mozilla/5.0"}
    base_url = "https://tanzlii.org"
    results = []

    for page in range(3):  # Check first 3 pages
        url = f"{base_url}/judgments/TZHCLD?page={page}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("div.view-content .views-row"):
            title_tag = row.select_one(".title a")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link = base_url + title_tag.get("href")
            if query.lower() in title.lower():
                summary = extract_summary(link)
                results.append({
                    "title": title,
                    "link": link,
                    **summary
                })
            if len(results) >= max_results:
                return results
    return results

def extract_summary(link):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Get the judgment date from the metadata
        meta_date = soup.select_one('span.date-display-single')
        date = meta_date.text.strip() if meta_date else "Unknown"

        # Simple heuristic extraction
        full_text = soup.get_text(separator='\n')
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        outcome = next((l for l in lines if "outcome" in l.lower() or "ordered" in l.lower()), "Outcome not found")
        appeal = next((l for l in lines if "appeal" in l.lower()), "No appeal info found")
        duration = next((l for l in lines if "employment" in l.lower() or "years" in l.lower()), "N/A")

        return {
            "date": date,
            "summary": outcome,
            "duration": duration,
            "appeal": appeal
        }
    except:
        return {
            "date": "Unknown",
            "summary": "Summary not available.",
            "duration": "N/A",
            "appeal": "N/A"
        }

# --- Streamlit Tab2 ---
with tab2:
    st.header("Search for Similar Cases on TanzLII")

    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if not query:
        st.info("Please enter a description to search.")
    else:
        search_url = f"https://tanzlii.org/search/?suggestion=&q={query.replace(' ', '+')}#gsc.tab=0"
        st.markdown(f"<p style='font-size: 0.85rem;'><a href='{search_url}' target='_blank'>🔎 View full search results on TanzLII</a></p>", unsafe_allow_html=True)

        with st.spinner("Fetching similar judgments..."):
            cases = fetch_judgments(query)

        if cases:
            st.subheader("Top Matching Cases:")
            for case in cases:
                st.markdown(f"""
                <div style='font-size: 0.85rem; line-height: 1.5; margin-bottom: 1.5em;'>
                    <strong><a href="{case['link']}" target="_blank">{case['title']}</a></strong><br>
                    📅 <strong>Date:</strong> {case['date']}<br>
                    📄 <strong>Outcome:</strong> {case['summary']}<br>
                    ⏳ <strong>Duration:</strong> {case['duration']}<br>
                    🔁 <strong>Appeal:</strong> {case['appeal']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No similar cases found. Try broader or different keywords.")
