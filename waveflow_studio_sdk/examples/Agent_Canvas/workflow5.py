##############################################
# Creating worklfow and running through Bussiness Automation
# Can also run throgh conevrsational ai or citation by chosing option in run_workflow():(aichatooption)
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
    def get_prompt_framework(self, session_id: str) -> Union[str, dict]:
            """
            Calls the GET /prompt_framework endpoint to generate a prompt template.
            
            Args:
                session_id: The ID of the session. This is sent as a 'Sessionid' header.

            Returns:
                - On success: A string containing the raw prompt template.
                - On failure: A dictionary containing error details.
            """
            url = f"{self.base_url}/prompt_framework"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Sessionid": session_id  # Note the header name 'Sessionid'
            }
            
            try:
                response = requests.get(url, headers=headers)
                
                # Raise an exception for bad status codes (4xx, 5xx)
                response.raise_for_status()
                
                # On success (200), the API returns the raw text.
                # We return response.text, not response.json()
                return response.text 
                
            except requests.exceptions.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
                try:
                    # Errors (400, 500, etc.) ARE returned as JSON
                    return response.json() 
                except json.JSONDecodeError:
                    # Fallback if the error response isn't JSON
                    return {"success": False, "error": str(http_err), "details": response.text}
            except requests.exceptions.RequestException as req_err:
                print(f"An error occurred: {req_err}")
                return {"success": False, "error": str(req_err)}
    def file(self, file_path: str):
        url = f"{self.base_url}/file"
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            headers = {"Authorization": f"Bearer {self.api_key}"}  # minimal auth only
            response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    def extract_text(self, file_path: str):
            """
            Uploads a file (PDF, DOCX, or TXT) to extract its text content.

            Args:
                file_path (str): The local path to the file you want to upload.

            Returns:
                dict: The JSON response from the server, containing the extracted text
                    or an error message.
            """
            # 1. Check if the file exists locally before trying to send it
            if not os.path.exists(file_path):
                return {"error": "File not found", "path": file_path}

            # 2. Construct the full URL for the endpoint
            url = f"{self.base_url}/extract-text"

            # 3. Open the file in binary read mode and send the request
            try:
                with open(file_path, "rb") as f:
                    # The 'files' dictionary key 'file' must match the FastAPI
                    # parameter name: async def extract_text(file: UploadFile ...):
                    files = {"file": (os.path.basename(file_path), f)}
                    
                    response = requests.post(url, files=files)
                    
                    # Raise an exception for bad responses (4xx or 5xx)
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
    
    def test_automation_workflow(
            self,
            session_id: str,
            query: str,
            cycle_type: str = "immediate",
            config: Optional[Dict[str, Any]] = None,
            filenames: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """
            Triggers or schedules a test automation workflow.
            This is an authenticated POST endpoint.

            Args:
                session_id (str): The session ID associated with the agents.
                query (str): The natural language query/instruction for the automation.
                cycle_type (str, optional): Execution type. Options: "immediate", 
                                        "regular_interval", or "custom". Defaults to "immediate".
                config (Optional[Dict[str, Any]]): Configuration for scheduling (e.g., repeat interval, 
                                                start dates). Defaults to {}.
                filenames (Optional[List[str]]): A list of filenames (strings) that have previously 
                                            been uploaded to the staging area. Defaults to [].

            Returns:
                Dict[str, Any]: The API response containing schedule status and job details.

            Raises:
                Exception: If the API call fails.
                ValueError: For missing required arguments.
            """
            if not session_id: raise ValueError("session_id is required.")
            if not query: raise ValueError("query is required.")

            url = f"{self.base_url}/test-automation-workflow"

            # The endpoint expects Form data where 'config' and 'filenames' 
            # are JSON-serialized strings.
            import json
            
            payload = {
                "session_id": session_id,
                "query": query,
                "cycle_type": cycle_type,
                "config": json.dumps(config if config is not None else {}),
                "filenames": json.dumps(filenames if filenames is not None else [])
            }

            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                # Use 'data' instead of 'json' because the endpoint uses Form(...)
                response = requests.post(url, data=payload, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def save_prompt(self, name: str, session_id: str, desc: str = None):
            """
            Saves a new prompt to the database.

            Args:
                name: The required name of the prompt.
                session_id: The session ID to associate the prompt with.
                desc: An optional description for the prompt.

            Returns:
                A dictionary with the API success response.
            
            Raises:
                Exception: If the API call fails (e.g., 400, 500).
            """
            if not name:
                # Client-side validation to prevent a bad request
                raise ValueError("Prompt name is required.")

            url = f"{self.base_url}/save_prompt"
            payload = {
                "name": name,
                "desc": desc,
                "session_id": session_id
            }
            
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, headers=headers, json=payload)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")

    def fetch_prompt_data(self, session_id: str):
            """
            Fetches all prompt data associated with a specific session_id.

            Args:
                session_id: The session ID to fetch data for.

            Returns:
                A dictionary containing the API response.
                - On success with data: {"data": [...]}
                - On success with no data: {"message": "No data found"}
            
            Raises:
                Exception: If the API call fails (e.g., 400, 500).
            """
            if not session_id:
                # Client-side validation
                raise ValueError("Session ID is required.")

            url = f"{self.base_url}/fetch_prompt_data"
            payload = {
                "session_id": session_id
            }
            
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, headers=headers, json=payload)
                # _handle_response will correctly return the JSON for 200 OK
                # whether it contains 'data' or 'message'
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
            
    def user_query(self, session_id: str, user_id: str, query: str, filenames: Optional[str] = None):
            """
            Submits a query to the main user_query endpoint.
            This endpoint uses form-data and is unauthenticated.

            Args:
                session_id (str): The session ID.
                user_id (str): The user ID.
                query (str): The user's query.
                filenames (Optional[str]): A string of filenames (e.g., "file1.pdf,file2.txt").

            Returns:
                Dict[str, Any]: The API response, e.g., {"message": "success", "final_answer": "..."}
            
            Raises:
                Exception: If the API call fails.
                ValueError: For missing required arguments.
            """
            if not session_id: raise ValueError("session_id is required.")
            if not user_id: raise ValueError("user_id is required.")
            if not query: raise ValueError("query is required.")
                
            url = f"{self.base_url}/user_query"
            
            # This payload will be sent as 'application/x-www-form-urlencoded'
            # because we are using 'data=' instead of 'json='
            payload: Dict[str, str] = {
                "session_id": session_id,
                "user_id": user_id,
                "query": query,
            }
            
            if filenames is not None:
                payload["filenames"] = filenames

            try:
                # We use 'data=' for form data.
                # We do NOT pass 'headers' because this endpoint is unauthenticated
                # and 'requests' will set the 'Content-Type' for 'data=' automatically.
                response = requests.post(url, data=payload)
                
                # We can still use _handle_response to parse the JSON *response*
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")