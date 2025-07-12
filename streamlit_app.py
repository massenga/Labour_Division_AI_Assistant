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

with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if query:
        search_url = f"https://tanzlii.org/search/?q={query.replace(' ', '+')}"
        st.markdown(f"### [Full TanzLII search results for '{query}']({search_url})")

        with st.spinner("Fetching cases..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(search_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    st.error(f"Failed to retrieve search results (status {response.status_code})")
                else:
                    soup = BeautifulSoup(response.text, "html.parser")
                    # Each search result usually inside div with class 'gs-title' or similar
                    results = []
                    # Look for search result links
                    # TanzLII search results have links inside <div class="gs-title"><a href=...>
                    for item in soup.select("div.gs-title a"):
                        title = item.get_text(strip=True)
                        link = item['href']
                        if not link.startswith("http"):
                            link = "https://tanzlii.org" + link
                        results.append((title, link))
                        if len(results) >= 6:
                            break

                    if results:
                        st.subheader("Top 6 Similar Cases")
                        for title, link in results:
                            st.markdown(f"- [{title}]({link})")
                    else:
                        st.warning("No cases found in the search results.")
            except Exception as e:
                st.error(f"Error fetching search results: {e}")

