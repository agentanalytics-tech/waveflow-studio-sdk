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
    def set_model_from_file(self, file_path: str) -> Dict[str, Any]:
            """
            Uploads a JSON file to configure and save a new AI model definition.
            This is an authenticated POST endpoint.

            Args:
                file_path (str): The local path to the .json file containing the model details.
                                The JSON must contain: id, client, api_key, model_name,
                                base_url, description, and date.

            Returns:
                Dict[str, Any]: The API response containing the saved model details.

            Raises:
                FileNotFoundError: If the provided file_path does not exist.
                Exception: If the API call fails or returns an error.
            """
            import os
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file '{file_path}' was not found.")

            url = f"{self.base_url}/set_model_from_file"
            
            # We do NOT set 'Content-Type' header manually when sending files; 
            # the requests library handles the boundary generation automatically.
            headers = {"Authorization": f"Bearer {self.api_key}"}

            try:
                with open(file_path, 'rb') as f:
                    # 'file' matches the parameter name in FastAPI: file: UploadFile = File(...)
                    # We explicitly set the filename and mime type
                    files = {'file': (os.path.basename(file_path), f, 'application/json')}
                    
                    response = requests.post(url, headers=headers, files=files)
                    return self._handle_response(response)
                    
            except requests.exceptions.RequestException as e:
                raise Exception(f"Connection error: {e}")