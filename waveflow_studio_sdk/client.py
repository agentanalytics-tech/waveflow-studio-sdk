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

    def enhance_prompt(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Call the /enhance_prompt endpoint to enhance a user-provided prompt.

        Parameters:
            prompt (str): The text prompt to enhance.
            session_id (str, optional): Optional session ID. If not provided, server can generate one.

        Returns:
            Dict[str, Any]: Dictionary containing 'original_prompt' and 'enhanced_prompt'.
        """
        url = f"{self.base_url}/enhance_prompt"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())  # generate new session ID if not provided

        headers["Sessionid"] = session_id

        body = {"prompt": prompt}

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if response.status_code != 200:
                return {"error": data.get("error", "Unknown error occurred")}
            data["session_id"]=session_id
            return data

        except Exception as e:
            return {"error": str(e)}


    def create_agent(self, session_id: str) -> dict:
        """
        Create agents for a given workflow session.

        Args:
            session_id (str): The session ID of the workflow.

        Returns:
            dict: A dictionary containing the created agents and workflow name.
        """
        url = f"{self.base_url}/create_agent"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"session_id": session_id}

        try:
            response = requests.post(url, headers=headers, json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_together_models(self) -> list:
        """
        Fetch available models from the Together API.

        Returns:
            list: List of model IDs.
        """
        url = f"{self.base_url}/get-together-models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to fetch models: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    
    
    def model_health_check(self, model_name: str, api_key: str, base_url: str, description: str = None):
        """
        Performs a health check for a given model using the API.

        Args:
            model_name (str): The model identifier (e.g. "mistralai/Mistral-7B-Instruct-v0.2")
            api_key (str): The API key for the model provider (e.g. Together API key)
            base_url (str): The base API URL (e.g. "https://api.together.xyz/v1")
            description (str, optional): A custom system description for the model

        Returns:
            dict: JSON response from the server, e.g.
                {"message": "success"} or {"message": "error", "details": "..."}
        """
        payload = {
            "model_name": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "description": description
        }

        url = f"{self.base_url}/model_health_check"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"message": "error", "details": str(e)}



    def get_models(self):
        """
        Fetches the user's saved models from the backend database.

        Returns:
            dict: A dictionary containing the list of models, e.g.
                {"models": ["gpt-4", "mistral-7b", "custom-agent-v1"]}
        """
        url = f"{self.base_url}/get_models"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to fetch models", "details": str(e)}

    # -----------------------------
    # Assign Roles
    # -----------------------------
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
