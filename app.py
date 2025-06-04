from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
import json
from werkzeug.utils import secure_filename
import PyPDF2
import re
from dotenv import load_dotenv

load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

# Configure Gemini API (Replace 'YOUR_API_KEY' with the actual API key)
# genai.configure(api_key="")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory store
processed_notes = {}

def format_gemini_response(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    lines = text.split('\n')
    formatted_lines, in_list = [], False
    for line in lines:
        if line.strip().startswith(('- ', '* ')):
            if not in_list:
                formatted_lines.append('<ul>')
                in_list = True
            formatted_lines.append(f'<li>{line.strip()[2:]}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append(line)
    if in_list:
        formatted_lines.append('</ul>')
    return '\n'.join(formatted_lines)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"PDF error: {e}")
    return text

def generate_structured_notes(content, subject=""):
    prompt = f"""
Summarize this educational content into structured notes in JSON:
Subject: {subject}
Content: {content[:3000]}

Return:
{{
    "title": "...",
    "summary": "...",
    "key_points": ["..."],
    "important_concepts": ["..."],
    "study_tips": ["..."]
}}
"""
    try:
        response = model.generate_content(prompt)
        try:
            return json.loads(response.text)
        except:
            return {"summary": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        subject = request.form.get('subject', 'General')

        content = ""
        if filename.endswith('.pdf'):
            content = extract_text_from_pdf(file)
        elif filename.endswith('.txt'):
            content = file.read().decode('utf-8')
        elif filename.endswith('.json'):
            content = str(json.loads(file.read().decode('utf-8')))

        if content:
            notes = generate_structured_notes(content, subject)
            file_key = f"{subject}_{filename.replace('.', '_')}"
            processed_notes[file_key] = {
                "filename": filename,
                "subject": subject,
                "content": content,
                "structured_notes": notes
            }
            return jsonify({"message": f"{filename} processed!", "structured_notes": notes})

    return jsonify({"error": "Invalid file type"}), 400

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()

    print(user_message)

    if not user_message:
        return jsonify({"response": "Please enter a message to start chatting."})

    # Build context from uploaded notes
    context_summary = ""
    if processed_notes:
        for note in processed_notes.values():
            context_summary += f"Subject: {note['subject']}\n"
            summary = note.get('structured_notes', {}).get('summary', '')
            context_summary += f"Summary: {summary[:300]}...\n\n"

    # Debugging prints
    print(f"User message: {user_message}")
    print(f"Context summary: {context_summary}")

    # Proper Prompting to Gemini
    prompt = f"""
You are EduBot, a friendly educational assistant.

Your job is to:
- Answer student questions clearly and concisely.
- Refer to uploaded content when relevant.
- Use **bold** for key ideas and ## for sections.
- Be friendly and helpful.

Context from uploaded study notes:
{context_summary if context_summary else "No notes uploaded yet."}

User question:
{user_message}
"""

    try:
        response = model.generate_content(prompt)
        formatted_response = format_gemini_response(response.text)
        print(f"Raw response: {response.text}")
        return jsonify({"response": formatted_response})

    except Exception as e:
        fallback_responses = {
            "hi": "Hello! Ask me anything about your studies 😊",
            "hello": "Hey! What would you like to learn today?",
            "motivation": "Keep going! You're smarter than you think and stronger than you feel! 💪"
        }
        for key in fallback_responses:
            if key in user_message.lower():
                return jsonify({"response": fallback_responses[key]})
        return jsonify({"response": f"Something went wrong. Please try again. Error: {str(e)}"})

@app.route("/notes")
def get_notes():
    return jsonify(processed_notes)

if __name__ == "__main__":
    app.run(debug=True)
