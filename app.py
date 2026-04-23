import os
import json
import uuid
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "khusboo-secret-2024")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SETTINGS_FILE = "settings.json"
LEADS_FILE = "leads.json"

DEFAULT_SETTINGS = {
    "admin_password": "khusboo2024",
    "admins": [
        {"username": "Gaurav", "password": "khusboo2024", "role": "owner"},
        {"username": "Khusboo", "password": "khusboo@admin", "role": "admin"}
    ],
    "site_name": "Khusboo Creatives",
    "tagline": "Grow Your Brand with Stunning Reels & Ads that Actually Convert",
    "whatsapp": "",
    "instagram": "",
    "email": "",
    "services": [
        {"icon": "🎬", "title": "Instagram Reels", "desc": "Engaging, scroll-stopping reels crafted with trending audio, hooks, and on-brand visuals that boost reach."},
        {"icon": "📢", "title": "Facebook & Instagram Ads", "desc": "Data-driven paid campaigns that target the right audience and maximise your ad spend ROI."},
        {"icon": "📈", "title": "Instagram Growth Strategy", "desc": "Full account audit, bio optimisation, hashtag research, and a growth roadmap built for your niche."},
        {"icon": "🗓️", "title": "Content Calendar", "desc": "Monthly content plan with captions, post ideas, and posting schedules so you never run out of ideas."},
        {"icon": "🎨", "title": "Brand Identity", "desc": "Colour palette, fonts, templates — a cohesive aesthetic that makes you look premium."},
        {"icon": "🤝", "title": "Influencer Outreach", "desc": "Find and connect with the right micro-influencers to amplify your brand reach authentically."},
    ]
}

conversations = {}
leads = []
settings = {}


def load_data():
    global leads, settings
    leads = json.load(open(LEADS_FILE)) if os.path.exists(LEADS_FILE) else []
    settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else DEFAULT_SETTINGS.copy()
    for key, val in DEFAULT_SETTINGS.items():
        settings.setdefault(key, val)


def save_leads():
    json.dump(leads, open(LEADS_FILE, "w"), indent=2)


def save_settings():
    json.dump(settings, open(SETTINGS_FILE, "w"), indent=2)


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def build_system_prompt():
    svc_list = "\n".join(f"- {s['title']}" for s in settings.get("services", DEFAULT_SETTINGS["services"]))
    return f"""You are Priya, the friendly AI assistant for {settings.get('site_name', 'Khusboo Creatives')}.

Services offered:
{svc_list}

Your job: chat naturally with potential clients, understand their needs, and collect their details.

Collect these one by one in conversation (never ask all at once):
1. Their name
2. Business name / niche
3. Email address
4. Phone number (WhatsApp preferred)
5. Instagram handle (if any)
6. Which services they need
7. Monthly budget (under ₹5k / ₹5k-15k / ₹15k-30k / ₹30k+)
8. Current pain point on social media

Rules:
- Warm, friendly, professional tone — 1-2 emojis max per message
- Ask ONE question at a time
- Once ALL 8 details collected, confirm and say Khusboo will reach out within 24 hours
- Then output at the very end (hidden from user):

<LEAD_CAPTURED>
{{"name":"...","business":"...","email":"...","phone":"...","instagram":"...","services":"...","budget":"...","pain_point":"..."}}
</LEAD_CAPTURED>

Start by greeting and asking their name."""


# ─── PUBLIC ROUTES ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", settings=settings)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"message": "Please type something 😊", "lead_captured": False})

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=build_system_prompt(),
        messages=conversations[session_id],
    )

    assistant_text = response.content[0].text
    lead_captured = False

    if "<LEAD_CAPTURED>" in assistant_text:
        try:
            start = assistant_text.index("<LEAD_CAPTURED>") + len("<LEAD_CAPTURED>")
            end = assistant_text.index("</LEAD_CAPTURED>")
            lead_data = json.loads(assistant_text[start:end].strip())
            lead_data["timestamp"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
            lead_data["id"] = str(uuid.uuid4())[:8].upper()
            lead_data["status"] = "new"
            leads.append(lead_data)
            save_leads()
            lead_captured = True
        except Exception:
            pass
        assistant_text = assistant_text.split("<LEAD_CAPTURED>")[0].strip()

    conversations[session_id].append({"role": "assistant", "content": assistant_text})
    return jsonify({"message": assistant_text, "lead_captured": lead_captured})


# ─── DASHBOARD / ADMIN ────────────────────────────────────────────────────────

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        pwd = request.form.get("password", "")
        admins = settings.get("admins", [{"username": "Khusboo", "password": settings.get("admin_password", "khusboo2024"), "role": "admin"}])
        matched = next((a for a in admins if a["username"].lower() == username.lower() and a["password"] == pwd), None)
        if matched:
            session["admin"] = True
            session["admin_name"] = matched["username"]
            session["admin_role"] = matched["role"]
            return redirect(url_for("admin_leads"))
        return render_template("login.html", error=True)
    if session.get("admin"):
        return redirect(url_for("admin_leads"))
    return render_template("login.html", error=False)


@app.route("/dashboard/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/admin/leads")
@admin_required
def admin_leads():
    status_filter = request.args.get("status", "all")
    filtered = leads if status_filter == "all" else [l for l in leads if l.get("status") == status_filter]
    return render_template("admin_leads.html", leads=list(reversed(filtered)),
                           settings=settings, filter=status_filter, total=len(leads))


@app.route("/admin/lead/<lead_id>/status", methods=["POST"])
@admin_required
def update_lead_status(lead_id):
    new_status = request.form.get("status")
    for lead in leads:
        if lead.get("id") == lead_id:
            lead["status"] = new_status
            break
    save_leads()
    return redirect(url_for("admin_leads"))


@app.route("/admin/lead/<lead_id>/delete", methods=["POST"])
@admin_required
def delete_lead(lead_id):
    global leads
    leads = [l for l in leads if l.get("id") != lead_id]
    save_leads()
    return redirect(url_for("admin_leads"))


@app.route("/admin/export/csv")
@admin_required
def export_csv():
    fields = ["id", "name", "business", "email", "phone", "instagram", "services", "budget", "pain_point", "status", "timestamp"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(leads)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=khusboo_leads.csv"})


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    msg = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "general":
            settings["site_name"] = request.form.get("site_name", "").strip()
            settings["tagline"] = request.form.get("tagline", "").strip()
            settings["whatsapp"] = request.form.get("whatsapp", "").strip()
            settings["instagram"] = request.form.get("instagram", "").strip()
            settings["email"] = request.form.get("email", "").strip()
            save_settings()
            msg = ("success", "Settings saved!")

        elif action == "admins":
            usernames = request.form.getlist("admin_username")
            passwords = request.form.getlist("admin_password")
            roles = request.form.getlist("admin_role")
            settings["admins"] = [
                {"username": u.strip(), "password": p.strip(), "role": r}
                for u, p, r in zip(usernames, passwords, roles) if u.strip() and p.strip()
            ]
            save_settings()
            msg = ("success", "Admin users updated!")

        elif action == "password":
            current = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "").strip()
            confirm = request.form.get("confirm_password", "").strip()
            if current != settings.get("admin_password"):
                msg = ("error", "Current password is wrong.")
            elif len(new_pwd) < 6:
                msg = ("error", "New password must be at least 6 characters.")
            elif new_pwd != confirm:
                msg = ("error", "Passwords don't match.")
            else:
                settings["admin_password"] = new_pwd
                save_settings()
                msg = ("success", "Password changed successfully!")

        elif action == "services":
            icons = request.form.getlist("svc_icon")
            titles = request.form.getlist("svc_title")
            descs = request.form.getlist("svc_desc")
            settings["services"] = [
                {"icon": i.strip(), "title": t.strip(), "desc": d.strip()}
                for i, t, d in zip(icons, titles, descs) if t.strip()
            ]
            save_settings()
            msg = ("success", "Services updated!")

    return render_template("admin_settings.html", settings=settings, msg=msg)


if __name__ == "__main__":
    load_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
