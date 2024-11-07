import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json

app = Flask(__name__)
CORS(app)

# Configure the API key
api_key = os.getenv("GENAI_API_KEY")

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

try:
    with open('./conversation_history/all_user_history.json') as ch:
        all_user_conversation_history = json.load(ch)
except:
    all_user_conversation_history = {}

def get_conversation_history(user_id):
    if user_id in all_user_conversation_history:
        return all_user_conversation_history[user_id]
    else:
        all_user_conversation_history[user_id] = []
        return []

def update_conversation_history(user_id, history_to_append):
    if user_id not in all_user_conversation_history:
        print('wrong user id')
    else:
        all_user_conversation_history[user_id] += history_to_append
        with open('./conversation_history/all_user_history.json', 'w') as ch:
            json.dump(all_user_conversation_history, ch)

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

def prompt_engineer_message(message, history):
    final_message = ''
    system_prompt = '''
    You are a Health related chatbot. This is a user's chat conversation so far : \n
    ===============================================================
    \n
    '''
    user_prompt = f'''
    \n
    ===============================================================
    Here is the message: \n{message}\n
    Give the response - 
    '''

    history = "\n\n\n".join([str(i) for i in history[:6]])
    final_message = system_prompt + history + user_prompt
    return final_message

def get_gemini_response(user_id, message):
    """
    Send a message to Gemini and return the response.

    Args:
        message (str): the message to send to Gemini

    Returns:
        str: the plain text response from Gemini, formatted for display in the chat window
    """
    try:
        conversation_history = get_conversation_history(user_id)
        formatted_history = format_history_for_api(conversation_history)
        # print("\n\nmessage:\n", message)
        chat_session = model.start_chat(history=formatted_history)
        # print('\n\n\nchat session initialized\n')
        modified_message = prompt_engineer_message(message, formatted_history)
        print('\n\nmodified message after prompt engineering:\n', modified_message)
        response = chat_session.send_message(modified_message)
        # print('\n\n\nResponse received', response)
        
        history_to_append = [{"role": "user", "content": message}, {"role": "model", "content": response.text}]
        update_conversation_history(user_id, history_to_append)
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
    user_id = request.json.get("user_id")
    bot_message = get_gemini_response(user_id, user_message)
    
    return jsonify({"content": bot_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
