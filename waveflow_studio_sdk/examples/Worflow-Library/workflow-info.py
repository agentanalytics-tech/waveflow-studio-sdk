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
    def get_workflows(self) -> Dict[str, Any]:
        """
        Retrieve all workflows created by the authenticated user.

        Returns:
            Dict[str, Any]: A list of saved workflows and count.
        """
        url = f"{self.base_url}/get_workflows"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            data = response.json()

            if response.status_code == 200:
                return {
                    "templates": data.get("templates", []),
                    "workflows_count": data.get("workflows_count", 0)
                }
            else:
                return {"error": data.get("error", "Failed to fetch workflows")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
    def get_workflow_admin_details(self) -> List[Dict[str, Any]]:
            """
            Fetches detailed workflow information for the authenticated user.
            This is an authenticated GET endpoint.

            Returns:
                List[Dict[str, Any]]: A list of workflow detail objects.
            
            Raises:
                Exception: If the API call fails.
            """
            url = f"{self.base_url}/workflow_admin"
            try:
                # Use self.headers for authentication
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                
                # This endpoint returns a list directly on success,
                # so we modify the standard handler logic slightly.
                if response.status_code == 200:
                    return response.json()
                else:
                    # Use the standard handler for error responses (4xx, 5xx)
                    return self._handle_response(response)
                    
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def get_workflows_by_model(self, model_id: str) -> Dict[str, Any]:
            """
            Finds all workflows that use a specific model.
            This is an authenticated GET endpoint.
            
            Args:
                model_id (str): The ID of the model to search for.
                
            Returns:
                Dict[str, Any]: API response, e.g., {"workflows": [...]}
                
            Raises:
                Exception: If the API call fails or the server returns an error.
                ValueError: For missing required arguments.
            """
            if not model_id:
                raise ValueError("model_id is required.")
                
            url = f"{self.base_url}/workflows_by_model"
            params = {"model_id": model_id}
            
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, params=params, headers=headers)
                # The improved _handle_response will catch 200 OK errors
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
            
    def get_workflows_by_tool(self, tool_id: str) -> Dict[str, Any]:
            """
            Finds all workflows that use a specific tool.
            This is an authenticated GET endpoint.
            
            Args:
                tool_id (str): The ID of the tool to search for.
                
            Returns:
                Dict[str, Any]: API response, e.g., {"workflows": [...]}
                
            Raises:
                Exception: If the API call fails or the server returns an error.
                ValueError: For missing required arguments.
            """
            if not tool_id:
                raise ValueError("tool_id is required.")
                
            url = f"{self.base_url}/workflows_by_tool"
            params = {"tool_id": tool_id}
            
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, params=params, headers=headers)
                # The improved _handle_response will catch 200 OK errors
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def chat(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat with the workflow.
        Requires workflow_id to be set (from create_workflow).
        """
        if not self.workflow_id:
            return {"error": "Workflow not created. Call create_workflow first."}

        url = f"{self.base_url}/workflow-run-chat-pdf-sdk"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "workflow_id": self.workflow_id,
            "query": query,
            "context": context or ""
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            data = response.json()
            # print(data)
            return {"answer": data.get("final_answer"), "conversation":data.get("conversation"), "citation": data.get("citation")}
        except Exception as e:
            return {"error": str(e)}