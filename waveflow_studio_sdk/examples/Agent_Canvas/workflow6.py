##############################################
# Generating prompts with enhance_prompt, suprise_me, edit_with_ai and geting agents
##############################################
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
    def enhance_prompt(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Call the /enhance_prompt endpoint to enhance a user-provided prompt.

        Parameters:
            prompt (str): The text prompt to enhance.
            session_id (str, optional): Optional session ID. If not provided, server can generate one.

        Returns:
            Dict[str, Any]: Dictionary containing 'original_prompt' and 'enhanced_prompt'.
        """
        url = f"{self.base_url}/enhance_prompt"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not session_id:
            session_id = str(uuid.uuid4())  # generate new session ID if not provided

        headers["Sessionid"] = session_id

        body = {"prompt": prompt}

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if response.status_code != 200:
                return {"error": data.get("error", "Unknown error occurred")}
            data["session_id"]=session_id
            return data

        except Exception as e:
            return {"error": str(e)}
    def surprise_me(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a surprise prompt from the backend.

        If session_id is not provided, a new one is auto-generated.
        """
        url = f"{self.base_url}/surprise_me"

        if not session_id:
            session_id = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Sessionid": session_id
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to fetch models", "details": str(e)}
    def edit_with_ai(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a prompt to the backend for AI-powered enhancement.

        Args:
            prompt (str): The text prompt to be improved by AI.
            session_id (Optional[str]): Optional session identifier header.

        Returns:
            dict: Edited prompt or error information.
        """
        url = f"{self.base_url}/edit-with-ai"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Attach session header only if provided
        if session_id:
            headers["Sessionid"] = session_id

        body = {"prompt": prompt}

        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }

        except requests.exceptions.RequestException as req_err:
            return {"error": "Request failed", "details": str(req_err)}

        except Exception as e:
            return {"error": "Unexpected failure", "details": str(e)}
    def assign_roles(self, prompt: str):
        """
        Creates agents and assigns roles based on the given prompt.

        Args:
            prompt (str): The user prompt describing what agents/tools to create.

        Returns:
            dict: Details about created agents, tools, and session info.
        """
        url = f"{self.base_url}/assign_roles"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}
        list_ = self.get_models()

        if len(list_["models"])==0:
            return {"error": "No model is added, Please do add one model", "details": "use WaveFlowStudio.set_model() to create one"}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to assign roles", "details": str(e)}