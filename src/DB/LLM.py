import ollama
from ollama import generate, chat
from config import models, ai

import subprocess
import requests
import time
import sys
import logging

OLLAMA_API_URL = "http://localhost:11434"
DEFAULT_LLM = models.DEFAULT_LLM
DEFAULT_VISION_MODEL = models.DEFAULT_VISION_MODEL

CONTEXT_CHAT_INSTRUCTION = ai.CONTEXT_CHAT_INSTRUCTION
CONTEXT_CHAT_KEY = ai.CONTEXT_CHAT_KEY

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

def init_ollama_models(models):
    if not is_ollama_running():
        if not start_ollama():
            return False
    else:
        print("Ollama is already running.")

    local_models = get_local_model_names()
    print(f"Models currently available locally: {local_models if local_models else 'None'}")
    print(f"Models expected to initialize: {models}")
    for model in models:
        if model in set(local_models):
            print(f"{model} is already pulled")
        else:
            print(f"Pulling the model {model}...")
            if pull_model(model):
                print(f"Model {model} is pulled")
            else:
                print(f"Error: failed to pull a model ({model})")
                return False

        print(f"Loading model '{model}' into memory...")
        try:
            preload_payload = {
                "model": model,
                "keep_alive": "10m"
            }
            requests.post(f"{OLLAMA_API_URL}/api/generate", json=preload_payload, timeout=3)
        except requests.Timeout:
            pass
        except Exception as e:
            print(f"Warning during model preload: {e}")

        print(f"Model '{model}' is ready.")
    return True

def launch_local_llm():
    models = [DEFAULT_VISION_MODEL,DEFAULT_LLM]
    success =  init_ollama_models(models)
    if success:
        print(f"SUCCESS: Models '{models}' has been passed to the main application.")
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
    print("LLM ASKED", flush=True)
    if DEFAULT_LLM:
        response = generate(
            model=DEFAULT_LLM,
            prompt=s,
            stream = False
        )
        return response.response
    else:
        return None

def ask_vision_model(s, images):
    response = ollama.chat(
        model=DEFAULT_VISION_MODEL,
        messages=[
            {
                'role': 'user',
                'content': s,
                'images': images
            }
        ]
    )
    return(response['message']['content'])

class ChatSession:
    def __init__(self, model=DEFAULT_LLM):
        self.messages = []
        self.model = model

    def ask(self, user_input):
        if DEFAULT_LLM:
            self.messages.append({'role': 'user', 'content': user_input})
            stream = ollama.chat(
                model=DEFAULT_LLM,
                messages=self.messages,
                stream=False,
            )
            response = stream['message']['content']
            self.messages.append({'role': 'assistant', 'content': response})

            return response
        else:
            return None


class ContextChat:
    def __init__(self, model=DEFAULT_LLM):
        self.messages = [
                {'role':'user', 'content': ai.CONTEXT_CHAT_INSTRUCTION}
                ]
        self.model = model
    
    def record(self, user_id, user_input):
        self.messages.append({'role':'user', 'content':f"From {user_id}: {user_input}"})

    def ask(self, user_input):
        if DEFAULT_LLM:
            self.messages.append({'role': 'user', 'content': ai.CONTEXT_CHAT_KEY+" "+user_input})
            stream = ollama.chat(
                model=DEFAULT_LLM,
                messages=self.messages,
                stream=False,
            )
            response = stream['message']['content']

            return response
        else:
            return None

