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


    def surprise_me(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a surprise prompt from the backend.

        If session_id is not provided, a new one is auto-generated.
        """
        url = f"{self.base_url}/surprise_me"

        if not session_id:
            session_id = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Sessionid": session_id
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to fetch models", "details": str(e)}

  
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

    def get_groq_models(self):

        """
        Fetches the list of available Groq models from the backend.

        Returns:
            dict: A list of Groq model IDs or an error message.
        """
        url = f"{self.base_url}/get-groq-models"
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
                "error": "Failed to fetch Groq models",
                "details": str(e)
            }

    def get_gemini_models(self):
        """
        Fetches the list of available Gemini models from the backend.

        Returns:
            dict: A list of Gemini model names or an error message.
        """
        url = f"{self.base_url}/get-gemini-models"
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
                "error": "Failed to fetch Gemini models",
                "details": str(e)
            }

    def get_openai_models(self):
        """
        Fetches the list of available OpenAI models from the backend.

        Returns:
            dict: A list of OpenAI model names or an error message.
        """
        url = f"{self.base_url}/get-openai-models"
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
                "error": "Failed to fetch OpenAI models",
                "details": str(e)
            }
    def get_models_by_provider(self, provider: str):
        """
        Fetches model lists dynamically based on the selected provider.

        Args:
            provider (str): The model provider name. Must be one of:
                            'groq', 'gemini', or 'openai'.

        Returns:
            dict | list: A list of model names or an error message.
        """
        provider = provider.lower()
        endpoint_map = {
            "groq": "get-groq-models",
            "gemini": "get-gemini-models",
            "openai": "get-openai-models"
        }

        if provider not in endpoint_map:
            return {
                "error": "Invalid provider",
                "details": "Valid providers are: 'groq', 'gemini', 'openai'"
            }

        url = f"{self.base_url}/{endpoint_map[provider]}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return {
                "provider": provider,
                "models": response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Failed to fetch {provider} models",
                "details": str(e)
            }


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

    def return_models(self, file_name: str) -> dict:
        """
        Fetch model configurations by file name.
        """
        url = f"{self.base_url}/return_models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=body)
            return response.json()
        except Exception as e:
            return {"error": str(e)}


    def return_agents(self, file_name: str) -> dict:
        """
        Fetch agent configurations by file name.
        """
        url = f"{self.base_url}/return_agents"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=body)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

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
    def get_session_data(self) -> Dict[str, Any]:
        """
        Fetch all session summaries for the authenticated user.

        Returns:
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
    def save_workflow(
        self,
        flowname: str,
        workflow_type: str,
        flow_desc: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save the current workflow to the user's account.

        Args:
            flowname (str): Name of the workflow to save.
            workflow_type (str): Type/category of the workflow (e.g., 'AI Agent').
            flow_desc (str): Short description of the workflow.
            session_id (Optional[str]): The session/workflow ID to save. 
                                        If not provided, uses the internally stored workflow_id.

        Returns:
            Dict[str, Any]: Server response with message or error details.
        """
        url = f"{self.base_url}/save"

        # ✅ Use stored workflow_id if not explicitly passed
        sid = session_id or self.workflow_id
        if not sid:
            return {"error": "No session_id found. Please create or run a workflow first."}

        # Headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Sessionid": sid
        }

        # Payload
        payload = {
            "flowname": flowname,
            "workflow_type": workflow_type,
            "flowDesc": flow_desc
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            # Optional: Update stored workflow_id if backend returns new session
            if "session_id" in data:
                self.workflow_id = data["session_id"]

            return data
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}


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


    def return_workflows(self, file_name: str) -> dict:
        """
        Fetch workflow data from a local JSON file on the backend.

        Parameters:
            file_name (str): The name of the JSON file to read (e.g., 'workflows.json').

        Returns:
            dict: Parsed JSON content or an error message.
        """
        url = f"{self.base_url}/return_workflows"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"file_name": file_name}

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if response.status_code == 200:
                return data
            else:
                return {"error": f"Failed with status {response.status_code}", "response": data}
        except Exception as e:
            return {"error": str(e)}

    def set_model(self, client: str, model_api_key: str, model_name: str, base_url: str, date: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Saves model details to the server.

        Args:
            client (str): The client name (e.g., "groq", "openai").
            model_api_key (str): The API key for the model's service.
            model_name (str): The specific name of the model.
            base_url (str): The base URL for the model's API endpoint.
            date (str): The date of setting the model, as a string.
            description (Optional[str], optional): An optional description for the model. Defaults to None.

        Returns:
            Dict[str, Any]: The JSON response from the server, indicating success or failure.
        """
        url = f"{self.base_url}/set_model"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "client": client,
            "api_key": model_api_key,
            "model_name": model_name,
            "base_url": base_url,
            "date": date,
            "description": description or ""
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return {"error": f"HTTP error occurred: {http_err}", "details": response.text}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}
    
    
    def reset_workflow(self, session_id: str):
        """
        Resets the workflow state on the server for a specific session.

        Args:
            session_id (str): The identifier for the user session whose
                              workflow should be reset.

        Returns:
            dict: The JSON response from the server.
        """
        # The endpoint URL
        url = f"{self.base_url}/reset"

        # Headers including standard auth and the custom Sessionid
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Sessionid": session_id
        }

        try:
            # Make the GET request
            response = requests.get(url, headers=headers)
            
            # Check for HTTP errors (e.g., 4xx or 5xx responses)
            response.raise_for_status()

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
            # Handle other network-related errors
            return {"error": "Request failed", "details": str(req_err)}
    
    
    
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
    def add_executor(self, session_id: str, executors: int) -> dict:
        """
        Calls the /add_executor endpoint to add executors to a session.

        Args:
            session_id: The ID of the session.
            executors: The number of executors to add.

        Returns:
            A dictionary containing the JSON response from the server.
        """
        url = f"{self.base_url}/add_executor"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "session_id": session_id,
            "executors": executors
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for bad status codes
            return response.json()
            
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            try:
                # Try to return the server's error message
                return response.json()
            except json.JSONDecodeError:
                return {"success": False, "message": str(http_err)}
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred: {req_err}")
            return {"success": False, "message": str(req_err)}
        except json.JSONDecodeError:
            print("Failed to decode JSON response")
            return {"success": False, "message": "Invalid JSON response from server."}

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
    def update_model(
            self,
            model_id: str,
            client: str,
            api_key: str,
            model_name: str,
            base_url: str,
            description: str = ""
        ) -> Dict:
            """
            Calls the POST /update_model endpoint to update an existing model.
            All request logic is self-contained in this method.
            """
            
            # 1. Construct the full URL
            url = f"{self.base_url}/update_model"
            
            # 2. Construct the headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 3. Construct the payload
            payload = {
                "id": model_id, # Crucial: pass the ID
                "client": client.lower(),
                "api_key": api_key,
                "model_name": model_name,
                "base_url": base_url,
                "description": description
            }
            
            # 4. Make the request and handle errors
            try:
                response = requests.post(url, json=payload, headers=headers)
                
                # Raise an exception for bad status codes (4xx, 5xx)
                response.raise_for_status()

                # Success: return the JSON response
                return response.json()

            except requests.exceptions.HTTPError as http_err:
                # Handle 4xx/5xx errors
                print(f"HTTP error occurred: {http_err} - {response.text}")
                try:
                    # Try to return the API's JSON error message
                    return response.json() 
                except json.JSONDecodeError:
                    # If the error response itself isn't JSON
                    return {"success": False, "error": str(http_err), "details": response.text}
            
            except requests.exceptions.RequestException as req_err:
                # Handle connection errors, timeouts, etc.
                print(f"An error occurred: {req_err}")
                return {"success": False, "error": str(req_err)}
            
            except json.JSONDecodeError:
                # If the *success* response wasn't valid JSON
                print("Failed to decode successful JSON response")
                return {"success": False, "error": "Invalid JSON response from server."}
    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """
        Delete a saved model for the authenticated user.

        Args:
            model_id (str): The ID of the model to delete.

        Returns:
            Dict[str, Any]: Response containing success message or error details.
        """
        if not model_id:
            return {"error": "model_id is required"}

        url = f"{self.base_url}/delete_model/{model_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.delete(url, headers=headers)
            data = response.json()

            if response.status_code == 200:
                return {"message": data.get("message")}
            else:
                return {"error": data.get("error", "Unknown error"), "status": response.status_code}

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
            
    def download_file(
            self, tool_id: str, save_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Downloads a file associated with a tool_id.

            Args:
                tool_id (str): The unique identifier for the tool/file.
                save_path (Optional[str]): The local file path to save the downloaded
                                        content. If None, the content is returned
                                        as a string.

            Returns:
                Dict[str, Any]: A dictionary containing success status and either
                                the file_path, the content, or an error message.
            """
            if not tool_id:
                return {"error": "Tool ID is required."}

            url = f"{self.base_url}/download_file"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"tool_id": tool_id}

            try:
                # stream=True is good practice for file downloads
                response = requests.get(url, headers=headers, params=params, stream=True)

                # Check for HTTP errors (4xx, 5xx)
                response.raise_for_status()

                # Check if the server returned a JSON error instead of a file
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return response.json()  # Server sent a JSON error (e.g., {"status": "error", ...})

                # Handle successful file download
                if "text/x-python" in content_type or "octet-stream" in content_type:
                    # Get content
                    content = response.text
                    
                    # Try to get filename from header
                    filename = "downloaded_file.py"
                    content_disposition = response.headers.get("Content-Disposition")
                    if content_disposition:
                        match = re.search(r'filename="?([^"]+)"?', content_disposition)
                        if match:
                            filename = match.group(1)

                    # Save to file if path is provided
                    if save_path:
                        try:
                            os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
                            with open(save_path, "w", encoding="utf-8") as f:
                                f.write(content)
                            return {
                                "status": "success",
                                "file_path": os.path.abspath(save_path),
                                "filename": filename
                            }
                        except IOError as e:
                            return {"status": "error", "message": f"Failed to save file: {str(e)}"}
                    
                    # Return content as string if no path
                    else:
                        return {
                            "status": "success",
                            "content": content,
                            "filename": filename
                        }
                
                # Fallback for unexpected content type
                return {"status": "error", "message": f"Unexpected content type: {content_type}"}

            except requests.exceptions.HTTPError as http_err:
                try:
                    # Try to parse the error response as JSON
                    return http_err.response.json()
                except requests.exceptions.JSONDecodeError:
                    return {"status": "error", "message": f"HTTP error: {http_err}", "status_code": http_err.response.status_code}
            
            except requests.exceptions.RequestException as req_err:
                return {"status": "error", "message": f"Request failed: {req_err}"}
            
            except Exception as e:
                return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
            

    def view_file(self, tool_id: str) -> Dict[str, Any]:
            """
            Fetches the file data/details associated with a tool_id from /view_file.

            Args:
                tool_id (str): The unique identifier for the tool/file.

            Returns:
                Dict[str, Any]: A dictionary containing file details (like content,
                                filename, status) or an error message.
            """
            if not tool_id:
                return {"error": "Tool ID is required."}

            url = f"{self.base_url}/view_file"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"tool_id": tool_id}

            try:
                response = requests.get(url, headers=headers, params=params)
                
                # Raise an exception for bad status codes (4xx, 5xx)
                response.raise_for_status()
                
                # The endpoint should always return a JSON response
                return response.json()

            except requests.exceptions.HTTPError as http_err:
                try:
                    # If the server sent a JSON error, parse and return it
                    return http_err.response.json()
                except requests.exceptions.JSONDecodeError:
                    # Fallback if the error response wasn't valid JSON
                    return {
                        "status": "error",
                        "message": f"HTTP error: {http_err}",
                        "status_code": http_err.response.status_code
                    }
            
            except requests.exceptions.RequestException as req_err:
                return {"status": "error", "message": f"Request failed: {req_err}"}
            
            except Exception as e:
                return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

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
    def file(self, file_path: str):
        url = f"{self.base_url}/file"
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            headers = {"Authorization": f"Bearer {self.api_key}"}  # minimal auth only
            response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    
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
    def get_all_prompt_data(self) -> Dict[str, Any]:
        """
        Fetch all saved prompts for the authenticated user.

        Returns:
            Dict[str, Any]: List of all prompt records or an error message.
        """
        url = f"{self.base_url}/show_all_prompt_data"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }
        except Exception as e:
            return {"error": "Failed to fetch prompt data", "details": str(e)}
    
    def run_prompt_test_copy(
        self,
        prompt: list,
        session_id: str,
        model_data: dict,
        selected_model: str,
        system_message: list = None,
        temperature: float = 0.7,
        top_p: int = 50,
        max_tokens: int = 1024,
        json_response: bool = False
    ) -> Dict[str, Any]:
        """
        Test prompts against selected LLM model.

        Args:
            prompt (list): List of user prompts.
            session_id (str): Active session ID.
            model_data (dict): Must contain id, client, base_url.
            selected_model (str): Model name to use.
            system_message (list, optional): Defaults to AI assistant role.
            temperature (float)
            top_p (int)
            max_tokens (int)
            json_response (bool)

        Returns:
            Dict[str, Any]: JSON response with answer or error.
        """

        url = f"{self.base_url}/prompt_testing_copy"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "session_id": session_id,
            "model": model_data,
            "selected_model": selected_model,
            "system_message": system_message or ["You are a Helpful AI Assistant"],
            "temperature": temperature,
            "top_p": top_p,
            "tokens": max_tokens,
            "json": json_response
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {"error": "HTTP error occurred", "details": str(http_err)}
        except Exception as e:
            return {"error": str(e)}

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
    def edit_with_ai(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a prompt to the backend for AI-powered enhancement.

        Args:
            prompt (str): The text prompt to be improved by AI.
            session_id (Optional[str]): Optional session identifier header.

        Returns:
            dict: Edited prompt or error information.
        """
        url = f"{self.base_url}/edit-with-ai"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Attach session header only if provided
        if session_id:
            headers["Sessionid"] = session_id

        body = {"prompt": prompt}

        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            return {
                "error": "HTTP error occurred",
                "details": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None
            }

        except requests.exceptions.RequestException as req_err:
            return {"error": "Request failed", "details": str(req_err)}

        except Exception as e:
            return {"error": "Unexpected failure", "details": str(e)}
    def get_user_metadata(self) -> Dict[str, Any]:
            """
            Fetches the metadata for the authenticated user.
            This is an authenticated GET endpoint.

            Returns:
                Dict[str, Any]: The API response, e.g., {"user_metadata": {...}}
            
            Raises:
                Exception: If the API call fails (e.g., 404 Not Found, 401 Unauthorized).
            """
            url = f"{self.base_url}/profile/user-metadata"
            try:
                headers= {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                return self._handle_response(response)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")