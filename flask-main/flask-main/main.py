from flask import Flask, render_template, request, jsonify, send_from_directory
import time, os, re, random, string, base64
from datetime import datetime, timedelta
import json
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Data structures
channels = {
    "main": {
        "id": "main",
        "name": "Main Chat",
        "type": "public",
        "code": None,
        "messages": [],
        "created_at": time.time(),
        "last_activity": time.time(),
        "message_lifetime": 86400,  # 24 hours default
        "creator": "system",
        "members": set(),
        "is_system": True
    }
}
nicknames = {}
notification_settings = {}

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
    "bomb", "shooter", "kill", "nigger", "fck", "violence", "gun", "knife", "weapon", "niggar", "nigglet",
    "345fdgfdg", "nazi", "hitler", "345fdgfdg", "sexist", "nga", "n g a", "345fdgfdg", "345fdgfdg", "nigge",
    "porn", "sex", "nude", "naked", "horny", "sexy", "dick", "penis", "vagina", "boobs", "345fdgfdg",
    "345fdgfdg", "heroin", "345fdgfdg", "345fdgfdg", "345fdgfdg", "marijuana", "crack", "ecstasy", "lsd",
    "fuck", "shit", "bitch", "whore", "slut"
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_channel_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def is_nickname_unique(nickname):
    nickname_lower = nickname.lower()
    for user_data in nicknames.values():
        if user_data["nickname"].lower() == nickname_lower:
            return False
    return True

def create_dm_channel(user1_id, user2_id):
    sorted_users = sorted([user1_id, user2_id])
    channel_id = f"dm_{sorted_users[0]}_{sorted_users[1]}"
    
    user1_nickname = nicknames.get(user1_id, {}).get("nickname", "Unknown")
    user2_nickname = nicknames.get(user2_id, {}).get("nickname", "Unknown")
    
    if channel_id not in channels:
        channels[channel_id] = {
            "id": channel_id,
            "name": f"💬 {user1_nickname} & {user2_nickname}",
            "type": "dm",
            "code": None,
            "messages": [],
            "created_at": time.time(),
            "last_activity": time.time(),
            "message_lifetime": 86400,
            "creator": user1_id,
            "members": {user1_id, user2_id},
            "is_system": False,
            "is_dm": True,
            "dm_users": {user1_id, user2_id}
        }
        save_data()
    
    return channel_id

def get_user_by_nickname(nickname):
    nickname_lower = nickname.lower()
    for user_id, user_data in nicknames.items():
        if user_data["nickname"].lower() == nickname_lower:
            return user_id
    return None

def cleanup_messages():
    now = time.time()
    global channels, nicknames
    
    # Clean up old nicknames (5 minutes)
    nicknames = {k: v for k, v in nicknames.items() if now - v["time"] < 300}
    
    # Clean up messages in each channel
    channels_to_remove = []
    for channel_id, channel in channels.items():
        # Remove old messages and their associated files
        old_messages = [m for m in channel["messages"] if now - m["time"] >= channel["message_lifetime"]]
        
        # Delete associated media files
        for message in old_messages:
            if message.get("type") == "image" and message.get("file_path"):
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], message["file_path"])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {message.get('file_path')}: {e}")
        
        channel["messages"] = [m for m in channel["messages"] if now - m["time"] < channel["message_lifetime"]]
        
        # Remove inactive user-created channels after 12 hours
        if not channel.get("is_system", False) and not channel.get("is_dm", False):
            if now - channel["last_activity"] > 43200:  # 12 hours
                channels_to_remove.append(channel_id)
                print(f"Auto-deleting inactive channel: {channel['name']} (ID: {channel_id})")
    
    # Remove inactive channels
    for channel_id in channels_to_remove:
        del channels[channel_id]

def save_data():
    data_to_save = {
        "channels": {},
        "nicknames": {}
    }
    
    for channel_id, channel in channels.items():
        channel_copy = channel.copy()
        channel_copy["members"] = list(channel["members"])
        if "dm_users" in channel_copy:
            channel_copy["dm_users"] = list(channel_copy["dm_users"])
        data_to_save["channels"][channel_id] = channel_copy
    
    data_to_save["nicknames"] = nicknames
    
    try:
        with open("chat_data.json", "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    global channels, nicknames
    try:
        with open("chat_data.json", "r") as f:
            data = json.load(f)
            
        for channel_id, channel in data["channels"].items():
            channel["members"] = set(channel["members"])
            if "dm_users" in channel:
                channel["dm_users"] = set(channel["dm_users"])
            channels[channel_id] = channel
            
        nicknames = data["nicknames"]
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error loading data: {e}")

# --- NOTIFICATION SETTINGS API ENDPOINTS ---
@app.route("/notification_settings", methods=["GET"])
def get_notification_settings():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    user_settings = notification_settings.get(user_id, {})
    return jsonify(user_settings)

@app.route("/notification_settings", methods=["POST"])
def set_notification_settings():
    data = request.get_json()
    user_id = data.get("userId")
    channel_id = data.get("channelId")
    enabled = data.get("enabled")
    if not user_id or not channel_id or enabled is None:
        return jsonify({"error": "Missing params"}), 400
    if user_id not in notification_settings:
        notification_settings[user_id] = {}
    notification_settings[user_id][channel_id] = bool(enabled)
    save_data()
    return jsonify({"success": True})

# --- FILE SERVING ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- MAIN ROUTES ---
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/set_nickname", methods=["POST"])
def set_nickname():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_id = data.get("userId", "").strip()
        nickname = data.get("nickname", "").strip()
        
        if not user_id or not nickname:
            return jsonify({"error": "User ID and nickname are required"}), 400
        if len(nickname) > 25:
            return jsonify({"error": "Nickname must be 25 characters or less"}), 400
        if contains_banned_content(nickname):
            return jsonify({"error": "Nickname contains inappropriate content"}), 400
        
        cleanup_messages()
        
        if not is_nickname_unique(nickname):
            return jsonify({"error": "Nickname already taken"}), 400
        
        if user_id not in nicknames:
            nicknames[user_id] = {
                "nickname": nickname,
                "created_at": time.time(),
                "last_seen": time.time(),
                "time": time.time()
            }
        else:
            nicknames[user_id]["nickname"] = nickname
            nicknames[user_id]["last_seen"] = time.time()
            nicknames[user_id]["time"] = time.time()
        
        save_data()
        
        return jsonify({"success": True, "nickname": nickname, "userId": user_id})
        
    except Exception as e:
        print(f"Error in set_nickname: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")
    if user_id in nicknames:
        return jsonify({"success": True, "user": nicknames[user_id]})
    return jsonify({"success": False, "user": None})

# --- IMAGE UPLOAD ENDPOINT ---
@app.route("/upload_image", methods=["POST"])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        user_id = request.form.get('userId', '').strip()
        nickname = request.form.get('nickname', '').strip()
        channel_id = request.form.get('channelId', 'main').strip()
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not user_id or not nickname:
            return jsonify({"error": "User ID and nickname are required"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Only PNG, JPG, JPEG, GIF, and WEBP files are supported."}), 400
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        channel = channels[channel_id]
        
        # Check permissions same as text messages
        if channel.get("is_dm", False):
            if user_id not in channel["dm_users"]:
                return jsonify({"error": "You are not part of this direct message"}), 403
        elif channel["type"] == "private" and user_id not in channel["members"]:
            return jsonify({"error": "You are not a member of this private channel"}), 403
        
        # Generate unique filename
        timestamp = str(int(time.time()))
        filename = secure_filename(f"{user_id}_{timestamp}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(file_path)
        
        # Determine if it's a GIF
        is_gif = filename.lower().endswith('.gif')
        
        # Update nickname and channel activity
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        channel["last_activity"] = time.time()
        
        # Add message to channel
        message = {
            "text": "",  # No text for image messages
            "nickname": nickname,
            "userId": user_id,
            "time": time.time(),
            "type": "image",
            "file_path": filename,
            "file_url": f"/uploads/{filename}",
            "is_gif": is_gif
        }
        
        channel["messages"].append(message)
        save_data()
        
        return jsonify({"success": True, "message": message})
        
    except Exception as e:
        print(f"Error in upload_image: {str(e)}")
        return jsonify({"error": "Server error"}), 500

# --- EXISTING ENDPOINTS (Updated to handle media messages) ---
@app.route("/channels")
def get_channels():
    cleanup_messages()
    channel_list = []
    
    for channel_id, channel in channels.items():
        if not channel.get("is_dm", False):
            channel_list.append({
                "id": channel_id,
                "name": channel["name"],
                "type": channel["type"],
                "code": channel.get("code"),
                "message_count": len(channel["messages"]),
                "last_activity": channel["last_activity"],
                "is_system": channel.get("is_system", False)
            })
    
    return jsonify(channel_list)

@app.route("/get_dm_channels", methods=["GET"])
def get_dm_channels():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    
    cleanup_messages()
    
    dm_channels = []
    for channel_id, channel in channels.items():
        if channel.get("is_dm", False) and user_id in channel["dm_users"]:
            other_user_id = next(uid for uid in channel["dm_users"] if uid != user_id)
            other_nickname = nicknames.get(other_user_id, {}).get("nickname", "Unknown")
            
            dm_channels.append({
                "id": channel_id,
                "name": f"💬 {other_nickname}",
                "type": "dm",
                "message_count": len(channel["messages"]),
                "last_activity": channel["last_activity"],
                "other_user": other_nickname,
                "other_user_id": other_user_id
            })
    
    return jsonify({"dm_channels": dm_channels})

@app.route("/create_dm", methods=["POST"])
def create_dm():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_id = data.get("userId", "").strip()
        target_nickname = data.get("targetNickname", "").strip()
        
        if not user_id or not target_nickname:
            return jsonify({"error": "User ID and target nickname are required"}), 400
        
        cleanup_messages()
        
        target_user_id = get_user_by_nickname(target_nickname)
        if not target_user_id:
            return jsonify({"error": "User not found"}), 404
        
        if target_user_id == user_id:
            return jsonify({"error": "You cannot create a DM with yourself"}), 400
        
        channel_id = create_dm_channel(user_id, target_user_id)
        
        return jsonify({
            "success": True,
            "channel": {
                "id": channel_id,
                "name": channels[channel_id]["name"],
                "type": "dm"
            }
        })
        
    except Exception as e:
        print(f"Error in create_dm: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/create_channel", methods=["POST"])
def create_channel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        name = data.get("name", "").strip()
        channel_type = data.get("type", "public")
        message_lifetime = int(data.get("messageLifetime", 300))
        user_id = data.get("userId", "").strip()
        custom_code = data.get("customCode", "").strip()
        
        if not name or not user_id:
            return jsonify({"error": "Channel name and user ID are required"}), 400
        if len(name) > 50:
            return jsonify({"error": "Channel name must be 50 characters or less"}), 400
        if contains_banned_content(name):
            return jsonify({"error": "Channel name contains inappropriate content"}), 400
        if message_lifetime < 60 or message_lifetime > 86400:
            return jsonify({"error": "Message lifetime must be between 1 minute and 24 hours"}), 400
        
        if channel_type == "private":
            if not custom_code or len(custom_code) != 6:
                return jsonify({"error": "Private channels require a 6-character code"}), 400
            if not custom_code.isalnum():
                return jsonify({"error": "Channel code must contain only letters and numbers"}), 400
        
        cleanup_messages()
        
        channel_id = name.lower().replace(" ", "-") + "-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        if channel_type == "private":
            code = custom_code.upper() if custom_code else generate_channel_code()
        else:
            code = None
        
        channels[channel_id] = {
            "id": channel_id,
            "name": name,
            "type": channel_type,
            "code": code,
            "messages": [],
            "created_at": time.time(),
            "last_activity": time.time(),
            "message_lifetime": message_lifetime,
            "creator": user_id,
            "members": {user_id},
            "is_system": False
        }
        
        save_data()
        
        return jsonify({
            "success": True,
            "channel": {
                "id": channel_id,
                "name": name,
                "type": channel_type,
                "code": code
            }
        })
        
    except Exception as e:
        print(f"Error in create_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/join_channel", methods=["POST"])
def join_channel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        channel_id = data.get("channelId", "").strip()
        code = data.get("code", "").strip()
        user_id = data.get("userId", "").strip()
        
        if not channel_id:
            return jsonify({"error": "Channel ID is required"}), 400
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        channel = channels[channel_id]
        
        if channel.get("is_dm", False):
            if user_id not in channel["dm_users"]:
                return jsonify({"error": "You are not part of this direct message"}), 403
        elif channel["type"] == "private":
            if user_id in channel["members"]:
                pass
            else:
                if not code:
                    return jsonify({"error": "Private channel requires a code to join"}), 403
                if channel["code"] != code.upper():
                    return jsonify({"error": "Invalid channel code"}), 403
                channel["members"].add(user_id)
        
        channel["last_activity"] = time.time()
        save_data()
        
        return jsonify({
            "success": True,
            "channel": {
                "id": channel_id,
                "name": channel["name"],
                "type": channel["type"],
                "messageLifetime": channel["message_lifetime"]
            }
        })
        
    except Exception as e:
        print(f"Error in join_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/messages/<channel_id>")
def get_messages(channel_id):
    cleanup_messages()
    
    if channel_id not in channels:
        return jsonify({"error": "Channel not found"}), 404
    
    channel = channels[channel_id]
    messages = []
    
    for m in channel["messages"]:
        message = {
            "text": m["text"], 
            "nickname": m["nickname"], 
            "userId": m["userId"],
            "timestamp": m["time"],
            "type": m.get("type", "text")
        }
        
        # Add media-specific fields
        if message["type"] == "image":
            message["file_url"] = m.get("file_url", "")
            message["is_gif"] = m.get("is_gif", False)
        
        messages.append(message)
    
    return jsonify(messages)

@app.route("/send", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        text = data.get("text", "").strip()
        user_id = data.get("userId", "").strip()
        nickname = data.get("nickname", "").strip()
        channel_id = data.get("channelId", "main").strip()
        
        if not text:
            return jsonify({"error": "Message cannot be empty"}), 400
        if not user_id or not nickname:
            return jsonify({"error": "User ID and nickname are required"}), 400
        if contains_banned_content(text):
            return jsonify({"error": "Message contains inappropriate content"}), 400
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        channel = channels[channel_id]
        
        if channel.get("is_dm", False):
            if user_id not in channel["dm_users"]:
                return jsonify({"error": "You are not part of this direct message"}), 403
        elif channel["type"] == "private" and user_id not in channel["members"]:
            return jsonify({"error": "You are not a member of this private channel"}), 403
        
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        channel["last_activity"] = time.time()
        
        message = {
            "text": text, 
            "nickname": nickname,
            "userId": user_id,
            "time": time.time(),
            "type": "text"
        }
        
        channel["messages"].append(message)
        save_data()
        
        return jsonify({"success": True, "message": message})
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/delete_channel", methods=["POST"])
def delete_channel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        channel_id = data.get("channelId", "").strip()
        user_id = data.get("userId", "").strip()
        
        if not channel_id or not user_id:
            return jsonify({"error": "Channel ID and user ID are required"}), 400
        
        if channel_id == "main":
            return jsonify({"error": "Cannot delete the main channel"}), 403
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        channel = channels[channel_id]
        
        if channel.get("is_dm", False):
            if user_id not in channel["dm_users"]:
                return jsonify({"error": "You are not part of this direct message"}), 403
        elif user_id not in channel["members"]:
            return jsonify({"error": "You are not a member of this channel"}), 403
        
        # Delete associated media files
        for message in channel["messages"]:
            if message.get("type") == "image" and message.get("file_path"):
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], message["file_path"])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {message.get('file_path')}: {e}")
        
        del channels[channel_id]
        save_data()
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in delete_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

# ===== ADMIN ENDPOINTS =====
@app.route("/admin/users")
def get_users():
    cleanup_messages()
    user_list = []
    for user_id, user_data in nicknames.items():
        user_list.append({
            "userId": user_id,
            "nickname": user_data["nickname"],
            "time": user_data["time"]
        })
    return jsonify(user_list)

@app.route("/admin/delete_user", methods=["POST"])
def delete_user():
    data = request.get_json()
    user_id = data.get("userId")
    
    if user_id in nicknames:
        del nicknames[user_id]
        for channel in channels.values():
            if "members" in channel and user_id in channel["members"]:
                channel["members"].remove(user_id)
            if "dm_users" in channel and user_id in channel["dm_users"]:
                channel["dm_users"].remove(user_id)
        save_data()
        return jsonify({"success": True})
    
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    load_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
