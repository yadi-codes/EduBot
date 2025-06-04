### 📚 EduBot – AI-Powered Study Assistant

EduBot is a Flask-based educational chatbot that helps students by converting uploaded PDFs, TXT, or JSON files into structured notes and answering study-related questions using Google's Gemini API.

---

### 🔧 Features

* 📂 Upload educational materials (PDF, TXT, JSON)
* 📘 Auto-generates structured study notes with:

  * Title
  * Summary
  * Key Points
  * Important Concepts
  * Study Tips
* 💬 Chat with an AI assistant trained on your uploaded content
* 🧠 Uses Gemini 1.5 Flash model by Google
* 📄 REST API endpoints for easy frontend integration

---

### 🛠 Tech Stack

* Python + Flask
* Google Generative AI (Gemini API)
* HTML (for frontend template)
* dotenv for secure API key handling
* PyPDF2 for PDF parsing

---

### 🚀 Getting Started

#### 1. Clone the repository

```bash
git clone https://github.com/yadi-codes/EduBot.git
cd EduBot
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Set up your environment variables

Create a `.env` file in the root directory:

```
GEMINI_API_KEY=your_api_key_here
```

#### 4. Run the Flask server

```bash
python app.py
```

EduBot will be available at `http://127.0.0.1:5000/`

---

### 🧪 API Endpoints

| Endpoint  | Method | Description                           |
| --------- | ------ | ------------------------------------- |
| `/`       | GET    | Home page                             |
| `/upload` | POST   | Upload a file and receive notes       |
| `/chat`   | POST   | Ask questions based on uploaded notes |
| `/notes`  | GET    | Retrieve all structured notes so far  |

---

### 📂 File Upload Format

Allowed file types:

* `.pdf`
* `.txt`
* `.json`

Each file must be sent with a `subject` form field.

---

### 📄 Example Upload (via Postman or frontend)

**POST** `/upload`

Form-data:

* `file`: yourfile.pdf
* `subject`: Physics

**Response:**

```json
{
  "message": "yourfile.pdf processed!",
  "structured_notes": {
    "title": "...",
    "summary": "...",
    "key_points": [...],
    "important_concepts": [...],
    "study_tips": [...]
  }
}
```

---

### 💡 Future Ideas

* Add database storage for users and notes
* JWT-based authentication
* Deploy on Render or Railway
* Frontend UI improvements

---

### 👌 Contributions

Pull requests and suggestions are welcome! Fork this repo and help make EduBot smarter.

---

### 📜 License

This project is licensed under the MIT License.

