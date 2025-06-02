# import openai
#
# openai.api_key = "sk-proj-14NWcowzngmF2u3yg3c0T3BlbkFJebz7zhH68sG2a6XHBp0k"
#
#
# def ask_gpt(prompt):
#     response = openai.ChatCompletion.create(
#         model="gpt-4",  # Use "gpt-4" or another supported model
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant."},  # System role (optional)
#             {"role": "user", "content": prompt},  # User's question
#         ],
#     )
#     return response['choices'][0]['message']['content']
#
#
# def search_pdf_content(query, pdf_texts):
#     # `pdf_texts` is a dictionary with filenames as keys and text as values
#     results = []
#     for filename, content in pdf_texts.items():
#         if query.lower() in content.lower():
#             results.append((filename, content))
#     return results
#
#
# def construct_prompt(query, relevant_texts):
#     context = "\n".join(relevant_texts)
#     prompt = f"You are a chatbot that only answers based on the following context:\n\n{context}\n\nQuestion: {query}\nAnswer:"
#     return prompt
