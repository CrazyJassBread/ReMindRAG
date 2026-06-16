from .base import AgentBase
from ..utils.timing import emit_timing
from openai import OpenAI
import atexit
import time
from typing import Optional, List, Dict, Any
from openai import APIConnectionError, APIError, RateLimitError
import requests.exceptions
import urllib3.exceptions 
import socket

class OpenaiAgent(AgentBase):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        llm_model_name: str,
        time_out: int = 120,
        max_retries: int = 20,
        retry_delay: float = 1.0,
        agent_name: Optional[str] = None,
    ):
        self.base_url = base_url
        self.llm_model_name = llm_model_name
        self.agent_name = agent_name or llm_model_name
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_count = 0
        self.completed_requests = 0
        self.failed_requests = 0
        self.retry_count = 0
        self.total_request_elapsed = 0.0
        self.max_request_elapsed = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=time_out
        )
        atexit.register(self._print_timing_summary)

    def _print_timing_summary(self):
        if self.request_count == 0:
            return
        average_elapsed = self.total_request_elapsed / self.completed_requests if self.completed_requests else 0.0
        emit_timing(
            None,
            "llm.summary",
            agent=self.agent_name,
            model=self.llm_model_name,
            requests=self.request_count,
            completed=self.completed_requests,
            failed=self.failed_requests,
            retries=self.retry_count,
            total_elapsed=f"{self.total_request_elapsed:.3f}s",
            average_elapsed=f"{average_elapsed:.3f}s",
            max_elapsed=f"{self.max_request_elapsed:.3f}s",
            prompt_tokens=self.total_prompt_tokens,
            completion_tokens=self.total_completion_tokens,
        )
        
    def generate_response(self, system_prompt: Optional[str], chat_history: List[Dict[str, Any]]) -> str:
        messages = []
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + chat_history
        else:
            messages = chat_history

        self.request_count += 1
        request_id = self.request_count
        prompt_chars = sum(len(str(message.get("content", ""))) for message in messages)
        request_started_at = time.perf_counter()
        emit_timing(
            None,
            "llm.request.sent",
            request_id=request_id,
            model=self.llm_model_name,
            agent=self.agent_name,
            messages=len(messages),
            prompt_chars=prompt_chars,
        )

        last_error = None
        for attempt in range(self.max_retries + 1):
            attempt_started_at = time.perf_counter()
            try:
                response = self.client.chat.completions.create(
                    model=self.llm_model_name,
                    messages=messages,
                    seed=123,
                    temperature=0
                )
                content = response.choices[0].message.content
                usage = getattr(response, "usage", None)
                request_elapsed = time.perf_counter() - request_started_at
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0
                self.completed_requests += 1
                self.total_request_elapsed += request_elapsed
                self.max_request_elapsed = max(self.max_request_elapsed, request_elapsed)
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                emit_timing(
                    None,
                    "llm.response.received",
                    request_started_at,
                    request_id=request_id,
                    model=self.llm_model_name,
                    agent=self.agent_name,
                    attempt=attempt + 1,
                    attempt_elapsed=f"{time.perf_counter() - attempt_started_at:.3f}s",
                    response_chars=len(content or ""),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
                return content
                
            except (APIConnectionError, APIError, RateLimitError,
                   requests.exceptions.ConnectionError,
                   requests.exceptions.RequestException,
                   urllib3.exceptions.ProtocolError,
                   urllib3.exceptions.HTTPError,
                   ConnectionResetError,
                   socket.timeout,
                   TimeoutError) as e:
                last_error = e
                emit_timing(
                    None,
                    "llm.request.attempt_failed",
                    attempt_started_at,
                    request_id=request_id,
                    model=self.llm_model_name,
                    agent=self.agent_name,
                    attempt=attempt + 1,
                    error=type(e).__name__,
                )
                if attempt < self.max_retries:
                    self.retry_count += 1
                    # time.sleep(self.retry_delay * (attempt + 1))
                    time.sleep(1)
                    continue
                else:
                    self.failed_requests += 1
                    emit_timing(
                        None,
                        "llm.request.failed",
                        request_started_at,
                        request_id=request_id,
                        model=self.llm_model_name,
                        agent=self.agent_name,
                        attempts=attempt + 1,
                    )
                    raise Exception(f"Failed after {self.max_retries} retries. Last error: {str(last_error)}") from last_error
