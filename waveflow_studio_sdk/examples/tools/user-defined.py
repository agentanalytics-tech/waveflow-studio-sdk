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
    def add_tool(self, token: str, name: str, description: str, file_path: str, secrets: list = None):
        """
        Uploads a Python tool file along with metadata and optional secrets.

        Args:
            token (str): Authorization token.
            name (str): Tool name.
            description (str): Tool description.
            file_path (str): Path to the Python file (.py) to upload.
            secrets (list): Optional list of dictionaries. Example:
                            [{"key": "OPENAI_API_KEY", "value": "sk-xxxxx"}]
        Returns:
            dict: JSON response from the API.
        """

        url = f"{self.base_url}/add-tools"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        # Form data
        data = {
            "name": name,
            "description": description
        }

        # Add secrets if present
        if secrets:
            for i, secret in enumerate(secrets):
                data[f"secrets[{i}][key]"] = secret["key"]
                data[f"secrets[{i}][value]"] = secret["value"]

        # Ensure file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        files = {
            "file": open(file_path, "rb")
        }

        try:
            response = requests.post(url, headers=headers, data=data, files=files)
            files["file"].close()
        except Exception as e:
            files["file"].close()
            return {"error": f"Request failed: {str(e)}"}

        try:
            return response.json()
        except Exception:
            return {"error": "Invalid response format", "raw_text": response.text}
    
    
    def delete_tool(self, tool_id: str):
            """
            Deletes a tool from the database using its unique ID.

            Args:
                tool_id (str): The unique identifier of the tool to be deleted.

            Returns:
                dict: The JSON response from the server.
            """
            # Construct the full URL for the DELETE request
            url = f"{self.base_url}/delete-tool/{tool_id}"

            # Set up the authorization header
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            try:
                # Make the DELETE request
                response = requests.delete(url, headers=headers)
                
                # Raise an exception for bad status codes (like 404, 500, etc.)
                response.raise_for_status()

                # Return the JSON body of the response
                return response.json()

            except requests.exceptions.HTTPError as http_err:
                # Handle specific HTTP errors
                return {
                    "error": "HTTP error occurred",
                    "status_code": response.status_code,
                    "details": str(http_err),
                    "response_text": response.text
                }
            except requests.exceptions.RequestException as req_err:
                # Handle other request-related errors (e.g., connection error)
                return {"error": "Request failed", "details": str(req_err)}