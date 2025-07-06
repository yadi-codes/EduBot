// Modern EduBot Frontend Script
class EduBotApp {
    constructor() {
        this.currentSessionId = localStorage.getItem('sessionId') || this.generateSessionId();
        this.isTyping = false;
        this.uploadedFiles = new Map();
        this.messageHistory = [];
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadTheme();
        this.initializeSession();
    }

    initializeElements() {
        // Core elements
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.chatMessages = document.getElementById('chat-messages');
        this.fileInput = document.getElementById('file-input');
        this.attachBtn = document.getElementById('attach-btn');
        this.uploadStatus = document.getElementById('upload-status');
        this.filePreview = document.getElementById('file-preview');
        this.themeToggle = document.getElementById('theme-toggle');
        this.characterCount = document.querySelector('.character-count');
        
        // Study tools
        this.quizBtn = document.getElementById('quiz-btn');
        this.flashcardsBtn = document.getElementById('flashcards-btn');
        this.sessionBtn = document.getElementById('session-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        
        // Session management
        this.sessionHistory = document.getElementById('session-history');
        this.sessionList = document.getElementById('session-list');
    }

    setupEventListeners() {
        // Message input
        this.messageInput.addEventListener('input', () => this.handleInputChange());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // File upload
        this.attachBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Theme toggle
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
        
        // Study tools
        this.quizBtn.addEventListener('click', () => this.generateQuiz());
        this.flashcardsBtn.addEventListener('click', () => this.generateFlashcards());
        this.sessionBtn.addEventListener('click', () => this.toggleSessionPanel());
        this.newChatBtn.addEventListener('click', () => this.createNewSession());
        
        // Suggestion chips
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('chip')) {
                this.handleSuggestionClick(e.target.textContent);
            }
        });
    }

    generateSessionId() {
        const id = 'session-' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('sessionId', id);
        return id;
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
        }
    }

    toggleTheme() {
        document.body.classList.toggle('light-theme');
        const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
        localStorage.setItem('theme', theme);
    }

    initializeSession() {
        this.loadSessionHistory();
        this.showWelcomeMessage();
    }

    showWelcomeMessage() {
        // Remove default welcome message and show dynamic one
        const welcomeMsg = document.querySelector('.welcome-message');
        if (welcomeMsg && this.messageHistory.length === 0) {
            // Keep welcome message for new sessions
            return;
        }
    }

    handleInputChange() {
        const length = this.messageInput.value.length;
        this.characterCount.textContent = `${length} / 4000`;
        
        // Auto-resize textarea
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        
        // Enable/disable send button
        this.sendBtn.disabled = length === 0 || this.isTyping;
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Add user message to UI
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        // this.handleInputChange();

        // Show typing indicator
        this.isTyping = true;
        const typingIndicator = this.showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.currentSessionId
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId
                })
            });

            const data = await response.json();

            // Remove typing indicator
            this.removeTypingIndicator(typingIndicator);
            this.isTyping = false;

            if (data.error) {
                this.addMessage('Sorry, I encountered an error. Please try again! 🤖', 'assistant');
            } else {
                this.addMessage(data.response, 'assistant', data.follow_ups);
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.removeTypingIndicator(typingIndicator);
            this.isTyping = false;
            this.addMessage('Connection error. Please check your internet and try again.', 'assistant');
        }
    }

    // addMessage(content, role, followUps = []) {
    //     const messageDiv = document.createElement('div');
    //     messageDiv.className = `message message-${role}`;
    //     messageDiv.setAttribute('data-message-id', Date.now());

    //     if (role === 'user') {
    //         messageDiv.innerHTML = `
    //             <div class="message-content">${this.escapeHtml(content)}</div>
    //             <div class="message-avatar">
    //                 <div class="avatar-gradient"></div>
    //                 <span>You</span>
    //             </div>
    //         `;
    //     } else {
    //         messageDiv.innerHTML = `
    //             <div class="message-avatar">
    //                 <div class="avatar-gradient"></div>
    //                 <span>✨</span>
    //             </div>
    //             <div class="message-content">
    //                 ${content}
    //                 ${followUps.length > 0 ? this.createFollowUps(followUps) : ''}
    //             </div>
    //         `;
    //     }

    //     // Remove welcome message if it exists
    //     const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
    //     if (welcomeMessage && this.messageHistory.length === 0) {
    //         welcomeMessage.remove();
    //     }

    //     this.chatMessages.appendChild(messageDiv);
    //     this.scrollToBottom();
        
    //     // Store in history
    //     this.messageHistory.push({ role, content, timestamp: new Date().toISOString() });
    // }
    
// Also update the addMessage function to ensure proper scrolling
    addMessage(content, role, followUps = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;
        messageDiv.setAttribute('data-message-id', Date.now());

        if (role === 'user') {
            messageDiv.innerHTML = `
                <div class="message-content">${this.escapeHtml(content)}</div>
                <div class="message-avatar">
                    <div class="avatar-gradient"></div>
                    <span>You</span>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-avatar">
                    <div class="avatar-gradient"></div>
                    <span>✨</span>
                </div>
                <div class="message-content">
                    ${content}
                    ${followUps.length > 0 ? this.createFollowUps(followUps) : ''}
                </div>
            `;
        }

        // Remove welcome message if it exists
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage && this.messageHistory.length === 0) {
            welcomeMessage.remove();
        }

        this.chatMessages.appendChild(messageDiv);
        
        // Force scroll after DOM update
        setTimeout(() => {
            this.scrollToBottom();
        }, 100);
        
        // Store in history
        this.messageHistory.push({ role, content, timestamp: new Date().toISOString() });
    }

    createFollowUps(followUps) {
        return `
            <div class="follow-ups">
                <div class="follow-up-title">You might ask:</div>
                ${followUps.map(q => `
                    <button class="follow-up-btn" onclick="eduBot.handleFollowUp('${this.escapeHtml(q)}')">
                        ${this.escapeHtml(q)}
                    </button>
                `).join('')}
            </div>
        `;
    }

    handleFollowUp(question) {
        this.messageInput.value = question;
        this.messageInput.focus();
        this.handleInputChange();
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message message-assistant typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-gradient"></div>
                <span>✨</span>
            </div>
            <div class="message-content">
                <div class="typing-dots">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
        return typingDiv;
    }

    removeTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }

    // Add this to your script.js file - replace the existing scrollToBottom function

    scrollToBottom() {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            });
        });
    }



// Also add this CSS to ensure proper scrolling behavior
    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        this.showFilePreview(files);
        this.uploadFiles(files);
    }

    showFilePreview(files) {
        this.filePreview.innerHTML = files.map(file => `
            <div class="file-preview-item" data-filename="${this.escapeHtml(file.name)}">
                <div class="file-info">
                    <div class="file-icon">📄</div>
                    <div class="file-details">
                        <div class="file-name">${this.escapeHtml(file.name)}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
                <div class="file-status">
                    <div class="upload-progress">
                        <div class="progress-bar"></div>
                    </div>
                    <span class="status-text">Uploading...</span>
                </div>
            </div>
        `).join('');
    }

    async uploadFiles(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('file', file));
        
        const subject = prompt('Enter subject/topic for these files:', 'General Studies') || 'General Studies';
        formData.append('subject', subject);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                headers: {
                    'X-Session-ID': this.currentSessionId
                },
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showUploadSuccess(data);
                this.addMessage(
                    `Great! I've processed ${data.processed_files.length} file(s). What would you like to know about them?`,
                    'assistant'
                );
            } else {
                this.showUploadError(data.error);
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showUploadError('Upload failed. Please try again.');
        } finally {
            // Clear file input and preview after a delay
            setTimeout(() => {
                this.fileInput.value = '';
                this.filePreview.innerHTML = '';
            }, 3000);
        }
    }

    showUploadSuccess(data) {
        this.uploadStatus.innerHTML = `
            <div class="upload-status success">
                ✅ Successfully processed ${data.processed_files.length} file(s)
            </div>
        `;
        this.hideUploadStatus();
    }

    showUploadError(error) {
        this.uploadStatus.innerHTML = `
            <div class="upload-status error">
                ❌ ${error}
            </div>
        `;
        this.hideUploadStatus();
    }

    hideUploadStatus() {
        setTimeout(() => {
            this.uploadStatus.innerHTML = '';
        }, 5000);
    }

    async generateQuiz() {
        const topic = prompt('Enter topic for quiz (leave blank for all topics):') || '';
        const difficulty = prompt('Enter difficulty (beginner/intermediate/advanced):', 'intermediate') || 'intermediate';
        
        this.showStatus('Generating quiz...', 'info');

        try {
            const response = await fetch('/generate_quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.currentSessionId
                },
                body: JSON.stringify({ topic, difficulty, num_questions: 5 })
            });

            const quiz = await response.json();

            if (quiz.error) {
                this.showStatus(quiz.error, 'error');
                return;
            }

            this.displayQuiz(quiz);

        } catch (error) {
            console.error('Quiz generation error:', error);
            this.showStatus('Failed to generate quiz', 'error');
        }
    }

    displayQuiz(quiz) {
        let quizHtml = `
            <div class="quiz-container">
                <h3>${quiz.quiz_title}</h3>
                <div class="quiz-meta">
                    <span>📊 ${quiz.total_questions} questions</span>
                    <span>⏱️ ${quiz.estimated_time}</span>
                    <span>📈 ${quiz.difficulty}</span>
                </div>
        `;

        quiz.questions.forEach((q, i) => {
            quizHtml += `
                <div class="quiz-question" data-question="${i}">
                    <div class="question-header">
                        <span class="question-number">Q${i + 1}</span>
                        <span class="question-difficulty">${q.difficulty || 'medium'}</span>
                    </div>
                    <p class="question-text">${q.question}</p>
                    <div class="quiz-options">
                        ${q.options.map((opt, j) => `
                            <button class="quiz-option" onclick="eduBot.checkAnswer(${i}, ${j}, ${q.correct_answer}, '${this.escapeHtml(q.explanation)}')">
                                <span class="option-letter">${String.fromCharCode(65 + j)}</span>
                                <span class="option-text">${opt}</span>
                            </button>
                        `).join('')}
                    </div>
                    <div class="quiz-explanation" id="explanation-${i}"></div>
                </div>
            `;
        });

        quizHtml += '</div>';
        this.addMessage(quizHtml, 'assistant');
    }

    checkAnswer(questionIndex, selectedIndex, correctIndex, explanation) {
        const questionDiv = document.querySelector(`[data-question="${questionIndex}"]`);
        const options = questionDiv.querySelectorAll('.quiz-option');
        const explanationDiv = document.getElementById(`explanation-${questionIndex}`);

        // Disable all options
        options.forEach(opt => opt.disabled = true);

        // Color code the options
        options.forEach((opt, i) => {
            if (i === correctIndex) {
                opt.classList.add('correct');
            } else if (i === selectedIndex) {
                opt.classList.add('incorrect');
            } else {
                opt.classList.add('neutral');
            }
        });

        // Show explanation
        const isCorrect = selectedIndex === correctIndex;
        explanationDiv.innerHTML = `
            <div class="explanation ${isCorrect ? 'correct' : 'incorrect'}">
                <div class="explanation-header">
                    ${isCorrect ? '✅ Correct!' : '❌ Incorrect'}
                </div>
                <div class="explanation-text">${explanation}</div>
            </div>
        `;
    }

    async generateFlashcards() {
        const topic = prompt('Enter topic for flashcards (leave blank for all topics):') || '';
        const numCards = parseInt(prompt('How many flashcards? (max 20):', '10')) || 10;
        
        this.showStatus('Generating flashcards...', 'info');

        try {
            const response = await fetch('/generate_flashcards', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.currentSessionId
                },
                body: JSON.stringify({ topic, num_cards: Math.min(numCards, 20) })
            });

            const data = await response.json();

            if (data.error) {
                this.showStatus(data.error, 'error');
                return;
            }

            this.displayFlashcards(data.flashcards);

        } catch (error) {
            console.error('Flashcard generation error:', error);
            this.showStatus('Failed to generate flashcards', 'error');
        }
    }

    displayFlashcards(flashcards) {
        let flashcardHtml = `
            <div class="flashcards-container">
                <h3>📚 Flashcards (${flashcards.length} cards)</h3>
                <div class="flashcards-grid">
        `;

        flashcards.forEach((card, i) => {
            flashcardHtml += `
                <div class="flashcard" onclick="eduBot.flipFlashcard(this)" data-card="${i}">
                    <div class="flashcard-inner">
                        <div class="flashcard-front">
                            <div class="card-header">
                                <span class="card-number">${i + 1}</span>
                                <span class="card-difficulty">${card.difficulty || 'medium'}</span>
                            </div>
                            <div class="card-content">
                                <div class="card-term">${card.term}</div>
                                <div class="card-hint">💡 ${card.hint}</div>
                            </div>
                        </div>
                        <div class="flashcard-back">
                            <div class="card-content">
                                <div class="card-definition">${card.definition}</div>
                                <div class="card-example">
                                    <strong>Example:</strong> ${card.example}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        flashcardHtml += `
                </div>
                <div class="flashcard-controls">
                    <button onclick="eduBot.shuffleFlashcards()">🔀 Shuffle</button>
                    <button onclick="eduBot.resetFlashcards()">🔄 Reset All</button>
                </div>
            </div>
        `;

        this.addMessage(flashcardHtml, 'assistant');
    }

    flipFlashcard(element) {
        element.classList.toggle('flipped');
    }

    shuffleFlashcards() {
        const container = document.querySelector('.flashcards-grid');
        const cards = Array.from(container.children);
        
        // Shuffle array
        for (let i = cards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [cards[i], cards[j]] = [cards[j], cards[i]];
        }
        
        // Re-append in new order
        cards.forEach(card => container.appendChild(card));
    }

    resetFlashcards() {
        document.querySelectorAll('.flashcard.flipped').forEach(card => {
            card.classList.remove('flipped');
        });
    }

    async loadSessionHistory() {
        try {
            const response = await fetch('/sessions');
            const data = await response.json();
            
            this.displaySessionHistory(data.sessions);
        } catch (error) {
            console.error('Failed to load session history:', error);
        }
    }

    displaySessionHistory(sessions) {
        if (!this.sessionList) return;

        this.sessionList.innerHTML = sessions.map(session => `
            <div class="session-item ${session.id === this.currentSessionId ? 'active' : ''}" 
                 onclick="eduBot.loadSession('${session.id}')">
                <div class="session-preview">${session.preview}</div>
                <div class="session-meta">
                    <span class="session-date">${new Date(session.last_activity).toLocaleDateString()}</span>
                    <div class="session-stats">
                        <span>💬 ${session.message_count}</span>
                        ${session.has_files ? '<span>📎</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    async loadSession(sessionId) {
        if (sessionId === this.currentSessionId) return;

        try {
            const response = await fetch(`/session/${sessionId}`);
            const data = await response.json();

            // Update current session
            this.currentSessionId = sessionId;
            localStorage.setItem('sessionId', sessionId);

            // Clear current chat
            this.chatMessages.innerHTML = '';
            this.messageHistory = [];

            // Load session messages
            const messages = data.session.message_history || [];
            messages.forEach(msg => {
                this.addMessage(msg.content, msg.role);
            });

            // Update session list
            this.loadSessionHistory();

            // Show success message
            this.showStatus('Session loaded successfully', 'success');

        } catch (error) {
            console.error('Failed to load session:', error);
            this.showStatus('Failed to load session', 'error');
        }
    }

    createNewSession() {
        this.currentSessionId = this.generateSessionId();
        this.chatMessages.innerHTML = '';
        this.messageHistory = [];
        
        // Show welcome message
        this.showWelcomeMessage();
        this.loadSessionHistory();
        
        this.showStatus('New session started', 'success');
    }

    toggleSessionPanel() {
        // This would toggle a session panel in a more complex UI
        // For now, just reload the session history
        this.loadSessionHistory();
    }

    handleSuggestionClick(text) {
        // Extract the actual suggestion text (remove emoji)
        const suggestion = text.replace(/^[📄❓🎯]\s*/, '');
        
        if (suggestion.includes('Upload')) {
            this.fileInput.click();
        } else if (suggestion.includes('quiz')) {
            this.generateQuiz();
        } else {
            this.messageInput.value = suggestion;
            this.messageInput.focus();
        }
    }

    showStatus(message, type) {
        this.uploadStatus.innerHTML = `
            <div class="upload-status ${type}">
                ${message}
            </div>
        `;
        
        setTimeout(() => {
            this.uploadStatus.innerHTML = '';
        }, 3000);
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.eduBot = new EduBotApp();
});

// Add some additional CSS for the new components
const additionalStyles = `
<style>
.follow-ups {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border-tertiary);
}

.follow-up-title {
    font-size: 12px;
    color: var(--text-tertiary);
    margin-bottom: 8px;
    font-weight: 500;
}

.follow-up-btn {
    display: block;
    width: 100%;
    padding: 8px 12px;
    margin: 4px 0;
    background: var(--surface-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
}

.follow-up-btn:hover {
    background: var(--surface-tertiary);
    border-color: var(--border-primary);
    color: var(--text-primary);
}

.typing-dots {
    display: flex;
    gap: 4px;
    align-items: center;
}

.quiz-container {
    max-width: 100%;
    margin: 16px 0;
}

.quiz-meta {
    display: flex;
    gap: 16px;
    margin: 12px 0;
    font-size: 12px;
    color: var(--text-tertiary);
}

.quiz-question {
    margin: 24px 0;
    padding: 20px;
    background: var(--surface-secondary);
    border-radius: 12px;
    border: 1px solid var(--border-secondary);
}

.question-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.question-number {
    background: var(--accent-primary);
    color: white;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}

.question-difficulty {
    font-size: 11px;
    color: var(--text-tertiary);
    text-transform: uppercase;
}

.quiz-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 16px 0;
}

.quiz-option {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--surface-tertiary);
    border: 1px solid var(--border-secondary);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
}

.quiz-option:hover:not(:disabled) {
    background: var(--surface-primary);
    border-color: var(--border-primary);
}

.quiz-option.correct {
    background: rgba(16, 185, 129, 0.1);
    border-color: var(--success);
    color: var(--success);
}

.quiz-option.incorrect {
    background: rgba(239, 68, 68, 0.1);
    border-color: var(--error);
    color: var(--error);
}

.quiz-option.neutral {
    opacity: 0.6;
}

.option-letter {
    width: 24px;
    height: 24px;
    background: var(--accent-primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
}

.flashcards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.flashcard {
    height: 200px;
    perspective: 1000px;
    cursor: pointer;
}

.flashcard-inner {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;
    transition: transform 0.6s;
    transform-style: preserve-3d;
}

.flashcard.flipped .flashcard-inner {
    transform: rotateY(180deg);
}

.flashcard-front, .flashcard-back {
    position: absolute;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    background: var(--surface-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
}

.flashcard-back {
    transform: rotateY(180deg);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.card-number {
    background: var(--accent-primary);
    color: white;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
}

.card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.card-term {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 12px;
}

.card-definition {
    font-size: 16px;
    color: var(--text-primary);
    margin-bottom: 12px;
    line-height: 1.4;
}

.card-hint, .card-example {
    font-size: 13px;
    color: var(--text-secondary);
    font-style: italic;
}

.flashcard-controls {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-top: 16px;
}

.flashcard-controls button {
    padding: 8px 16px;
    background: var(--surface-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 8px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.flashcard-controls button:hover {
    background: var(--surface-tertiary);
    border-color: var(--border-primary);
}

.file-preview-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--surface-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 10px;
    margin-bottom: 8px;
}

.file-info {
    display: flex;
    align-items: center;
    gap: 12px;
}

.file-icon {
    font-size: 20px;
}

.file-details {
    display: flex;
    flex-direction: column;
}

.file-name {
    font-weight: 500;
    color: var(--text-primary);
}

.file-size {
    font-size: 12px;
    color: var(--text-tertiary);
}

.upload-progress {
    width: 100px;
    height: 4px;
    background: var(--surface-tertiary);
    border-radius: 2px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: var(--accent-primary);
    width: 0%;
    animation: progressAnimation 2s ease-in-out infinite;
}

@keyframes progressAnimation {
    0% { width: 0%; }
    50% { width: 70%; }
    100% { width: 100%; }
}

.session-item {
    padding: 12px;
    margin: 4px 0;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.session-item:hover {
    background: var(--surface-secondary);
}

.session-item.active {
    background: var(--surface-tertiary);
    border: 1px solid var(--border-primary);
}

.session-preview {
    font-size: 14px;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.session-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.session-date {
    font-size: 12px;
    color: var(--text-tertiary);
}

.session-stats {
    display: flex;
    gap: 8px;
    font-size: 12px;
    color: var(--text-tertiary);
}

@media (max-width: 768px) {
    .flashcards-grid {
        grid-template-columns: 1fr;
    }
    
    .quiz-meta {
        flex-direction: column;
        gap: 8px;
    }
    
    .quiz-option {
        padding: 10px 12px;
    }
    
    .option-letter {
        width: 20px;
        height: 20px;
        font-size: 11px;
    }
}
</style>
`;

// Inject additional styles
document.head.insertAdjacentHTML('beforeend', additionalStyles);