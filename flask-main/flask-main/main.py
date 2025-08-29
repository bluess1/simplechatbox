from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)

# store messages as { "text": ..., "time": ... }
messages = []
MAX_AGE = 10  # 5 minutes in seconds

def cleanup():
    """Remove messages older than MAX_AGE seconds"""
    now = time.time()
    global messages
    messages = [m for m in messages if now - m["time"] < MAX_AGE]

@app.route('/')
def index():
    return render_template("chat.html")

@app.route('/send')
def send():
    msg = request.args.get("msg", "")
    if msg:
        cleanup()
        messages.append({"text": msg, "time": time.time()})
    return ("", 204)

@app.route('/messages')
def get_messages():
    cleanup()
    # return just the text values
    return jsonify([m["text"] for m in messages])
