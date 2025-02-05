from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, AIMessageChunk
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from typing import Any, List, Optional, Iterator, Mapping, Dict
from huggingface_hub import InferenceClient
from transformers import AutoTokenizer
from pydantic import Field, PrivateAttr
import json

class ChatHuggingFace(BaseChatModel):
    """Custom LangChain chat model implementation for HuggingFace Inference API"""
    model_name: str = Field(description="Name of the HuggingFace model to use")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_new_tokens: int = Field(default=128, description="Maximum number of tokens to generate")
    top_p: float = Field(default=0.9, description="Top p sampling parameter")
    streaming: bool = Field(default=True, description="Whether to stream the output")
    api_key: Optional[str] = Field(default=None, description="HuggingFace API key")
    _client: InferenceClient = PrivateAttr()
    _tokenizer: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = InferenceClient(token=self.api_key)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.api_key)

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "huggingface"

    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert messages to Llama 2 chat format"""
        prompt = ""
        for message in messages:
            if isinstance(message, AIMessage):
                prompt += f"Assistant: {message.content}\n"
            else:
                prompt += f"Human: {message.content}\n"
        prompt += "Assistant:"
        return prompt

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> List[BaseMessage]:
        prompt = self._convert_messages_to_prompt(messages)
        response = self._client.text_generation(
            prompt,
            model=self.model_name,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=stop if stop else None,
            details=True,
        )

        # Create message with usage metadata only
        message = AIMessage(
            content=response.generated_text,
            additional_kwargs={
                'usage_metadata': {
                    'output_tokens': response.details.generated_tokens,
                    'prompt_tokens': len(self.get_token_ids(prompt)),
                    'total_tokens': len(self.get_token_ids(prompt)) + response.details.generated_tokens
                }
            }
        )
        return [message]

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[AIMessageChunk]:
        prompt = self._convert_messages_to_prompt(messages)
        prompt_tokens = len(self.get_token_ids(prompt))
        accumulated_text = ""
        accumulated_tokens = 0

        stream = self._client.text_generation(
            prompt,
            model=self.model_name,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=stop if stop else None,
            stream=True,
            details=True,
        )

        for response in stream:
            accumulated_tokens += 1
            token_text = response.token.text
            accumulated_text += token_text

            # Create chunk with only the necessary metadata
            chunk = AIMessageChunk(
                content=token_text,
                additional_kwargs={
                    'usage_metadata': {
                        'output_tokens': accumulated_tokens,
                        'prompt_tokens': prompt_tokens,
                        'total_tokens': prompt_tokens + accumulated_tokens
                    }
                }
            )
            yield chunk

    def get_token_ids(self, text: str) -> List[int]:
        """Get token IDs for a given text using the model's tokenizer"""
        return self._tokenizer(text)['input_ids']

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_new_tokens": self.max_new_tokens,
            "top_p": self.top_p
        }

def init_model(
    model="meta-llama/Llama-3.2-1B-Instruct",
    temperature=0.7,
    max_tokens=128,
    top_p=0.9,
    device=None,  # Not used for API calls
    stream=True,
    api_key=None
):
    """
    Initialize and return the model instance.
    Args:
        model (str): The name of the model to use.
        temperature (float): Sampling temperature for the model.
        max_tokens (int): Maximum tokens for the model output.
        top_p (float): Nucleus sampling parameter.
        device (str, optional): Device to use (not used for API calls)
        stream (bool): Whether to stream the output
        api_key (str): HuggingFace API key
    Returns:
        ChatHuggingFace: The initialized shared model.
    """
    return ChatHuggingFace(
        model_name=model,
        temperature=temperature,
        max_new_tokens=max_tokens,
        top_p=top_p,
        streaming=stream,
        api_key=api_key
    )

def load_json_config(path):
    """
    Load the default configuration from the JSON file.
    Returns:
    dict: The default configuration dictionary.
    """
    with open(path, "r") as file:
        return json.load(file)
