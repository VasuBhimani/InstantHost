import os
import google.generativeai as genai
# os.environ["GOOGLE_API_KEY"] = "AIzaSyDUFmklrd8A5yxK2jwrEQyvUWoVBDT72TA"

genai.configure(api_key="AIzaSyDUFmklrd8A5yxK2jwrEQyvUWoVBDT72TA")

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-pro",
  generation_config=generation_config,
)

chat_session = model.start_chat(
  history=[
  ]
)

response = chat_session.send_message("hi")

print(response.text)