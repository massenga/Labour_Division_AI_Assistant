import os, re, requests, streamlit as st
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import openai

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

st.title("Labour Division AI Assistant")
tab1, tab2 = st.tabs(["📄 Summarization", "🔍 Similar Cases"])

# Tab 1: Summarization (unchanged) …
with tab1:
    st.header("Upload Judgment PDF")
    pdf = st.file_uploader("", type="pdf")
    if pdf:
        text = ""
        for p in PdfReader(pdf).pages:
            t = p.extract_text() or ""
            text += t + "\n"
        st.text_area("Extracted Text", text, height=200)
        if st.button("Summarize"):
            with st.spinner("Summarizing..."):
                try:
                    prompt = (
                        "Summarize into 5 key points: 1) cause, 2) reasoning, "
                        "3) ruling, 4) cited laws, 5) impact.\n\n" + text
                    )
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role":"user","content":prompt}],
                        max_tokens=500, temperature=0.4
                    )
                    st.write(resp.choices[0].message.content)
                except Exception as e:
                    st.error(e)

# Tab 2: Similar Cases with better filtering …
with tab2:
    st.header("Find Similar Labour Judgments")
    query = st.text_input("Enter keywords (e.g., 'unfair termination pregnancy')")
    if st.button("Search"):
        with st.spinner("Searching TanzLII..."):
            matched = []
            url_base = "https://tanzlii.org"
            url = url_base + "/judgments/TZHCLD"
            headers = {"User-Agent": "Mozilla/5.0"}
            qtext = query.lower().strip()

            for pg in range(15):  # includes ~15 pages
                r = requests.get(url, params={"page": pg}, headers=headers, timeout=10)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.select("div.view-content .views-row")
                if not rows:
                    break

                for row in rows:
                    a = row.select_one(".title a")
                    if not a:
                        continue
                    title = a.text.strip()
                    link = url_base + a["href"]
                    block = (title + " " + (row.select_one(".field-content").text if row.select_one(".field-content") else "")).lower()
                    if qtext in block:
                        matched.append((title, link))
                    if len(matched) >= 6:
                        break
                if len(matched) >= 6:
                    break

            if not matched:
                st.warning("✅ No matching cases found in recent judgments.")
            else:
                st.subheader("Matched Judgments")
                for title, link in matched:
                    st.markdown(f"- [{title}]({link})")
