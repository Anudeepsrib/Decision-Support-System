export type Status = 'Draft' | 'Review' | 'Approved';
export type Scores = { impact: number; confidence: number; feasibility: number };
export type Option = { name: string; note: string; scores: Scores };
export type Decision = {
  id: number; title: string; summary: string; owner: string; team: string;
  status: Status; due: string; comments: number; reviewers: number;
  evidence: string[]; options: Option[];
};

const weights: Scores = { impact: 40, confidence: 35, feasibility: 25 };

export const optionScore = (scores: Scores, customWeights: Scores = weights) =>
  Math.round((scores.impact * customWeights.impact + scores.confidence * customWeights.confidence + scores.feasibility * customWeights.feasibility) / (customWeights.impact + customWeights.confidence + customWeights.feasibility));

export const isDecisionList = (value: unknown): value is Decision[] => Array.isArray(value) && value.every(item => {
  if (!item || typeof item !== 'object') return false;
  const decision = item as Partial<Decision>;
  return typeof decision.id === 'number' && typeof decision.title === 'string' &&
    typeof decision.summary === 'string' && typeof decision.owner === 'string' &&
    typeof decision.team === 'string' && ['Draft', 'Review', 'Approved'].includes(String(decision.status)) &&
    typeof decision.due === 'string' && typeof decision.comments === 'number' &&
    typeof decision.reviewers === 'number' && Array.isArray(decision.evidence) &&
    decision.evidence.every(source => typeof source === 'string') && Array.isArray(decision.options) &&
    decision.options.length >= 2 && decision.options.every(option => option && typeof option.name === 'string' &&
      typeof option.note === 'string' && ['impact', 'confidence', 'feasibility'].every(key => {
        const score = option.scores?.[key as keyof Scores];
        return typeof score === 'number' && score >= 0 && score <= 100;
      }));
});
