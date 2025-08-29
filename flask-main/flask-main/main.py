from flask import Flask, render_template, request, jsonify
import time, os, re

app = Flask(__name__)
messages = []
nicknames = {}
MAX_AGE = 300  # 5 minutes

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    substitutions = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't',
        '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'l'
    }
    for char, replacement in substitutions.items():
        text = text.replace(char, replacement)
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', '', text)
    return text

banned_words = [
    # Violence/Weapons
    "bomb", "shoot", "kill", "murder", "terrorist", "violence", "gun", "knife", "weapon", "attack", "assault",
    
    # Hate Speech & Slurs
    "hate", "nazi", "hitler", "racist", "sexist", "homophobe", "bigot", "retard", "fag", "faggot",
    
    # Sexual/Adult Content
    "porn", "sex", "nude", "naked", "horny", "sexy", "dick", "penis", "vagina", "boobs", "ass",
    
    # Drugs
    "cocaine", "heroin", "meth", "drugs", "weed", "marijuana", "crack", "ecstasy", "lsd",
    
    # Spam/Scam
    "spam", "scam", "hack", "cheat", "exploit", "bot", "fake", "phishing",
    
    # General Toxicity
    "nigger", "nga", "n g a", "niggar", "nigga", "nigge", "nigglet"
    
    # Common Profanity
    "fuck", "hell", "328947yusdftdf", "bastard", "crap", "piss", "45dfgszerwtsgdf", "slut"
]

def contains_banned_content(text):
    if not text:
        return False
    norm = normalize(text)
    for bad in banned_words:
        if bad in norm:
            return True
    compressed = re.sub(r'(.)\1{2,}', r'\1', norm)
    for bad in banned_words:
        if bad in compressed:
            return True
    return False

def cleanup():
    now = time.time()
    global messages, nicknames
    messages = [m for m in messages if now - m["time"] < MAX_AGE]
    nicknames = {k: v for k, v in nicknames.items() if now - v["time"] < MAX_AGE}

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/messages")
def get_messages():
    cleanup()
    return jsonify([{"text": m["text"], "nickname": m["nickname"], "userId": m["userId"]} for m in messages])

@app.route("/set_nickname", methods=["POST"])
def set_nickname():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_id = data.get("userId", "").strip()
        nickname = data.get("nickname", "").strip()
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
        if not nickname:
            return jsonify({"error": "Nickname is required"}), 400
        if len(nickname) > 25:
            return jsonify({"error": "Nickname must be 25 characters or less"}), 400
        if contains_banned_content(nickname):
            return jsonify({"error": "Nickname contains inappropriate content"}), 400
        
        cleanup()
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in set_nickname: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/send", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        text = data.get("text", "").strip()
        user_id = data.get("userId", "").strip()
        nickname = data.get("nickname", "").strip()
        
        if not text:
            return jsonify({"error": "Message cannot be empty"}), 400
        if not user_id or not nickname:
            return jsonify({"error": "User ID and nickname are required"}), 400
        if contains_banned_content(text) or contains_banned_content(nickname):
            return jsonify({"error": "Message contains inappropriate content"}), 400
        
        cleanup()
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        messages.append({
            "text": text, 
            "nickname": nickname,
            "userId": user_id,
            "time": time.time()
        })
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)














banned_words = [
    # Violence/Weapons
    "bomb", "shoot", "kill", "murder", "terrorist", "violence", "gun", "knife", "weapon", "attack", "assault",
    
    # Hate Speech & Slurs
    "hate", "nazi", "hitler", "racist", "sexist", "homophobe", "bigot", "retard", "fag", "faggot",
    
    # Sexual/Adult Content
    "porn", "sex", "nude", "naked", "horny", "sexy", "dick", "penis", "vagina", "boobs", "ass",
    
    # Drugs
    "cocaine", "heroin", "meth", "drugs", "weed", "marijuana", "crack", "ecstasy", "lsd",
    
    # Spam/Scam
    "spam", "scam", "hack", "cheat", "exploit", "bot", "fake", "phishing",
    
    # General Toxicity
    "nigger", "nga", "n g a", "niggar", "nigga", "nigge", "nigglet"
    
    # Common Profanity
    "fuck", "hell", "328947yusdftdf", "bastard", "crap", "piss", "45dfgszerwtsgdf", "slut"
]
