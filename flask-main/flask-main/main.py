from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

messages = []

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

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/messages")
def get_messages():
    return jsonify(messages)

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json()
    text = data.get("text", "").strip()
    if contains_banned_word(text):
        return jsonify({"error": "Message contains banned words"}), 400
    messages.append({"text": text})
    return jsonify({"success": True})
