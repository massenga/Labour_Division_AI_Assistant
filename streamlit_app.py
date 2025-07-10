import os
import streamlit as st
from PyPDF2 import PdfReader
import openai
import requests
from bs4 import BeautifulSoup

# Load API key
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

# App Title
st.title("Labour Division AI Assistant")

# Tabs for Use Cases
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
with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if st.button("Find Similar Judgments"):
        with st.spinner("Searching TanzLII..."):
            try:
                # TanzLII search URL
                search_url = f"https://tanzlii.org/judgments/TZHCLD?search_api_fulltext={query.replace(' ', '+')}"
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(search_url, headers=headers)
                soup = BeautifulSoup(response.text, "html.parser")

                results = soup.select("div.view-content .views-row")
                if not results:
                    st.warning("No similar cases found.")
                else:
                    st.subheader("Recent Similar Cases")
                    for case in results[:6]:  # limit to 6
                        title_tag = case.select_one(".title a")
                        if title_tag:
                            title = title_tag.text.strip()
                            link = "https://tanzlii.org" + title_tag["href"]
                            st.markdown(f"- [{title}]({link})")

            except Exception as e:
                st.error(f"Error retrieving cases: {e}")
