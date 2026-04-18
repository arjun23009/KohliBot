import os
import requests
import base64
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SECTION_CONFIG = {
    "video": {
        "title": "Video Analysis",
        "icon": "🎥",
        "color": "#f5a623",
        "glow": "rgba(245,166,35,0.15)",
        "desc": "Upload your batting video for frame-by-frame analysis.",
        "welcome": "Upload your batting video and I'll break down every aspect of your technique — footwork, head position, bat swing, everything.",
        "placeholder": "Ask about your technique or upload a video...",
        "suggestions": ["Analyze my batting stance", "What's wrong with my backlift?", "How's my footwork?", "Rate my cover drive"],
        "prompt": """You are Virat Kohli coaching Arjun on batting technique through video analysis.
Always address him as Arjun. Analyze footwork, head position, backlift, bat swing, weight transfer, balance, follow-through.
Be intense, direct, honest. Reference your own experience. Keep it 4-5 lines max. Never break character."""
    },
    "batting": {
        "title": "Batting Coach",
        "icon": "🏏",
        "color": "#3b82f6",
        "glow": "rgba(59,130,246,0.15)",
        "desc": "Personal batting drills and technique coaching.",
        "welcome": "Arjun, let's get to work on your batting. Tell me what you're struggling with and I'll give you the drills and mindset to fix it.",
        "placeholder": "Ask about shots, drills, technique...",
        "suggestions": ["How do I improve my cover drive?", "Drills for playing short pitch", "How to build an innings?", "Tips for playing spin bowling"],
        "prompt": """You are Virat Kohli personally coaching Arjun to become a great batsman.
Arjun is a beginner who wants to become a national level player. He struggles with batting, fielding and bowling.
Always address him as Arjun. Give specific drills, techniques, and mental frameworks.
Be intense, direct, motivating. Reference your own journey. Keep it 4-5 lines max. Never break character."""
    },
    "communication": {
        "title": "Communication Skills",
        "icon": "🗣️",
        "color": "#22c55e",
        "glow": "rgba(34,197,94,0.15)",
        "desc": "Body language, confidence and communication on and off the field.",
        "welcome": "Arjun, cricket isn't just about batting. How you carry yourself separates good players from great ones. Let's work on that.",
        "placeholder": "Ask about confidence, body language, communication...",
        "suggestions": ["How to show confidence on field?", "How do you handle sledging?", "Tips for team communication", "How to carry yourself like a champion?"],
        "prompt": """You are Virat Kohli coaching Arjun on communication, body language and confidence.
Always address him as Arjun. Draw from your own experience of building confidence and leading teams.
Be direct, intense, real. Keep it 4-5 lines max. Never break character."""
    },
    "leadership": {
        "title": "Leadership & Mindset",
        "icon": "👑",
        "color": "#ef4444",
        "glow": "rgba(239,68,68,0.15)",
        "desc": "Captaincy philosophy, winning mindset and handling pressure.",
        "welcome": "Arjun, the best batsmen aren't just technically good — they have a champion's mindset. Let me share what I've learned.",
        "placeholder": "Ask about mindset, leadership, pressure...",
        "suggestions": ["How to handle pressure situations?", "What's your captaincy philosophy?", "How to build a winning mindset?", "How to bounce back from failure?"],
        "prompt": """You are Virat Kohli coaching Arjun on leadership, mindset and handling pressure.
Always address him as Arjun. Share your captaincy experience and mental frameworks.
Be intense, philosophical, real. Keep it 4-5 lines max. Never break character."""
    }
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    session.clear()
    return render_template("index.html")

@app.route("/chat/<section>")
def chat_page(section):
    session.clear()
    config = SECTION_CONFIG.get(section, SECTION_CONFIG["batting"])
    return render_template("chat.html",
        section=section,
        section_title=config["title"],
        section_icon=config["icon"],
        section_desc=config["desc"],
        accent_color=config["color"],
        accent_glow=config["glow"],
        welcome_msg=config["welcome"],
        placeholder=config["placeholder"],
        suggestions=config["suggestions"]
    )

@app.route("/chat", methods=["POST"])
def chat():
    history = session.get("history", [])
    section = request.form.get("section", "batting")
    config = SECTION_CONFIG.get(section, SECTION_CONFIG["batting"])

    video_content = None
    if "video" in request.files and request.files["video"].filename != "":
        video = request.files["video"]
        if allowed_file(video.filename):
            video_path = os.path.join(UPLOAD_FOLDER, video.filename)
            video.save(video_path)
            with open(video_path, "rb") as f:
                video_data = base64.standard_b64encode(f.read()).decode("utf-8")
            ext = video.filename.rsplit(".", 1)[1].lower()
            media_type_map = {
                "mp4": "video/mp4",
                "mov": "video/quicktime",
                "avi": "video/x-msvideo",
                "mkv": "video/x-matroska",
                "webm": "video/webm"
            }
            media_type = media_type_map.get(ext, "video/mp4")
            video_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{video_data}"
                }
            }

    user_message = request.form.get("message", "").strip()
    if not user_message and not video_content:
        return jsonify({"error": "Send a message or upload a video."})

    user_content = []
    if video_content:
        user_content.append(video_content)
    if user_message:
        user_content.append({"type": "text", "text": user_message})
    elif video_content:
        user_content.append({
            "type": "text",
            "text": "Coach, I've uploaded my batting video. Please analyze my technique and tell me what I need to work on."
        })

    if video_content:
        history.append({
            "role": "user",
            "content": [{"type": "text", "text": f"[Arjun uploaded a batting video] {user_message or 'Please analyze my batting technique.'}"}]
        })
    else:
        history.append({"role": "user", "content": user_content})

    if len(history) > 20:
        history = history[-20:]

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/auto",
                "messages": [
                    {"role": "system", "content": config["prompt"]}
                ] + history
            }
        )

        data = response.json()

        if "error" in data:
            return jsonify({"error": data["error"]["message"]})

        reply = data["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        session["history"] = history

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": f"Failed: {str(e)}"})

if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)