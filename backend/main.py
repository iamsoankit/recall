from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import uuid
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DEFAULT_DB_PATH = (
    Path("/tmp/recall.db")
    if os.getenv("VERCEL") or not os.access(ROOT, os.W_OK)
    else ROOT / "recall.db"
)
DB_PATH = Path(
    os.getenv(
        "RECALL_DB_PATH",
        str(DEFAULT_DB_PATH),
    )
)
STOP_WORDS = {
    "the", "and", "for", "with", "was", "were", "did", "does", "what",
    "when", "where", "who", "how", "why", "from", "into", "this", "that",
    "will", "would", "should", "could", "about", "team", "meeting", "they",
    "their", "then", "than", "have", "has", "had", "are", "our", "you",
}

app = FastAPI(title="Recall API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def json_row(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    if "entities" in value:
        value["entities"] = json.loads(value["entities"] or "[]")
    if "approved" in value:
        value["approved"] = bool(value["approved"])
    return value


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                meeting_date TEXT NOT NULL,
                attendees TEXT NOT NULL DEFAULT '[]',
                notes TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('decision', 'action', 'open')),
                text TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT '',
                meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                meeting_date TEXT NOT NULL,
                source TEXT NOT NULL,
                entities TEXT NOT NULL DEFAULT '[]',
                approved INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open',
                supersedes TEXT REFERENCES memories(id) DEFERRABLE INITIALLY DEFERRED,
                superseded_by TEXT REFERENCES memories(id) DEFERRABLE INITIALLY DEFERRED,
                change_reason TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memories_meeting ON memories(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_memories_approved ON memories(approved);
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        if count == 0:
            seed_data(connection)


def seed_data(connection: sqlite3.Connection) -> None:
    meetings = [
        ("m4", "Class project demo check-in", "2026-11-10", ["Ananya Rao", "Arjun Kumar", "Meera Shah"], "The sign-in page now works on phones. We agreed to hold our class project demo on Saturday, instead of postponing it. This changes the Nov 8 decision, when we were waiting for the mobile sign-in fix. Arjun has prepared the slides. Open question: should we show the app live or bring a recorded video as backup?"),
        ("m1", "Class project demo planning", "2026-11-08", ["Ananya Rao", "Arjun Kumar", "Meera Shah"], "We decided to postpone our class project demo until the sign-in page works on phones. Arjun will prepare the slides by Friday. Open question: should we show the app live or use a recorded video?"),
        ("m2", "Notes app team meeting", "2026-11-05", ["Ananya Rao", "Arjun Kumar", "Meera Shah"], "We decided to keep our class project app simple: save class notes and search them later. Arjun will ask three classmates to try the search. Open question: would reminders before exams be useful? We agreed that people should be able to edit or delete a saved note."),
        ("m3", "First app idea discussion", "2026-11-02", ["Ananya Rao", "Arjun Kumar", "Meera Shah"], "We agreed to build a small app that helps students find their class notes. Arjun will ask three classmates what they lose track of most often. Open question: should the app search handwritten notes too? We decided to start by testing typed notes first."),
    ]
    connection.executemany(
        "INSERT INTO meetings(id,title,meeting_date,attendees,notes) VALUES(?,?,?,?,?)",
        [(i, title, when, json.dumps(attendees), notes) for i, title, when, attendees, notes in meetings],
    )
    memories = [
        ("d7", "decision", "Hold the class project demo on Saturday now that sign-in works on phones.", "", "m4", "2026-11-10", "We agreed to hold our class project demo on Saturday, instead of postponing it. This changes the Nov 8 decision, when we were waiting for the mobile sign-in fix.", ["Class project demo", "Notes app"], 1, "done", "d1", None, "The sign-in page now works on phones, so the team can show the app."),
        ("a4", "action", "Prepare the slides for the class project demo.", "Arjun Kumar", "m4", "2026-11-10", "Arjun has prepared the slides.", ["Arjun Kumar", "Class project demo"], 1, "done", None, None, None),
        ("q4", "open", "Should we show the app live or bring a recorded video as backup?", "", "m4", "2026-11-10", "Open question: should we show the app live or bring a recorded video as backup?", ["Class project demo"], 1, "open", None, None, None),
        ("d1", "decision", "Postpone the class project demo until sign-in works on phones.", "", "m1", "2026-11-08", "We decided to postpone our class project demo until the sign-in page works on phones.", ["Class project demo", "Notes app"], 1, "done", None, "d7", None),
        ("a1", "action", "Prepare the slides by Friday.", "Arjun Kumar", "m1", "2026-11-08", "Arjun will prepare the slides by Friday.", ["Arjun Kumar", "Class project demo"], 1, "done", None, None, None),
        ("q1", "open", "Should we show the app live or use a recorded video?", "", "m1", "2026-11-08", "Open question: should we show the app live or use a recorded video?", ["Class project demo"], 1, "open", None, None, None),
        ("d3", "decision", "Keep the class project app simple: save class notes and search them later.", "", "m2", "2026-11-05", "We decided to keep our class project app simple: save class notes and search them later.", ["Notes app"], 1, "done", None, None, None),
        ("a2", "action", "Ask three classmates to try searching their notes.", "Arjun Kumar", "m2", "2026-11-05", "Arjun will ask three classmates to try the search.", ["Arjun Kumar", "Notes app"], 1, "open", None, None, None),
        ("q2", "open", "Would reminders before exams be useful?", "", "m2", "2026-11-05", "Open question: would reminders before exams be useful?", ["Notes app"], 1, "open", None, None, None),
        ("d4", "decision", "Let people edit or delete a saved note.", "", "m2", "2026-11-05", "We agreed that people should be able to edit or delete a saved note.", ["Notes app"], 1, "done", None, None, None),
        ("d5", "decision", "Start by testing typed class notes first.", "", "m3", "2026-11-02", "We decided to start by testing typed notes first.", ["Notes app", "Typed notes"], 1, "done", None, None, None),
        ("a3", "action", "Ask three classmates what they lose track of most often.", "Arjun Kumar", "m3", "2026-11-02", "Arjun will ask three classmates what they lose track of most often.", ["Arjun Kumar", "Notes app"], 1, "done", None, None, None),
        ("q3", "open", "Should the app search handwritten notes too?", "", "m3", "2026-11-02", "Open question: should the app search handwritten notes too?", ["Notes app"], 1, "open", None, None, None),
        ("d6", "decision", "Build a small app that helps students find their class notes.", "", "m3", "2026-11-02", "We agreed to build a small app that helps students find their class notes.", ["Notes app"], 1, "done", None, None, None),
    ]
    connection.executemany(
        """INSERT INTO memories(id,kind,text,owner,meeting_id,meeting_date,source,entities,approved,status,supersedes,superseded_by,change_reason)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(*row[:7], json.dumps(row[7]), *row[8:]) for row in memories],
    )


@app.on_event("startup")
def startup() -> None:
    init_db()


class MeetingInput(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    meeting_date: Optional[str] = None
    notes: str = Field(min_length=10, max_length=20000)


class MemoryUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=3, max_length=1000)
    owner: Optional[str] = Field(default=None, max_length=120)
    approved: Optional[bool] = None


class QueryInput(BaseModel):
    question: str = Field(min_length=3, max_length=400)


def meeting_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["attendees"] = json.loads(result["attendees"] or "[]")
    return result


def get_memories(approved_only: bool = False) -> list[dict[str, Any]]:
    with db() as connection:
        where = "WHERE m.approved = 1" if approved_only else ""
        rows = connection.execute(
            f"""SELECT m.*, g.title AS meeting_title FROM memories m
                JOIN meetings g ON g.id=m.meeting_id {where}
                ORDER BY m.meeting_date DESC, m.id"""
        ).fetchall()
    return [json_row(row) for row in rows]


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in STOP_WORDS]


def rank_memories(question: str, approved: Optional[list[dict[str, Any]]] = None) -> list[tuple[float, dict[str, Any]]]:
    items = approved if approved is not None else get_memories(approved_only=True)
    if not items:
        return []
    query_terms = tokens(question)
    documents = [tokens(item["text"] + " " + item["source"] + " " + item["owner"] + " " + " ".join(item["entities"])) for item in items]
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(set(document))
    query_counts = Counter(query_terms)
    total_docs = len(documents)
    scored: list[tuple[float, dict[str, Any]]] = []
    for item, document in zip(items, documents):
        document_counts = Counter(document)
        dot = 0.0
        query_norm = 0.0
        doc_norm = 0.0
        for term, count in query_counts.items():
            idf = math.log((total_docs + 1) / (document_frequency.get(term, 0) + 1)) + 1
            q_weight = (1 + math.log(count)) * idf
            d_count = document_counts.get(term, 0)
            d_weight = (1 + math.log(d_count)) * idf if d_count else 0.0
            dot += q_weight * d_weight
            query_norm += q_weight * q_weight
        for term, count in document_counts.items():
            idf = math.log((total_docs + 1) / (document_frequency.get(term, 0) + 1)) + 1
            weight = (1 + math.log(count)) * idf
            doc_norm += weight * weight
        score = dot / (math.sqrt(query_norm) * math.sqrt(doc_norm)) if dot and query_norm and doc_norm else 0.0
        if score:
            scored.append((score, item))
    return sorted(scored, key=lambda pair: (pair[0], pair[1]["meeting_date"]), reverse=True)


def is_change_question(question: str) -> bool:
    return bool(re.search(r"\b(chang(?:e|ed|ing)|current|now|before|previous|original|history|updated|earlier|later|move|moved|postponed|first)\b", question.lower()))


def decision_pair(items: list[dict[str, Any]]) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
    for old in items:
        if old.get("superseded_by"):
            newer = next((item for item in items if item["id"] == old["superseded_by"]), None)
            if newer:
                return old, newer
    return None


def extract_notes(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for sentence in re.split(r"\n+|(?<=[.!?])\s+", text):
        sentence = sentence.strip()
        low = sentence.lower()
        kind = None
        if re.search(r"open question|unresolved|still need to decide|should we|how long|whether to|do people want", low):
            kind = "open"
        elif re.search(r"\b(decided|agreed|we will|we'll|will not|won't|keep the first|start with|defer|approved|chose to|postpone)\b", low):
            kind = "decision"
        elif re.search(r"\b(owns|owner is|will draft|will prepare|will prototype|will review|will share|will send|will follow up|has finished|is complete|will ask|action item)\b", low):
            kind = "action"
        if not kind or len(sentence) < 12:
            continue
        owner_match = re.search(r"\b(Ananya Rao|Arjun Kumar|Meera Shah|Ananya|Arjun|Meera)\b", sentence, re.I)
        owner = owner_match.group(0) if owner_match else ""
        owner = {"ananya": "Ananya Rao", "arjun": "Arjun Kumar", "meera": "Meera Shah"}.get(owner.lower(), owner)
        found.append({"kind": kind, "text": sentence, "owner": owner, "source": sentence, "entities": [entity for entity in ["class project demo", "notes app", "class notes", "handwritten notes"] if entity in low]})
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in found:
        unique[(item["kind"], item["text"].lower())] = item
    return list(unique.values())[:10]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": "sqlite"}


@app.get("/api/meetings")
def list_meetings() -> list[dict[str, Any]]:
    with db() as connection:
        meetings = connection.execute("SELECT * FROM meetings ORDER BY meeting_date DESC").fetchall()
        result = []
        for meeting in meetings:
            row = meeting_dict(meeting)
            memories = connection.execute("SELECT COUNT(*) AS total, SUM(approved) AS saved FROM memories WHERE meeting_id=?", (row["id"],)).fetchone()
            row["memory_count"] = memories["total"] or 0
            row["saved_count"] = memories["saved"] or 0
            result.append(row)
    return result


@app.get("/api/memories")
def list_memories() -> list[dict[str, Any]]:
    return get_memories()


@app.post("/api/meetings", status_code=201)
def create_meeting(payload: MeetingInput) -> dict[str, Any]:
    meeting_id = str(uuid.uuid4())
    meeting_date = payload.meeting_date or date.today().isoformat()
    suggestions = extract_notes(payload.notes)
    with db() as connection:
        connection.execute(
            "INSERT INTO meetings(id,title,meeting_date,attendees,notes) VALUES(?,?,?,?,?)",
            (meeting_id, payload.title.strip(), meeting_date, "[]", payload.notes.strip()),
        )
        for item in suggestions:
            connection.execute(
                """INSERT INTO memories(id,kind,text,owner,meeting_id,meeting_date,source,entities,approved,status)
                   VALUES(?,?,?,?,?,?,?,?,0,'open')""",
                (str(uuid.uuid4()), item["kind"], item["text"], item["owner"], meeting_id, meeting_date, item["source"], json.dumps(item["entities"])),
            )
    return {"id": meeting_id, "suggestions": len(suggestions)}


@app.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, payload: MemoryUpdate) -> dict[str, Any]:
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No changes supplied")
    if "text" in fields and fields["text"] is None:
        del fields["text"]
    if "owner" in fields and fields["owner"] is None:
        del fields["owner"]
    if "approved" in fields and fields["approved"] is not None:
        fields["approved"] = int(fields["approved"])
    if not fields:
        raise HTTPException(status_code=400, detail="No changes supplied")
    with db() as connection:
        exists = connection.execute("SELECT id FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Saved item not found")
        assignments = ", ".join(f"{key}=?" for key in fields)
        connection.execute(f"UPDATE memories SET {assignments} WHERE id=?", [*fields.values(), memory_id])
        row = connection.execute("SELECT m.*, g.title AS meeting_title FROM memories m JOIN meetings g ON g.id=m.meeting_id WHERE m.id=?", (memory_id,)).fetchone()
    return json_row(row)


@app.delete("/api/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: str) -> None:
    with db() as connection:
        cursor = connection.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved item not found")


@app.post("/api/query")
def query(payload: QueryInput) -> dict[str, Any]:
    items = get_memories(approved_only=True)
    ranked = rank_memories(payload.question, items)
    if not ranked:
        return {"kind": "empty", "answer": "I couldn't find that in the saved meeting notes.", "citations": []}
    if is_change_question(payload.question):
        pair = decision_pair(items)
        if pair:
            old, current = pair
            return {
                "kind": "change",
                "answer": f"Earlier, the team decided to {old['text'][0].lower() + old['text'][1:]}. Now, they plan to {current['text'][0].lower() + current['text'][1:]}",
                "citations": [old, current],
            }
    score, item = ranked[0]
    if score < 0.07:
        return {"kind": "empty", "answer": "I couldn't find that in the saved meeting notes.", "citations": []}
    answer = f"{item['owner']} is handling this: {item['text']}" if item["owner"] else item["text"]
    return {"kind": item["kind"], "answer": answer, "citations": [item]}


BENCHMARK = [
    {"id": "q1", "question": "Why was the class project demo postponed at first?", "expected": ["d1"]},
    {"id": "q2", "question": "What changed, and when is the class project demo now?", "expected": ["d1", "d7"]},
    {"id": "q3", "question": "Who prepared the demo slides?", "expected": ["a4"]},
    {"id": "q4", "question": "How many classmates will try searching their notes?", "expected": ["a2"]},
    {"id": "q5", "question": "What did the team decide about the class project app?", "expected": ["d3"]},
    {"id": "q6", "question": "Should the app search handwritten notes too?", "expected": ["q3"]},
]


@app.post("/api/evaluation/run")
def run_evaluation() -> dict[str, Any]:
    items = get_memories(approved_only=True)
    by_id = {item["id"]: item for item in items}
    results = []
    hits = 0
    citation_hits = 0
    for test in BENCHMARK:
        ranked = rank_memories(test["question"], items)
        if is_change_question(test["question"]):
            pair = decision_pair(items)
            found = list(pair) if pair else []
        else:
            found = [ranked[0][1]] if ranked else []
        expected = [by_id[memory_id] for memory_id in test["expected"] if memory_id in by_id]
        hit = bool(expected) and all(any(item["id"] == want["id"] for item in found) for want in expected)
        cited = hit and all(any(item["meeting_id"] == want["meeting_id"] for item in found) for want in expected)
        hits += int(hit)
        citation_hits += int(cited)
        if len(found) > 1:
            answer = f"Earlier: {found[0]['text']} Now: {found[-1]['text']}"
        else:
            answer = found[0]["text"] if found else "No saved item found."
        results.append({"id": test["id"], "question": test["question"], "expected": test["expected"], "found": [item["id"] for item in found], "answer": answer, "passed": hit, "source_found": cited})
    temporal = [test for test in BENCHMARK if len(test["expected"]) > 1]
    lineage_hits = sum(1 for test in temporal if all(memory_id in next((row["found"] for row in results if row["id"] == test["id"]), []) for memory_id in test["expected"]))
    latest_hits = 0
    latest_items = [item for item in items if not item.get("superseded_by")]
    for test in temporal:
        expected = [memory_id for memory_id in test["expected"] if memory_id in by_id]
        latest_ranked = rank_memories(test["question"], latest_items)
        latest_found = {item["id"] for _, item in latest_ranked}
        if expected and all(memory_id in latest_found for memory_id in expected):
            latest_hits += 1
    return {
        "total": len(BENCHMARK),
        "found": hits,
        "citation_found": citation_hits,
        "lineage": lineage_hits,
        "latest_only": latest_hits,
        "results": results,
    }


@app.get("/api/graph")
def graph() -> dict[str, Any]:
    items = get_memories(approved_only=True)
    people = sorted({item["owner"] for item in items if item["owner"]})
    topics = sorted({entity for item in items for entity in item["entities"]})
    return {"items": items, "people": people, "topics": topics}


# On Vercel, the same FastAPI application serves both the React build and /api.
# In local development, Vite serves the UI and proxies /api to this app instead.
WEB_DIST = PROJECT_ROOT / "web" / "dist"
if WEB_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
