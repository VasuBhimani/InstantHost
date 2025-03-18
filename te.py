import google.generativeai as genai
import os

# Set your API key here
os.environ["GOOGLE_API_KEY"] = "AIzaSyDUFmklrd8A5yxK2jwrEQyvUWoVBDT72TA"

# Configure the Gemini model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro')


file_path = os.path.join(os.getcwd(), "input.txt")  # Use input.txt from the same directory
    
    # Read file content
try:
    with open(file_path, 'r') as file:
        prompt_content = file.read()
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found.")
    
PROMPT = prompt_content

def generate_dockerfile():
    response = model.generate_content(PROMPT)
    return response.text

if __name__ == '__main__':
    # language = input("Enter the programming language: ")
    dockerfile = generate_dockerfile()
    print("\nGenerated Dockerfile:\n")
    print(dockerfile)