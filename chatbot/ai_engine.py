import os
import math
from collections import Counter
from django.conf import settings
from functools import lru_cache
from groq import Groq

LANGUAGE_MODEL = "llama-3.1-8b-instant"

RAG_FILE_PATH = os.path.join(settings.BASE_DIR, "chatbot", "data", "rag.txt")

# Load dataset once
with open(RAG_FILE_PATH, "r", encoding="utf-8") as file:
    DATA_SET = [line.strip() for line in file.readlines() if line.strip()]

def get_words(text):
    # Simple word extraction
    return [w.lower() for w in text.split() if len(w) > 2]

# Pure Python Keyword Scoring (Replaces heavy scikit-learn TF-IDF)
def score_chunk(query_words, chunk_words):
    chunk_counter = Counter(chunk_words)
    score = 0
    for word in query_words:
        score += chunk_counter.get(word, 0)
    return score

def get_rag_response(user_query):
    # CRITICAL: Do NOT hardcode the API key in GitHub!
    # cPanel env variables are injected via Setup Python App
    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

    query_words = get_words(user_query)
    
    # Score all chunks based on matching words
    scored_chunks = []
    for chunk in DATA_SET:
        chunk_words = get_words(chunk)
        score = score_chunk(query_words, chunk_words)
        scored_chunks.append((score, chunk))
    
    # Sort by highest score first
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Take top 3 chunks (if they have a score > 0)
    context_chunks = [chunk for score, chunk in scored_chunks[:3] if score > 0]
    
    context_text = " ".join(context_chunks)

    instruction_prompt = (
        "You are TravelSync AI Assistant.\n"
        "Answer strictly based only on the provided context about bus travel.\n"
        "Do not create new information.\n"
        "If the answer is not present in the context, respond with:\n"
        "'The requested information is currently not available in the provided context.'\n\n"
        f"Context:\n{context_text}"
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': instruction_prompt},
                {'role': 'user', 'content': user_query}
            ],
            model=LANGUAGE_MODEL,
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Groq API Error: {e}")
        return "Sorry, I am having trouble connecting to my AI brain right now."