import os
import json
import re
import logging
import httpx
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_xai import ChatXAI
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_openai import ChatOpenAI
from langchain_gigachat import GigaChat
from langchain_ollama import ChatOllama
from enum import Enum
from pydantic import BaseModel
from typing import Tuple, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Enum for supported LLM providers"""

    ALIBABA = "Alibaba"
    ANTHROPIC = "Anthropic"
    DEEPSEEK = "DeepSeek"
    GOOGLE = "Google"
    GROQ = "Groq"
    META = "Meta"
    MISTRAL = "Mistral"
    OPENAI = "OpenAI"
    OLLAMA = "Ollama"
    OPENROUTER = "OpenRouter"
    GIGACHAT = "GigaChat"
    AZURE_OPENAI = "Azure OpenAI"
    XAI = "xAI"
    PUTER = "Puter"
    OPENCODE = "OpenCode"


class LLMModel(BaseModel):
    """Represents an LLM model configuration"""

    display_name: str
    model_name: str
    provider: ModelProvider

    def to_choice_tuple(self) -> Tuple[str, str, str]:
        """Convert to format needed for questionary choices"""
        return (self.display_name, self.model_name, self.provider.value)

    def is_custom(self) -> bool:
        """Check if the model is a Gemini model"""
        return self.model_name == "-"

    def has_json_mode(self) -> bool:
        """Check if the model supports JSON mode"""
        if self.is_deepseek() or self.is_gemini():
            return False
        # Only certain Ollama models support JSON mode
        if self.is_ollama():
            return "llama3" in self.model_name or "neural-chat" in self.model_name
        # OpenRouter models generally support JSON mode
        if self.provider == ModelProvider.OPENROUTER:
            return True
        return True

    def is_deepseek(self) -> bool:
        """Check if the model is a DeepSeek model"""
        return self.model_name.startswith("deepseek")

    def is_gemini(self) -> bool:
        """Check if the model is a Gemini model"""
        return self.model_name.startswith("gemini")

    def is_ollama(self) -> bool:
        """Check if the model is an Ollama model"""
        return self.provider == ModelProvider.OLLAMA


class OpenCodeChatModel:
    """Wrapper class untuk menggunakan OpenCode CLI sebagai LLM"""
    
    JSON_PATTERNS = [
        r'\{[\s\S]*?"[^"]+"\s*:\s*[^}]*\}',  # Simple object pattern
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested object pattern
        r'\[[\s\S]*\]',  # Array pattern
        r'\{[\s\S]*\}',  # Full object (fallback)
    ]
    
    def __init__(self, model: str = "opencode/grok-code"):
        self.model = model
        self._pydantic_model = None
        self._check_opencode()
        self._parse_failures = 0
        self._total_calls = 0
    
    def _check_opencode(self):
        """Cek apakah opencode CLI tersedia"""
        import shutil
        if not shutil.which("opencode"):
            raise RuntimeError("OpenCode CLI tidak ditemukan. Install dari https://opencode.ai/")
    
    def _run_command(self, prompt: str) -> str:
        """Jalankan opencode run command"""
        import subprocess
        import os
        
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
                logger.error(f"OpenCode command failed: {result.stderr}")
                return f"Error: {result.stderr}"
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("OpenCode command timed out")
            return "Error: Timeout"
        except Exception as e:
            logger.error(f"OpenCode command error: {str(e)}")
            return f"Error: {str(e)}"
    
    def with_structured_output(self, pydantic_model, method="json_mode"):
        """Create structured output wrapper"""
        new_instance = OpenCodeChatModel(self.model)
        new_instance._pydantic_model = pydantic_model
        return new_instance
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from text using multiple patterns"""
        for pattern in self.JSON_PATTERNS:
            try:
                matches = re.findall(pattern, text)
                for match in matches:
                    if match.startswith('[') and match.endswith(']'):
                        # Try parsing as array
                        try:
                            parsed = json.loads(match)
                            if isinstance(parsed, (list, dict)):
                                return parsed if isinstance(parsed, dict) else {"data": parsed}
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Try parsing as object
                        try:
                            parsed = json.loads(match)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                continue
        return None
    
    def _validate_json(self, data: Any, pydantic_model) -> bool:
        """Validate if parsed JSON has required fields for pydantic model"""
        if not isinstance(data, dict):
            return False
        required_fields = set(pydantic_model.model_fields.keys())
        provided_fields = set(data.keys())
        # Check if at least some fields are present
        return bool(provided_fields & required_fields)
    
    def invoke(self, input_data):
        """Invoke the model"""
        self._total_calls += 1
        
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
            if self._pydantic_model:
                return self._get_default_response()
            return ""
        
        result = self._run_command(prompt)
        
        if "Error:" in result:
            logger.warning(f"OpenCode returned error: {result}")
            if self._pydantic_model:
                return self._get_default_response()
            return result
        
        if self._pydantic_model:
            # Try to parse JSON from result
            parsed = None
            
            # First try: direct JSON parse
            try:
                parsed = json.loads(result)
                if self._validate_json(parsed, self._pydantic_model):
                    return self._pydantic_model(**parsed)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.debug(f"Direct JSON parse failed: {e}")
            
            # Second try: extract JSON from text
            if parsed is None:
                extracted = self._extract_json(result)
                if extracted and self._validate_json(extracted, self._pydantic_model):
                    try:
                        return self._pydantic_model(**extracted)
                    except Exception as e:
                        logger.debug(f"Pydantic validation failed for extracted JSON: {e}")
            
            # Third try: partial JSON with field mapping
            if parsed is None:
                partial = self._extract_partial_json(result, self._pydantic_model)
                if partial:
                    try:
                        return self._pydantic_model(**partial)
                    except Exception as e:
                        logger.debug(f"Pydantic validation failed for partial JSON: {e}")
            
            # Log failure and return default
            self._parse_failures += 1
            logger.warning(f"JSON parsing failed (failure {self._parse_failures}/{self._total_calls})")
            return self._get_default_response()
        
        return result
    
    def _extract_partial_json(self, text: str, pydantic_model) -> Optional[dict]:
        """Extract partial JSON data matching pydantic model fields"""
        result = {}
        model_fields = set(pydantic_model.model_fields.keys())
        
        # Try to find key-value pairs
        for field in model_fields:
            # Look for patterns like "field": value or "field": "value"
            patterns = [
                rf'"{field}"\s*:\s*([^\s,}}]+)',  # Unquoted value
                rf'"{field}"\s*:\s*"([^"]*)"',  # Quoted string
                rf'"{field}"\s*:\s*(\d+\.?\d*)',  # Number
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    field_type = pydantic_model.model_fields[field].annotation
                    
                    # Convert value to correct type
                    if field_type == str:
                        result[field] = value.strip('"')
                    elif field_type in (int, float):
                        try:
                            result[field] = float(value) if field_type == float else int(value)
                        except ValueError:
                            continue
                    elif hasattr(field_type, "__args__"):
                        # Literal types
                        try:
                            literal_values = [str(v) for v in field_type.__args__]
                            if value.strip('"') in literal_values:
                                result[field] = value.strip('"')
                        except:
                            continue
                    break
        
        return result if result else None
    
    def _get_default_response(self):
        """Get default response for the pydantic model"""
        if not self._pydantic_model:
            return None
        
        default_values = {}
        for field_name, field in self._pydantic_model.model_fields.items():
            field_type = field.annotation
            
            if field_type == str:
                if "signal" in field_name.lower():
                    default_values[field_name] = "HOLD"
                elif "action" in field_name.lower():
                    default_values[field_name] = "hold"
                elif "reason" in field_name.lower():
                    default_values[field_name] = "Insufficient data for analysis"
                else:
                    default_values[field_name] = "N/A"
            elif field_type == int:
                if "confidence" in field_name.lower():
                    default_values[field_name] = 50
                elif "count" in field_name.lower():
                    default_values[field_name] = 0
                else:
                    default_values[field_name] = 0
            elif field_type == float:
                if "confidence" in field_name.lower():
                    default_values[field_name] = 0.5
                elif "score" in field_name.lower():
                    default_values[field_name] = 50.0
                elif "price" in field_name.lower() or "amount" in field_name.lower():
                    default_values[field_name] = 0.0
                else:
                    default_values[field_name] = 0.0
            elif hasattr(field_type, "__args__"):
                # Literal types - get first value
                try:
                    default_values[field_name] = field_type.__args__[0]
                except:
                    default_values[field_name] = None
            elif field_type == bool:
                default_values[field_name] = False
            else:
                default_values[field_name] = None
        
        try:
            return self._pydantic_model(**default_values)
        except Exception as e:
            logger.error(f"Failed to create default response: {e}")
            return self._pydantic_model()


# Load models from JSON file
def load_models_from_json(json_path: str) -> List[LLMModel]:
    """Load models from a JSON file"""
    with open(json_path, 'r') as f:
        models_data = json.load(f)
    
    models = []
    for model_data in models_data:
        # Convert string provider to ModelProvider enum
        provider_enum = ModelProvider(model_data["provider"])
        models.append(
            LLMModel(
                display_name=model_data["display_name"],
                model_name=model_data["model_name"],
                provider=provider_enum
            )
        )
    return models


# Get the path to the JSON files
current_dir = Path(__file__).parent
models_json_path = current_dir / "api_models.json"
ollama_models_json_path = current_dir / "ollama_models.json"

# Load available models from JSON
AVAILABLE_MODELS = load_models_from_json(str(models_json_path))

# Load Ollama models from JSON
OLLAMA_MODELS = load_models_from_json(str(ollama_models_json_path))

# Create LLM_ORDER in the format expected by the UI
LLM_ORDER = [model.to_choice_tuple() for model in AVAILABLE_MODELS]

# Create Ollama LLM_ORDER separately
OLLAMA_LLM_ORDER = [model.to_choice_tuple() for model in OLLAMA_MODELS]


def get_model_info(model_name: str, model_provider: str) -> LLMModel | None:
    """Get model information by model_name"""
    all_models = AVAILABLE_MODELS + OLLAMA_MODELS
    return next((model for model in all_models if model.model_name == model_name and model.provider == model_provider), None)


def find_model_by_name(model_name: str) -> LLMModel | None:
    """Find a model by its name across all available models."""
    all_models = AVAILABLE_MODELS + OLLAMA_MODELS
    return next((model for model in all_models if model.model_name == model_name), None)


def get_models_list():
    """Get the list of models for API responses."""
    return [
        {
            "display_name": model.display_name,
            "model_name": model.model_name,
            "provider": model.provider.value
        }
        for model in AVAILABLE_MODELS
    ]


class PuterChatModel:
    """Wrapper class to make Puter API compatible with LangChain interface"""
    
    PUTER_API_BASE = "https://api.puter.com/v1"
    
    def __init__(self, model: str, api_key: str = None, driver: str = "openai-completion"):
        self.model = model
        self.api_key = api_key or os.getenv("PUTER_API_KEY")
        self.driver = driver
        self._structured_output_method = None
        self._pydantic_model = None
        self._parse_failures = 0
        self._total_calls = 0
        
        if "gpt-4o" in model.lower() or "gpt-4" in model.lower():
            self.driver = "openai-completion"
        elif "claude" in model.lower():
            self.driver = "claude"
    
    def with_structured_output(self, pydantic_model, method="json_mode"):
        """Create a new instance with structured output configuration"""
        new_instance = PuterChatModel(self.model, self.api_key, self.driver)
        new_instance._structured_output_method = method
        new_instance._pydantic_model = pydantic_model
        return new_instance
    
    def _make_request(self, messages: list, stream: bool = False):
        """Make a request to the Puter API"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "interface": "puter-chat-completion",
            "driver": self.driver,
            "method": "complete",
            "args": {
                "messages": messages,
                "model": self.model,
            }
        }
        
        if stream:
            payload["args"]["stream"] = True
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.PUTER_API_BASE}/drivers/call",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    
    def _extract_content(self, result):
        """Extract content from API response"""
        if isinstance(result, str):
            return result
        
        if "choice" in result and "message" in result["choice"]:
            return result["choice"]["message"]["content"]
        elif "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        elif "message" in result and "content" in result["message"]:
            return result["message"]["content"]
        elif "text" in result:
            return result["text"]
        elif "content" in result:
            return result["content"]
        else:
            return str(result)
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from text using multiple patterns"""
        patterns = [
            r'\{[\s\S]*?"[^"]+"\s*:\s*[^}]*\}',
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            r'\[[\s\S]*\]',
            r'\{[\s\S]*\}',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text)
                for match in matches:
                    if match.startswith('[') and match.endswith(']'):
                        try:
                            parsed = json.loads(match)
                            if isinstance(parsed, (list, dict)):
                                return parsed if isinstance(parsed, dict) else {"data": parsed}
                        except json.JSONDecodeError:
                            continue
                    else:
                        try:
                            parsed = json.loads(match)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                continue
        return None
    
    def _validate_json(self, data: Any, pydantic_model) -> bool:
        """Validate if parsed JSON has required fields"""
        if not isinstance(data, dict):
            return False
        required_fields = set(pydantic_model.model_fields.keys())
        provided_fields = set(data.keys())
        return bool(provided_fields & required_fields)
    
    def invoke(self, input):
        """Invoke the model with a message list"""
        self._total_calls += 1
        
        messages = []
        input_text = ""
        
        if isinstance(input, str):
            input_text = input
            messages = [{"role": "user", "content": input}]
        elif isinstance(input, dict):
            for msg in input.get("messages", []):
                if hasattr(msg, 'content') and hasattr(msg, 'type'):
                    messages.append({
                        "role": msg.type.replace("-message", ""),
                        "content": msg.content
                    })
                else:
                    content = getattr(msg, 'content', str(msg))
                    msg_type = getattr(msg, 'type', 'user')
                    messages.append({
                        "role": msg_type.replace("-message", "") if "-" in msg_type else msg_type,
                        "content": content
                    })
            if not messages and "content" in input:
                input_text = input["content"]
                messages = [{"role": "user", "content": input_text}]
        else:
            input_text = str(input)
            messages = [{"role": "user", "content": input_text}]
        
        try:
            result = self._make_request(messages, stream=False)
            content = self._extract_content(result)
            
            if self._pydantic_model:
                parsed = None
                
                # Try direct JSON parse
                try:
                    parsed = json.loads(content)
                    if self._validate_json(parsed, self._pydantic_model):
                        return self._pydantic_model(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                # Try extracted JSON
                if parsed is None:
                    extracted = self._extract_json(content)
                    if extracted and self._validate_json(extracted, self._pydantic_model):
                        try:
                            return self._pydantic_model(**extracted)
                        except:
                            pass
                
                # Log failure and return default
                self._parse_failures += 1
                logger.warning(f"Puter JSON parsing failed (failure {self._parse_failures}/{self._total_calls})")
                return self._get_default_response()
            
            return content
        except Exception as e:
            logger.error(f"Puter API error: {e}")
            if self._pydantic_model:
                return self._get_default_response()
            raise
    
    def _get_default_response(self):
        """Get default response for the pydantic model"""
        if not self._pydantic_model:
            return None
        
        default_values = {}
        for field_name, field in self._pydantic_model.model_fields.items():
            field_type = field.annotation
            
            if field_type == str:
                if "signal" in field_name.lower():
                    default_values[field_name] = "HOLD"
                elif "action" in field_name.lower():
                    default_values[field_name] = "hold"
                elif "reason" in field_name.lower():
                    default_values[field_name] = "Insufficient data for analysis"
                else:
                    default_values[field_name] = "N/A"
            elif field_type == int:
                if "confidence" in field_name.lower():
                    default_values[field_name] = 50
                else:
                    default_values[field_name] = 0
            elif field_type == float:
                if "confidence" in field_name.lower():
                    default_values[field_name] = 0.5
                else:
                    default_values[field_name] = 0.0
            elif hasattr(field_type, "__args__"):
                try:
                    default_values[field_name] = field_type.__args__[0]
                except:
                    default_values[field_name] = None
            elif field_type == bool:
                default_values[field_name] = False
            else:
                default_values[field_name] = None
        
        try:
            return self._pydantic_model(**default_values)
        except Exception as e:
            logger.error(f"Failed to create default response: {e}")
            return self._pydantic_model()
    
    def stream(self, input):
        """Stream response from the model"""
        messages = []
        for msg in input.get("messages", []):
            if hasattr(msg, 'content') and hasattr(msg, 'type'):
                messages.append({
                    "role": msg.type.replace("-message", ""),
                    "content": msg.content
                })
            else:
                content = getattr(msg, 'content', str(msg))
                msg_type = getattr(msg, 'type', 'user')
                messages.append({
                    "role": msg_type.replace("-message", "") if "-" in msg_type else msg_type,
                    "content": content
                })
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "interface": "puter-chat-completion",
            "driver": self.driver,
            "method": "complete",
            "args": {
                "messages": messages,
                "model": self.model,
                "stream": True
            }
        }
        
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", f"{self.PUTER_API_BASE}/drivers/call", headers=headers, json=payload) as response:
                for line in response.iter_lines():
                    if line:
                        yield line


def get_model(model_name: str, model_provider: ModelProvider, api_keys: dict = None) -> ChatOpenAI | ChatGroq | ChatOllama | GigaChat | PuterChatModel | OpenCodeChatModel | None:
    if model_provider == ModelProvider.GROQ:
        api_key = (api_keys or {}).get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            # Print error to console
            print(f"API Key Error: Please make sure GROQ_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("Groq API key not found.  Please make sure GROQ_API_KEY is set in your .env file or provided via API keys.")
        return ChatGroq(model=model_name, api_key=api_key)
    elif model_provider == ModelProvider.OPENAI:
        # Get and validate API key
        api_key = (api_keys or {}).get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE")
        if not api_key:
            # Print error to console
            print(f"API Key Error: Please make sure OPENAI_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("OpenAI API key not found.  Please make sure OPENAI_API_KEY is set in your .env file or provided via API keys.")
        return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)
    elif model_provider == ModelProvider.ANTHROPIC:
        api_key = (api_keys or {}).get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure ANTHROPIC_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("Anthropic API key not found.  Please make sure ANTHROPIC_API_KEY is set in your .env file or provided via API keys.")
        return ChatAnthropic(model=model_name, api_key=api_key)
    elif model_provider == ModelProvider.DEEPSEEK:
        api_key = (api_keys or {}).get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure DEEPSEEK_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("DeepSeek API key not found.  Please make sure DEEPSEEK_API_KEY is set in your .env file or provided via API keys.")
        return ChatDeepSeek(model=model_name, api_key=api_key)
    elif model_provider == ModelProvider.GOOGLE:
        api_key = (api_keys or {}).get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure GOOGLE_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("Google API key not found.  Please make sure GOOGLE_API_KEY is set in your .env file or provided via API keys.")
        return ChatGoogleGenerativeAI(model=model_name, api_key=api_key)
    elif model_provider == ModelProvider.OLLAMA:
        # For Ollama, we use a base URL instead of an API key
        # Check if OLLAMA_HOST is set (for Docker on macOS)
        ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        base_url = os.getenv("OLLAMA_BASE_URL", f"http://{ollama_host}:11434")
        return ChatOllama(
            model=model_name,
            base_url=base_url,
        )
    elif model_provider == ModelProvider.OPENROUTER:
        api_key = (api_keys or {}).get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure OPENROUTER_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("OpenRouter API key not found. Please make sure OPENROUTER_API_KEY is set in your .env file or provided via API keys.")
        
        # Get optional site URL and name for headers
        site_url = os.getenv("YOUR_SITE_URL", "https://github.com/virattt/ai-hedge-fund")
        site_name = os.getenv("YOUR_SITE_NAME", "AI Hedge Fund")
        
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": site_url,
                    "X-Title": site_name,
                }
            }
        )
    elif model_provider == ModelProvider.XAI:
        api_key = (api_keys or {}).get("XAI_API_KEY") or os.getenv("XAI_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure XAI_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("xAI API key not found. Please make sure XAI_API_KEY is set in your .env file or provided via API keys.")
        return ChatXAI(model=model_name, api_key=api_key)
    elif model_provider == ModelProvider.GIGACHAT:
        if os.getenv("GIGACHAT_USER") or os.getenv("GIGACHAT_PASSWORD"):
            return GigaChat(model=model_name)
        else: 
            api_key = (api_keys or {}).get("GIGACHAT_API_KEY") or os.getenv("GIGACHAT_API_KEY") or os.getenv("GIGACHAT_CREDENTIALS")
            if not api_key:
                print("API Key Error: Please make sure api_keys is set in your .env file or provided via API keys.")
                raise ValueError("GigaChat API key not found. Please make sure GIGACHAT_API_KEY is set in your .env file or provided via API keys.")

            return GigaChat(credentials=api_key, model=model_name)
    elif model_provider == ModelProvider.AZURE_OPENAI:
        # Get and validate API key
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            # Print error to console
            print(f"API Key Error: Please make sure AZURE_OPENAI_API_KEY is set in your .env file.")
            raise ValueError("Azure OpenAI API key not found.  Please make sure AZURE_OPENAI_API_KEY is set in your .env file.")
        # Get and validate Azure Endpoint
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            # Print error to console
            print(f"Azure Endpoint Error: Please make sure AZURE_OPENAI_ENDPOINT is set in your .env file.")
            raise ValueError("Azure OpenAI endpoint not found.  Please make sure AZURE_OPENAI_ENDPOINT is set in your .env file.")
        # get and validate deployment name
        azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not azure_deployment_name:
            # Print error to console
            print(f"Azure Deployment Name Error: Please make sure AZURE_OPENAI_DEPLOYMENT_NAME is set in your .env file.")
            raise ValueError("Azure OpenAI deployment name not found.  Please make sure AZURE_OPENAI_DEPLOYMENT_NAME is set in your .env file.")
        return AzureChatOpenAI(azure_endpoint=azure_endpoint, azure_deployment=azure_deployment_name, api_key=api_key, api_version="2024-10-21")
    elif model_provider == ModelProvider.PUTER:
        api_key = (api_keys or {}).get("PUTER_API_KEY") or os.getenv("PUTER_API_KEY")
        if not api_key:
            print(f"API Key Error: Please make sure PUTER_API_KEY is set in your .env file or provided via API keys.")
            raise ValueError("Puter API key not found. Please make sure PUTER_API_KEY is set in your .env file.")
        
        if "gpt-4o" in model_name or "gpt-4o-mini" in model_name:
            driver = "openai-completion"
        elif "claude" in model_name:
            driver = "claude"
        else:
            driver = "openai-completion"
        
        return PuterChatModel(model=model_name, api_key=api_key, driver=driver)
    elif model_provider == ModelProvider.OPENCODE:
        return OpenCodeChatModel(model=model_name)


