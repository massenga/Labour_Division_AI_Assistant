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

def scrape_tanzlii_cases(query, max_cases=6):
    search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    result_blocks = soup.find_all('h5', class_='card-title', limit=max_cases)
    cases = []

    for block in result_blocks:
        # Extract title and link
        link_tag = block.find('a', class_='h5')
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        href = link_tag['href']
        full_link = "https://tanzlii.org" + href

        # Try to find date and summary in nearby elements
        meta = block.find_next('div', class_='mb-2')
        date = "Date not found"
        if meta:
            date_tag = meta.find('span', class_='me-3')
            if date_tag:
                date = date_tag.get_text(strip=True)

        # Get summary — first section’s text-muted content
        summary = "Summary not found"
        summary_div = block.find_next('div', class_='mb-1')
        if summary_div:
            summary_text = summary_div.find('div', class_='text-muted')
            if summary_text:
                summary = summary_text.get_text(strip=True)

        cases.append({
            "title": title,
            "link": full_link,
            "date": date,
            "summary": summary,
        })

    return cases


with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description")

    if query:
        cases = scrape_tanzlii_cases(query)
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
