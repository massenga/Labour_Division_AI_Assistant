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

# --- Use Case 2: Similar Case Retrieval ---
with tab2:
    st.header("Search for Similar Cases on TanzLII")

    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if not query:
        st.info("Please enter a description to search.")
    else:
        # TanzLII search URL
        search_url = f"https://tanzlii.org/search/?suggestion=&q={query.replace(' ', '+')}#gsc.tab=0"
        st.markdown(f"<small>[🔎 View full search results on TanzLII]({search_url})</small>", unsafe_allow_html=True)

        # Simulated cases for known keywords
        if "unfair termination" in query.lower():
            st.subheader("Top Matching Cases:")

            cases = [
                {
                    "title": "Standard Chartered Bank vs Anitha Rukoijo (2022)",
                    "link": "https://media.tanzlii.org/media/judgment/151493/source_file/standard-chartered-bank-vs-anitha-rukoijo-2022-tzhcld-122-8-march-2022.pdf",
                    "date": "8 March 2022",
                    "summary": "Termination was found to be unfair due to lack of fair hearing.",
                    "duration": "N/A",
                    "appeal": "No appeal noted."
                },
                {
                    "title": "Viettel Tanzania Ltd vs Esther Ndudumizi (2020)",
                    "link": "https://media.tanzlii.org/media/judgment/213366/source_file/viettel-tanzania-l-t-d-vs-esther-ndudumizi-2020-tzhc-4278-10-july-2020.pdf",
                    "date": "10 July 2020",
                    "summary": "Employer ordered to pay 24 months' salary for unlawful dismissal.",
                    "duration": "Over 3 years",
