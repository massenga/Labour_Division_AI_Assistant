import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup
import feedparser

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

def fetch_filtered_judgments(search_term, max_items=6):
    feed_url = "https://tanzlii.org/feeds/all.xml"
    feed = feedparser.parse(feed_url)

    filtered = []
    search_term_lower = search_term.lower()

    for entry in feed.entries:
        title = entry.title.lower()
        summary = entry.summary.lower() if hasattr(entry, 'summary') else ""
        
        if search_term_lower in title or search_term_lower in summary:
            filtered.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published if hasattr(entry, 'published') else "No date",
                "summary": entry.summary if hasattr(entry, 'summary') else "No summary",
            })
            if len(filtered) >= max_items:
                break

    return filtered

with tab2:
    st.header("Search for Similar Cases on TanzLII (via RSS Feed)")

    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if query:
        cases = fetch_filtered_judgments(query, max_items=6)

        if cases:
            st.subheader(f"Top matching cases for '{query}':")
            for case in cases:
                st.markdown(f"### [{case['title']}]({case['link']})")
                st.markdown(f"**Published:** {case['published']}")
                st.markdown(f"**Summary:** {case['summary']}")
                st.markdown("---")
        else:
            st.warning("No matching summaries available. Try a broader keyword.")
    else:
        st.info("Please enter a keyword to search judgments.")
