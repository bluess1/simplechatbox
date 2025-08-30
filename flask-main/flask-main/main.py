from flask import Flask, render_template, request, jsonify
import time, os, re, random, string
from datetime import datetime, timedelta
import json

app = Flask(__name__)

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
        "message_lifetime": 300,  # 5 minutes default
        "creator": "system",
        "members": set(),  # Track who has joined
        "is_system": True  # Mark system channels
    }
}
nicknames = {}

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
    "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg",
    "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg", "345fdgfdg",
    "fuck", "shit", "345fdgfdg", "345fdgfdg", "bitch", "345fdgfdg", "345fdgfdg", "345fdgfdg", "whore", "slut"
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

def generate_channel_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_nickname_unique(nickname):
    # Convert to lowercase for case-insensitive comparison
    nickname_lower = nickname.lower()
    for user_data in nicknames.values():
        if user_data["nickname"].lower() == nickname_lower:
            return False
    return True

def create_dm_channel(user1_id, user2_id):
    """Create a direct message channel between two users"""
    # Sort user IDs to ensure consistent channel naming
    sorted_users = sorted([user1_id, user2_id])
    channel_id = f"dm_{sorted_users[0]}_{sorted_users[1]}"
    
    # Get nicknames for display
    user1_nickname = nicknames.get(user1_id, {}).get("nickname", "Unknown")
    user2_nickname = nicknames.get(user2_id, {}).get("nickname", "Unknown")
    
    if channel_id not in channels:
        channels[channel_id] = {
            "id": channel_id,
            "name": f"�� {user1_nickname} ↔ {user2_nickname}",
            "type": "dm",
            "code": None,
            "messages": [],
            "created_at": time.time(),
            "last_activity": time.time(),
            "message_lifetime": 300,
            "creator": user1_id,
            "members": {user1_id, user2_id},
            "is_system": False,
            "dm_users": {user1_id, user2_id}
        }
    
    return channel_id

def cleanup_messages():
    """Remove old messages and inactive channels"""
    now = time.time()
    global channels, nicknames
    
    # Clean up old nicknames (5 minutes)
    nicknames = {k: v for k, v in nicknames.items() if now - v["time"] < 300}
    
    # Clean up messages in each channel
    channels_to_remove = []
    for channel_id, channel in channels.items():
        # Remove old messages based on channel's message lifetime
        channel["messages"] = [m for m in channel["messages"] if now - m["time"] < channel["message_lifetime"]]
        
        # Remove inactive user-created channels after 12 hours (43200 seconds)
        if not channel.get("is_system", False) and now - channel["last_activity"] > 43200:
            channels_to_remove.append(channel_id)
    
    # Remove inactive channels
    for channel_id in channels_to_remove:
        del channels[channel_id]

@app.route("/")
def index():
    cleanup_messages()
    return render_template("chat.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/set_nickname", methods=["POST"])
def set_nickname():
    cleanup_messages()
    data = request.get_json()
    user_id = data.get("userId")
    nickname = data.get("nickname", "").strip()
    
    if not nickname:
        return jsonify({"success": False, "error": "Nickname cannot be empty"})
    
    if len(nickname) > 20:
        return jsonify({"success": False, "error": "Nickname too long (max 20 characters)"})
    
    # Check if nickname is already taken (case-insensitive)
    if not is_nickname_unique(nickname):
        return jsonify({"success": False, "error": "Nickname already taken"})
    
    # Set nickname
    nicknames[user_id] = {
        "nickname": nickname,
        "time": time.time()
    }
    
    return jsonify({"success": True, "nickname": nickname})

@app.route("/get_nickname", methods=["POST"])
def get_nickname():
    cleanup_messages()
    data = request.get_json()
    user_id = data.get("userId")
    
    if user_id in nicknames:
        return jsonify({"success": True, "nickname": nicknames[user_id]["nickname"]})
    else:
        return jsonify({"success": False, "error": "No nickname found"})

@app.route("/channels")
def get_channels():
    cleanup_messages()
    channel_list = []
    for channel in channels.values():
        channel_copy = channel.copy()
        # Convert set to list for JSON serialization
        channel_copy["members"] = list(channel["members"])
        channel_list.append(channel_copy)
    return jsonify(channel_list)

@app.route("/create_channel", methods=["POST"])
def create_channel():
    cleanup_messages()
    data = request.get_json()
    name = data.get("name", "").strip()
    channel_type = data.get("type", "public")
    message_lifetime = int(data.get("messageLifetime", 300))
    custom_code = data.get("customCode", "").strip()
    
    if not name:
        return jsonify({"success": False, "error": "Channel name cannot be empty"})
    
    if len(name) > 30:
        return jsonify({"success": False, "error": "Channel name too long (max 30 characters)"})
    
    # Generate unique channel ID
    channel_id = f"channel_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # Handle custom code for private channels
    if channel_type == "private":
        if custom_code:
            code = custom_code
        else:
            code = generate_channel_code()
    else:
        code = None
    
    # Create channel
    channels[channel_id] = {
        "id": channel_id,
        "name": name,
        "type": channel_type,
        "code": code,
        "messages": [],
        "created_at": time.time(),
        "last_activity": time.time(),
        "message_lifetime": message_lifetime,
        "creator": data.get("creator", "unknown"),
        "members": set(),
        "is_system": False
    }
    
    return jsonify({"success": True, "channelId": channel_id, "code": code})

@app.route("/join_channel", methods=["POST"])
def join_channel():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    code = data.get("code", "").strip()
    user_id = data.get("userId")
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    channel = channels[channel_id]
    
    # Check if user is already a member
    if user_id in channel["members"]:
        return jsonify({"success": True, "channel": channel, "message": "Already a member"})
    
    # For private channels, check code
    if channel["type"] == "private":
        if not code:
            return jsonify({"success": False, "error": "Private channel requires a code"})
        if code != channel["code"]:
            return jsonify({"success": False, "error": "Invalid code"})
    
    # Add user to channel members
    channel["members"].add(user_id)
    channel["last_activity"] = time.time()
    
    return jsonify({"success": True, "channel": channel})

@app.route("/send_message", methods=["POST"])
def send_message():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    message_text = data.get("message", "").strip()
    user_id = data.get("userId")
    
    if not message_text:
        return jsonify({"success": False, "error": "Message cannot be empty"})
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    channel = channels[channel_id]
    
    # Check if user is a member of the channel
    if user_id not in channel["members"]:
        return jsonify({"success": False, "error": "You are not a member of this channel"})
    
    # Check for banned content
    if contains_banned_content(message_text):
        return jsonify({"success": False, "error": "Message contains inappropriate content"})
    
    # Get user nickname
    user_nickname = nicknames.get(user_id, {}).get("nickname", "Unknown")
    
    # Create message
    message = {
        "id": f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
        "text": message_text,
        "user": user_nickname,
        "userId": user_id,
        "timestamp": time.time(),
        "channelId": channel_id
    }
    
    # Add message to channel
    channel["messages"].append(message)
    channel["last_activity"] = time.time()
    
    return jsonify({"success": True, "message": message})

@app.route("/get_messages", methods=["POST"])
def get_messages():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    channel = channels[channel_id]
    return jsonify({"success": True, "messages": channel["messages"]})

@app.route("/delete_channel", methods=["POST"])
def delete_channel():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    user_id = data.get("userId")
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    channel = channels[channel_id]
    
    # Check if user can delete (creator or member for DMs)
    if channel["type"] == "dm":
        if user_id not in channel["members"]:
            return jsonify({"success": False, "error": "You cannot delete this channel"})
    else:
        if channel.get("is_system", False):
            return jsonify({"success": False, "error": "Cannot delete system channels"})
        if user_id not in channel["members"]:
            return jsonify({"success": False, "error": "You must be a member to delete this channel"})
    
    # Delete channel
    del channels[channel_id]
    
    return jsonify({"success": True, "message": "Channel deleted"})

@app.route("/create_dm", methods=["POST"])
def create_dm():
    cleanup_messages()
    data = request.get_json()
    user1_id = data.get("userId")
    target_nickname = data.get("targetNickname", "").strip()
    
    if not target_nickname:
        return jsonify({"success": False, "error": "Please enter a nickname"})
    
    # Find target user by nickname
    target_user_id = None
    for uid, user_data in nicknames.items():
        if user_data["nickname"].lower() == target_nickname.lower():
            target_user_id = uid
            break
    
    if not target_user_id:
        return jsonify({"success": False, "error": "User not found"})
    
    if target_user_id == user1_id:
        return jsonify({"success": False, "error": "Cannot message yourself"})
    
    # Create or get existing DM channel
    channel_id = create_dm_channel(user1_id, target_user_id)
    
    return jsonify({"success": True, "channelId": channel_id, "channel": channels[channel_id]})

@app.route("/get_dm_channels", methods=["POST"])
def get_dm_channels():
    cleanup_messages()
    data = request.get_json()
    user_id = data.get("userId")
    
    dm_channels = []
    for channel in channels.values():
        if channel["type"] == "dm" and user_id in channel["members"]:
            dm_channels.append(channel)
    
    return jsonify({"success": True, "channels": dm_channels})

@app.route("/search_users", methods=["GET"])
def search_users():
    """Search users by nickname"""
    query = request.args.get("query", "").lower()
    
    user_list = []
    for user_id, user_data in nicknames.items():
        nickname = user_data["nickname"]
        # If no query, show all users. If query exists, filter by nickname
        if not query or query in nickname.lower():
            user_list.append({
                "userId": user_id,
                "nickname": nickname,
                "lastSeen": time.time() - user_data["time"]
            })
    
    return jsonify({"success": True, "users": user_list})

# Admin endpoints
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
    return jsonify({"success": True, "users": user_list})

@app.route("/admin/delete_message", methods=["POST"])
def admin_delete_message():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    message_id = data.get("messageId")
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    channel = channels[channel_id]
    original_count = len(channel["messages"])
    channel["messages"] = [m for m in channel["messages"] if m["id"] != message_id]
    
    if len(channel["messages"]) == original_count:
        return jsonify({"success": False, "error": "Message not found"})
    
    return jsonify({"success": True, "message": "Message deleted"})

@app.route("/admin/delete_channel", methods=["POST"])
def admin_delete_channel():
    cleanup_messages()
    data = request.get_json()
    channel_id = data.get("channelId")
    
    if channel_id not in channels:
        return jsonify({"success": False, "error": "Channel not found"})
    
    if channels[channel_id].get("is_system", False):
        return jsonify({"success": False, "error": "Cannot delete system channels"})
    
    del channels[channel_id]
    return jsonify({"success": True, "message": "Channel deleted"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
