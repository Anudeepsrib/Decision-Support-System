import assert from 'node:assert/strict';
import test from 'node:test';
import { decisionToMarkdown, optionScore, parseDecisions, templates } from './decision.ts';

test('scores 1-5 criteria, migrates legacy data, and rejects unsafe imports', () => {
  const option = { name: 'A', note: '', scores: { impact: 5, confidence: 4, feasibility: 2 } };
  assert.equal(optionScore(option, templates[0].criteria), 3.8);
  assert.equal(optionScore({ ...option, scores: { ...option.scores, impact: null } }, templates[0].criteria), null);
  const migrated = parseDecisions([{ id: 1, title: 'Legacy', summary: 'Old data', owner: 'You', team: 'General', status: 'Approved', due: 'Oct 4', evidence: [], options: [{ name: 'A', note: '', scores: { impact: 92, confidence: 84, feasibility: 76 } }, { name: 'B', note: '', scores: { impact: 48, confidence: 94, feasibility: 90 } }] }]);
  assert.equal(migrated?.[0].status, 'Decided');
  assert.equal(migrated?.[0].options[0].scores.impact, 5);
  assert.match(decisionToMarkdown(migrated![0]), /# Legacy/);
  assert.equal(parseDecisions([{ id: 2, title: 'Bad criteria', summary: 'Unsafe import', options: [{ name: 'A', note: '', scores: {} }, { name: 'B', note: '', scores: {} }], criteria: [{ id: 'risk', name: '', weight: 100 }] }]), null);
  assert.equal(parseDecisions([{ title: 'missing required fields' }]), null);
});
