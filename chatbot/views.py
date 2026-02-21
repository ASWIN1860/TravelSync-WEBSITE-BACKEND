from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ask_ai
from .translator import to_english, to_malayalam


class ChatAPIView(APIView):

    def post(self, request):
        question = request.data.get("question")
        language = request.data.get("language", "en")

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

        # Special ping for frontend status check
        if question == "ping":
            return Response({"status": "ok"})

        try:
            # Translate Malayalam → English
            if language == "ml":
                question = to_english(question)

            # Ask AI
            answer = ask_ai(question)

            # Translate back if needed
            if language == "ml":
                answer = to_malayalam(answer)

            return Response({"answer": answer})

        except Exception as e:
            return Response(
                {"error": "Server error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )