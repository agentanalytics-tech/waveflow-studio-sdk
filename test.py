from waveflow_studio_sdk.client import WaveFlowStudio
import json

# from waveflow_studio_sdk import WaveFlowStudio

# Initialize the client
client = WaveFlowStudio(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:5000" # optional
)

# Create a workflow from JSON file
# result = client.create_workflow(r"C:\Users\Agent\Downloads\workflow.json")
# print("Workflow created:", result)

# Chat with the workflow
# response = client.chat("Hello, how can you help me?")
# print("Response:", response.get("answer"))

# # Chat with additional context
# response = client.chat(
#     query="What's the weather like?",
#     context="User is located in New York"
# )
# print("Response:", response.get("answer"))

#1st
# prompt_text = "I want to write a story about AI that helps humans."
# enhance_result = client.enhance_prompt(prompt_text)

# print("Enhance Prompt Result:", enhance_result)

# result = client.create_agent(session_id="your session id")

# print(json.dumps(result, indent=2))


# models = client.get_together_models()
# print("Together Models:", models)