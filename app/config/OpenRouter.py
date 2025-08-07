import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load from .env
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

# Validate
if not api_key:
    raise EnvironmentError("❌ OPENROUTER_API_KEY not found in .env file")

if not google_api_key:
    raise EnvironmentError("❌ GOOGLE_API_KEY not found in .env file")

# COST OPTIMIZATION: Use Gemini 8B (cheaper) with balanced production settings
# Gemini-1.5-Flash-8B is ~50% cheaper than regular Gemini-1.5-Flash
# llm = ChatGoogleGenerativeAI(
#     model="models/gemini-1.5-flash",  # UPDATED: Using 8B model for cost savings
#     temperature=0.3,
#     google_api_key=google_api_key,
#     # max_output_tokens=1024,  # BALANCED: Increased from 512 for better accuracy
#     # convert_system_message_to_human=True
# )

# OpenRouter backup configuration (commented out to prevent double billing)
# Uncomment only if Google API fails and you need fallback

llm = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key,
    model_name="sarvamai/sarvam-m:free",  
    temperature=0.3,
    # max_tokens=1024,  # BALANCED: Increased token limit
    # request_timeout=30,  # Add timeout to prevent hanging requests
)
def get_llm_model(model_name, temperature=0.3, max_tokens=1024):
    """
    Returns a ChatOpenAI object for the given model name using OpenRouter.
    """
    return ChatOpenAI(
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        # request_timeout=30,
    )

# Export the primary LLM and new functions for consistent usage across the app
__all__ = ['llm']


