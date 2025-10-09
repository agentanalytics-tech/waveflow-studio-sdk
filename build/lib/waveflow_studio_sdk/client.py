import requests
import json
from typing import Optional, Dict, Any

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

    def _validate_api_key(self) -> str:
        """
        Validate API key with server and return user_id if valid.
        """
        url = f"{self.base_url}/user"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            res = response.json()
            if res.get("status_code") == 200:
                user_id = res.get("content").get("valid")
                if not user_id:
                    raise InvalidAPIKeyError("API key not associated with any user.")
                return 
            elif response.status_code == 401:
                raise InvalidAPIKeyError("Invalid API key provided.")
            else:
                raise Exception(f"Unexpected error: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            raise Exception(f"[ERROR] API validation failed: {e}")


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
        
    def get_history(self):
        url = f"{self.base_url}/get-session-history"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "session_id": self.workflow_id,
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            data = response.json()
            # print(data)
            return data
        except Exception as e:
            return {"error": str(e)}
