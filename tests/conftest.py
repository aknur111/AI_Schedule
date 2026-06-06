import os

os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("MAX_RETRIES", "3")
