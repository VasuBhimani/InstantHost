from ollama import Client
from pydantic import BaseModel
import json
client = Client(
    host='https://7e02-136-233-130-145.ngrok-free.app/',
    headers={'x-some-header': 'some-value'}
)
class project_type(BaseModel):
    project_type:str
    # capital:str

# class PetList(BaseModel):
#     pets: list[Pet]

response = client.chat(model='qwen2.5-coder:32b', messages=[{
        'role': 'user',
        'content': ''' read this file structure and return the project type i would be Python or Node app.py
static/
    images/
        1_0.jpg
        1_1.png
        1_2.png
        3_0.jpg
        3_1.jpeg
        Neon.jpeg
        output_image.jpg
templates/
    index.html
        ''',
    }],
    format=project_type.model_json_schema(),
)

# project_info= project_type.model_validate_json(response.message.content)
# print(project_info)

response_data = json.loads(response.message.content)
print(response_data["project_type"]) 