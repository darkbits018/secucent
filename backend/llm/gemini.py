import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_name = "models/embedding-001"
gen_model = genai.GenerativeModel("gemini-2.0-flash")


def embed_text(text: str, is_query: bool = False) -> list:
    task_type = "retrieval_query" if is_query else "retrieval_document"
    response = genai.embed_content(
        model=model_name,
        content=text,
        task_type=task_type
    )
    return response["embedding"]


def generate_answer(prompt: str) -> str:
    response = gen_model.generate_content(prompt)
    return response.text.strip()
