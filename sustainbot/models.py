"""LLM interface for SustainBot"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface to interact with Ollama (local LLM service)"""

    def __init__(self, model: str = 'llama2', host: str = 'localhost', port: int = 11434):
        self.model = model
        self.host = host
        self.port = port
        self.api_url = f"http://{host}:{port}"
        self.timeout = 30

    def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text using the LLM"""
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False, **kwargs}
            response = requests.post(f"{self.api_url}/api/generate", json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"LLM error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to LLM: {e}")
            return None

    def chat(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Chat interface for multi-turn conversations"""
        try:
            payload = {"model": self.model, "messages": messages, "stream": False}
            response = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json().get('message', {}).get('content', '')
            else:
                logger.error(f"Chat error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in chat: {e}")
            return None

    def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m.get('name', '') for m in models]
            return []
        except requests.exceptions.RequestException:
            return []
