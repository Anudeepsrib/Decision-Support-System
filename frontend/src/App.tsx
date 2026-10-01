import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Criterion, Decision, Scores, Status, decisionToMarkdown, evaluationProgress, leadingOption, optionScore, parseDecisions, scoreLabel, templates } from './decision';
import { JevAssessment, WorkspaceConnection, createSharedWorkspace, pullSharedWorkspace, pushSharedWorkspace, reviewWithJev } from './sync';

const STORAGE_KEY = 'compass-decisions-v2';
const SYNC_KEY = 'compass-shared-workspace-v1';
const githubUrl = 'https://github.com/Anudeepsrib/Compass';
const initials = (name: string) => name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase();
const today = () => new Date().toISOString().slice(0, 10);
const formatDate = (value: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value || 'Not set';
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`));
};
const makeScores = (criteria: Criterion[], values: number[]): Scores => Object.fromEntries(criteria.map((item, index) => [item.id, values[index] ?? null]));
const blankScores = (criteria: Criterion[]): Scores => Object.fromEntries(criteria.map(item => [item.id, null]));
const isLink = (value: string) => { try { return ['http:', 'https:'].includes(new URL(value).protocol); } catch { return false; } };
const savedConnection = (): WorkspaceConnection | null => {
  try {
    const value = JSON.parse(localStorage.getItem(SYNC_KEY) || 'null');
    return value && typeof value.id === 'string' && typeof value.name === 'string' && typeof value.token === 'string' && typeof value.revision === 'number' ? value : null;
  } catch { return null; }
};

const sampleWorkspace = (): Decision[] => {
  const now = new Date().toISOString();
  const build = templates.find(item => item.id === 'build-buy')!;
  const vendor = templates.find(item => item.id === 'vendor')!;
  return [
    {
      id: Date.now(), title: 'Choose a customer support platform', summary: 'Replace overlapping tools with one maintainable support platform before the next renewal.', owner: 'Avery', team: 'Operations', status: 'Review', due: today(), criteria: vendor.criteria,
      evidence: ['https://example.com/security-review', 'Support team workflow notes'],
      options: [
        { name: 'PlainDesk', note: 'Strong automation and migration support.', scores: makeScores(vendor.criteria, [5, 4, 5, 3, 4]) },
        { name: 'Current stack', note: 'Lowest migration effort, but overlap remains.', scores: makeScores(vendor.criteria, [3, 4, 2, 4, 3]) },
      ], createdAt: now, updatedAt: now,
    },
    {
      id: Date.now() + 1, title: 'Build or buy analytics infrastructure', summary: 'Decide whether the next analytics platform should be built internally or purchased.', owner: 'Jordan', team: 'Product', status: 'Decided', due: today(), criteria: build.criteria,
      evidence: ['Engineering capacity plan', 'Three-year cost model'],
      options: [
        { name: 'Buy and integrate', note: 'Faster delivery with vendor dependency.', scores: makeScores(build.criteria, [4, 3, 5, 2]) },
        { name: 'Build internally', note: 'More control with a longer delivery window.', scores: makeScores(build.criteria, [5, 2, 2, 5]) },
      ], chosenOption: 'Buy and integrate', rationale: 'Time to value matters more than full control this year. We will review vendor dependency after six months.', reviewDate: today(), createdAt: now, updatedAt: now,
    },
  ];
};

function App() {
  const [decisions, setDecisions] = useState<Decision[]>(() => {
    for (const key of [STORAGE_KEY, 'compass-decisions']) {
      try { const parsed = parseDecisions(JSON.parse(localStorage.getItem(key) || 'null')); if (parsed) return parsed; } catch { /* try the next source */ }
    }
    return [];
  });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'All' | Status>('All');
  const [query, setQuery] = useState('');
  const [sortNewest, setSortNewest] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showRecord, setShowRecord] = useState(false);
  const [showSync, setShowSync] = useState(false);
  const [templateId, setTemplateId] = useState('blank');
  const [newEvidence, setNewEvidence] = useState('');
  const [notice, setNotice] = useState('');
  const [connection, setConnection] = useState<WorkspaceConnection | null>(savedConnection);
  const [jevAssessment, setJevAssessment] = useState<JevAssessment | null>(null);
  const [busy, setBusy] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const selected = decisions.find(decision => decision.id === selectedId);

  useEffect(() => localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions)), [decisions]);
  useEffect(() => connection ? localStorage.setItem(SYNC_KEY, JSON.stringify(connection)) : localStorage.removeItem(SYNC_KEY), [connection]);
  useEffect(() => setJevAssessment(null), [selectedId]);
  useEffect(() => {
    const shortcuts = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setShowForm(false); setShowRecord(false); setShowSync(false); setSelectedId(null); }
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); searchRef.current?.focus(); }
    };
    window.addEventListener('keydown', shortcuts);
    return () => window.removeEventListener('keydown', shortcuts);
  }, []);

  const visible = useMemo(() => decisions.filter(decision =>
    (filter === 'All' || decision.status === filter) &&
    `${decision.title} ${decision.summary} ${decision.team} ${decision.owner}`.toLowerCase().includes(query.trim().toLowerCase())
  ).sort((a, b) => (sortNewest ? -1 : 1) * a.updatedAt.localeCompare(b.updatedAt)), [decisions, filter, query, sortNewest]);

  const updateDecision = (id: number, change: (decision: Decision) => Decision) => setDecisions(items => items.map(item => item.id === id ? { ...change(item), updatedAt: new Date().toISOString() } : item));
  const openNew = (id = 'blank') => { setTemplateId(id); setShowForm(true); };

  const addDecision = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const template = templates.find(item => item.id === String(data.get('template'))) || templates[0];
    const timestamp = new Date().toISOString();
    const created: Decision = {
      id: Date.now(), title: String(data.get('title')).trim(), summary: String(data.get('summary')).trim(), owner: String(data.get('owner')).trim() || 'You', team: String(data.get('team')).trim() || 'General', status: 'Draft', due: String(data.get('due')), criteria: template.criteria.map(item => ({ ...item })), evidence: [],
      options: [String(data.get('optionA')).trim(), String(data.get('optionB')).trim()].map(name => ({ name, note: '', scores: blankScores(template.criteria) })), createdAt: timestamp, updatedAt: timestamp,
    };
    setDecisions(items => [created, ...items]);
    setShowForm(false);
    setSelectedId(created.id);
  };

  const setStatus = (id: number, status: Status) => updateDecision(id, decision => ({ ...decision, status }));
  const updateScore = (id: number, optionIndex: number, criterionId: string, value: number | null) => updateDecision(id, decision => ({ ...decision, options: decision.options.map((option, index) => index === optionIndex ? { ...option, scores: { ...option.scores, [criterionId]: value } } : option) }));
  const updateOption = (id: number, optionIndex: number, field: 'name' | 'note', value: string) => updateDecision(id, decision => ({ ...decision, options: decision.options.map((option, index) => index === optionIndex ? { ...option, [field]: value } : option) }));
  const addOption = (id: number) => updateDecision(id, decision => ({ ...decision, options: [...decision.options, { name: `Option ${decision.options.length + 1}`, note: '', scores: blankScores(decision.criteria) }] }));
  const removeOption = (id: number, optionIndex: number) => updateDecision(id, decision => ({ ...decision, options: decision.options.filter((_, index) => index !== optionIndex) }));
  const updateCriterion = (id: number, criterionId: string, field: 'name' | 'weight', value: string | number) => updateDecision(id, decision => ({ ...decision, criteria: decision.criteria.map(item => item.id === criterionId ? { ...item, [field]: value } : item) }));
  const addCriterion = (id: number) => updateDecision(id, decision => {
    const criterion = { id: `criterion-${Date.now()}`, name: 'New criterion', weight: 10 };
    return { ...decision, criteria: [...decision.criteria, criterion], options: decision.options.map(option => ({ ...option, scores: { ...option.scores, [criterion.id]: null } })) };
  });
  const removeCriterion = (id: number, criterionId: string) => updateDecision(id, decision => ({ ...decision, criteria: decision.criteria.filter(item => item.id !== criterionId), options: decision.options.map(option => { const scores = { ...option.scores }; delete scores[criterionId]; return { ...option, scores }; }) }));

  const addEvidence = (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !newEvidence.trim()) return;
    updateDecision(selected.id, decision => ({ ...decision, evidence: [...decision.evidence, newEvidence.trim()] }));
    setNewEvidence('');
  };

  const recordDecision = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    updateDecision(selected.id, decision => ({ ...decision, status: 'Decided', chosenOption: String(data.get('choice')), rationale: String(data.get('rationale')).trim(), reviewDate: String(data.get('reviewDate') || '') || undefined }));
    setShowRecord(false);
    setNotice('Decision recorded with its rationale.');
  };

  const download = (contents: string, filename: string, type: string) => {
    const url = URL.createObjectURL(new Blob([contents], { type }));
    const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
  };
  const exportWorkspace = () => { download(JSON.stringify(decisions, null, 2), `compass-workspace-${today()}.json`, 'application/json'); setNotice('Workspace exported.'); };
  const exportMarkdown = (decision: Decision) => { download(decisionToMarkdown(decision), `${decision.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.md`, 'text/markdown'); setNotice('Decision record exported.'); };
  const importDecisions = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    try { const imported = parseDecisions(JSON.parse(await file.text())); if (!imported) throw new Error(); setDecisions(imported); setSelectedId(null); setNotice(`${imported.length} decisions imported.`); }
    catch { setNotice('Import failed. Choose a valid Compass JSON export.'); }
    event.target.value = '';
  };

  const createShare = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy('create');
    try {
      const data = new FormData(event.currentTarget);
      setConnection(await createSharedWorkspace(String(data.get('name')).trim(), decisions));
      setNotice('Shared workspace created. Save its access token.');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not create the workspace.'); }
    finally { setBusy(''); }
  };
  const connectShare = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy('connect');
    try {
      const data = new FormData(event.currentTarget);
      const pulled = await pullSharedWorkspace(String(data.get('id')).trim(), String(data.get('token')).trim());
      setDecisions(pulled.decisions); setConnection(pulled.connection); setSelectedId(null); setNotice('Shared workspace connected.');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not connect.'); }
    finally { setBusy(''); }
  };
  const pushShare = async () => {
    if (!connection) return; setBusy('push');
    try { setConnection(await pushSharedWorkspace(connection, decisions)); setNotice('Changes saved to the shared workspace.'); }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Could not save changes.'); }
    finally { setBusy(''); }
  };
  const pullShare = async () => {
    if (!connection || !window.confirm('Replace local decisions with the latest shared workspace?')) return; setBusy('pull');
    try { const pulled = await pullSharedWorkspace(connection.id, connection.token); setDecisions(pulled.decisions); setConnection(pulled.connection); setSelectedId(null); setNotice('Latest shared workspace loaded.'); }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Could not load changes.'); }
    finally { setBusy(''); }
  };
  const runJevReview = async () => {
    if (!selected) return;
    if (!connection) { setShowSync(true); setNotice('Connect a shared workspace to use Jev review.'); return; }
    setBusy('jev'); setJevAssessment(null);
    try {
      const saved = await pushSharedWorkspace(connection, decisions);
      setConnection(saved);
      setJevAssessment(await reviewWithJev(saved, selected.id));
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Jev review failed.'); }
    finally { setBusy(''); }
  };

  const reviewCount = decisions.filter(decision => decision.status === 'Review').length;
  const evidenceCount = decisions.reduce((total, decision) => total + decision.evidence.length, 0);
  const dateHeading = new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date()).toUpperCase();

  return <div className="shell">
    <aside>
      <a className="brand" href="#top"><span><img src="/compass-logo.png" alt="" /></span>Compass</a>
      <p className="nav-label">Workspace</p>
      <nav aria-label="Main navigation">
        <button className={filter === 'All' ? 'active' : ''} onClick={() => setFilter('All')}><span>▦</span><b>All decisions</b><i>{decisions.length}</i></button>
        <button className={filter === 'Review' ? 'active' : ''} onClick={() => setFilter('Review')}><span>◇</span><b>Needs review</b><i>{reviewCount}</i></button>
        <button className={filter === 'Decided' ? 'active' : ''} onClick={() => setFilter('Decided')}><span>✓</span><b>Decided</b></button>
      </nav>
      <p className="nav-label data-label">Your data</p>
      <nav aria-label="Data tools">
        <button onClick={() => setShowSync(true)}><span>☁</span><b>{connection ? 'Shared workspace' : 'Share workspace'}</b></button>
        <button onClick={exportWorkspace}><span>↓</span><b>Export workspace</b></button>
        <button onClick={() => importRef.current?.click()}><span>↑</span><b>Import workspace</b></button>
      </nav>
      <div className="open-source"><span>OPEN SOURCE</span><strong>Shape Compass with us</strong><p>Share a workflow, template, or focused improvement.</p><button onClick={() => window.open(githubUrl, '_blank', 'noopener')}>View on GitHub ↗</button></div>
      <div className="local-note"><i>◉</i><span><strong>{connection ? connection.name : 'Local workspace'}</strong><small>{connection ? `Shared · revision ${connection.revision}` : 'Private to this browser'}</small></span></div>
    </aside>

    <main id="top">
      <header><span className="mobile-logo"><img src="/compass-logo.png" alt="Compass" /></span><label className="search"><span>⌕</span><input ref={searchRef} value={query} onChange={event => setQuery(event.target.value)} placeholder="Search decisions, teams, owners..." /><kbd>Ctrl K</kbd></label><div><button className="secondary mobile-data" onClick={() => setShowSync(true)} aria-label="Shared workspace">☁</button><button className="secondary header-export" onClick={exportWorkspace}>Export</button><button className="primary" onClick={() => openNew()}>＋ New decision</button></div></header>
      <input ref={importRef} className="visually-hidden" type="file" accept="application/json,.json" onChange={importDecisions} />
      <div className="content">
        {!decisions.length ? <section className="onboarding">
          <p className="eyebrow">LOCAL-FIRST DECISION RECORDS</p><h1>Make the choice clear.<br />Preserve the reasoning.</h1><p>Compare options, weigh evidence, and record why the decision was made. Your data stays in this browser.</p>
          <div className="start-actions"><button className="primary" onClick={() => openNew()}>Create a decision</button><button className="secondary" onClick={() => { setDecisions(sampleWorkspace()); setNotice('Sample workspace loaded.'); }}>Explore sample workspace</button><button className="secondary" onClick={() => importRef.current?.click()}>Import workspace</button></div>
          <div className="template-library"><div><h2>Start from a template</h2><p>Use a proven scorecard, then adjust it to fit the decision.</p></div><div className="template-grid">{templates.slice(1).map(template => <button key={template.id} onClick={() => openNew(template.id)}><strong>{template.name}</strong><span>{template.description}</span><small>{template.criteria.length} criteria →</small></button>)}</div></div>
        </section> : <>
          <section className="welcome"><div><p className="eyebrow">{dateHeading}</p><h1>Make the next decision clear.</h1><p>{reviewCount ? `${reviewCount} ${reviewCount === 1 ? 'decision needs' : 'decisions need'} review.` : 'Your review queue is clear.'}</p></div>{reviewCount > 0 && <button className="secondary" onClick={() => { setFilter('Review'); document.getElementById('decisions')?.scrollIntoView({ behavior: 'smooth' }); }}>Review now <span>→</span></button>}</section>
          <section className="summary-grid">
            <article className="attention"><div><span className="summary-icon">!</span><p><strong>{reviewCount} {reviewCount === 1 ? 'review' : 'reviews'} waiting</strong><small>{reviewCount ? 'Keep decisions moving' : 'Nothing is blocked'}</small></p></div>{reviewCount > 0 && <button onClick={() => setFilter('Review')}>Review now →</button>}</article>
            <article><span>Active decisions</span><strong>{decisions.filter(item => item.status !== 'Decided').length}</strong><small>Drafts and reviews</small></article>
            <article><span>Evidence sources</span><strong>{evidenceCount}</strong><small>Across this browser</small></article>
            <article><span>Decided</span><strong>{decisions.filter(item => item.status === 'Decided').length}</strong><small>Rationale preserved</small></article>
          </section>
          <section className="decision-list" id="decisions">
            <div className="section-head"><div><h2>Decision records</h2><p>Compare the options, review the evidence, make the call.</p></div><div className="view-tools"><div className="filters">{(['All','Draft','Review','Decided'] as const).map(item => <button key={item} className={filter === item ? 'selected' : ''} onClick={() => setFilter(item)}>{item}</button>)}</div><button className="sort" onClick={() => setSortNewest(value => !value)}>↕ {sortNewest ? 'Newest' : 'Oldest'}</button></div></div>
            <div className="decision-table"><div className="table-head"><span>Decision</span><span>Outcome</span><span>Evaluated</span><span>Owner</span><span></span></div>{visible.map(decision => {
              const leader = leadingOption(decision); const progress = evaluationProgress(decision); const outcome = decision.chosenOption || leader?.option.name;
              return <button className="decision-row" key={decision.id} onClick={() => setSelectedId(decision.id)}><span className="decision-name"><i className={`status-dot ${decision.status.toLowerCase()}`} /><span><strong>{decision.title}</strong><small>{decision.team} · {formatDate(decision.due)}</small></span></span><span className="outcome"><strong>{outcome || 'Not evaluated'}</strong><small>{decision.chosenOption ? 'Recorded decision' : leader ? 'Leading option' : `${decision.options.length} options`}</small></span><span className="readiness"><span><i style={{width: `${progress}%`}} /></span><b>{progress}%</b></span><span className="row-owner"><i>{initials(decision.owner)}</i><span><strong>{decision.owner}</strong><small>Decision owner</small></span></span><span className="row-arrow">→</span></button>;
            })}{!visible.length && <div className="empty"><b>No decisions found</b><span>Try another search or filter.</span></div>}</div>
          </section>
        </>}
      </div>
    </main>

    {selected && <div className="drawer-backdrop" onMouseDown={() => setSelectedId(null)}><section className="drawer" role="dialog" aria-modal="true" aria-labelledby="decision-title" onMouseDown={event => event.stopPropagation()}>
      <div className="drawer-top"><span className={`status-pill ${selected.status.toLowerCase()}`}>{selected.status}</span><div><button className="text-button" onClick={runJevReview} disabled={busy === 'jev'}>{busy === 'jev' ? 'Reviewing...' : 'Check with Jev'}</button><button className="text-button" onClick={() => exportMarkdown(selected)}>Export Markdown</button><button className="close" onClick={() => setSelectedId(null)} aria-label="Close">×</button></div></div>
      <p className="breadcrumb">Decisions / {selected.team}</p><h2 id="decision-title">{selected.title}</h2><p className="drawer-summary">{selected.summary}</p>
      <div className="meta"><span><small>Owner</small><b>{selected.owner}</b></span><span><small>Decision date</small><b>{formatDate(selected.due)}</b></span><span><small>Review date</small><b>{selected.reviewDate ? formatDate(selected.reviewDate) : 'Not scheduled'}</b></span></div>
      <div className="completion"><strong>Decision checklist</strong>{([['Context', !!selected.summary], ['Options', selected.options.length > 1], ['Criteria', !!selected.criteria.length], ['Evidence', !!selected.evidence.length], ['Evaluate', evaluationProgress(selected) === 100], ['Record', selected.status === 'Decided']] as const).map(([label, done]) => <span className={done ? 'done' : ''} key={label}>{done ? '✓' : '○'} {label}</span>)}</div>

      {jevAssessment && <div className={`jev-review ${jevAssessment.needs_attention ? 'attention-needed' : ''}`}><div><span>JEV READINESS CHECK</span><strong>{jevAssessment.readiness.replace('_', ' ')}</strong><small>{Math.round(jevAssessment.confidence * 100)}% confidence</small></div><p><b>Review focus:</b> {jevAssessment.focus}. Unsupported evidence probability: {Math.round(jevAssessment.unsupported_evidence_probability * 100)}%.</p><small>Jev checks record quality. A human still chooses and records the outcome.</small></div>}

      <div className="drawer-section"><div className="drawer-heading"><div><h3>Criteria</h3><p>Adjust what matters and how much it counts.</p></div>{selected.status !== 'Decided' && <button className="text-button" onClick={() => addCriterion(selected.id)}>＋ Add criterion</button>}</div><div className="criteria-editor">{selected.criteria.map(criterion => <div key={criterion.id}><input value={criterion.name} disabled={selected.status === 'Decided'} onChange={event => updateCriterion(selected.id, criterion.id, 'name', event.target.value)} aria-label="Criterion name" /><label><input type="number" min="1" max="100" value={criterion.weight} disabled={selected.status === 'Decided'} onChange={event => updateCriterion(selected.id, criterion.id, 'weight', Math.max(1, Number(event.target.value)))} aria-label={`${criterion.name} weight`} />%</label>{selected.status !== 'Decided' && selected.criteria.length > 1 && <button onClick={() => removeCriterion(selected.id, criterion.id)} aria-label={`Remove ${criterion.name}`}>×</button>}</div>)}</div></div>

      <div className="drawer-section"><div className="drawer-heading"><div><h3>Option comparison</h3><p>Use the honest 1–5 scale. A leader appears only after every score is complete.</p></div><div className="heading-actions"><span className="scorecard-label">{evaluationProgress(selected)}% evaluated</span>{selected.status !== 'Decided' && <button className="text-button" onClick={() => addOption(selected.id)}>＋ Add option</button>}</div></div><div className="options">{selected.options.map((option, optionIndex) => {
        const leader = leadingOption(selected); const score = optionScore(option, selected.criteria); const isLeader = leader?.option === option;
        return <article className={isLeader ? 'leader' : ''} key={optionIndex}><div className="option-head"><span><i>{optionIndex + 1}</i><input className="option-name" value={option.name} disabled={selected.status === 'Decided'} onChange={event => updateOption(selected.id, optionIndex, 'name', event.target.value)} aria-label={`Option ${optionIndex + 1} name`} />{isLeader && !selected.chosenOption && <em>Leading option</em>}{selected.chosenOption === option.name && <em>Selected</em>}</span><span><b>{score ?? '-'}</b>{selected.status !== 'Decided' && selected.options.length > 2 && <button onClick={() => removeOption(selected.id, optionIndex)} aria-label={`Remove ${option.name}`}>×</button>}</span></div><input className="option-note" value={option.note} disabled={selected.status === 'Decided'} onChange={event => updateOption(selected.id, optionIndex, 'note', event.target.value)} placeholder="Add a concise tradeoff or constraint" aria-label={`${option.name} note`} /><div className="option-scores">{selected.criteria.map(criterion => <label key={criterion.id}><span>{criterion.name}</span><select value={option.scores[criterion.id] ?? ''} disabled={selected.status === 'Decided'} onChange={event => updateScore(selected.id, optionIndex, criterion.id, event.target.value ? Number(event.target.value) : null)} aria-label={`${option.name} ${criterion.name}`}><option value="">Not scored</option>{[1,2,3,4,5].map(value => <option key={value} value={value}>{value} · {scoreLabel(value)}</option>)}</select></label>)}</div></article>;
      })}</div></div>

      <div className="drawer-section evidence"><div className="drawer-heading"><div><h3>Evidence</h3><p>{selected.evidence.length ? `${selected.evidence.length} sources attached.` : 'Add links, documents, interviews, or analysis.'}</p></div></div>{selected.evidence.length ? <ul>{selected.evidence.map((item, index) => <li key={`${item}-${index}`}><span>▤</span><div>{isLink(item) ? <a href={item} target="_blank" rel="noreferrer">{item}</a> : <strong>{item}</strong>}<small>Evidence source</small></div></li>)}</ul> : <div className="evidence-empty">No evidence yet. Add a source before review.</div>}{selected.status !== 'Decided' && <form className="evidence-form" onSubmit={addEvidence}><input value={newEvidence} onChange={event => setNewEvidence(event.target.value)} placeholder="Paste a link or name a source" aria-label="New evidence source" /><button className="secondary">＋ Add source</button></form>}</div>

      {selected.status === 'Decided' && <div className="drawer-section decision-record"><h3>Recorded decision</h3><strong>{selected.chosenOption}</strong><p>{selected.rationale || 'No final rationale was recorded.'}</p></div>}
      <footer className="drawer-actions"><span>Updated {formatDate(selected.updatedAt.slice(0, 10))}</span>{selected.status === 'Draft' && <button className="primary" onClick={() => setStatus(selected.id, 'Review')}>Ready for review</button>}{selected.status === 'Review' && <button className="primary" onClick={() => setShowRecord(true)}>Record decision</button>}{selected.status === 'Decided' && <button className="secondary" onClick={() => setStatus(selected.id, 'Review')}>Reopen decision</button>}</footer>
    </section></div>}

    {showForm && <div className="modal-backdrop" onMouseDown={() => setShowForm(false)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={event => event.stopPropagation()}><button className="close" onClick={() => setShowForm(false)} aria-label="Close">×</button><p className="eyebrow">NEW DECISION</p><h2 id="modal-title">Frame the choice</h2><p>Start with the question, viable options, and a scorecard that fits.</p><form onSubmit={addDecision}><label className="wide">1. What are you deciding?<input name="title" minLength={6} required placeholder="Choose our next support platform" /></label><label className="wide">Context<textarea name="summary" minLength={20} required rows={3} placeholder="What prompted this decision, and what does success look like?" /></label><label>2. Option A<input name="optionA" required placeholder="First viable path" /></label><label>Option B<input name="optionB" required placeholder="Alternative path" /></label><label className="wide">3. Scorecard<select name="template" value={templateId} onChange={event => setTemplateId(event.target.value)}>{templates.map(template => <option key={template.id} value={template.id}>{template.name}</option>)}</select></label><p className="form-hint wide">{templates.find(item => item.id === templateId)?.description} You can edit criteria and weights after creation.</p><label>Owner<input name="owner" defaultValue="You" required /></label><label>Team<input name="team" defaultValue="General" required /></label><label>Decision date<input name="due" type="date" defaultValue={today()} required /></label><div className="form-actions"><button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button><button className="primary">Create decision</button></div></form></section></div>}

    {showRecord && selected && <div className="modal-backdrop nested" onMouseDown={() => setShowRecord(false)}><section className="modal record-modal" role="dialog" aria-modal="true" aria-labelledby="record-title" onMouseDown={event => event.stopPropagation()}><button className="close" onClick={() => setShowRecord(false)} aria-label="Close">×</button><p className="eyebrow">FINAL OUTCOME</p><h2 id="record-title">Record the decision</h2><p>The score informs the choice. Your rationale preserves why it was made.</p><form onSubmit={recordDecision}><label className="wide">Selected option<select name="choice" defaultValue={leadingOption(selected)?.option.name || selected.options[0].name}>{selected.options.map(option => <option key={option.name}>{option.name}</option>)}</select></label><label className="wide">Final rationale<textarea name="rationale" minLength={20} required rows={5} placeholder="Why was this option selected? Note tradeoffs, assumptions, and concerns." /></label><label>Review date<input name="reviewDate" type="date" /></label><div className="form-actions"><button type="button" className="secondary" onClick={() => setShowRecord(false)}>Cancel</button><button className="primary">Save decision record</button></div></form></section></div>}

    {showSync && <div className="modal-backdrop nested" onMouseDown={() => setShowSync(false)}><section className="modal sync-modal" role="dialog" aria-modal="true" aria-labelledby="sync-title" onMouseDown={event => event.stopPropagation()}><button className="close" onClick={() => setShowSync(false)} aria-label="Close">×</button><p className="eyebrow">SHARED WORKSPACE</p><h2 id="sync-title">{connection ? connection.name : 'Share decisions safely'}</h2><p>{connection ? 'Push or pull explicitly so local edits are never overwritten silently.' : 'Create a protected workspace or connect with credentials from a teammate.'}</p>{connection ? <div className="sync-connected"><label>Workspace ID<input readOnly value={connection.id} /></label><label>Access token<input readOnly value={connection.token} /></label><p>Anyone with both values can read and change this workspace.</p><div className="sync-actions"><button className="secondary" onClick={() => { navigator.clipboard.writeText(JSON.stringify({ id: connection.id, token: connection.token })); setNotice('Connection details copied.'); }}>Copy connection details</button><button className="secondary" onClick={pullShare} disabled={!!busy}>{busy === 'pull' ? 'Pulling...' : 'Pull latest'}</button><button className="primary" onClick={pushShare} disabled={!!busy}>{busy === 'push' ? 'Saving...' : 'Push changes'}</button></div><button className="disconnect" onClick={() => { setConnection(null); setShowSync(false); setJevAssessment(null); }}>Disconnect this browser</button></div> : <div className="sync-forms"><form onSubmit={createShare}><h3>Create from this browser</h3><label>Workspace name<input name="name" minLength={2} maxLength={80} required placeholder="Product team" /></label><button className="primary" disabled={!!busy}>{busy === 'create' ? 'Creating...' : 'Create and upload'}</button></form><form onSubmit={connectShare}><h3>Connect existing workspace</h3><label>Workspace ID<input name="id" required autoComplete="off" /></label><label>Access token<input name="token" required type="password" autoComplete="off" /></label><button className="secondary" disabled={!!busy}>{busy === 'connect' ? 'Connecting...' : 'Connect and pull'}</button></form></div>}</section></div>}
    {notice && <button className="notice" aria-live="polite" onClick={() => setNotice('')}>{notice}<span>×</span></button>}
  </div>;
}

export default App;
