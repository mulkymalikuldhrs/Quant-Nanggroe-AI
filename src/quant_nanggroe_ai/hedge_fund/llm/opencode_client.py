"""OpenCode LLM Provider for AI Hedge Fund"""

import json
import subprocess
import os
import shutil
from pydantic import BaseModel
from typing import List, Optional


class OpenCodeLLM:
    """Wrapper untuk menggunakan OpenCode CLI sebagai LLM"""
    
    def __init__(self, model: str = "opencode/gpt-5-nano"):
        self.model = model
        self._check_opencode()
    
    def _check_opencode(self):
        """Cek apakah opencode CLI tersedia"""
        if not shutil.which("opencode"):
            raise RuntimeError("OpenCode CLI tidak ditemukan. Install dari https://opencode.ai/")
    
    def _run_command(self, prompt: str) -> str:
        """Jalankan opencode run command"""
        try:
            result = subprocess.run(
                ["opencode", "run", "--model", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "OPENCODE_NO_INTERACTION": "1"}
            )
            
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "Error: Timeout"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def invoke(self, prompt: str) -> str:
        """Panggil LLM dengan prompt"""
        return self._run_command(prompt)
    
    def chat(self, messages: List[dict]) -> str:
        """Chat dengan multiple messages"""
        # Konversi messages ke format prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        
        prompt = "\n".join(prompt_parts)
        return self.invoke(prompt)
    
    def structured_output(self, prompt: str, schema: dict) -> dict:
        """Dapatkan output dalam format JSON berdasarkan schema"""
        schema_prompt = f"""{prompt}

Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Do not include any other text or explanation."""
        
        result = self.invoke(schema_prompt)
        
        # Coba parse JSON dari response
        try:
            # Coba langsung parse
            return json.loads(result)
        except json.JSONDecodeError:
            # Coba cari JSON dalam response
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {}


class OpenCodeChatModel:
    """LangChain-compatible wrapper untuk OpenCode"""
    
    def __init__(self, model: str = "opencode/gpt-5-nano"):
        self.model = model
        self.llm = OpenCodeLLM(model)
    
    def invoke(self, input_data):
        """Invoke LLM"""
        if isinstance(input_data, str):
            return self.llm.invoke(input_data)
        
        messages = input_data.get("messages", [])
        if not messages and "content" in input_data:
            return self.llm.invoke(input_data["content"])
        
        return self.llm.chat(messages)
    
    def with_structured_output(self, pydantic_model, method="json_mode"):
        """Create structured output wrapper"""
        class StructuredOpenCode:
            def __init__(self, llm, model_class):
                self.llm = llm
                self.model_class = model_class
            
            def invoke(self, input_data):
                prompt = ""
                if isinstance(input_data, str):
                    prompt = input_data
                elif isinstance(input_data, dict):
                    if "content" in input_data:
                        prompt = input_data["content"]
                    else:
                        for msg in input_data.get("messages", []):
                            if hasattr(msg, 'content'):
                                prompt = msg.content
                                break
                
                if not prompt:
                    return self.model_class()
                
                schema = self.model_class.model_json_schema()
                result = self.llm.structured_output(prompt, schema)
                
                try:
                    return self.model_class(**result)
                except:
                    return self.model_class()
        
        return StructuredOpenCode(self.llm, pydantic_model)


# Helper functions
def get_opencode_model(model_name: str):
    """Get OpenCode model instance"""
    return OpenCodeLLM(model=model_name)


def opencode_chat(model: str, prompt: str) -> str:
    """Simple chat dengan OpenCode"""
    llm = OpenCodeLLM(model)
    return llm.invoke(prompt)


if __name__ == "__main__":
    # Test
    print("Testing OpenCode LLM...")
    
    llm = OpenCodeLLM("opencode/gpt-5-nano")
    
    # Simple test
    result = llm.invoke("What is Python? Answer in 1 sentence.")
    print(f"Simple: {result}")
    
    # Structured output test
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"}
        },
        "required": ["name", "version"]
    }
    
    result = llm.structured_output("Tell me about Python programming language", schema)
    print(f"Structured: {result}")
