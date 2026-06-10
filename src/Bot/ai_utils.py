import ollama
from ollama import generate, chat

MODEL = 'granite4.1:3b'
#models = ollama.list()
#for model in models['models']:
#    print(model['model'])

def ask_llm(s):
    response = generate(
        model=MODEL,
        prompt=s,
        stream = False
    )
    return response.response

class AI_Chat:
    def __init__(self, model=MODEL):
        self.messages = []
        self.model = model

    def ask(self, user_input):
        self.messages.append({'role': 'user', 'content': user_input})
        stream = ollama.chat(
            model=MODEL,
            messages=self.messages,
            stream=False,
        )
        response = stream['message']['content']
        self.messages.append({'role': 'assistant', 'content': response})

        return response

"""
#EXAMPLE of a chat with memory
chat_list = [AI_Chat(), AI_Chat()]
while True:
    for i, ch in enumerate(chat_list):
        print(f"{i}>", end='')
        inp = input()
        if inp == "\\bye":
            break
        print(ch.ask(inp))

"""

"""
#EXAMPLE of a prompt with stream
stream = ollama.chat(
    model=MODEL,
    messages=[{'role': 'user', 'content': 'Write a haiku about debugging.'}],
    stream=True,
)
for chunk in stream:
    print(chunk['message']['content'], end='', flush=True)

"""


