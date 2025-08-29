from flask import Flask, render_template, request, jsonify
import time, os, re

app = Flask(__name__)
messages = []
nicknames = {}  # Store nicknames with their creation time
MAX_AGE = 300  # 5 minutes

# Advanced text normalization for filtering
def normalize(text):
    # Convert to lowercase and handle common character substitutions
    text = text.lower()
    
    # Replace common number/symbol substitutions
    substitutions = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't',
        '@': 'a', '

def cleanup():
    """Remove messages and nicknames older than MAX_AGE seconds"""
    now = time.time()
    global messages, nicknames
    messages = [m for m in messages if now - m["time"] < MAX_AGE]
    # Clean up old nicknames
    nicknames = {k: v for k, v in nicknames.items() if now - v["time"] < MAX_AGE}

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/messages")
def get_messages():
    cleanup()
    # return messages with nicknames
    return jsonify([{"text": m["text"], "nickname": m["nickname"], "userId": m["userId"]} for m in messages])

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json()
    text = data.get("text", "").strip()
    user_id = data.get("userId", "").strip()
    nickname = data.get("nickname", "").strip()
    
    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    if not user_id or not nickname:
        return jsonify({"error": "User ID and nickname are required"}), 400
    
    if len(nickname) > 25:
        return jsonify({"error": "Nickname must be 25 characters or less"}), 400
    
    if contains_banned_content(text) or contains_banned_content(nickname):
        return jsonify({"error": "Message or nickname contains banned words"}), 400
    
    cleanup()
    
    # Store/update nickname with timestamp
    nicknames[user_id] = {"nickname": nickname, "time": time.time()}
    
    messages.append({
        "text": text, 
        "nickname": nickname,
        "userId": user_id,
        "time": time.time()
    })
    return jsonify({"success": True})

@app.route("/set_nickname", methods=["POST"])
def set_nickname():
    data = request.get_json()
    user_id = data.get("userId", "").strip()
    nickname = data.get("nickname", "").strip()
    
    if not user_id or not nickname:
        return jsonify({"error": "User ID and nickname are required"}), 400
    
    if len(nickname) > 25:
        return jsonify({"error": "Nickname must be 25 characters or less"}), 400
    
    if contains_banned_content(nickname):
        return jsonify({"error": "Nickname contains banned words"}), 400
    
    cleanup()
    
    # Store nickname with timestamp
    nicknames[user_id] = {"nickname": nickname, "time": time.time()}
    
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT env variable
    app.run(host="0.0.0.0", port=port, debug=True): 's', '!': 'i', '+': 't', '|': 'l'
    }
    
    for char, replacement in substitutions.items():
        text = text.replace(char, replacement)
    
    # Remove all non-alphabetic characters and extra spaces
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', '', text)  # Remove all spaces
    
    return text

# Basic banned words list - you should expand this appropriately
banned_words = ["bomb", "shoot", "kill", "hate", "terrorist", "violence"]

# Pattern-based detection for better filtering
def contains_banned_content(text):
    norm = normalize(text)
    
    # Check against banned words
    for bad in banned_words:
        if bad in norm:
            return True
    
    # Check for repeated characters (common evasion technique)
    # e.g., "boooomb" -> "bomb"
    compressed = re.sub(r'(.)\1{2,}', r'\1', norm)
    for bad in banned_words:
        if bad in compressed:
            return True
    
    # Check for character spacing (another evasion technique)
    # This is handled by our normalization removing spaces
    
    return False

def cleanup():
    """Remove messages and nicknames older than MAX_AGE seconds"""
    now = time.time()
    global messages, nicknames
    messages = [m for m in messages if now - m["time"] < MAX_AGE]
    # Clean up old nicknames
    nicknames = {k: v for k, v in nicknames.items() if now - v["time"] < MAX_AGE}

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/messages")
def get_messages():
    cleanup()
    # return messages with nicknames
    return jsonify([{"text": m["text"], "nickname": m["nickname"], "userId": m["userId"]} for m in messages])

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json()
    text = data.get("text", "").strip()
    user_id = data.get("userId", "").strip()
    nickname = data.get("nickname", "").strip()
    
    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    if not user_id or not nickname:
        return jsonify({"error": "User ID and nickname are required"}), 400
    
    if len(nickname) > 25:
        return jsonify({"error": "Nickname must be 25 characters or less"}), 400
    
    if contains_banned_word(text) or contains_banned_word(nickname):
        return jsonify({"error": "Message or nickname contains banned words"}), 400
    
    cleanup()
    
    # Store/update nickname with timestamp
    nicknames[user_id] = {"nickname": nickname, "time": time.time()}
    
    messages.append({
        "text": text, 
        "nickname": nickname,
        "userId": user_id,
        "time": time.time()
    })
    return jsonify({"success": True})

@app.route("/set_nickname", methods=["POST"])
def set_nickname():
    data = request.get_json()
    user_id = data.get("userId", "").strip()
    nickname = data.get("nickname", "").strip()
    
    if not user_id or not nickname:
        return jsonify({"error": "User ID and nickname are required"}), 400
    
    if len(nickname) > 25:
        return jsonify({"error": "Nickname must be 25 characters or less"}), 400
    
    if contains_banned_word(nickname):
        return jsonify({"error": "Nickname contains banned words"}), 400
    
    cleanup()
    
    # Store nickname with timestamp
    nicknames[user_id] = {"nickname": nickname, "time": time.time()}
    
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT env variable
    app.run(host="0.0.0.0", port=port, debug=True)
