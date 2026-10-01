import { Decision, parseDecisions } from './decision';

export type WorkspaceConnection = { id: string; name: string; token: string; revision: number };
export type JevAssessment = {
  readiness: 'not_ready' | 'needs_work' | 'ready';
  readiness_score: number;
  confidence: number;
  focus: 'evidence' | 'criteria' | 'alternatives' | 'rationale' | 'ready';
  focus_confidence: number;
  unsupported_evidence_probability: number;
  needs_attention: boolean;
  model: string;
  request_id: string;
  human_decision_required: true;
};

const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${API}${path}`, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.message || 'The server could not complete this request.');
  return body;
}

const auth = (connection: WorkspaceConnection) => ({ Authorization: `Bearer ${connection.token}` });

export async function createSharedWorkspace(name: string, decisions: Decision[]): Promise<WorkspaceConnection> {
  const body = await request('/api/workspaces', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, decisions }) });
  return { id: body.workspace.id, name: body.workspace.name, revision: body.workspace.revision, token: body.token };
}

export async function pullSharedWorkspace(id: string, token: string) {
  const body = await request(`/api/workspaces/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
  const decisions = parseDecisions(body.workspace.decisions);
  if (!decisions) throw new Error('The server returned an invalid Compass workspace.');
  return { connection: { id, token, name: body.workspace.name, revision: body.workspace.revision } as WorkspaceConnection, decisions };
}

export async function pushSharedWorkspace(connection: WorkspaceConnection, decisions: Decision[]) {
  const body = await request(`/api/workspaces/${encodeURIComponent(connection.id)}/decisions`, { method: 'PUT', headers: { ...auth(connection), 'Content-Type': 'application/json', 'If-Match': String(connection.revision) }, body: JSON.stringify({ decisions }) });
  return { ...connection, revision: body.workspace.revision };
}

export async function reviewWithJev(connection: WorkspaceConnection, decisionId: number): Promise<JevAssessment> {
  const body = await request(`/api/workspaces/${encodeURIComponent(connection.id)}/assist`, { method: 'POST', headers: { ...auth(connection), 'Content-Type': 'application/json' }, body: JSON.stringify({ decision_id: decisionId }) });
  return body.assessment;
}
