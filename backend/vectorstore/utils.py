import json
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


def clean_guide_data(guide_data):
    """
    Converts the guide's JSON into clean plain text by stripping HTML tags.
    """
    try:
        parsed = json.loads(guide_data)
        if not isinstance(parsed, dict):
            return ""

        all_html = ""
        for _, section in parsed.items():
            if isinstance(section, dict):
                inner_sections = section.get("sections", {})
                for _, subsection in inner_sections.items():
                    html = subsection.get("content", {}).get("value", "")
                    all_html += html + "\n"

        soup = BeautifulSoup(all_html, "html.parser")
        return soup.get_text(separator="\n")
    except Exception as e:
        print("❌ Failed to extract guide text:", e)
        return ""


def chunk_text(text, chunk_size=500, chunk_overlap=100):
    """
    Splits the cleaned text into overlapping chunks.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)
