#!/usr/bin/env python3
"""Simple UI for Aster & Row Support Agent."""

import json
import sys
import uuid
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.orchestrator import handle_message
from dotenv import load_dotenv

load_dotenv()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aster & Row Support</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px; display: flex; justify-content: center; height: 100vh; box-sizing: border-box; }
        .chat-container { width: 100%; max-width: 600px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column; overflow: hidden; }
        .header { background: #111827; color: white; padding: 16px; text-align: center; font-weight: bold; font-size: 1.2em; }
        .messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .message { padding: 12px 16px; border-radius: 8px; max-width: 80%; line-height: 1.5; white-space: pre-wrap; }
        .user-message { background: #3b82f6; color: white; align-self: flex-end; border-bottom-right-radius: 0; }
        .agent-message { background: #f3f4f6; color: #1f2937; align-self: flex-start; border-bottom-left-radius: 0; }
        .handoff-message { background: #fee2e2; color: #991b1b; align-self: center; font-size: 0.9em; max-width: 90%; border: 1px solid #f87171; }
        .input-area { padding: 16px; background: #fff; border-top: 1px solid #e5e7eb; display: flex; gap: 8px; }
        input[type="text"] { flex: 1; padding: 12px; border: 1px solid #d1d5db; border-radius: 6px; outline: none; font-size: 1em; }
        button { padding: 12px 24px; background: #111827; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:hover { background: #374151; }
        button:disabled { background: #9ca3af; cursor: not-allowed; }
        .loading-indicator { animation: pulse 1.5s infinite; color: #6b7280; font-style: italic; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>

<div class="chat-container">
    <div class="header">Aster & Row Support</div>
    <div class="messages" id="messages">
        <div class="message agent-message">Hi there! How can I help you today?</div>
    </div>
    <div class="input-area">
        <input type="text" id="userInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
        <button id="sendBtn" onclick="sendMessage()">Send</button>
    </div>
</div>

<script>
    const sessionId = crypto.randomUUID();

    function addMessage(text, className) {
        const msgs = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = `message ${className}`;
        
        if (className === 'agent-message') {
            div.innerHTML = marked.parse(text);
        } else {
            div.textContent = text;
        }
        
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
        return div;
    }

    async function sendMessage() {
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');
        const text = input.value.trim();
        
        if (!text) return;
        
        input.value = '';
        input.disabled = true;
        btn.disabled = true;
        
        addMessage(text, 'user-message');
        const loadingDiv = addMessage('...', 'agent-message loading-indicator');
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message: text })
            });
            
            const data = await response.json();
            loadingDiv.remove();
            
            addMessage(data.answer, 'agent-message');
            
            if (data.handoff) {
                addMessage(`System: Human handoff triggered (Reason: ${data.handoff_reason})`, 'handoff-message');
            }
        } catch (e) {
            addMessage('Error communicating with server.', 'handoff-message');
        } finally {
            input.disabled = false;
            btn.disabled = false;
            input.focus();
        }
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    }
</script>

</body>
</html>
"""

class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body)
                session_id = data.get('session_id', str(uuid.uuid4()))
                message = data.get('message', '')
                
                resp = handle_message(session_id, message)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                result = {
                    "answer": resp.answer,
                    "handoff": resp.handoff,
                    "handoff_reason": resp.handoff_reason
                }
                self.wfile.write(json.dumps(result).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"Error: {e}")
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ChatHandler)
    print(f"UI Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped.")

if __name__ == '__main__':
    run_server()
