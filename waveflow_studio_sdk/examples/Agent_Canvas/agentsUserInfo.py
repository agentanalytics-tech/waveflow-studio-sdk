##############################################
# All the get methods of the Agent Canvas
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
    def get_agents(self) -> Dict[str, Any]:
        """
        Retrieves the list of agents and workflow name from the server.

        Returns:
            Dict[str, Any]: A JSON object containing 'agents' and 'workflow_name',
                            or an error message if the request fails.
        """
        url = f"{self.base_url}/get-agents"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {"error": f"HTTP error occurred: {http_err}", "details": response.text}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}
    def get_history(self) -> Dict[str, Any]:
            """
            Fetches all data from the /history endpoint.
            
            Returns:
                Dict[str, Any]: The API response.
            
            Raises:
                Exception: If the API call fails.
            """
            url = f"{self.base_url}/history"
            try:
                headers=    {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as req_err:
                # Handle other request errors (e.g., connection error)
                raise Exception(f"Request failed: {req_err}")
    def get_agents_data(self, session_id: str) -> Dict[str, Any]:
            """
            Fetch encrypted agent data for a given session.

            Args:
                session_id (str): The session ID associated with the agents.

            Returns:
                Dict[str, Any]: Encrypted agent data or an error message.
            """
            url = f"{self.base_url}/agent_data"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"session_id": session_id}

            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"Failed with status {response.status_code}",
                        "response": response.text
                    }
            except Exception as e:
                return {"error": str(e)}
    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve chat history for a specific session.

        Args:
            session_id (str): The session ID whose chat history should be fetched.

        Returns:
            Dict[str, Any]: Chat history or an error message.
        """
        url = f"{self.base_url}/get-session-history"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"session_id": session_id}

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Failed with status {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}