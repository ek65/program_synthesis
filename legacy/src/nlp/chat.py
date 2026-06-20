
from openai import OpenAI

class ChatEntry:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class Chat:
    def __init__(self, client, model='gpt-4o'):
        self.model = model
        self.client = client

    def __call__(self, input: list[ChatEntry], json=False) -> str:
        chat = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    'role': entry.role,
                    'content': entry.content
                }
                for entry in input
            ],
            response_format={'type': 'json_object' if json else 'text'},
            temperature=0
        )
        return chat.choices[0].message.content

client = OpenAI(api_key='YOUR_OPENAI_KEY')
chat = Chat(client)