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
    def get_user_summary(self):
        """
        Fetches the user's summary (workflows, models, tools) from the backend.

        Returns:
            dict: Summary data or error details.
        """
        url = f"{self.base_url}/get-user-summary"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to fetch user summary",
                "details": str(e)
            }
    def user_details(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch the authenticated user's profile details.

        Args:
            username (Optional[str]): Optional username header to include.
                                    If not provided, defaults to 'Unknown'.

        Returns:
            dict: Contains the user details or error information.
        """
        url = f"{self.base_url}/profile/user-details"

        # Build headers safely
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Username": username or "Unknown"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            # Return structured response so tests can check exact failure type
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }
        except requests.exceptions.RequestException as req_err:
            # Covers timeouts, connection issues, etc.
            return {"error": "Request failed", "details": str(req_err)}
        except Exception as e:
            # Generic safeguard
            return {"error": "Unexpected failure", "details": str(e)}
    def get_token_data(self) -> Dict[str, Any]:
            """
            Fetches the authenticated user's token and usage data from the /token_data endpoint.
            
            The user is identified by the API key (token) on the server side.

            Returns:
                Dict[str, Any]: A dictionary containing usage statistics,
                                or an error message.
            """
            url = f"{self.base_url}/token_data"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            try:
                response = requests.get(url, headers=headers)
                # Raise an HTTPError for bad responses (4xx or 5xx)
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.HTTPError as http_err:
                # Try to return the JSON error response from the server if it exists
                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError:
                    return {"error": f"HTTP error: {http_err}", "status_code": response.status_code}
            
            except requests.exceptions.RequestException as req_err:
                # Handle other request-related errors (e.g., connection error)
                return {"error": f"Request failed: {req_err}"}
            
            except Exception as e:
                return {"error": f"An unexpected error occurred: {str(e)}"}
    def update_user_runs(self, run_data: dict):
            """
            Updates the user's run count or run data based on the provided dictionary.
            The 'run_data' dict is sent as the JSON payload.

            Args:
                run_data: A dictionary of data to send to the endpoint 
                        (e.g., {"workflow_id": "wf_123", "status": "success"}).

            Returns:
                A dictionary with the new run count, e.g. {"count_runs": 5}
            
            Raises:
                Exception: If the API call fails (e.g., 401, 400, 500).
                ValueError: If 'run_data' is not a dictionary.
            """
            if not isinstance(run_data, dict):
                # Client-side validation
                raise ValueError("run_data must be a dictionary.")

            url = f"{self.base_url}/update-user-runs"
            # The endpoint expects a 'data' dict, which is the JSON body.
            # The 'email' is added by the server, so we just send the run_data.
            payload = run_data
            
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, headers=headers, json=payload)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")  
    def get_user_details(self) -> Dict[str, Any]:
            """
            Checks if the current user's token is valid.
            This is an authenticated GET endpoint.

            Returns:
                Dict[str, Any]: The API response, e.g., {"status_code": 200, "content": {"valid": True}}
            
            Raises:
                Exception: If the API call fails (e.g., 401 Unauthorized).
            """
            url = f"{self.base_url}/user"
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def get_session_data(self) -> Dict[str, Any]:
        """
        Fetch all session summaries for the authenticated user.

        Returns:get_session_history()
            Dict[str, Any]: A dictionary containing all session summaries or an error message.
        """
        url = f"{self.base_url}/session_data"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Failed with status {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}