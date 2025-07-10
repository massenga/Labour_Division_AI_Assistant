import os
import streamlit as st
import openai
import requests
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup

# Load API Key
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

st.title("Labour Division AI Assistant")

# --- Use Case 1: PDF Summarization ---
st.header("📄 Use Case 1: Judgment Summarization")
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"], key="pdf_upload")

if uploaded_file:
    pdf_reader = PdfReader(uploaded_file)
    full_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    st.subheader("Extracted Text")
    st.write(full_text[:1000] + "...")  # Preview first 1000 characters

    if st.button("Summarize Judgment"):
        with st.spinner("Summarizing judgment..."):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a legal assistant. Summarize judgments in 5 key points: (1) cause of dispute, (2) legal reasoning, (3) ruling, (4) cited laws, and (5) impact or implications."},
                        {"role": "user", "content": full_text}
                    ],
                    max_tokens=500,
                    temperature=0.4,
                )
                summary = response.choices[0].message.content
                st.success("Summary Generated:")
                st.write(summary)
            except openai.error.RateLimitError:
                st.error("❌ OpenAI quota exceeded. Check your billing.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- Use Case 2: Similar Case Retrieval ---
st.header("🔍 Use Case 2: Similar Case Retrieval")
query = st.text_input("Enter case description (e.g., unfair termination due to pregnancy)", key="case_query")

def fetch_similar_cases(query, max_cases=6):
    url = "https://tanzlii.org/judgments/TZHCLD"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    cases = []

    for row in soup.find_all("div", class_="views-row"):
        title_tag = row.find("h3")
        link_tag = row.find("a", href=True)
        if not title_tag or not link_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = "https://tanzlii.org" + link_tag['href']

        # Flexible keyword matching
        if any(keyword in title.lower() for keyword in query.lower().split()):
            cases.append((title, link))
        if len(cases) >= max_cases:
            break

    return cases

if st.button("Find Similar Cases"):
    with st.spinner("Searching TanzLII..."):
        try:
            results = fetch_similar_cases(query)
            if results:
                st.subheader("📚 Similar Cases Found:")
                for i, (title, link) in enumerate(results, 1):
                    st.markdown(f"{i}. [{title}]({link})")
            else:
                st.warning("No similar cases found. Try different or simpler keywords.")
        except Exception as e:
            st.error(f"Error fetching cases: {e}")
