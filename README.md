# Valid Person Finder

You enter a company name and a job title (e.g. Microsoft, CEO). The app finds that person’s full name using web search and Groq, then shows first name, last name, source link, and a confidence score.

**Run it**

1. Python 3.9+. Get a free API key from [Groq](https://console.groq.com/) (API Keys).
2. From the project folder:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your key:
   ```env
   GROQ_API_KEY=your_key_here
   ```
   Optional: set `USE_AGENTIC_CREW=1` to use the CrewAI Researcher / Validator / Reporter flow instead of the default pipeline.
4. Start the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000, type company and designation, click Find person.

**What you get**

- If someone is found: first name, last name, title, source URL, and confidence (e.g. High 95%). Confidence is higher when the same name appears in multiple sources.
- If not: an error message (e.g. no results or no name extracted).

Test data is in `Test data.xlsx` (company + title per row). Use those rows in the UI or call `POST /api/search` with `{"company": "...", "designation": "..."}` for the same JSON result.
