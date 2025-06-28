import requests
import json
from typing import List
from types import Personality

class LocalLLMService:
    def __init__(self, llm_endpoint: str = "http://localhost:11434", model: str = "llama3.1"):
        self.llm_endpoint = llm_endpoint
        self.model = model

    def generateNextTurn(self, storySoFar: str, activePersonality: Personality) -> str:
        system_instruction = """You are an expert improv comedian playing a game of 'Yes, And...'.
Your goal is to collaboratively build a story.
You MUST accept the previous parts of the story as fact and build upon them.
You MUST stay in character based on the personality provided to you.
You MUST only add one or two new sentences to the story.
Do NOT add any prefixes like your character name. Just output the story sentence(s)."""

        prompt = f"""Here is the story so far:
---
{storySoFar if storySoFar else '(The story is just beginning...)'}
---
Now, as the character "{activePersonality.name}" whose personality is: "{activePersonality.prompt}", continue the story."""

        try:
            response = requests.post(
                f"{self.llm_endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_instruction,
                    "options": {
                        "temperature": 0.9,
                        "top_p": 1,
                        "top_k": 1
                    }
                },
                stream=False
            )
            response.raise_for_status()
            # Ollama returns JSON lines; we collect the response
            result = ""
            for line in response.iter_lines():
                if line:
                    result += json.loads(line.decode('utf-8'))["response"]
            return result.strip()
        except Exception as e:
            print(f"Error calling local LLM: {e}")
            return "I seem to have forgotten my lines... (An LLM error occurred)."

    def summarizeStory(self, fullStory: str, personalityPrompts: List[str]) -> str:
        system_instruction = f"""You are a master storyteller with a complex, multifaceted personality. Your task is to narrate a sequence of events from a singular, first-person ("I") perspective.
Your personality is a seamless blend of the following characteristics:
---
{'\n'.join(f'- {p}' for p in personalityPrompts)}
---

You will be given a block of raw, unordered text representing a series of events or thoughts. Your job is to synthesize this text into a single, coherent story passage, told through your unique, blended personality.

- Do not act as separate characters. You are one person who contains all these traits.
- Weave the different personality flavors into your narrative naturally.
- The final output must be a smooth, flowing story paragraph from a single "I" perspective."""

        prompt = f"""Here are the raw story fragments. Narrate them as a single, first-person story using your blended personality:
---
{fullStory}
---"""

        try:
            response = requests.post(
                f"{self.llm_endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_instruction,
                    "options": {
                        "temperature": 0.75
                    }
                },
                stream=False
            )
            response.raise_for_status()
            result = ""
            for line in response.iter_lines():
                if line:
                    result += json.loads(line.decode('utf-8'))["response"]
            return result.strip()
        except Exception as e:
            print(f"Error calling local LLM for summarization: {e}")
            return "The editor seems to be on a coffee break... (An LLM error occurred)."