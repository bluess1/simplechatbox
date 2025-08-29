from flask import Flask, render_template, request, jsonify
import time, os, re, random, string
from datetime import datetime, timedelta

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
        if not channel.get("is_system", False):  # Only check user-created channels
            if now - channel["last_activity"] > 43200:  # 12 hours
                channels_to_remove.append(channel_id)
                print(f"Auto-deleting inactive channel: {channel['name']} (ID: {channel_id})")
    
    # Remove inactive channels
    for channel_id in channels_to_remove:
        del channels[channel_id]

@app.route("/")
def index():
    return render_template("chat.html")

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
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in set_nickname: {str(e)}")
        return jsonify({"error": "Server error"}), 500

# Add these new admin routes to your existing main.py

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

@app.route("/admin/delete_channel", methods=["POST"])
def admin_delete_channel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        channel_id = data.get("channelId", "").strip()
        admin_password = data.get("adminPassword", "").strip()
        
        if not channel_id or not admin_password:
            return jsonify({"error": "Channel ID and admin password are required"}), 400
        
        if admin_password != "admin123":  # Change this to match your password
            return jsonify({"error": "Invalid admin password"}), 403
        
        if channel_id == "main":
            return jsonify({"error": "Cannot delete the main channel"}), 403
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        # Delete the channel
        del channels[channel_id]
        
        return jsonify({"success": True, "message": "Channel deleted successfully"})
        
    except Exception as e:
        print(f"Error in admin_delete_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/admin/clear_channel", methods=["POST"])
def admin_clear_channel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        channel_id = data.get("channelId", "").strip()
        admin_password = data.get("adminPassword", "").strip()
        
        if not channel_id or not admin_password:
            return jsonify({"error": "Channel ID and admin password are required"}), 400
        
        if admin_password != "admin123":  # Change this to match your password
            return jsonify({"error": "Invalid admin password"}), 403
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        # Clear all messages from the channel
        channels[channel_id]["messages"] = []
        
        return jsonify({"success": True, "message": "Channel cleared successfully"})
        
    except Exception as e:
        print(f"Error in admin_clear_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/admin/delete_message", methods=["POST"])
def admin_delete_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        channel_id = data.get("channelId", "").strip()
        timestamp = data.get("timestamp", "").strip()
        admin_password = data.get("adminPassword", "").strip()
        
        if not channel_id or not timestamp or not admin_password:
            return jsonify({"error": "Channel ID, timestamp, and admin password are required"}), 400
        
        if admin_password != "admin123":  # Change this to match your password
            return jsonify({"error": "Invalid admin password"}), 403
        
        cleanup_messages()
        
        if channel_id not in channels:
            return jsonify({"error": "Channel not found"}), 404
        
        # Find and remove the message
        channel = channels[channel_id]
        original_count = len(channel["messages"])
        channel["messages"] = [m for m in channel["messages"] if m["time"] != float(timestamp)]
        
        if len(channel["messages"]) == original_count:
            return jsonify({"error": "Message not found"}), 404
        
        return jsonify({"success": True, "message": "Message deleted successfully"})
        
    except Exception as e:
        print(f"Error in admin_delete_message: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/admin/ban_user", methods=["POST"])
def admin_ban_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_id = data.get("userId", "").strip()
        admin_password = data.get("adminPassword", "").strip()
        
        if not user_id or not admin_password:
            return jsonify({"error": "User ID and admin password are required"}), 400
        
        if admin_password != "admin123":  # Change this to match your password
            return jsonify({"error": "Invalid admin password"}), 403
        
        # Remove user from nicknames (effectively banning them)
        if user_id in nicknames:
            del nicknames[user_id]
        
        # Remove user from all channel members
        for channel in channels.values():
            if "members" in channel and user_id in channel["members"]:
                channel["members"].remove(user_id)
        
        return jsonify({"success": True, "message": "User banned successfully"})
        
    except Exception as e:
        print(f"Error in admin_ban_user: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/channels")
def get_channels():
    cleanup_messages()
    channel_list = []
    for channel_id, channel in channels.items():
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
        
        # Add validation for custom codes
        if channel_type == "private":
            if not custom_code or len(custom_code) != 6:
                return jsonify({"error": "Private channels require a 6-character code"}), 400
            if not custom_code.isalnum():
                return jsonify({"error": "Channel code must contain only letters and numbers"}), 400
        
        cleanup_messages()
        
        channel_id = name.lower().replace(" ", "-") + "-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        # Use custom code if provided, otherwise generate random
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
            "members": {user_id},  # Creator automatically becomes a member
            "is_system": False  # Mark as user-created channel
        }
        
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
        
        # Check if private channel requires code
        if channel["type"] == "private":
            # Check if user is already a member
            if user_id in channel["members"]:
                # User is already a member, no need for code
                pass
            else:
                # New user needs to provide code
                if not code:
                    return jsonify({"error": "Private channel requires a code to join"}), 403
                if channel["code"] != code.upper():
                    return jsonify({"error": "Invalid channel code"}), 403
                
                # Add user to members when they successfully join with code
                channel["members"].add(user_id)
        
        # Update last activity when someone joins
        channel["last_activity"] = time.time()
        
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
    return jsonify([{
        "text": m["text"], 
        "nickname": m["nickname"], 
        "userId": m["userId"],
        "timestamp": m["time"]
    } for m in channel["messages"]])

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
        
        # For private channels, check if user is a member
        channel = channels[channel_id]
        if channel["type"] == "private" and user_id not in channel["members"]:
            return jsonify({"error": "You are not a member of this private channel"}), 403
        
        # Update nickname and channel activity
        nicknames[user_id] = {"nickname": nickname, "time": time.time()}
        channels[channel_id]["last_activity"] = time.time()
        
        # Add message to channel
        message = {
            "text": text, 
            "nickname": nickname,
            "userId": user_id,
            "time": time.time()
        }
        
        channels[channel_id]["messages"].append(message)
        
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
        
        # Check if user is a member of the channel
        if user_id not in channel["members"]:
            return jsonify({"error": "You are not a member of this channel"}), 403
        
        # Delete the channel
        del channels[channel_id]
        
        return jsonify({"success": True, "message": "Channel deleted successfully"})
        
    except Exception as e:
        print(f"Error in delete_channel: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/channel_info/<channel_id>")
def get_channel_info(channel_id):
    cleanup_messages()
    
    if channel_id not in channels:
        return jsonify({"error": "Channel not found"}), 404
    
    channel = channels[channel_id]
    return jsonify({
        "id": channel_id,
        "name": channel["name"],
        "type": channel["type"],
        "code": channel.get("code"),
        "messageLifetime": channel["message_lifetime"],
        "messageCount": len(channel["messages"]),
        "lastActivity": channel["last_activity"],
        "creator": channel["creator"],
        "is_system": channel.get("is_system", False)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
