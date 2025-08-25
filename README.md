# WaveFlow Studio SDK

A Python SDK for interacting with the WaveFlow Studio API, providing easy-to-use methods for creating workflows and chatting with AI agents.

## Features

- **Easy Authentication**: Simple API key-based authentication
- **Workflow Management**: Create and manage workflows from JSON configurations
- **Interactive Chat**: Chat with your workflows using natural language
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Type Hints**: Full type hint support for better development experience

## Installation

install from source:

```bash
git clone https://github.com/agentanalytics-tech/waveflow-studio-sdk.git
cd waveflow_studio_sdk
python setup.py install
pip install .
```

## Quick Start

Here's a simple example to get you started:

```python
from waveflow_studio_sdk import WaveFlowStudio

# Initialize the client
client = WaveFlowStudio(
    api_key="your-api-key-here",
    base_url="http://your-server-url:8000" # optional
)

# Create a workflow from JSON file
result = client.create_workflow("path/to/your/workflow.json")
print("Workflow created:", result)

# Chat with the workflow
response = client.chat("Hello, how can you help me?")
print("Response:", response.get("answer"))

# Chat with additional context
response = client.chat(
    query="What's the weather like?",
    context="User is located in New York"
)
print("Response:", response.get("answer"))
```

## API Reference

### WaveFlowStudio Class

#### Constructor

```python
WaveFlowStudio(api_key: str)
```

- **api_key** (str): Your API key for authentication
- **base_url** (str, optional): The base URL of the WaveFlow Studio server

#### Methods

##### create_workflow(json_file_path: str) → Dict[str, Any]

Creates a new workflow by uploading a JSON configuration file.

**Parameters:**
- **json_file_path** (str): Path to the JSON workflow configuration file

**Returns:**
- Dict containing the workflow creation response, including `workflow_id`

**Example:**
```python
result = client.create_workflow("workflow.json")
if "workflow_id" in result:
    print(f"Workflow created with ID: {result['workflow_id']}")
else:
    print(f"Error: {result.get('error')}")
```

##### chat(query: str, context: Optional[str] = None) → Dict[str, Any]

Sends a chat message to the workflow.

**Parameters:**
- **query** (str): The message/question to send
- **context** (str, optional): Additional context for the query

**Returns:**
- Dict containing `answer` and `conversation` fields

**Example:**
```python
response = client.chat("Explain machine learning")
print(response.get("answer"))
```

## Error Handling

The SDK includes custom exceptions for better error handling:

```python
from waveflow_studio import WaveFlowStudio

try:
    client = WaveFlowStudio(api_key="invalid-key")
except Exception as e:
    print(f"Other error: {e}")
```

### Exception Types

- **InvalidAPIKeyError**: Raised when the API key is invalid or not associated with any user

## Workflow JSON Format

Your workflow JSON file should follow the WaveFlow Studio specification. Here's a basic example structure:

```json
You have to download this from https://studio.agentanalytics.ai/
```

## Examples

Check out the `examples/` directory for more comprehensive usage examples:

- `basic_usage.py`: Simple workflow creation and chat example
- `workflow.json`: Sample workflow configuration

## Development

### Setting up development environment

```bash
# Clone the repository
git clone https://github.com/agentanalytics-tech/waveflow-studio-sdk.git
cd waveflow_studio_sdk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .


Made with ❤️ for the AgentAnalytics.AI family