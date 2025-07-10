import os, re, requests, streamlit as st
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import openai

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

st.title("Labour Division AI Assistant")
tab1, tab2 = st.tabs(["📄 Summarization", "🔍 Similar Cases"])

# --- Tab 1: PDF Summarization ---
with tab1:
    st.header("Upload Judgment PDF")
    uploaded = st.file_uploader("", type="pdf")
    if uploaded:
        text = ""
        for p in PdfReader(uploaded).pages:
            t = p.extract_text()
            if t: text += t + "\n"
        st.write(text)
        if st.button("Summarize"):
            with st.spinner("Working..."):
                prompt = (
                    "Summarize into 5 key points: 1) cause, 2) legal reasoning, "
                    "3) ruling, 4) cited laws, 5) impact.\n\n" + text
                )
                try:
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role":"user","content":prompt}],
                        max_tokens=500, temperature=0.4
                    )
                    st.write(resp.choices[0].message.content)
                except Exception as e:
                    st.error(e)

# --- Tab 2: Similar Case Retrieval ---
with tab2:
    st.header("Find Similar Labour Judgments")
    query = st.text_input("Keywords (e.g., 'unfair termination pregnancy')")

    if st.button("Search"):
        with st.spinner("Searching TanzLII..."):
            matches = []
            base = "https://tanzlii.org"
            url = base + "/judgments/TZHCLD"
            headers = {"User-Agent": "Mozilla/5.0"}

            # Scrape first 5 pages (~50 cases)
            for pg in range(5):
                resp = requests.get(url, params={"page": pg}, headers=headers, timeout=10)
                if resp.status_code != 200: break
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("div.view-content .views-row")
                if not rows: break

                for row in rows:
                    ttag = row.select_one(".title a")
                    summary = row.select_one(".field-content")
                    if not ttag: continue
                    title = ttag.text.strip()
                    summ = summary.text.strip() if summary else ""
                    tokens = set(re.findall(r"\w+", (title + " " + summ).lower()))

                    # Check intersection with query tokens
                    q_tokens = set(re.findall(r"\w+", query.lower()))
                    if q_tokens & tokens:
                        link = base + ttag["href"]
                        matches.append((title, link))
                if len(matches) >= 6:
                    break

            if not matches:
                st.warning("No similar cases found in recent judgments.")
            else:
                st.subheader("Matched Judgments")
                for title, link in matches[:6]:
                    st.markdown(f"- [{title}]({link})")
