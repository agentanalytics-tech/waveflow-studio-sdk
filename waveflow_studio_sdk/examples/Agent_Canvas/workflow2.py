##############################################
# Creating worklfow with option to update the agents
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
    def update_agent(
        self, 
        agent_id: str, 
        name: str, 
        role: str, 
        description: str,
        model: Dict[str, Any] = None,
        tools: List[Dict[str, Any]] = None,
        advanced_parameters: Dict[str, Any] = None,
        web_search: bool = False
    ) -> dict:
        """
        Calls the /update-agent endpoint for a node of type 'agent'.
        """
        url = f"{self.base_url}/update-agent"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct the payload as expected by the API
        payload = {
            "type": "agent",
            "id": agent_id,
            "name": name,
            "role": role,
            "description": description,
            "model": model,
            "tool": tools if tools is not None else [], # API logic uses 'tool'
            "advanced_parameters": advanced_parameters if advanced_parameters is not None else {},
            "webSearch": web_search
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"success": False, "error": str(http_err)}
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred: {req_err}")
            return {"success": False, "error": str(req_err)}
        except json.JSONDecodeError:
            print("Failed to decode JSON response")
            return {"success": False, "error": "Invalid JSON response from server."}
    def update_sequence_ids(self, file_name: str, agents: List[str]) -> Dict[str, Any]:
            """
            Updates the sequence of agent IDs for a given file.
            This is an authenticated POST endpoint that expects JSON.

            Args:
                file_name (str): The name of the file (e.g., "workflow-abc")
                agents (List[str]): A list of agent ID strings.

            Returns:
                Dict[str, Any]: The API response.
            
            Raises:
                Exception: If the API call fails.
                ValueError: For missing required arguments.
            """
            if not file_name: raise ValueError("file_name is required.")
            if not isinstance(agents, list): raise ValueError("agents must be a list.")
                
            url = f"{self.base_url}/sequence-ids"
            
            payload = {
                "file_name": file_name,
                "agents": agents
            }
            
            try:
                # Use json= to send data as 'application/json'
                # Use self.headers for authentication
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, json=payload, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def run_workflow(
        self,
        agents: list,
        file_name: str = "agents",
        aichat_option: str = "Conversationalai",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the workflow to generate a sequence of agents.

        Args:
            agents (list): List of agent IDs or agent configurations.
            file_name (str): File or collection name (default: "agents").
            aichat_option (str): Type of AI chat mode (default: "Conversationalai").
            session_id (Optional[str]): The current session ID.

        Returns:
            Dict[str, Any]: API response containing message and sequence data.
        """
        url = f"{self.base_url}/run"
        sid = session_id or self.workflow_id
        if not sid:
            return {"error": "No session_id found. Create a workflow first."}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Sessionid": sid
        }

        payload = {
            "agents": agents,
            # "file_name": file_name,
            "aichatOption": aichat_option
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            # Optionally update workflow_id if backend returns new one
            if "session_id" in data:
                self.workflow_id = data["session_id"]

            return data
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
    def chat_pdf(
            self,
            session_id: str,
            query: str,
            file_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Send a chat query (and optionally a file) to the /chat_pdf endpoint.

            Args:
                session_id (str): Session ID obtained from /run.
                query (str): Text query for the chatbot.
                file_path (Optional[str]): Optional path to a file to upload.

            Returns:
                Dict[str, Any]: API response from backend.
            """
            url = f"{self.base_url}/chat_pdf"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Sessionid": session_id
            }

            # Build request
            files = None
            data = {"query": query}

            if file_path and os.path.exists(file_path):
                files = {"files": (os.path.basename(file_path), open(file_path, "rb"))}

            try:
                response = requests.post(url, headers=headers, data=data, files=files)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                return {"error": f"Request failed: {str(e)}"}
            except Exception as e:
                return {"error": str(e)}
            finally:
                if files:
                    files["files"][1].close()
    def upload_file(self, user_id: str, file_path: str) -> dict:
        """
        Upload a file for a given user to the backend.

        Args:
            user_id (str): The user ID or email.
            file_path (str): Path to the file on local system.

        Returns:
            dict: Response from the server.
        """
        url = f"{self.base_url}/file_upload"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            with open(file_path, "rb") as file:
                files = {"file": (os.path.basename(file_path), file)}
                data = {"user_id": user_id}
                response = requests.post(url, headers=headers, files=files, data=data)

            try:
                return response.json()
            except Exception:
                return {"error": "Invalid JSON response", "raw": response.text}

        except Exception as e:
            return {"error": str(e)}
