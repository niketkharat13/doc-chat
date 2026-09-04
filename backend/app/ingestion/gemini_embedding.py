from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import GOOGLE_API_KEY, GEMINI_MODEL

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    api_key=GOOGLE_API_KEY,
)
