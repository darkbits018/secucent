import streamlit as st
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.fetch_guides import fetch_guides
from llm.answer import answer_question

st.set_page_config(page_title="Lab Guide Assistant", page_icon="🧪", layout="wide")

st.title("🧠 Lab Guide Assistant")
st.markdown("Ask questions based on the selected lab guide.")

with st.sidebar:
    st.info("💡 Select a guide, enter a question, and press Ask to get a RAG+LLM-based answer!")
    st.title("Sample Questions")
    st.info("What is the purpose of using FTK Imager in digital forensics [guide 21]")
    st.info("What is the difference between an AD1 and E01 image [guide 21]")
    st.info("What are the objectives of this lab [guide 21]")

guides = fetch_guides()
guide_options = {f"Guide {g['id']}": g["id"] for g in guides}
selected_guide_label = st.selectbox("Select Lab Guide", list(guide_options.keys()))
guide_id = guide_options[selected_guide_label]

question = st.text_input("Enter your question:")

if st.button("Ask") and question.strip():
    with st.spinner("Thinking..."):
        try:
            answer = answer_question(guide_id, question)
            if "**Details:**" in answer:
                main_answer, details = answer.split("**Details:**", 1)
            else:
                main_answer, details = answer, ""

            st.markdown("### 💬 Answer")
            st.success(main_answer.strip())

            if details.strip():
                with st.expander("🔎 View Source Details"):
                    st.code(details.strip(), language="markdown")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
