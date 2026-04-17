from langchain.chat_models import init_chat_model
import os

try:
    llm = init_chat_model("gemini-1.5-flash", model_provider="google_genai")
    print(f"Success: {type(llm)}")
except Exception as e:
    print(f"Error: {e}")
