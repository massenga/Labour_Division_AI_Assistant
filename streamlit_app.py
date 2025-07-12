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
    st.header("Find Similar Labour Judgments on TanzLII")
    query = st.text_input("Enter case description (e.g., 'unfair termination due to pregnancy')")

    if st.button("Search and Summarize Cases"):
        headers = {"User-Agent": "Mozilla/5.0"}
        base = "https://tanzlii.org"
        listing = f"{base}/judgments/TZHCLD"
        max_pages = 5
        limit = 6
        found = []
        q = query.lower().strip()

        # 1) Find matching case titles & links
        for pg in range(max_pages):
            resp = requests.get(listing, params={"page": pg}, headers=headers, timeout=10)
            if resp.status_code != 200:
                break
            page_soup = BeautifulSoup(resp.text, "html.parser")
            rows = page_soup.select("div.view-content .views-row")
            if not rows:
                break

            for row in rows:
                a = row.select_one(".title a")
                if not a:
                    continue
                title = a.text.strip()
                if q not in title.lower():
                    continue
                link = base + a["href"]
                found.append((title, link))
                if len(found) >= limit:
                    break
            if len(found) >= limit:
                break

        # 2) For each match, fetch details and display
        if not found:
            st.warning("No similar cases found. Try a broader keyword.")
        else:
            st.subheader("Top Matching Judgments")
            for title, link in found:
                # Fetch judgment page
                case_resp = requests.get(link, headers=headers, timeout=10)
                case_soup = BeautifulSoup(case_resp.text, "html.parser")

                # Extract Cause: first paragraph of body
                paras = [p.get_text(strip=True)
                         for p in case_soup.select("div.field--name-body p")]
                cause = paras[0] if paras else "Not found"

                # Extract Outcome
                outcome = "Not found"
                for heading in case_soup.find_all(["h2","h3"]):
                    h = heading.get_text(strip=True).lower()
                    if "outcome" in h or "decision" in h:
                        sib = heading.find_next_sibling(["p","div"])
                        if sib:
                            outcome = sib.get_text(strip=True)
                        break

                # Extract a date (judgment date) and estimate duration
                import re
                all_text = case_soup.get_text(separator=" ")
                dates = re.findall(r"\b\d{1,2}\s+\w+\s+\d{4}\b", all_text)
                duration = dates[-1] if dates else "Date not found"

                # Extract Appeals
                appeals = "None recorded"
                for heading in case_soup.find_all(["h2","h3"]):
                    h = heading.get_text(strip=True).lower()
                    if "appeal" in h:
                        sib = heading.find_next_sibling(["p","div"])
                        if sib:
                            appeals = sib.get_text(strip=True)
                        break

                # Render
                st.markdown(f"### [{title}]({link})")
                st.markdown(f"- **Cause:** {cause}")
                st.markdown(f"- **Outcome:** {outcome}")
                st.markdown(f"- **Duration/Date:** {duration}")
                st.markdown(f"- **Appeals:** {appeals}")
                st.markdown("---")

