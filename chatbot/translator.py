from deep_translator import GoogleTranslator

def to_english(text):
    return GoogleTranslator(source="auto", target="en").translate(text)

def to_malayalam(text):
    return GoogleTranslator(source="auto", target="ml").translate(text)
