from flask import Flask, request, jsonify, render_template, send_from_directory
import google.generativeai as genai
import os
import json
from werkzeug.utils import secure_filename
import PyPDF2
import re
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
from datetime import datetime
import uuid
from dotenv import load_dotenv
from flask_cors import CORS
from flask import Flask, make_response

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for modern frontend
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[Config.RATE_LIMIT]
)

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Enhanced in-memory store with session management
sessions = {}
processed_notes = {}

# Create upload folder if not exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'json', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def format_gemini_response(text):
    """Enhanced formatting for modern UI"""
    # Convert markdown to HTML
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Handle code blocks
    text = re.sub(r'```(.*?)```', r'<code>\1</code>', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Handle lists
    lines = text.split('\n')
    formatted_lines, in_list = [], False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('- ', '* ', '• ')):
            if not in_list:
                formatted_lines.append('<ul class="message-list">')
                in_list = True
            formatted_lines.append(f'<li>{stripped[2:]}</li>')
        elif stripped.startswith(tuple(f'{i}. ' for i in range(1, 10))):
            if not in_list:
                formatted_lines.append('<ol class="message-list">')
                in_list = True
            formatted_lines.append(f'<li>{stripped[3:]}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>' if '- ' in text or '* ' in text else '</ol>')
                in_list = False
            if stripped:
                formatted_lines.append(f'<p>{line}</p>')
            else:
                formatted_lines.append('<br>')
    
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

def extract_file_content(filepath):
    """Extract text from various file types"""
    try:
        if filepath.endswith('.pdf'):
            with open(filepath, 'rb') as f:
                return extract_text_from_pdf(f)
        elif filepath.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        elif filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return str(json.load(f))
        elif filepath.endswith(('.doc', '.docx')):
            return "Document content extraction not yet implemented for this format."
    except Exception as e:
        print(f"Error extracting content: {e}")
        return ""
    return ""

def generate_structured_notes(content, subject=""):
    """Generate structured notes with enhanced prompt"""
    prompt = f"""
Analyze this educational content and create comprehensive structured notes in JSON format.

Subject: {subject}
Content: {content[:15000]}

Required JSON structure:
{{
    "title": "Concise, descriptive title",
    "summary": "Comprehensive 2-3 paragraph summary",
    "key_points": ["Important point 1", "Important point 2", "..."],
    "important_concepts": ["Concept 1", "Concept 2", "..."],
    "study_tips": ["Study tip 1", "Study tip 2", "..."],
    "potential_questions": ["Question 1", "Question 2", "..."],
    "difficulty_level": "Beginner/Intermediate/Advanced",
    "estimated_study_time": "X minutes"
}}

Focus on:
- Key formulas and equations (if applicable)
- Important dates and events (if applicable)
- Core theories and principles
- Vocabulary and definitions
- Practical applications
"""
    try:
        response = model.generate_content(prompt)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"summary": response.text, "title": f"Notes: {subject}"}
    except Exception as e:
        return {"error": str(e), "title": f"Processing Error: {subject}"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)

@app.route("/upload", methods=["POST"])
@limiter.limit("20 per minute")
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "status": "error"}), 400
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({"error": "No files selected", "status": "error"}), 400
    
    session_id = request.headers.get('X-Session-ID', str(uuid.uuid4()))
    subject = request.form.get('subject', 'General Studies')
    
    print(f"Upload - Session ID: {session_id}")  # Debug logging
    
    # Initialize session if not exists
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "message_history": [],
            "files": [],
            "preferences": {}
        }
    
    processed_files = []
    failed_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
                file.save(filepath)
                
                content = extract_file_content(filepath)
                if content:
                    notes = generate_structured_notes(content, subject)
                    file_key = f"{session_id}_{filename.replace('.', '_')}"
                    
                    processed_notes[file_key] = {
                        "id": file_key,
                        "filename": filename,
                        "subject": subject,
                        "content": content[:10000],
                        "structured_notes": notes,
                        "session_id": session_id,
                        "processed_at": datetime.now().isoformat(),
                        "file_size": len(content),
                        "file_type": filename.split('.')[-1].upper()
                    }
                    
                    sessions[session_id]["files"].append(file_key)
                    processed_files.append({
                        "filename": filename,
                        "status": "success",
                        "notes_preview": notes.get("summary", "")[:200] + "..."
                    })
                    print(f"Processed file: {file_key} for session: {session_id}")
                else:
                    failed_files.append({"filename": filename, "error": "Could not extract content"})
                    
            except Exception as e:
                print(f"File processing error: {e}")
                failed_files.append({"filename": file.filename, "error": str(e)})
        else:
            failed_files.append({"filename": file.filename, "error": "Invalid file type"})
    
    if processed_files:
        return jsonify({
            "message": f"Successfully processed {len(processed_files)} file(s)",
            "status": "success",
            "processed_files": processed_files,
            "failed_files": failed_files,
            "session_id": session_id
        })
    else:
        return jsonify({
            "error": "No files could be processed",
            "status": "error",
            "failed_files": failed_files
        }), 400

@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id") or request.headers.get('X-Session-ID', str(uuid.uuid4()))
        
        print(f"Chat - Session ID: {session_id}, Message: {user_message[:50]}...")  # Debug logging
        
        # Initialize session if not exists
        if session_id not in sessions:
            sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "message_history": [],
                "files": [],
                "preferences": {}
            }
        
        if not user_message:
            return jsonify({
                "response": "Please enter a message to start our conversation! 😊",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            })
        
        # Build enhanced context
        context = build_enhanced_context(session_id, user_message)
        
        prompt = f"""
You are EduBot, an advanced AI study assistant. You're helpful, encouraging, and educational.

Session Context:
{context['session_summary']}

Recent Conversation:
{context['recent_history']}

Available Study Materials:
{context['notes_summary']}

Current Question: {user_message}

Instructions:
1. Provide clear, educational responses
2. Use **bold** for key terms and concepts
3. Include relevant examples when helpful
4. Be encouraging and supportive
5. Suggest 2-3 thoughtful follow-up questions
6. Format lists and code properly
7. Keep responses conversational but informative

Response format:
{{
    "response": "Your detailed response here...",
    "follow_ups": ["Follow-up question 1?", "Follow-up question 2?", "Follow-up question 3?"],
    "confidence": 0.95,
    "topics": ["topic1", "topic2"]
}}
"""
        
        response = model.generate_content(prompt)
        response_data = parse_enhanced_response(response.text)
        
        # Create message objects
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        }
        
        bot_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": response_data["response"],
            "timestamp": datetime.now().isoformat(),
            "follow_ups": response_data.get("follow_ups", []),
            "confidence": response_data.get("confidence", 0.9),
            "topics": response_data.get("topics", [])
        }
        
        # Update session history
        sessions[session_id]["message_history"].extend([user_msg, bot_msg])
        
        # Keep only last 50 messages to prevent memory issues
        if len(sessions[session_id]["message_history"]) > 50:
            sessions[session_id]["message_history"] = sessions[session_id]["message_history"][-50:]
        
        return jsonify({
            "response": format_gemini_response(response_data["response"]),
            "follow_ups": response_data.get("follow_ups", []),
            "message_id": bot_msg["id"],
            "timestamp": bot_msg["timestamp"],
            "confidence": response_data.get("confidence", 0.9),
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            "response": "I apologize, but I encountered an issue processing your request. Please try again! 🤖",
            "error": True,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }), 500

def build_enhanced_context(session_id, current_message):
    """Build comprehensive context for better responses"""
    session = sessions.get(session_id, {})
    
    # Recent conversation history (last 10 messages)
    recent_history = ""
    history = session.get("message_history", [])[-10:]
    for msg in history:
        role = "You" if msg["role"] == "user" else "EduBot"
        recent_history += f"{role}: {msg['content'][:200]}...\n"
    
    # Session summary
    session_summary = f"""
Session started: {session.get('created_at', 'Unknown')}
Messages exchanged: {len(session.get('message_history', []))}
Files uploaded: {len(session.get('files', []))}
"""
    
    # Notes summary from uploaded files
    notes_summary = ""
    session_files = session.get("files", [])
    for file_key in session_files:
        if file_key in processed_notes:
            note = processed_notes[file_key]
            notes_summary += f"""
File: {note['filename']} ({note['subject']})
Summary: {note.get('structured_notes', {}).get('summary', 'No summary available')[:300]}...
Key Points: {', '.join(note.get('structured_notes', {}).get('key_points', [])[:3])}
---
"""
    
    return {
        "session_summary": session_summary,
        "recent_history": recent_history or "No previous conversation",
        "notes_summary": notes_summary or "No study materials uploaded yet"
    }

def parse_enhanced_response(text):
    """Parse Gemini response with better error handling"""
    try:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to extract JSON from the text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        # Fallback: create structured response from plain text
        return {
            "response": text,
            "follow_ups": generate_fallback_followups(text),
            "confidence": 0.8,
            "topics": []
        }
    except Exception as e:
        print(f"Response parsing error: {e}")
        return {
            "response": text,
            "follow_ups": ["Can you tell me more about this topic?", "What would you like to explore next?"],
            "confidence": 0.7,
            "topics": []
        }

def generate_fallback_followups(text):
    """Generate follow-up questions when JSON parsing fails"""
    fallbacks = [
        "Would you like me to explain this in more detail?",
        "Do you have any questions about this topic?",
        "What aspect would you like to explore further?"
    ]
    return fallbacks

@app.route("/generate_quiz", methods=["POST"])
@limiter.limit("10 per hour")
def generate_quiz():
    try:
        session_id = request.headers.get('X-Session-ID')
        data = request.get_json() or {}
        topic = data.get('topic', '')
        difficulty = data.get('difficulty', 'intermediate')
        num_questions = min(data.get('num_questions', 5), 10)
        
        print(f"Quiz generation - Session ID: {session_id}")
        print(f"Available sessions: {list(sessions.keys())}")
        print(f"Available processed notes: {list(processed_notes.keys())}")
        
        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid session. Please refresh and try again."}), 400
        
        # Get relevant notes for this session
        session_files = sessions[session_id].get("files", [])
        relevant_notes = []
        
        for file_key in session_files:
            if file_key in processed_notes:
                note = processed_notes[file_key]
                if not topic or topic.lower() in note["subject"].lower():
                    relevant_notes.append(note)
        
        # If no notes found in session files, search by session_id in processed_notes
        if not relevant_notes:
            print("No notes found in session files, searching by session_id...")
            for file_key, note in processed_notes.items():
                if note.get("session_id") == session_id:
                    if not topic or topic.lower() in note["subject"].lower():
                        relevant_notes.append(note)
                        print(f"Found note by session_id: {file_key}")
        
        if not relevant_notes:
            return jsonify({
                "error": "No study materials found. Please upload some files first!",
                "debug": {
                    "session_id": session_id,
                    "session_files": session_files,
                    "available_notes": list(processed_notes.keys())
                }
            }), 400
        
        # Create comprehensive context for quiz generation
        context = ""
        for note in relevant_notes:
            context += f"Subject: {note['subject']}\n"
            context += f"Content: {note['content'][:2000]}...\n"
            if 'structured_notes' in note:
                sn = note['structured_notes']
                context += f"Key Points: {', '.join(sn.get('key_points', []))}\n"
                context += f"Concepts: {', '.join(sn.get('important_concepts', []))}\n\n"
        
        prompt = f"""Generate a {difficulty} level quiz with {num_questions} questions based on this study material:

{context}

Topic focus: {topic or 'All topics covered'}

Requirements:
1. Create {num_questions} multiple choice questions
2. Each question should have 4 options (A, B, C, D)
3. Include detailed explanations for correct answers
4. Vary question types (factual, conceptual, application)
5. Make questions challenging but fair

Format as JSON:
{{
    "quiz_title": "Quiz: {topic or 'Study Materials'}",
    "difficulty": "{difficulty}",
    "total_questions": {num_questions},
    "estimated_time": "5 minutes",
    "questions": [
        {{
            "id": 1,
            "question": "Question text here?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Detailed explanation of why this is correct...",
            "topic": "Specific topic",
            "difficulty": "easy"
        }}
    ]
}}"""
        
        response = model.generate_content(prompt)
        
        # Enhanced JSON parsing with multiple methods
        quiz_data = None
        
        # Method 1: Extract from code blocks
        json_match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
        if json_match:
            try:
                quiz_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Method 2: Extract JSON object from text
        if not quiz_data:
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                try:
                    quiz_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        # Method 3: Use existing parser
        if not quiz_data:
            quiz_data = parse_enhanced_response(response.text)
        
        # Ensure proper structure
        if not quiz_data or "questions" not in quiz_data:
            raise ValueError("Invalid quiz format")
        
        # Add metadata
        quiz_data["generated_at"] = datetime.now().isoformat()
        quiz_data["session_id"] = session_id
        
        return jsonify(quiz_data)
        
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return jsonify({
            "error": "Failed to generate quiz. Please try again with different parameters.",
            "details": str(e)
        }), 500

@app.route("/generate_flashcards", methods=["POST"])
@limiter.limit("10 per hour")
def generate_flashcards():
    try:
        session_id = request.headers.get('X-Session-ID')
        data = request.get_json() or {}
        topic = data.get("topic", "")
        num_cards = min(data.get("num_cards", 10), 20)
        
        print(f"Flashcard generation - Session ID: {session_id}")
        print(f"Available sessions: {list(sessions.keys())}")
        print(f"Available processed notes: {list(processed_notes.keys())}")
        
        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid session"}), 400
        
        # Get relevant notes
        session_files = sessions[session_id].get("files", [])
        relevant_notes = []
        
        for file_key in session_files:
            if file_key in processed_notes:
                note = processed_notes[file_key]
                if not topic or topic.lower() in note["subject"].lower():
                    relevant_notes.append(note)
        
        # If no notes found in session files, search by session_id in processed_notes
        if not relevant_notes:
            print("No notes found in session files, searching by session_id...")
            for file_key, note in processed_notes.items():
                if note.get("session_id") == session_id:
                    if not topic or topic.lower() in note["subject"].lower():
                        relevant_notes.append(note)
                        print(f"Found note by session_id: {file_key}")
        
        if not relevant_notes:
            return jsonify({
                "error": "No study materials found for flashcard generation",
                "debug": {
                    "session_id": session_id,
                    "session_files": session_files,
                    "available_notes": list(processed_notes.keys())
                }
            }), 400
        
        # Build context
        context = ""
        for note in relevant_notes:
            context += f"Subject: {note['subject']}\n"
            context += f"Content: {note['content'][:3000]}...\n\n"
        
        prompt = f"""Create {num_cards} educational flashcards based on this material:

{context}

Topic focus: {topic or 'All available topics'}

Requirements:
1. Create {num_cards} flashcards
2. Include term, definition, example, and study hint
3. Cover key concepts, vocabulary, and important facts
4. Make them useful for active recall
5. Vary difficulty levels

Format as JSON array:
[
    {{
        "id": 1,
        "term": "Key term or concept",
        "definition": "Clear, concise definition",
        "example": "Practical example or application",
        "hint": "Memory aid or study tip",
        "category": "Subject category",
        "difficulty": "easy"
    }}
]"""
        
        response = model.generate_content(prompt)
        
        # Enhanced JSON parsing for arrays
        flashcards = None
        
        # Method 1: Extract from code blocks
        json_match = re.search(r'```json\n(\[.*?\])\n```', response.text, re.DOTALL)
        if json_match:
            try:
                flashcards = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Method 2: Extract JSON array from text
        if not flashcards:
            json_match = re.search(r'\[.*?\]', response.text, re.DOTALL)
            if json_match:
                try:
                    flashcards = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if not flashcards:
            raise ValueError("Could not parse flashcards")
        
        # Validate and fix flashcard structure
        if not isinstance(flashcards, list):
            raise ValueError("Flashcards must be an array")
        
        # Add metadata to each card
        for i, card in enumerate(flashcards):
            card["generated_at"] = datetime.now().isoformat()
            card["session_id"] = session_id
            if "id" not in card:
                card["id"] = i + 1
            # Ensure all required fields exist
            for field, default in [
                ("term", f"Term {i + 1}"),
                ("definition", "Definition not provided"),
                ("example", "Example not provided"),
                ("hint", "Study this concept carefully"),
                ("category", "General"),
                ("difficulty", "medium")
            ]:
                if field not in card:
                    card[field] = default
        
        return jsonify({
            "flashcards": flashcards,
            "total_cards": len(flashcards),
            "topic": topic or "Mixed Topics",
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Flashcard generation error: {e}")
        return jsonify({
            "error": "Failed to generate flashcards. Please try again.",
            "details": str(e)
        }), 500

@app.route("/sessions", methods=["GET"])
def list_sessions():
    """Get all sessions with enhanced metadata"""
    session_list = []
    
    for sid, session in sessions.items():
        messages = session.get("message_history", [])
        files = session.get("files", [])
        
        last_activity = session.get("created_at")                                                   
        if messages:
            last_activity = messages[-1].get("timestamp", last_activity)
        
        preview = "New session"
        for msg in reversed(messages):
            if msg.get("role") == "user":
                preview = msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
                break
        
        session_list.append({
            "id": sid,
            "created_at": session["created_at"],
            "last_activity": last_activity,
            "message_count": len(messages),
            "file_count": len(files),
            "preview": preview,
            "has_files": len(files) > 0
        })
    
    session_list.sort(key=lambda x: x["last_activity"], reverse=True)
    
    return jsonify({
        "sessions": session_list,
        "total_sessions": len(session_list)
    })

@app.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get detailed session information"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = sessions[session_id]
    
    session_files = []
    for file_key in session.get("files", []):
        if file_key in processed_notes:
            note = processed_notes[file_key]
            session_files.append({
                "id": file_key,
                "filename": note["filename"],
                "subject": note["subject"],
                "processed_at": note["processed_at"],
                "file_type": note.get("file_type", "Unknown"),
                "summary": note.get("structured_notes", {}).get("summary", "")[:200] + "..."
            })
    
    return jsonify({
        "session": {
            **session,
            "files_detail": session_files
        }
    })

@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session and its associated data"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session_files = sessions[session_id].get("files", [])
    for file_key in session_files:
        if file_key in processed_notes:
            del processed_notes[file_key]
    
    del sessions[session_id]
    
    return jsonify({"message": "Session deleted successfully"})

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
        "processed_files": len(processed_notes)
    })


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

app = Flask(__name__)  # or something like that
