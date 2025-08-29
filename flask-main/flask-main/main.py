from flask import Flask, render_template, request, jsonify
import time, os, re

app = Flask(__name__)
messages = []
MAX_AGE = 300  # 5 minutes

# Normalize text for filtering (remove symbols, numbers used as letters)
def normalize(text):
    return re.sub(r'[^a-z]', '', text.lower())

banned_words = ["nigger", "nigga", "nga", "bomb", "shoot"]

def contains_banned_word(text):
    norm = normalize(text)
    for bad in banned_words:
        if bad in norm:
            return True
    return False

def cleanup():
    """Remove messages older than MAX_AGE seconds"""
    now = time.time()
    global messages
    messages = [m for m in messages if now - m["time"] < MAX_AGE]

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/messages")
def get_messages():
    cleanup()
    # return just the text values
    return jsonify([{"text": m["text"]} for m in messages])

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json()
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    if contains_banned_word(text):
        return jsonify({"error": "Message contains banned words"}), 400
    
    cleanup()
    messages.append({"text": text, "time": time.time()})
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT env variable
    app.run(host="0.0.0.0", port=port, debug=True)
