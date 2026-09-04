from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GOOGLE_API_KEY, GEMINI_MODEL

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    api_key=GOOGLE_API_KEY,
    temperature=0.7,
)

