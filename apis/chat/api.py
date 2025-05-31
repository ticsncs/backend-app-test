from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apis.chat.utils import ask_gpt, search_pdf_content, construct_prompt
from apps.chat.models import PdfContent


class ChatbotAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        question = request.data.get("question", "")
        if not question:
            return Response(
                {"error": "Question is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        pdf_texts = {pdf.filename: pdf.content for pdf in PdfContent.objects.all()}
        relevant_results = search_pdf_content(question, pdf_texts)
        if not relevant_results:
            return Response(
                {"answer": "I couldn't find relevant information in the PDFs."}
            )
        relevant_texts = [text for _, text in relevant_results]

        prompt = construct_prompt(question, relevant_texts)
        answer = ask_gpt(prompt)
        return Response({"answer": answer})
