import ollama
from ollama import generate, chat
from env import llm

import subprocess
import requests
import time
import sys
import logging

OLLAMA_API_URL = "http://localhost:11434"
DEFAULT_MODEL = "granite4.1:3b"
#models = ollama.list()
#for model in models['models']:
#    print(model['model'])

def is_ollama_running():
    try:
        response = requests.get(OLLAMA_API_URL, timeout=2)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def start_ollama():
    print("Ollama is not running. Starting Ollama server...")
    try:
        subprocess.Popen(
            ["ollama", "serve"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        for _ in range(15):
            time.sleep(1)
            if is_ollama_running():
                print("Ollama server started successfully.")
                return True
                
        print("Error: Timeout waiting for Ollama to start.")
        return False
    except FileNotFoundError:
        print("Error: Ollama executable not found. Please ensure Ollama is installed.")
        return False
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def get_local_model_names():
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get('models', [])
        return [model['name'] for model in models]
    except Exception as e:
        print(f"Error fetching local models: {e}")
        return []

def pull_model(model_name):
    print(f"Downloading model '{model_name}'. This may take a few minutes...")
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print(f"Successfully downloaded {model_name}.")
            return True
        else:
            print(f"Failed to download {model_name}. Error:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"Exception occurred while pulling model: {e}")
        return False

def init_ollama_model(preferred_models):
    if not preferred_models:
        print("No preferred models provided.")
        return None

    if not is_ollama_running():
        if not start_ollama():
            return None
    else:
        print("Ollama is already running.")

    local_models = get_local_model_names()
    print(f"Models currently available locally: {local_models if local_models else 'None'}")

    selected_model = None

    for model in preferred_models:
        exact_match = model
        latest_match = f"{model}:latest"
        
        if exact_match in local_models:
            selected_model = exact_match
            break
        elif latest_match in local_models:
            selected_model = latest_match
            break

    if not selected_model:
        target_model = preferred_models[0]
        print(f"None of your preferred models were found locally. Falling back to downloading: {target_model}")
        if pull_model(target_model):
            selected_model = target_model
        else:
            print("Failed to secure a working model.")
            return None
    else:
        print(f"Found preferred model locally: {selected_model}")

    print(f"Loading model '{selected_model}' into memory...")
    try:
        preload_payload = {
            "model": selected_model,
            "keep_alive": "10m" # Keeps the model loaded in memory for 10 minutes
        }
        requests.post(f"{OLLAMA_API_URL}/api/generate", json=preload_payload, timeout=3)
    except requests.Timeout:
        pass 
    except Exception as e:
        print(f"Minor warning during model preload: {e}")

    print(f"Model '{selected_model}' is primed and ready.")
    
    # 5. Pass its name back
    return selected_model

def launch_local_llm():
    models = [DEFAULT_MODEL]
    try:
        models = llm.MODELS
    except:
        print(f"No custom model list found: Using default model - {DEFAULT_MODEL}")
    READY_MODEL = init_ollama_model(models)

    if READY_MODEL:
        print(f"SUCCESS: The model '{READY_MODEL}' has been passed to the main application.")
    else:
        print("CRITICAL: Pipeline failed. Could not initialize Ollama or prepare a model.")

launch_local_llm()

def run_model(model_name):
    process = subprocess.Popen(
        ["ollama", "run", model_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return process

def ask_llm(s):
    if READY_MODEL:
        response = generate(
            model=READY_MODEL,
            prompt=s,
            stream = False
        )
        return response.response
    else:
        return None

class ChatSession:
    def __init__(self, model=READY_MODEL):
        self.messages = []
        self.model = model

    def ask(self, user_input):
        if READY_MODEL:
            self.messages.append({'role': 'user', 'content': user_input})
            stream = ollama.chat(
                model=READY_MODEL,
                messages=self.messages,
                stream=False,
            )
            response = stream['message']['content']
            self.messages.append({'role': 'assistant', 'content': response})

            return response
        else:
            return None

"""
#EXAMPLE of a chat with memory
chat_list = [ChatSession(), ChatSession()]
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


