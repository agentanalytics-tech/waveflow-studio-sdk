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
    def read_workflows(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch all workflows for a given user ID.

        Parameters:
            user_id (str): The user ID (typically the user's email).

        Returns:
            Dict[str, Any]: The list of workflows or an error message.
        """
        url = f"{self.base_url}/read-workflows"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"user_id": user_id}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if response.status_code == 200:
                return data
            else:
                return {
                    "error": f"Failed with status {response.status_code}",
                    "response": data
                }

        except Exception as e:
            return {"error": str(e)}
    def create_workflow(self, json_file_path: str) -> Dict[str, Any]:
        """
        Create workflow by uploading JSON file.
        The server infers user_id from API key, so it is not sent explicitly.
        """
        url = f"{self.base_url}/workflow-config"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with open(json_file_path, 'r') as file:
                json_data = json.load(file)
                # print("file_content",json_data)

            body = {
                "agents_data" : json_data
            }
            response = requests.post(url, headers=headers, json = body)
            
            resp_json = response.json()
            # print("this is response :",resp_json)
            if resp_json.get("workflow_id"):
                self.workflow_id = resp_json["workflow_id"]
            return resp_json
        except Exception as e:
            # print(str(e))
            return {"error": str(e)}
    def create_workflow_config(self, agents_data: str) -> Dict[str, Any]:
            """
            Creates agents from an encrypted JSON file/string.
            This is an authenticated POST endpoint.

            Args:
                agents_data (str): The encrypted JSON data string.

            Returns:
                Dict[str, Any]: The API response, e.g., {"status_code": 200, "workflow_id": "..."}
            
            Raises:
                Exception: If the API call fails.
                ValueError: For missing required arguments.
            """
            if not agents_data:
                raise ValueError("agents_data is required.")
                
            url = f"{self.base_url}/workflow-config"
            
            payload = {
                "agents_data": agents_data
            }
            
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, json=payload, headers=headers)
                
                # This endpoint returns custom status_code in its body.
                # We'll rely on _handle_response for HTTP errors, but also
                # check the body for application-level errors.
                json_response = self._handle_response(response)
                
                if json_response.get("status_code") != 200:
                    raise Exception(f"API Error ({json_response.get('status_code')}): {json_response.get('message', 'Unknown error')}")
                    
                return json_response
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def rename_workflow(self, session_id: str, new_name: str, new_desc: Optional[str] = None) -> Dict[str, Any]:
            """
            Renames an existing workflow.
            This is an authenticated PUT endpoint that uses query parameters.

            Args:
                session_id (str): The ID of the workflow to rename.
                new_name (str): The new name for the workflow.
                new_desc (Optional[str]): The new description (optional).

            Returns:
                Dict[str, Any]: The API response, e.g., {"message": "Workflow renamed successfully", ...}
            
            Raises:
                Exception: If the API call fails (e.g., 404 Not Found, 500 Server Error).
                ValueError: For missing required arguments.
            """
            if not session_id:
                raise ValueError("session_id is required.")
            if not new_name:
                raise ValueError("new_name is required.")
                
            url = f"{self.base_url}/rename_workflow/"
            
            # This endpoint uses query parameters for a PUT request
            params: Dict[str, str] = {
                "session_id": session_id,
                "new_name": new_name
            }
            if new_desc is not None:
                params["new_desc"] = new_desc

            try:
                # Note: We use 'params=' here, not 'json='
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.put(url, params=params, headers=headers)
                return self._handle_response(response)
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def workflow_admin_run(self, session_id: str) -> Dict[str, Any]:
            """
            Triggers an admin run for a specific workflow session.

            Corresponds to the POST /workflow-admin-run endpoint.

            Args:
                session_id: The ID of the session to run.

            Returns:
                A dictionary with the API response (e.g., {"message": "sucess"}).

            Raises:
                ValueError: If session_id is not provided (client-side validation).
                Exception: If the API call fails (e.g., 401, 404, 500).
            """
            # Client-side validation
            if not session_id:
                raise ValueError("session_id is required.")

            url = f"{self.base_url}/workflow-admin-run"
            payload = {"session_id": session_id}

            try:
                # This might be a long-running process, so a longer timeout is wise
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60 
                )
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                # Handles connection errors, timeouts, etc.
                raise Exception(f"Connection error: {e}")
    
    def workflow_run_chat_pdf(self, session_id: str, query: str, filenames: Optional[List[str]] = None):
            """
            Runs the chat PDF workflow by sending a query for a specific session.

            Args:
                session_id (str): The active session ID for the workflow.
                query (str): The user's question or prompt.
                filenames (Optional[List[str]]): An optional list of filenames that are
                                                part of the context for this query.

            Returns:
                dict: The JSON response from the server, containing the final answer.
            """
            url = f"{self.base_url}/workflow-run-chat-pdf"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare the form data payload
            data = {
                "session_id": session_id,
                "query": query
            }

            # The backend expects 'filenames' as a single string.
            # This SDK method conveniently accepts a Python list and joins it.
            if filenames:
                data["filenames"] = ",".join(filenames)
                
            try:
                # Send data as form fields
                response = requests.post(url, headers=headers, data=data)
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
    def update_user_workflows(self, workflows_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the authenticated user's workflows.

        Args:
            workflows_data (dict): The workflow data to update, e.g. {"workflows": [...]}

        Returns:
            dict: Contains count of updated workflows or an error message.
        """
        url = f"{self.base_url}/update-user-workflows"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.post(url, headers=headers, json=workflows_data)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Failed with status {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def delete_workflow(self, session_id: str) -> Dict[str, Any]:
        """
        Delete a workflow and its associated history by session ID.

        Args:
            session_id (str): The unique session ID of the workflow to delete.

        Returns:
            Dict[str, Any]: Response from the backend confirming deletion or error.
        """
        if not session_id:
            return {"error": "Session ID is required to delete a workflow."}

        url = f"{self.base_url}/delete-workflow/{session_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.delete(url, headers=headers)
            data = response.json()
            if response.status_code == 200:
                # Optionally clear workflow_id if deleted
                if self.workflow_id == session_id:
                    self.workflow_id = None
                return {"message": data.get("message", "Workflow deleted successfully")}
            else:
                return {"error": data.get("error", "Unknown error occurred")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
    def publish_workflow(
        self,
        flowname: str,
        flowDesc: str,
        flowId: str,
        session_id: str,
        username: str
    ) -> Dict[str, Any]:
        """
        Publish a workflow template so it becomes publicly accessible.
        """

        url = f"{self.base_url}/publish_workflow"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Username": username,   
            "Content-Type": "application/json"
        }
        payload = {
            "workflow_name": flowname,
            "workflow_description": flowDesc,
            "workflow_id": flowId,
            "session_id": session_id
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def deploy_workflow(
            self,
            flow_id: str,
            flowname: str,
            flow_desc: str,
            deployment_req: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Triggers a deployment for a given workflow.
            This is an authenticated POST endpoint.

            Args:
                flow_id (str): The session_id of the workflow.
                flowname (str): The name of the workflow.
                flow_desc (str): A description for the workflow.
                deployment_req (Optional[Dict[str, Any]]): Optional deployment-specific
                                                        settings (e.g., {"repo_url": "..."}).

            Returns:
                Dict[str, Any]: The API response.
            
            Raises:
                Exception: If the API call fails.
                ValueError: For missing required arguments.
            """
            if not flow_id: raise ValueError("flow_id is required.")
            if not flowname: raise ValueError("flowname is required.")
            
            url = f"{self.base_url}/deploy"
            
            payload = {
                "flowId": flow_id,
                "flowname": flowname,
                "flowDesc": flow_desc,
                "deployment": deployment_req or {}
            }
            
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, json=payload, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")
    def undeploy_workflow(self, session_id: str) -> Dict[str, Any]:
            """
            Undeploys an active workflow.
            This is an authenticated POST endpoint.

            Args:
                session_id (str): The ID of the workflow to undeploy.

            Returns:
                Dict[str, Any]: The API response, e.g., {"message": "Workflow undeployed successfully...", ...}
            
            Raises:
                Exception: If the API call fails (e.g., 404 Not Found).
                ValueError: For missing required arguments.
            """
            if not session_id:
                raise ValueError("session_id is required.")
                
            url = f"{self.base_url}/undeploy"
            
            payload = {
                "session_id": session_id
            }
            
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, json=payload, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")