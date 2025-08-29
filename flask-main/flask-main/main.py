from flask import Flask, render_template, request, jsonify
import time, os

app = Flask(__name__)

messages = []
MAX_AGE = 1200  #time before msg is deleted

def cleanup():
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
    return jsonify([m["text"] for m in messages])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # port for railway
    app.run(host="0.0.0.0", port=port)
