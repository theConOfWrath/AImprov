# Temporary settings for LLM endpoint
# TODO: Replace with web-based settings page (Flask or Node.js)
ENDPOINT_TYPE = "huggingface"  # Options: "huggingface", "local", "openai"
MODEL_NAME = "google/flan-t5-large"  # Default model
LOCAL_ENDPOINT = "http://localhost:8000"  # For local LLM server