import os
import re
import time
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
def get_case_details(case_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    time.sleep(1)  # polite delay

    try:
        resp = requests.get(case_url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Initialize defaults
        outcome = "Not found"
        duration = "Not found"
        appeals = "Not found"

        # Look for headings related to outcome, appeals, duration
        for heading_text, attr_name in [
            ("outcome", "outcome"),
            ("decision", "outcome"),
            ("appeal", "appeals"),
            ("further proceedings", "appeals"),
            ("duration", "duration"),
            ("time frame", "duration"),
        ]:
            headings = soup.find_all(lambda tag: tag.name in ["h2", "h3"] and heading_text in tag.get_text(strip=True).lower())
            for h in headings:
                # Try to get next sibling paragraph or div text
                next_node = h.find_next_sibling(["p", "div"])
                if next_node:
                    text = next_node.get_text(strip=True)
                    if attr_name == "outcome" and outcome == "Not found":
                        outcome = text
                    elif attr_name == "appeals" and appeals == "Not found":
                        appeals = text
                    elif attr_name == "duration" and duration == "Not found":
                        duration = text

        # Fallback: try searching whole text for keywords (less reliable)
        page_text = soup.get_text(separator="\n").lower()
        if outcome == "Not found" and "outcome" in page_text:
            outcome = "Outcome mentioned in text."
        if appeals == "Not found" and "appeal" in page_text:
            appeals = "Appeal info mentioned in text."
        if duration == "Not found" and "duration" in page_text:
            duration = "Duration mentioned in text."

        return outcome, duration, appeals

    except Exception as e:
        return f"Error retrieving details: {e}", "", ""


with tab2:
    st.header("Search for Similar Cases on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if st.button("Find Similar Judgments"):
        with st.spinner("Searching TanzLII..."):
            try:
                search_url = "https://tanzlii.org/judgments/TZHCLD"
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(search_url, headers=headers)
                soup = BeautifulSoup(response.text, "html.parser")

                # Tokenize the query into words of length >= 3
                query_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))
                st.caption(f"Searching for keywords: {', '.join(query_tokens)}")

                results = []
                for case in soup.select("div.view-content .views-row"):
                    title_tag = case.select_one(".title a")
                    if not title_tag:
                        continue
                    title_text = title_tag.text.strip()
                    # Tokenize the case title
                    title_tokens = set(re.findall(r'\b\w{3,}\b', title_text.lower()))

                    # Check if any token from the query is in the title tokens
                    if query_tokens & title_tokens:
                        link = "https://tanzlii.org" + title_tag["href"]
                        results.append((title_text, link))

                    if len(results) >= 6:
                        break

                if results:
                    st.subheader("Recent Similar Cases")
                    for title, link in results:
                        st.markdown(f"### [{title}]({link})")
                        outcome, duration, appeals = get_case_details(link)

                        st.markdown(f"**Outcome:** {outcome}")
                        st.markdown(f"**Duration:** {duration}")
                        st.markdown(f"**Appeals:** {appeals}")
                        st.markdown("---")

                else:
                    st.warning("No similar cases found with those keywords.")

            except Exception as e:
                st.error(f"Error retrieving cases: {e}")
