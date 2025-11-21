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
    def get_tools(self):
        """
        Fetch all tools for the authenticated user.
        Matches the current /get_tools FastAPI endpoint behavior.
        """
        try:
            url = f"{self.base_url}/get_tools"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Return raw JSON as provided by your backend
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }
        except Exception as e:
            return {"error": "Failed to fetch tools", "details": str(e)}
    def get_enums_by_app(self, enum_name: str):
        """
        Fetches available enums (functions) for a given app/toolkit.

        Args:
            enum_name (str): The name of the app/toolkit (e.g., 'slack', 'notion', 'github').

        Returns:
            dict: Enum list or error details.
        """
        url = f"{self.base_url}/get-enums-by-app"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"enum": enum_name}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to fetch enums by app",
                "details": str(e)
            }
    def get_apps(self):
            """
            Retrieves the list of available Composio apps (toolkits) from the server.

            Returns:
                dict: The JSON response from the server, which should be a list
                    of app dictionaries on success.
            """
            url = f"{self.base_url}/apps"
            
            try:
                # Make a simple GET request, no headers or data needed
                response = requests.get(url)
                
                # Raise an exception for bad status codes (like 404, 500)
                response.raise_for_status()
                
                # Return the parsed JSON response
                return response.json()
                
            except requests.exceptions.HTTPError as http_err:
                return {
                    "error": "HTTP error occurred",
                    "status_code": response.status_code,
                    "details": str(http_err),
                    "response_text": response.text
                }
            except requests.exceptions.RequestException as req_err:
                # Handle other network-related errors
                return {"error": "Request failed", "details": str(req_err)}
            

    def get_connections(self):
            """
            Retrieves the list of active connections for the authenticated user.

            Returns:
                dict: The JSON response from the server, containing a list of connections.
            """
            url = f"{self.base_url}/connections"
            
            # This endpoint requires authentication to identify the user.
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
                
            except requests.exceptions.HTTPError as http_err:
                return {
                    "error": "HTTP error occurred",
                    "status_code": response.status_code,
                    "details": str(http_err),
                    "response_text": response.text
                }
            except requests.exceptions.RequestException as req_err:
                return {"error": "Request failed", "details": str(req_err)}
    
    
    
    def initiate_connection(self, toolkit: str, credentials: Optional[Dict[str, str]] = None):
            """
            Initiates a connection for a given toolkit (app).

            - If credentials are NOT provided, this may return a list of required fields.
            - If credentials ARE provided, it attempts to create the connection.
            - For OAuth apps, it may return a redirect URL.

            Args:
                toolkit (str): The slug of the toolkit to connect (e.g., 'github').
                credentials (Optional[Dict[str, str]]): A dictionary of credentials
                    (like API keys) if required by the toolkit for custom auth.

            Returns:
                dict: The JSON response from the server.
            """
            url = f"{self.base_url}/initiate-connection"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"  # Important for sending JSON data
            }
            
            # Prepare the JSON payload
            payload = {
                "toolkit": toolkit
            }
            if credentials:
                payload["credentials"] = credentials
                
            try:
                # The `json` parameter automatically serializes the payload
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as http_err:
                return {
                    "error": "HTTP error occurred",
                    "status_code": response.status_code,
                    "details": str(http_err),
                    "response_text": response.text
                }
            except requests.exceptions.RequestException as req_err:
                return {"error": "Request failed", "details": str(req_err)}
    def delete_connection(self, connection_id: str) -> Dict[str, Any]:
            """
            Deletes a specific tool connection.

            Corresponds to the POST /delete_connection endpoint.

            Args:
                connection_id: The ID of the connection to be deleted (maps to 'id' in backend).

            Returns:
                A dictionary with the API response 
                (e.g., {"success": True, "result": ...}).

            Raises:
                ValueError: If connection_id is not provided (client-side validation).
                Exception: If the API call fails (e.g., 401, 400, 500).
            """
            # Client-side validation
            if not connection_id:
                raise ValueError("connection_id is required.")

            url = f"{self.base_url}/delete_connection"
            payload = {"id": connection_id}

            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=30 # 30 seconds
                )
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:raise Exception(f"Connection error: {e}")
    def filter_apps(self) -> Dict[str, Any]:
        """
        Fetch and return available app/tool categories from the backend.

        Returns:
            Dict[str, Any]: A list of app categories or error details.
        """
        url = f"{self.base_url}/filter_apps"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return {"apps": response.json()}
            else:
                return {"error": response.json().get("error", "Unknown error occurred")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
        
    def get_tool_info(self, app_name: str) -> Dict[str, Any]:
        """
        Fetch tools and details associated with a given app/toolkit name.

        Args:
            app_name (str): Name of the app/toolkit (e.g., 'firecrawl', 'gmail', 'notion').

        Returns:
            Dict[str, Any]: List of tools or an error message.
        """
        if not app_name:
            return {"error": "app_name is required."}

        url = f"{self.base_url}/app_info"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"app_name": app_name}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if response.status_code == 200:
                return data  # Should include list of tools for this app
            else:
                return {"error": data.get("error", "Unknown error occurred")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
        

    def get_tool_fields(self, slug_name: str) -> Dict[str, Any]:
        """
        Fetch required input fields for a specific tool identified by its slug.

        Args:
            slug_name (str): Tool slug name (e.g., 'FIRECRAWL_SEARCH', 'NOTION_CREATE_PAGE').

        Returns:
            Dict[str, Any]: Field definitions including type, required, and examples.
        """
        if not slug_name:
            return {"error": "slug_name is required."}

        url = f"{self.base_url}/fields"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"slug_name": slug_name}

        try:
            response = requests.post(url, headers=headers, params=params, json={})
            data = response.json()

            if response.status_code == 200:
                return data.get("fields", data)
            else:
                return {"error": data.get("error", "Unknown error occurred")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    def execute_tool(self, slug: str, arguments: dict) -> Dict[str, Any]:
        """
        Execute a Composio tool by slug name.

        Args:
            slug (str): The slug/name of the tool to execute (e.g., "FIRECRAWL_SEARCH").
            arguments (dict): Dictionary of input parameters required by the tool.

        Returns:
            Dict[str, Any]: Execution result or error details.
        """
        if not slug:
            return {"error": "Tool slug is required."}

        url = f"{self.base_url}/execute"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "slug": slug,
            "arguments": arguments
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code == 200 and data.get("success"):
                return data["result"]

            return {"error": data.get("error", data)}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}