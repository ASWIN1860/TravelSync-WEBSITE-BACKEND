from deep_translator import GoogleTranslator

def to_english(text):
    try:
        return GoogleTranslator(source="ml", target="en").translate(text)
    except:
        return text


def to_malayalam(text):
    try:
        return GoogleTranslator(source="en", target="ml").translate(text)
    except:
        return text