import requests
import json
from typing import Optional, Dict, Any, Union
import uuid
import os
from typing import List
import re

class InvalidAPIKeyError(Exception):
    """Raised when the API key is invalid."""
    pass

class WaveFlowStudio:
    def __init__(self, api_key: str, base_url: str = "http://3.92.146.100:5000"):
        """
        Initialize SDK with API key and validate.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._validate_api_key()
        self.workflow_id = None

    # def _validate_api_key(self) -> str:
    #     """
    #     Validate API key with server and return user_id if valid.
    #     """
    #     url = f"{self.base_url}/user"
    #     headers = {"Authorization": f"Bearer {self.api_key}"}

    #     try:
    #         response = requests.get(url, headers=headers)
    #         res = response.json()
    #         if res.get("status_code") == 200:
    #             user_id = res.get("content").get("valid")
    #             if not user_id:
    #                 raise InvalidAPIKeyError("API key not associated with any user.")
    #             return 
    #         elif response.status_code == 401:
    #             raise InvalidAPIKeyError("Invalid API key provided.")
    #         else:
    #             raise Exception(f"Unexpected error: {response.status_code} - {response.text}")
    #     except requests.RequestException as e:
    #         raise Exception(f"[ERROR] API validation failed: {e}")

    def _validate_api_key(self):
        """
        Validate API key:
        - If AAAI key → trust backend during usage (skip /user validation)
        - If normal JWT → validate by calling /user
        """
        if self.api_key.startswith("AAAI"):
            # ✅ Skip /user check for AAAI keys (backend validates later automatically)
            return

        # ✅ Normal Supabase JWT validation
        url = f"{self.base_url}/user"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(url, headers=headers)
            res = response.json()
            if res.get("status_code") == 200 and res.get("content", {}).get("valid"):
                return
            raise InvalidAPIKeyError("Invalid API key provided.")
        except requests.RequestException:
            raise InvalidAPIKeyError("Invalid API key provided.")
        
    def _handle_response(self, response: requests.Response):
            """
            Private helper to parse responses and raise errors.
            """
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                response.raise_for_status()
                return {"status": "error", "message": "Unknown server error"}

            if not response.ok:
                # --- THIS IS THE UPDATE ---
                # It now checks for "detail" (FastAPI) first, 
                # then "error", then "message".
                error_message = data.get(
                    "detail", 
                    data.get("error", data.get("message", "Unknown API error"))
                )
                # --------------------------
                raise Exception(f"API Error (HTTP {response.status_code}): {error_message}")
                
            return data
    def get_all_prompt_data(self) -> Dict[str, Any]:
        """
        Fetch all saved prompts for the authenticated user.

        Returns:
            Dict[str, Any]: List of all prompt records or an error message.
        """
        url = f"{self.base_url}/show_all_prompt_data"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }
        except Exception as e:
            return {"error": "Failed to fetch prompt data", "details": str(e)}
    
    def run_prompt_test_copy(
        self,
        prompt: list,
        session_id: str,
        model_data: dict,
        selected_model: str,
        system_message: list = None,
        temperature: float = 0.7,
        top_p: int = 50,
        max_tokens: int = 1024,
        json_response: bool = False
    ) -> Dict[str, Any]:
        """
        Test prompts against selected LLM model.

        Args:
            prompt (list): List of user prompts.
            session_id (str): Active session ID.
            model_data (dict): Must contain id, client, base_url.
            selected_model (str): Model name to use.
            system_message (list, optional): Defaults to AI assistant role.
            temperature (float)
            top_p (int)
            max_tokens (int)
            json_response (bool)

        Returns:
            Dict[str, Any]: JSON response with answer or error.
        """

        url = f"{self.base_url}/prompt_testing_copy"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "session_id": session_id,
            "model": model_data,
            "selected_model": selected_model,
            "system_message": system_message or ["You are a Helpful AI Assistant"],
            "temperature": temperature,
            "top_p": top_p,
            "tokens": max_tokens,
            "json": json_response
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {"error": "HTTP error occurred", "details": str(http_err)}
        except Exception as e:
            return {"error": str(e)}