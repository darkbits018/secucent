import json
from bs4 import BeautifulSoup

def clean_guide_data(guide_data):
    """
    Converts the guide's JSON into clean, plain text using BeautifulSoup.
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
        return soup.get_text(separator="\n")  # Retains structure
    except Exception as e:
        print("❌ Failed to extract guide text:", e)
        return ""
