import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from backend.pipeline import run_pipeline

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)


def _use_agentic_crew():
    return os.getenv("USE_AGENTIC_CREW", "").strip().lower() in ("1", "true", "yes")


def _groq_configured():
    return bool(os.getenv("GROQ_API_KEY", "").strip())


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json() or {}
    company = data.get("company", "").strip()
    designation = data.get("designation", "").strip()
    if not company or not designation:
        return jsonify({
            "found": False,
            "error": "Missing company or designation",
            "first_name": "",
            "last_name": "",
            "current_title": designation or "",
            "source_url": "",
            "confidence_score": 0.0,
            "sources_checked": [],
        }), 400
    if _use_agentic_crew():
        try:
            from backend.crew_pipeline import run_crew_pipeline
            result = run_crew_pipeline(company, designation)
        except Exception as e:
            result = {
                "first_name": "",
                "last_name": "",
                "current_title": designation,
                "source_url": "",
                "confidence_score": 0.0,
                "sources_checked": [],
                "found": False,
                "error": str(e),
            }
    else:
        result = run_pipeline(company, designation)
    status = 200 if result.get("found") or not result.get("error") else 404
    return jsonify(result), status


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "groq_configured": _groq_configured(),
        "agentic_crew": _use_agentic_crew(),
    })


if __name__ == "__main__":
    if _groq_configured():
        print("Groq API key: configured (name extraction enabled)")
    else:
        print("WARNING: GROQ_API_KEY not set in .env - name extraction will fail.")
    if _use_agentic_crew():
        print("Bonus: Agentic CrewAI pipeline enabled (Researcher, Validator, Reporter)")
    app.run(host="0.0.0.0", port=5000, debug=True)
