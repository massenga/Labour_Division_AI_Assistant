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

# --- Use Case 2: Similar Case Retrieval (Semantic Ranking) ---
with tab2:
    st.header("Search for Similar Labour Judgments (Semantic Ranking)")
    query = st.text_input("Enter your case topic (e.g., 'unfair termination due to pregnancy')")

    if st.button("Find Similar Judgments"):
        with st.spinner("Fetching cases and ranking…"):
            # 1) Scrape a batch of recent judgments
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": "Mozilla/5.0"}
            base = "https://tanzlii.org"
            listing = f"{base}/judgments/TZHCLD"
            candidates = []

            for page in range(3):  # first 3 pages ~30 cases
                resp = requests.get(listing, params={"page": page}, headers=headers, timeout=10)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                for row in soup.select("div.view-content .views-row"):
                    a = row.select_one(".title a")
                    if not a:
                        continue
                    title = a.text.strip()
                    link = base + a["href"]
                    candidates.append({"title": title, "link": link})
                if len(candidates) >= 30:
                    break

            if not candidates:
                st.warning("Could not fetch any judgments from TanzLII.")
                return

            # 2) Ask OpenAI to rank the top 6 relevant cases
            import openai
            # Build the prompt
            prompt = (
                "I will give you a legal query and a list of recent TanzLII Labour Division judgments.\n"
                "Please return the top 6 cases most relevant to the query, in JSON list form:\n"
                "[{ \"title\": ..., \"link\": ... }, ...]\n\n"
                f"Query: \"{query}\"\n\n"
                "Judgments:\n"
            )
            for c in candidates:
                prompt += f"- {c['title']} | {c['link']}\n"

            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a legal research assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=512,
                    temperature=0.0,
                )
                content = resp.choices[0].message.content.strip()
                # Parse JSON out of the response
                import json, re
                match = re.search(r"\[.*\]", content, re.S)
                selected = json.loads(match.group(0)) if match else []
            except Exception as e:
                st.error(f"Error ranking cases: {e}")
                return

            # 3) Display the selected top 6 cases
            if not selected:
                st.warning("No cases selected by the AI. Try broadening your query.")
            else:
                st.subheader("Top 6 Semantically Relevant Judgments")
                for case in selected:
                    title = case.get("title")
                    link = case.get("link")
                    st.markdown(f"- [{title}]({link})")
