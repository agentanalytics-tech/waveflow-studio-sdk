import requests
import json
from typing import Optional, Dict, Any
import uuid
import os
from typing import List

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