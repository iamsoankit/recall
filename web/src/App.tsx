import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';

type Page = 'home' | 'meetings' | 'connections' | 'checks';
type Kind = 'decision' | 'action' | 'open';

type Meeting = {
  id: string;
  title: string;
  meeting_date: string;
  attendees: string[];
  notes: string;
  memory_count: number;
  saved_count: number;
};

type Memory = {
  id: string;
  kind: Kind;
  text: string;
  owner: string;
  meeting_id: string;
  meeting_date: string;
  meeting_title: string;
  source: string;
  entities: string[];
  approved: boolean;
  status: string;
  supersedes?: string | null;
  superseded_by?: string | null;
  change_reason?: string | null;
};

type Answer = { kind: string; answer: string; citations: Memory[] };
type EvalResult = {
  total: number;
  found: number;
  citation_found: number;
  lineage: number;
  latest_only: number;
  results: Array<{ id: string; question: string; expected: string[]; found: string[]; answer: string; passed: boolean; source_found: boolean }>;
};

const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
};

const questions = [
  { label: 'Why did the demo move?', query: 'What changed, and when is the class project demo now?' },
  { label: 'Who has the slides?', query: 'Who prepared the demo slides?' },
  { label: 'What is still undecided?', query: 'Should the app search handwritten notes too?' },
  { label: 'What app are they making?', query: 'What did the team decide about the class project app?' },
];

const kindName: Record<Kind, string> = { decision: 'Decision', action: 'Task', open: 'Question' };

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(`${value}T12:00:00`));
}

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [selectedMeeting, setSelectedMeeting] = useState('');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const [editing, setEditing] = useState<Memory | null>(null);
  const [evaluation, setEvaluation] = useState<EvalResult | null>(null);
  const [selectedGraphItem, setSelectedGraphItem] = useState<Memory | null>(null);

  const refresh = async () => {
    const [nextMeetings, nextMemories] = await Promise.all([
      api<Meeting[]>('/meetings'),
      api<Memory[]>('/memories'),
    ]);
    setMeetings(nextMeetings);
    setMemories(nextMemories);
    setSelectedMeeting((current) => current || nextMeetings[0]?.id || '');
  };

  useEffect(() => {
    refresh().catch((reason: Error) => setError(reason.message)).finally(() => setLoading(false));
  }, []);

  const selectedMeetingData = useMemo(
    () => meetings.find((meeting) => meeting.id === selectedMeeting),
    [meetings, selectedMeeting],
  );
  const selectedMemories = useMemo(
    () => memories.filter((memory) => memory.meeting_id === selectedMeeting),
    [memories, selectedMeeting],
  );
  const approvedMemories = useMemo(() => memories.filter((memory) => memory.approved), [memories]);
  const recentMemories = useMemo(
    () => [...approvedMemories].sort((a, b) => b.meeting_date.localeCompare(a.meeting_date)).slice(0, 3),
    [approvedMemories],
  );

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(''), 2400);
  };

  const ask = async (value: string) => {
    setQuestion(value);
    setAnswer(null);
    try {
      setAnswer(await api<Answer>('/query', { method: 'POST', body: JSON.stringify({ question: value }) }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not search meeting notes.');
    }
  };

  const toggleMemory = async (memory: Memory) => {
    try {
      await api(`/memories/${memory.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ approved: !memory.approved }),
      });
      await refresh();
      notify(memory.approved ? 'Removed from saved notes.' : 'Saved for the team.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update the item.');
    }
  };

  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    const form = new FormData(event.currentTarget);
    try {
      await api(`/memories/${editing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ text: form.get('text'), owner: form.get('owner') }),
      });
      setEditing(null);
      await refresh();
      notify('Saved correction.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the correction.');
    }
  };

  const addMeeting = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api<{ id: string; suggestions: number }>('/meetings', {
        method: 'POST',
        body: JSON.stringify({
          title: form.get('title'),
          meeting_date: form.get('meeting_date') || undefined,
          notes: form.get('notes'),
        }),
      });
      setShowMeetingForm(false);
      await refresh();
      setSelectedMeeting(result.id);
      setPage('meetings');
      notify(`Found ${result.suggestions} items to check.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not add the meeting.');
    }
  };

  const openCitation = (memory: Memory) => {
    setSelectedMeeting(memory.meeting_id);
    setPage('meetings');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const runCheck = async () => {
    try {
      setEvaluation(await api<EvalResult>('/evaluation/run', { method: 'POST' }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not run the check.');
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setPage('home')} aria-label="Recall home">
          <span className="brand-mark">✳</span>
          <span className="brand-name">recall<small>TEAM NOTES</small></span>
        </button>
        <nav aria-label="Main navigation">
          {([['home', 'Overview'], ['meetings', 'Meetings'], ['connections', 'Connections'], ['checks', 'Checks']] as const).map(([key, label], index) => (
            <button key={key} className={`nav-button ${page === key ? 'active' : ''}`} onClick={() => setPage(key)}>
              <small>0{index + 1}</small>{label}{key === 'meetings' && <i>{meetings.length}</i>}
            </button>
          ))}
        </nav>
        <div className="demo-label"><span /> SAMPLE / CLASS PROJECT</div>
        <div className="avatar">AK</div>
      </header>

      <main>
        {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label="Dismiss">×</button></div>}
        {loading ? <div className="loading-state">Opening the sample notes…</div> : (
          <>
            {page === 'home' && <>
              <section className="hero">
                <div className="hero-copy">
                  <div className="eyebrow"><span /> KEEP IMPORTANT TEAM DECISIONS · SAMPLE</div>
                  <h1>Remember what<br />your team <em>decided.</em></h1>
                  <p>Keep meeting notes, decisions, and follow-ups in one place.</p>
                  <button className="button dark" onClick={() => setShowMeetingForm(true)}>＋ Add meeting notes</button>
                </div>
                <div className="hero-note"><small>CLASS PROJECT</small><strong>Demo<br />Saturday</strong><span>SAMPLE TEAM</span></div>
              </section>

              <section className="ask-card">
                <div className="ask-heading"><span className="arrow-mark">↳</span><div><h2>Find something from a meeting.</h2><p>Ask a question, then open the note behind the answer.</p></div><small>SAVED IN THIS BROWSER</small></div>
                <form className="ask-form" onSubmit={(event) => { event.preventDefault(); if (question.trim()) void ask(question.trim()); }}>
                  <label htmlFor="question">ASK<br />01</label>
                  <input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Why was the class project demo postponed?" />
                  <button className="button lime" type="submit">Find an answer ↗</button>
                </form>
                <div className="question-options"><span>CLICK A QUESTION TO TRY IT</span>{questions.map((item) => <button key={item.label} onClick={() => void ask(item.query)}>{item.label} <b>↗</b></button>)}</div>
                {answer && <div className="answer-panel">
                  <small>{answer.kind === 'change' ? 'WHAT CHANGED · TWO MEETINGS' : answer.kind === 'empty' ? 'NO MATCHING NOTE' : 'FROM MEETING NOTES'}</small>
                  <p>{answer.answer}</p>
                  <div className="citations">{answer.citations.map((memory) => <button key={memory.id} onClick={() => openCitation(memory)}>↗ {memory.meeting_title} · {formatDate(memory.meeting_date)}</button>)}<span>Was this helpful?</span><button className="feedback" onClick={() => notify('Thanks for the feedback.')}>↑</button><button className="feedback" onClick={() => notify('Thanks, we’ll review this answer.')}>↓</button></div>
                </div>}
              </section>

              <section className="section-heading"><div><small>01 — NOTES TO KEEP</small><h2>Decisions & follow-ups.</h2><p>Things the team agreed to or still needs to do.</p></div><button className="text-link" onClick={() => setPage('connections')}>See how they connect ↗</button></section>
              <div className="memory-grid">{recentMemories.map((memory, index) => <MemoryCard key={memory.id} memory={memory} index={index} onSource={() => openCitation(memory)} />)}</div>
              <section className="section-heading"><div><small>02 — MEETING NOTES</small><h2>Recent meetings.</h2><p>Open a meeting to see its notes and saved decisions.</p></div><button className="text-link" onClick={() => setPage('meetings')}>See all meetings ↗</button></section>
              <div className="meeting-list">{meetings.slice(0, 3).map((meeting) => <MeetingRow key={meeting.id} meeting={meeting} onClick={() => { setSelectedMeeting(meeting.id); setPage('meetings'); }} />)}</div>
            </>}

            {page === 'meetings' && <>
              <PageHeading eyebrow="YOUR MEETING NOTES" title="Meetings" subtitle="Check what Recall picked out before saving it." action={<button className="button dark" onClick={() => setShowMeetingForm(true)}>＋ Add meeting notes</button>} />
              <div className="meeting-layout">
                <div className="meeting-list full-list">{meetings.map((meeting) => <MeetingRow key={meeting.id} meeting={meeting} selected={meeting.id === selectedMeeting} onClick={() => setSelectedMeeting(meeting.id)} />)}</div>
                {selectedMeetingData ? <section className="meeting-detail">
                  <div className="detail-head"><div><h2>{selectedMeetingData.title}</h2><p>{formatDate(selectedMeetingData.meeting_date)} · {selectedMeetingData.attendees.length} participants</p></div><span className="reviewed">{selectedMemories.every((item) => item.approved) ? '✓ REVIEWED' : `${selectedMemories.length - selectedMemories.filter((item) => item.approved).length} TO CHECK`}</span></div>
                  <div className="detail-label"><b>Suggestions</b><span>{selectedMemories.filter((item) => item.approved).length} of {selectedMemories.length} saved</span></div>
                  {selectedMemories.map((memory) => <MemoryReview key={memory.id} memory={memory} onToggle={() => void toggleMemory(memory)} onEdit={() => setEditing(memory)} />)}
                  <div className="detail-label"><b>Meeting notes</b><span>Original</span></div><blockquote>{selectedMeetingData.notes}</blockquote>
                </section> : <EmptyState title="No meetings yet" text="Add meeting notes to get started." />}
              </div>
            </>}

            {page === 'connections' && <>
              <PageHeading eyebrow="HOW NOTES CONNECT" title="Connections" subtitle="See which people, notes, and decisions belong together." />
              <div className="graph-layout">
                <section className="graph-card">
                  <div className="graph-head"><div><b>Class notes app</b><small>Click a circle to see the note behind it</small></div><span>● decision　● person　● topic</span></div>
                  <svg className="memory-graph" viewBox="0 0 100 100" role="img" aria-label="Connections between the class app, people, and decisions">
                    <line x1="50" y1="49" x2="25" y2="23" /><line x1="50" y1="49" x2="74" y2="22" /><line x1="50" y1="49" x2="26" y2="76" /><line x1="50" y1="49" x2="74" y2="76" />
                    <circle className="topic-node" cx="50" cy="49" r="10" /><text x="50" y="51">Notes app</text>
                    {approvedMemories.slice(0, 4).map((memory, index) => {
                      const places = [[25, 23], [74, 22], [26, 76], [74, 76]];
                      const [x, y] = places[index];
                      return <g key={memory.id} className="memory-node" onClick={() => setSelectedGraphItem(memory)} tabIndex={0} role="button" aria-label={`Inspect ${memory.text}`}><circle className={memory.kind === 'action' ? 'person-node' : 'decision-node'} cx={x} cy={y} r="4.5" /><text x={x} y={y + 10}>{memory.kind === 'action' ? memory.owner.split(' ')[0] || 'Task' : memory.superseded_by ? 'Earlier choice' : memory.supersedes ? 'New choice' : kindName[memory.kind]}</text></g>;
                    })}
                  </svg>
                </section>
                <aside className="node-inspector"><small>{selectedGraphItem ? kindName[selectedGraphItem.kind].toUpperCase() : 'SAMPLE PROJECT'}</small><h2>{selectedGraphItem ? selectedGraphItem.text : 'Class notes app'}</h2><p>{selectedGraphItem ? selectedGraphItem.source : 'A student team is making a simple app to save and find class notes.'}</p>{selectedGraphItem && <button className="text-link" onClick={() => openCitation(selectedGraphItem)}>Open meeting note ↗</button>}</aside>
              </div>
              <section className="section-heading"><div><small>WHAT CHANGED</small><h2>Decision history.</h2><p>See the earlier choice and what changed later.</p></div></section>
              <div className="history-card"><article><small>NOV 8 · EARLIER</small><b>Postpone the demo until sign-in works on phones.</b><button onClick={() => openCitation(memories.find((item) => item.id === 'd1')!)}>Read Nov 8 notes ↗</button></article><span className="history-arrow">→<small>APP FIXED</small></span><article className="current"><small>NOV 10 · NOW</small><b>Hold the class project demo on Saturday.</b><button onClick={() => openCitation(memories.find((item) => item.id === 'd7')!)}>Read Nov 10 notes ↗</button></article></div>
            </>}

            {page === 'checks' && <>
              <PageHeading eyebrow="TRY SIX SAMPLE QUESTIONS" title="Check Recall" subtitle="See if Recall finds the right answer and the meeting it came from." action={<button className="button lime" onClick={() => void runCheck()}>Run check ↗</button>} />
              <div className="check-summary"><div><small>QUICK CHECK</small><h2>Six questions. Clear sources.</h2><p>This sample check looks for a note, its source, and earlier choices when a plan changes.</p></div><div className="score"><b>{evaluation ? `${Math.round((evaluation.found / evaluation.total) * 100)}%` : '—'}</b><small>RIGHT ANSWERS</small></div><div className="score"><b>{evaluation ? `${Math.round((evaluation.citation_found / evaluation.total) * 100)}%` : '—'}</b><small>SOURCES FOUND</small></div></div>
              <div className="evaluation-list">{evaluation ? evaluation.results.map((result, index) => <article key={result.id} className="evaluation-row"><small>{String(index + 1).padStart(2, '0')}</small><div><b>{result.question}</b><p>Recall found: {result.answer}</p></div><span className={result.passed && result.source_found ? 'pass' : 'miss'}>{result.passed && result.source_found ? 'FOUND · SOURCE' : 'NOT FOUND'}</span></article>) : <EmptyState title="Run the check" text="Recall will try six sample questions and show what it found." />}</div>
              {evaluation && <div className="compare-card"><div><small>COMPARE TWO VIEWS</small><h2>Does keeping the old choice help?</h2><p>Compare answers that include both decisions with answers that show only the newest one.</p></div><div><b>{evaluation.lineage}/1</b><small>OLD + NEW CHOICES</small></div><div><b>{evaluation.latest_only}/1</b><small>NEWEST ONLY</small></div></div>}
              <p className="fine-print">These sample questions are for checking the demo. They are not results from a user study.</p>
            </>}
          </>
        )}
      </main>

      <footer><span>RECALL · A TEAM NOTES APP</span><span>NOTES STAY IN YOUR LOCAL SQLITE DATABASE</span></footer>
      {toast && <div className="toast" role="status">{toast}</div>}
      {showMeetingForm && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowMeetingForm(false); }}><form className="modal" onSubmit={addMeeting}>
        <div className="modal-heading"><div><small>ADD MEETING NOTES</small><h2>Add a meeting</h2><p>Recall will pick out decisions, tasks, and questions for you to check.</p></div><button type="button" className="close" onClick={() => setShowMeetingForm(false)} aria-label="Close">×</button></div>
        <label>Meeting title<input name="title" required placeholder="e.g. Class project demo planning" /></label>
        <label>Date<input name="meeting_date" type="date" /></label>
        <label>Notes<textarea name="notes" required minLength={10} rows={6} placeholder="We decided to move the demo to Saturday. Arjun will prepare the slides. Open question: should we show it live?" /></label>
        <div className="modal-actions"><button type="button" className="button outline" onClick={() => setShowMeetingForm(false)}>Cancel</button><button className="button dark">Find items & review →</button></div>
      </form></div>}
      {editing && <div className="modal-backdrop" role="presentation"><form className="modal" onSubmit={saveEdit}>
        <div className="modal-heading"><div><small>EDIT SAVED ITEM</small><h2>Correct this item</h2><p>Your change will update future answers.</p></div><button type="button" className="close" onClick={() => setEditing(null)} aria-label="Close">×</button></div>
        <label>Text<textarea name="text" required rows={4} defaultValue={editing.text} /></label><label>Who is doing it? <span>(optional)</span><input name="owner" defaultValue={editing.owner} /></label>
        <div className="modal-actions"><button type="button" className="button outline" onClick={() => setEditing(null)}>Cancel</button><button className="button dark">Save changes →</button></div>
      </form></div>}
    </div>
  );
}

function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <section className="page-heading"><div><div className="eyebrow"><span />{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</section>;
}

function MeetingRow({ meeting, selected = false, onClick }: { meeting: Meeting; selected?: boolean; onClick: () => void }) {
  return <button className={`meeting-row ${selected ? 'selected' : ''}`} onClick={onClick}><span className="meeting-date"><b>{formatDate(meeting.meeting_date).split(' ')[1]}</b><small>{formatDate(meeting.meeting_date).split(' ')[0].toUpperCase()}</small></span><span className="meeting-info"><b>{meeting.title}</b><small>{meeting.attendees.join(', ') || 'Your meeting'}</small></span><span className="meeting-count">{meeting.saved_count}/{meeting.memory_count} saved</span><span className="chevron">›</span></button>;
}

function MemoryCard({ memory, index, onSource }: { memory: Memory; index: number; onSource: () => void }) {
  return <article className={`memory-card card-${index}`}><small>{kindName[memory.kind]}</small><p>{memory.text}</p><div><span>{memory.meeting_title}</span><button onClick={onSource}>Source ↗</button></div></article>;
}

function MemoryReview({ memory, onToggle, onEdit }: { memory: Memory; onToggle: () => void; onEdit: () => void }) {
  return <article className="review-card"><div className="review-card-top"><small>{kindName[memory.kind]}{memory.owner && ` · ${memory.owner}`}</small><div><button onClick={onEdit}>Edit</button><button onClick={onToggle}>{memory.approved ? 'Remove' : 'Save'}</button></div></div><p>{memory.text}</p><blockquote>“{memory.source}”</blockquote></article>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><b>{title}</b><p>{text}</p></div>;
}
