export type PipelineMode = "mock_clean" | "mock_violation";

export type StageKey =
  | "requirements"
  | "test_design"
  | "defect_analysis"
  | "documentation";

export type StageView = "not_run" | "result" | "gate" | "failed";

export interface GuardrailCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface GuardrailResult {
  passed: boolean;
  checks: GuardrailCheck[];
}

export interface AcceptanceCriterion {
  id: string;
  text: string;
  source_ref: string;
}

export interface Requirement {
  requirement_id: string;
  status: "draft" | "approved";
  derived_from: string;
  statement: string;
  acceptance_criteria: AcceptanceCriterion[];
  open_questions: string[];
  possible_duplicates: string[];
}

export interface TestScenario {
  test_id: string;
  requirement_id: string;
  acceptance_criteria_id: string;
  type: "positive" | "negative" | "edge";
  preconditions: string;
  steps: string[];
  test_data_spec: string;
  expected_result: string;
  priority: string;
}

export interface RootCauseHypothesis {
  hypothesis: string;
  confidence: "high" | "medium" | "low" | "";
  evidence_ref: string;
}

export interface Defect {
  defect_id: string;
  execution_id: string;
  test_id: string;
  requirement_id: string;
  acceptance_criteria_id: string;
  classification: string;
  severity_suggestion: string;
  root_cause_hypotheses: RootCauseHypothesis[];
  duplicate_of: string | null;
  pattern_flag: string | null;
  status: "needs_human_review" | "root_cause_confirmed";
}

export interface TraceRecord {
  requirement_id: string;
  status: string;
  trace: {
    tests: string[];
    executions: string[];
    defects: string[];
  };
  gaps: string[];
  narrative: string;
  last_synced: string;
}

export interface IntakeSummary {
  intake_id: string;
  title: string;
  reported_at: string;
}

export interface TraceChain {
  requirementId?: string;
  testIds: string[];
  executionId?: string;
  defectId?: string;
}
