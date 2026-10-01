export type Status = 'Draft' | 'Review' | 'Decided';
export type Criterion = { id: string; name: string; weight: number };
export type Scores = Record<string, number | null>;
export type Option = { name: string; note: string; scores: Scores };
export type Decision = {
  id: number;
  title: string;
  summary: string;
  owner: string;
  team: string;
  status: Status;
  due: string;
  criteria: Criterion[];
  evidence: string[];
  options: Option[];
  chosenOption?: string;
  rationale?: string;
  reviewDate?: string;
  createdAt: string;
  updatedAt: string;
};

export type DecisionTemplate = {
  id: string;
  name: string;
  description: string;
  criteria: Criterion[];
};

const criteria = (...items: [string, number][]): Criterion[] => items.map(([name, weight]) => ({
  id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name, weight,
}));

export const templates: DecisionTemplate[] = [
  { id: 'blank', name: 'Blank decision', description: 'Start with a flexible general scorecard.', criteria: criteria(['Impact', 40], ['Confidence', 30], ['Feasibility', 30]) },
  { id: 'build-buy', name: 'Build vs. Buy', description: 'Compare ownership, speed, cost, and strategic value.', criteria: criteria(['Strategic fit', 30], ['Total cost', 25], ['Time to value', 25], ['Control', 20]) },
  { id: 'vendor', name: 'Vendor selection', description: 'Evaluate suppliers on the factors that survive procurement.', criteria: criteria(['Capability', 30], ['Security', 25], ['Integration', 20], ['Cost', 15], ['Support', 10]) },
  { id: 'technology', name: 'Technology selection', description: 'Balance fit, operability, ecosystem, and risk.', criteria: criteria(['Technical fit', 30], ['Maintainability', 25], ['Ecosystem', 20], ['Cost', 15], ['Risk', 10]) },
  { id: 'hiring', name: 'Hiring decision', description: 'Use a consistent, evidence-based candidate scorecard.', criteria: criteria(['Role fit', 35], ['Evidence', 25], ['Growth potential', 20], ['Team contribution', 20]) },
  { id: 'market', name: 'Market expansion', description: 'Compare market value, confidence, cost, and execution risk.', criteria: criteria(['Market potential', 35], ['Strategic fit', 25], ['Confidence', 20], ['Execution risk', 20]) },
];

export const scoreLabel = (score: number | null) => ['Not scored', 'Very low', 'Low', 'Medium', 'High', 'Very high'][score ?? 0];

export const optionScore = (option: Option, decisionCriteria: Criterion[]) => {
  if (!decisionCriteria.length || decisionCriteria.some(item => option.scores[item.id] == null)) return null;
  const weight = decisionCriteria.reduce((total, item) => total + item.weight, 0);
  if (!weight) return null;
  return Math.round(decisionCriteria.reduce((total, item) => total + Number(option.scores[item.id]) * item.weight, 0) / weight * 10) / 10;
};

export const leadingOption = (decision: Decision) => {
  const ranked = decision.options.map(option => ({ option, score: optionScore(option, decision.criteria) }));
  return ranked.every(item => item.score !== null) ? ranked.sort((a, b) => Number(b.score) - Number(a.score))[0] : null;
};

export const evaluationProgress = (decision: Decision) => {
  const total = decision.options.length * decision.criteria.length;
  const complete = decision.options.reduce((sum, option) => sum + decision.criteria.filter(item => option.scores[item.id] != null).length, 0);
  return total ? Math.round(complete / total * 100) : 0;
};

const isRecord = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object';
const stableDate = (id: number) => id > 946684800000 ? new Date(id).toISOString() : '2026-01-01T00:00:00.000Z';
const leadingName = (options: Option[], decisionCriteria: Criterion[]) => options
  .map(option => ({ name: option.name, score: optionScore(option, decisionCriteria) ?? 0 }))
  .sort((a, b) => b.score - a.score)[0]?.name;

export const parseDecisions = (value: unknown): Decision[] | null => {
  if (!Array.isArray(value)) return null;
  const parsed: Decision[] = [];
  for (const item of value) {
    if (!isRecord(item) || typeof item.id !== 'number' || typeof item.title !== 'string' || typeof item.summary !== 'string' || !Array.isArray(item.options) || item.options.length < 2) return null;
    let decisionCriteria = templates[0].criteria;
    if (Array.isArray(item.criteria)) {
      if (!item.criteria.length || !item.criteria.every((entry): entry is Criterion => isRecord(entry) && typeof entry.id === 'string' && typeof entry.name === 'string' && !!entry.name.trim() && typeof entry.weight === 'number' && Number.isFinite(entry.weight) && entry.weight > 0)) return null;
      decisionCriteria = item.criteria;
    }
    const options: Option[] = [];
    for (const entry of item.options) {
      if (!isRecord(entry) || typeof entry.name !== 'string' || typeof entry.note !== 'string' || !isRecord(entry.scores)) return null;
      const scores: Scores = {};
      for (const criterion of decisionCriteria) {
        const raw = entry.scores[criterion.id];
        if (raw == null) scores[criterion.id] = null;
        else if (typeof raw === 'number' && raw >= 0 && raw <= 100) scores[criterion.id] = raw === 0 ? null : raw > 5 ? Math.max(1, Math.round(raw / 20)) : raw;
        else return null;
      }
      options.push({ name: entry.name, note: entry.note, scores });
    }
    const rawStatus = String(item.status);
    const status: Status = rawStatus === 'Approved' || rawStatus === 'Decided' ? 'Decided' : rawStatus === 'Review' ? 'Review' : 'Draft';
    const fallbackDate = stableDate(item.id);
    parsed.push({
      id: item.id, title: item.title, summary: item.summary,
      owner: typeof item.owner === 'string' ? item.owner : 'You',
      team: typeof item.team === 'string' ? item.team : 'General', status,
      due: typeof item.due === 'string' ? item.due : '', criteria: decisionCriteria,
      evidence: Array.isArray(item.evidence) && item.evidence.every(source => typeof source === 'string') ? item.evidence : [], options,
      chosenOption: typeof item.chosenOption === 'string' ? item.chosenOption : status === 'Decided' ? leadingName(options, decisionCriteria) : undefined,
      rationale: typeof item.rationale === 'string' ? item.rationale : undefined,
      reviewDate: typeof item.reviewDate === 'string' ? item.reviewDate : undefined,
      createdAt: typeof item.createdAt === 'string' ? item.createdAt : fallbackDate,
      updatedAt: typeof item.updatedAt === 'string' ? item.updatedAt : fallbackDate,
    });
  }
  return parsed;
};

export const decisionToMarkdown = (decision: Decision) => {
  const rows = decision.options.map(option => `| ${option.name} | ${decision.criteria.map(item => scoreLabel(option.scores[item.id])).join(' | ')} | ${optionScore(option, decision.criteria) ?? 'Not evaluated'} |`).join('\n');
  const header = `| Option | ${decision.criteria.map(item => `${item.name} (${item.weight}%)`).join(' | ')} | Weighted score |`;
  const divider = `|---|${decision.criteria.map(() => '---|').join('')}---|`;
  return `# ${decision.title}\n\n**Status:** ${decision.status}  \n**Owner:** ${decision.owner}  \n**Decision date:** ${decision.due || 'Not set'}${decision.reviewDate ? `  \n**Review date:** ${decision.reviewDate}` : ''}\n\n## Context\n\n${decision.summary}\n\n## Options\n\n${header}\n${divider}\n${rows}\n\n## Evidence\n\n${decision.evidence.length ? decision.evidence.map(item => `- ${item}`).join('\n') : '- No evidence recorded'}\n\n## Decision\n\n**Selected option:** ${decision.chosenOption || 'Not decided'}\n\n${decision.rationale || 'No final rationale recorded.'}\n`;
};
