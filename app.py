import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# Configure the API key
api_key = "AIzaSyCgI2y4ZWQ3cmKnUm5ZBLkCFqWne-ZJep0"
genai.configure(api_key=api_key)

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Load health-related keywords from a text file
def load_health_keywords(file_path):
    with open(file_path, 'r') as file:
        keywords = file.read().splitlines()
    return keywords

HEALTH_KEYWORDS = load_health_keywords('health_keywords.txt')

# Keep track of the conversation history
conversation_history = []

def is_health_related(message):
    message = message.lower()
    return any(keyword in message for keyword in HEALTH_KEYWORDS)

def format_history_for_api(history):
    # Properly format the conversation history for the API
    formatted_history = []
    for entry in history:
        formatted_entry = {
            "role": entry['role'],
            "parts": [
                {
                    "text": entry['content']
                }
            ]
        }
        formatted_history.append(formatted_entry)
    return formatted_history

def format_response_text(response_text):
    # Format the text to include proper HTML for line breaks and paragraphs
    formatted_text = response_text.replace('\n', '<br>')
    return formatted_text

def get_gemini_response(message):
    """
    Send a message to Gemini and return the response.

    Args:
        message (str): the message to send to Gemini

    Returns:
        str: the plain text response from Gemini, formatted for display in the chat window
    """
    try:
        formatted_history = format_history_for_api(conversation_history)
        chat_session = model.start_chat(history=formatted_history)
        response = chat_session.send_message(message)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "model", "content": response.text})

        plain_text_response = re.sub(r'\*\*(.*?)\*\*', r'\1', response.text, flags=re.DOTALL)
        
        # Format the response for better display
        return plain_text_response
    except Exception as e:
        print(f"API Request failed: {e}")
        return "Sorry, I'm having trouble connecting to the service."

@app.route('/api', methods=['POST'])
def api():
    print(request.json)
    user_message = request.json.get("message")
    
    bot_message = get_gemini_response(user_message)
    
    return jsonify({"content": bot_message})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
