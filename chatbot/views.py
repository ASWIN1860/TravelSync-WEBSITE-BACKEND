from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ask_ai
from .translator import to_english, to_malayalam

class ChatAPIView(APIView):

    def post(self, request):
        question = request.data.get("question")
        language = request.data.get("language", "en")  # default en

        if not question:
            return Response(
                {"error": "Question is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if language not in ["en", "ml"]:
            return Response(
                {"error": "Invalid language"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Translate input
        if language == "ml":
            question = to_english(question)

        # Chatbot/AI logic
        answer = ask_ai(question)
        
# if the language is malayualam question is translated to english and answer is translated back to malayalam

        # Translate output
        if language == "ml":
            answer = to_malayalam(answer)

        return Response({
            "answer": answer
        }, status=status.HTTP_200_OK)
