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
    def return_models(self, file_name: str) -> dict:
        """
        Fetch model configurations by file name.
        """
        url = f"{self.base_url}/return_models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=body)
            return response.json()
        except Exception as e:
            return {"error": str(e)}


    def return_agents(self, file_name: str) -> dict:
        """
        Fetch agent configurations by file name.
        """
        url = f"{self.base_url}/return_agents"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=body)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    def return_workflows(self, file_name: str) -> dict:
        """
        Fetch workflow data from a local JSON file on the backend.

        Parameters:
            file_name (str): The name of the JSON file to read (e.g., 'workflows.json').

        Returns:
            dict: Parsed JSON content or an error message.
        """
        url = f"{self.base_url}/return_workflows"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if response.status_code == 200:
                return data
            else:
                return {"error": f"Failed with status {response.status_code}", "response": data}
        except Exception as e:
            return {"error": str(e)}
    def get_user_metadata(self) -> Dict[str, Any]:
            """
            Fetches the metadata for the authenticated user.
            This is an authenticated GET endpoint.

            Returns:
                Dict[str, Any]: The API response, e.g., {"user_metadata": {...}}
            
            Raises:
                Exception: If the API call fails (e.g., 404 Not Found, 401 Unauthorized).
            """
            url = f"{self.base_url}/profile/user-metadata"
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
