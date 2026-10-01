import assert from 'node:assert/strict';
import test from 'node:test';
import { isDecisionList, optionScore } from './decision.ts';

test('scores options and rejects unsafe imports', () => {
  assert.equal(optionScore({ impact: 100, confidence: 80, feasibility: 40 }), 78);
  assert.equal(isDecisionList([{ title: 'missing required fields' }]), false);
});
