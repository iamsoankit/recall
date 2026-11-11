# Recall

Recall helps a team find decisions, tasks, and unresolved questions in meeting notes. Ask a question, read the answer, and open the meeting that supports it.

The example follows three students building a class-notes app. Their project demo is postponed because sign-in does not work on phones, then moved to Saturday after the fix. The sample is intentionally simple; the product idea is for small teams that need to remember who decided or agreed to do what.

## Run it locally

You need Python 3.9+ and Node.js 20.19+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```sh
cd web
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://127.0.0.1:5173`). The API is at `http://127.0.0.1:8000`, and its interactive docs are at `/docs`. Notes and edits are stored in `backend/recall.db` on your machine. Delete that file to reset the sample workspace.

## Deploy on Vercel

Set the Vercel project's **Root Directory** to the repository root (`.`). Vercel then uses the Python entry point in `pyproject.toml`; its build script builds the React app, and FastAPI serves that build together with the `/api` routes on the same domain. The deployed SQLite database lives in the function's temporary filesystem, so changes are for demo use and may reset when Vercel replaces an instance. Local development continues to use Vite and the separate FastAPI server above.

## What works

- Add meeting notes. Recall suggests decisions, tasks, and questions for a person to review.
- Save, edit, or remove suggestions. Corrections persist in SQLite.
- Ask one of the sample questions or type your own. Answers link to the meeting notes they came from.
- See how decisions, people, and meetings connect.
- Run six sample questions and inspect the retrieved items and source results.

## Technical approach

- **Frontend:** React 19, TypeScript, Vite.
- **API:** Python 3, FastAPI, Pydantic.
- **Storage:** SQLite with separate meeting and memory records.
- **Retrieval:** TF-IDF cosine similarity over saved decisions, tasks, questions, and source text. When a question asks what changed, Recall returns both linked decisions.
- **Evaluation:** a small, inspectable six-question benchmark with per-question expected items and source checks.

This is a research prototype, not a production assistant. It does not call an LLM or use embeddings. The note extractor uses simple patterns, and TF-IDF is a baseline; both can miss paraphrases. The sample benchmark is not a user study and should not be presented as evidence of real-world performance.

## Connection to the internship

- **HCI:** people decide what gets saved, correct the text, and can follow an answer to its source.
- **Knowledge graphs:** the connection view shows relationships among meetings, people, topics, and decisions. The current graph is generated from SQLite records, not a graph database.
- **Memory over time:** when a plan changes, the earlier choice and the newer one remain linked.
- **Applied ML and evaluation:** TF-IDF retrieval provides a baseline to compare with embeddings or a language model later. The benchmark makes expected facts and citations inspectable.

The next research step is to compare the current retrieval with a stronger method on the same questions, then ask people whether the answer and its source help them remember why a decision changed.
