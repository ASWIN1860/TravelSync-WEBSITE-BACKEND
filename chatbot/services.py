from .ai_engine import  get_rag_response

def ask_ai(question):
    return get_rag_response(question)
