import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Decision, Scores, Status, isDecisionList, optionScore } from './decision';
const initialDecisions: Decision[] = [
  {
    id: 1, title: 'Consolidate customer support tools', summary: 'Replace three overlapping tools with one shared customer operations platform.', owner: 'Maya Chen', team: 'Operations', status: 'Review', due: 'Oct 4', comments: 18, reviewers: 7,
    evidence: ['Q3 support cost analysis', 'Agent workflow interviews', 'Vendor security review'],
    options: [
      { name: 'Move to PlainDesk', note: 'Best automation and migration support.', scores: { impact: 92, confidence: 84, feasibility: 76 } },
      { name: 'Keep current stack', note: 'Lowest disruption, continued tool overlap.', scores: { impact: 48, confidence: 94, feasibility: 90 } },
      { name: 'Build internally', note: 'Maximum control with a long delivery window.', scores: { impact: 81, confidence: 52, feasibility: 38 } },
    ],
  },
  {
    id: 2, title: 'Launch in the Nordic market', summary: 'Compare a direct launch against a local distribution partnership.', owner: 'Jordan Lee', team: 'Growth', status: 'Draft', due: 'Oct 12', comments: 9, reviewers: 3,
    evidence: ['Market sizing brief', 'Localization estimate'],
    options: [
      { name: 'Local partner', note: 'Faster entry with lower operating risk.', scores: { impact: 82, confidence: 76, feasibility: 88 } },
      { name: 'Direct launch', note: 'More upside, higher cost and uncertainty.', scores: { impact: 94, confidence: 58, feasibility: 51 } },
    ],
  },
  {
    id: 3, title: 'Adopt a four-day focus week', summary: 'Run a six-week pilot with one meeting-free day across the organization.', owner: 'Sam Rivera', team: 'People', status: 'Review', due: 'Oct 7', comments: 24, reviewers: 12,
    evidence: ['Engagement survey', 'Delivery baseline', 'Pilot risk assessment'],
    options: [
      { name: 'Six-week pilot', note: 'Measure impact before a permanent policy.', scores: { impact: 78, confidence: 81, feasibility: 87 } },
      { name: 'No policy change', note: 'Keep team-level scheduling autonomy.', scores: { impact: 51, confidence: 88, feasibility: 96 } },
    ],
  },
  {
    id: 4, title: 'Open-source the analytics SDK', summary: 'Publish the core client library to improve trust and integration velocity.', owner: 'Alex Morgan', team: 'Product', status: 'Approved', due: 'Sep 28', comments: 31, reviewers: 9,
    evidence: ['Developer survey', 'License review', 'Maintenance forecast'],
    options: [
      { name: 'Apache-2.0 release', note: 'Permissive adoption with patent protection.', scores: { impact: 94, confidence: 88, feasibility: 81 } },
      { name: 'Keep it private', note: 'No community maintenance overhead.', scores: { impact: 42, confidence: 91, feasibility: 97 } },
    ],
  },
];

const bestOption = (decision: Decision) => [...decision.options].sort((a, b) => optionScore(b.scores) - optionScore(a.scores))[0];
const initials = (name: string) => name.split(' ').map(part => part[0]).join('');

function App() {
  const [decisions, setDecisions] = useState<Decision[]>(() => {
    try { const saved = JSON.parse(localStorage.getItem('compass-decisions') || 'null'); return isDecisionList(saved) ? saved : initialDecisions; }
    catch { return initialDecisions; }
  });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'All' | Status>('All');
  const [query, setQuery] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [newEvidence, setNewEvidence] = useState('');
  const [notice, setNotice] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const selected = decisions.find(decision => decision.id === selectedId);

  useEffect(() => localStorage.setItem('compass-decisions', JSON.stringify(decisions)), [decisions]);
  useEffect(() => {
    const shortcuts = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setShowForm(false); setSelectedId(null); }
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); searchRef.current?.focus(); }
    };
    window.addEventListener('keydown', shortcuts);
    return () => window.removeEventListener('keydown', shortcuts);
  }, []);

  const visible = useMemo(() => decisions.filter(decision =>
    (filter === 'All' || decision.status === filter) &&
    `${decision.title} ${decision.summary} ${decision.team}`.toLowerCase().includes(query.toLowerCase())
  ), [decisions, filter, query]);

  const addDecision = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const created: Decision = {
      id: Date.now(), title: String(data.get('title')), summary: String(data.get('summary')),
      owner: 'You', team: String(data.get('team')), status: 'Draft', due: String(data.get('due') || 'Not set'), comments: 0, reviewers: 1, evidence: [],
      options: [
        { name: String(data.get('optionA')), note: 'Add supporting evidence and refine this option.', scores: { impact: 70, confidence: 60, feasibility: 70 } },
        { name: String(data.get('optionB')), note: 'Add supporting evidence and refine this option.', scores: { impact: 65, confidence: 60, feasibility: 75 } },
      ],
    };
    setDecisions(items => [created, ...items]);
    setShowForm(false);
    setSelectedId(created.id);
  };

  const setStatus = (id: number, status: Status) => setDecisions(items => items.map(item => item.id === id ? { ...item, status } : item));
  const updateScore = (id: number, optionIndex: number, key: keyof Scores, value: number) => setDecisions(items => items.map(item => item.id === id ? {
    ...item,
    options: item.options.map((option, index) => index === optionIndex ? { ...option, scores: { ...option.scores, [key]: value } } : option),
  } : item));
  const addEvidence = (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !newEvidence.trim()) return;
    setDecisions(items => items.map(item => item.id === selected.id ? { ...item, evidence: [...item.evidence, newEvidence.trim()] } : item));
    setNewEvidence('');
  };
  const exportDecisions = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(decisions, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `compass-decisions-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setNotice('Workspace exported.');
  };
  const importDecisions = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const imported: unknown = JSON.parse(await file.text());
      if (!isDecisionList(imported)) throw new Error('Invalid Compass file');
      setDecisions(imported);
      setSelectedId(null);
      setNotice(`${imported.length} decisions imported.`);
    } catch {
      setNotice('Import failed. Choose a valid Compass JSON export.');
    }
    event.target.value = '';
  };

  const reviewCount = decisions.filter(decision => decision.status === 'Review').length;
  const evidenceCount = decisions.reduce((total, decision) => total + decision.evidence.length, 0);
  const today = new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date()).toUpperCase();

  return <div className="shell">
    <aside>
      <a className="brand" href="#top"><span><img src="/compass-logo.png" alt="" /></span>Compass</a>
      <p className="nav-label">Workspace</p>
      <nav aria-label="Main navigation">
        <button className={filter === 'All' ? 'active' : ''} onClick={() => setFilter('All')}><span>▦</span><b>All decisions</b><i>{decisions.length}</i></button>
        <button className={filter === 'Review' ? 'active' : ''} onClick={() => setFilter('Review')}><span>◇</span><b>Needs review</b><i>{reviewCount}</i></button>
        <button className={filter === 'Approved' ? 'active' : ''} onClick={() => setFilter('Approved')}><span>✓</span><b>Approved</b></button>
      </nav>
      <p className="nav-label data-label">Your data</p>
      <nav aria-label="Data tools">
        <button onClick={exportDecisions}><span>↓</span><b>Export workspace</b></button>
        <button onClick={() => importRef.current?.click()}><span>↑</span><b>Import workspace</b></button>
      </nav>
      <input ref={importRef} className="visually-hidden" type="file" accept="application/json,.json" onChange={importDecisions} />
      <div className="upgrade"><span>OPEN SOURCE</span><strong>Shape Compass with us</strong><p>Share feedback, report issues, or contribute a workflow.</p><button onClick={() => window.open('https://github.com/Anudeepsrib/Decision-Support-System', '_blank', 'noopener')}>View on GitHub ↗</button></div>
      <div className="aside-bottom"><div className="workspace"><i>AC</i><span><strong>Acme Collective</strong><small>128 members</small></span><b>⌄</b></div><div className="profile"><i>MR</i><span><strong>Morgan Reed</strong><small>Workspace admin</small></span></div></div>
    </aside>

    <main id="top">
      <header><span className="mobile-logo"><img src="/compass-logo.png" alt="Compass" /></span><label className="search"><span>⌕</span><input ref={searchRef} value={query} onChange={event => setQuery(event.target.value)} placeholder="Search decisions, teams, owners..." /><kbd>Ctrl K</kbd></label><div><button className="secondary header-export" onClick={exportDecisions}>Export</button><button className="primary" onClick={() => setShowForm(true)}>＋ New decision</button></div></header>
      <div className="content">
        <section className="welcome"><div><p className="eyebrow">{today}</p><h1>Make the next decision clear.</h1><p>{reviewCount ? `${reviewCount} ${reviewCount === 1 ? 'decision needs' : 'decisions need'} review.` : 'Your review queue is clear.'}</p></div>{reviewCount > 0 && <button className="secondary" onClick={() => { setFilter('Review'); document.getElementById('decisions')?.scrollIntoView({ behavior: 'smooth' }); }}>Review now <span>→</span></button>}</section>

        <section className="summary-grid">
          <article className="attention"><div><span className="summary-icon">!</span><p><strong>{reviewCount} {reviewCount === 1 ? 'review' : 'reviews'} waiting</strong><small>{reviewCount ? 'Keep decisions moving' : 'Nothing is blocked'}</small></p></div>{reviewCount > 0 && <button onClick={() => setFilter('Review')}>Review now →</button>}</article>
          <article><span>Active decisions</span><strong>{decisions.filter(d => d.status !== 'Approved').length}</strong><small>Drafts and reviews</small></article>
          <article><span>Evidence sources</span><strong>{evidenceCount}</strong><small>Across the workspace</small></article>
          <article><span>Approved</span><strong>{decisions.filter(d => d.status === 'Approved').length}</strong><small>Recorded outcomes</small></article>
        </section>

        <section className="decision-list" id="decisions">
          <div className="section-head"><div><h2>Decision inbox</h2><p>Compare the options, review the evidence, make the call.</p></div><div className="view-tools"><div className="filters">{(['All','Draft','Review','Approved'] as const).map(item => <button key={item} className={filter === item ? 'selected' : ''} onClick={() => setFilter(item)}>{item}</button>)}</div><span className="sort">↕ Updated</span></div></div>
          <div className="decision-table">
            <div className="table-head"><span>Decision</span><span>Recommendation</span><span>Readiness</span><span>Owner</span><span></span></div>
            {visible.map(decision => {
              const recommendation = bestOption(decision);
              return <button className="decision-row" key={decision.id} onClick={() => setSelectedId(decision.id)}>
                <span className="decision-name"><i className={`status-dot ${decision.status.toLowerCase()}`} /><span><strong>{decision.title}</strong><small>{decision.team} · Due {decision.due}</small></span></span>
                <span className="recommendation"><strong>{recommendation.name}</strong><small>{decision.options.length} options compared</small></span>
                <span className="readiness"><span><i style={{width: `${optionScore(recommendation.scores)}%`}} /></span><b>{optionScore(recommendation.scores)}%</b></span>
                <span className="row-owner"><i>{initials(decision.owner)}</i><span><strong>{decision.owner}</strong><small>{decision.reviewers} reviewers</small></span></span>
                <span className="row-arrow">→</span>
              </button>;
            })}
            {!visible.length && <div className="empty"><b>No decisions found</b><span>Try another search or filter.</span></div>}
          </div>
        </section>
      </div>
    </main>

    {selected && <div className="drawer-backdrop" onMouseDown={() => setSelectedId(null)}><section className="drawer" role="dialog" aria-modal="true" aria-labelledby="decision-title" onMouseDown={event => event.stopPropagation()}>
      <div className="drawer-top"><span className={`status-pill ${selected.status.toLowerCase()}`}>{selected.status}</span><button className="close" onClick={() => setSelectedId(null)} aria-label="Close">×</button></div>
      <p className="breadcrumb">Decisions / {selected.team}</p><h2 id="decision-title">{selected.title}</h2><p className="drawer-summary">{selected.summary}</p>
      <div className="meta"><span><small>Owner</small><b>{selected.owner}</b></span><span><small>Due date</small><b>{selected.due}</b></span><span><small>Reviewers</small><b>{selected.reviewers} people</b></span></div>
      <div className="drawer-section"><div className="drawer-heading"><div><h3>Option comparison</h3><p>Score each path. Impact 40%, confidence 35%, feasibility 25%.</p></div><span className="scorecard-label">Editable scorecard</span></div>
        <div className="options">{selected.options.map((option, originalIndex) => ({ option, originalIndex })).sort((a,b) => optionScore(b.option.scores) - optionScore(a.option.scores)).map(({ option, originalIndex }, index) => <article className={index === 0 ? 'winner' : ''} key={`${option.name}-${originalIndex}`}><div className="option-head"><span><i>{index + 1}</i><strong>{option.name}</strong>{index === 0 && <em>Recommended</em>}</span><b>{optionScore(option.scores)}</b></div><p>{option.note}</p><div className="option-scores">{(Object.keys(option.scores) as (keyof Scores)[]).map(key => <label key={key}>{key}<input type="range" min="0" max="100" value={option.scores[key]} onChange={event => updateScore(selected.id, originalIndex, key, Number(event.target.value))} aria-label={`${option.name} ${key}`} /><b>{option.scores[key]}</b></label>)}</div></article>)}</div>
      </div>
      <div className="drawer-section evidence"><div className="drawer-heading"><div><h3>Evidence</h3><p>{selected.evidence.length} sources attached to this decision.</p></div></div>{selected.evidence.length ? <ul>{selected.evidence.map((item, index) => <li key={`${item}-${index}`}><span>▤</span><div><strong>{item}</strong><small>Added by {index ? selected.owner : 'You'} · Verified</small></div><b>✓</b></li>)}</ul> : <div className="evidence-empty">No evidence yet. Add a source before review.</div>}<form className="evidence-form" onSubmit={addEvidence}><input value={newEvidence} onChange={event => setNewEvidence(event.target.value)} placeholder="Paste a link or name a source…" aria-label="New evidence source" /><button className="secondary">＋ Add source</button></form></div>
      <footer className="drawer-actions"><span><b>{selected.comments}</b> comments in the discussion</span>{selected.status === 'Draft' && <button className="primary" onClick={() => setStatus(selected.id, 'Review')}>Send for review</button>}{selected.status === 'Review' && <button className="primary" onClick={() => setStatus(selected.id, 'Approved')}>Approve recommendation</button>}{selected.status === 'Approved' && <button className="secondary" onClick={() => setStatus(selected.id, 'Review')}>Reopen decision</button>}</footer>
    </section></div>}

    {showForm && <div className="modal-backdrop" onMouseDown={() => setShowForm(false)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={event => event.stopPropagation()}><button className="close" onClick={() => setShowForm(false)} aria-label="Close">×</button><p className="eyebrow">NEW DECISION</p><h2 id="modal-title">Frame the choice</h2><p>Start with a clear question and at least two viable options.</p><form onSubmit={addDecision}><label className="wide">Decision title<input name="title" minLength={6} required placeholder="What are we deciding?" /></label><label>Team<select name="team"><option>Product</option><option>Operations</option><option>People</option><option>Growth</option><option>Finance</option></select></label><label>Decision date<input name="due" type="date" required /></label><label className="wide">Context<textarea name="summary" minLength={20} required rows={3} placeholder="What prompted this decision, and what does success look like?" /></label><label>Option A<input name="optionA" required placeholder="First viable path" /></label><label>Option B<input name="optionB" required placeholder="Alternative path" /></label><div className="form-actions"><button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button><button className="primary">Create decision</button></div></form></section></div>}
    {notice && <button className="notice" aria-live="polite" onClick={() => setNotice('')}>{notice}<span>×</span></button>}
  </div>;
}

export default App;
