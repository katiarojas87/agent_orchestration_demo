import type {
  Defect,
  GuardrailResult,
  IntakeSummary,
  PipelineMode,
  Requirement,
  TestScenario,
  TraceRecord,
} from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof payload.detail === "string" ? payload.detail : response.statusText);
  }
  return response.json() as Promise<T>;
}

export function fetchIntakes(): Promise<IntakeSummary[]> {
  return request<IntakeSummary[]>("/api/intakes");
}

export function draftRequirement(intakeId: string, mode: PipelineMode) {
  return request<{ requirement: Requirement; guardrail_result: GuardrailResult }>(
    "/api/requirements/draft",
    {
      method: "POST",
      body: JSON.stringify({ intake_id: intakeId, mode }),
    },
  );
}

export function approveRequirement(requirementId: string) {
  return request<Requirement>("/api/requirements/approve", {
    method: "POST",
    body: JSON.stringify({ requirement_id: requirementId }),
  });
}

export function draftTestDesign(requirementId: string, mode: PipelineMode) {
  return request<{
    tests: TestScenario[];
    coverage_gaps: string[];
    clarification_needed: string[];
    guardrail_result: GuardrailResult;
  }>("/api/test-design/draft", {
    method: "POST",
    body: JSON.stringify({ requirement_id: requirementId, mode }),
  });
}

export function approveTestDesign(requirementId: string) {
  return request<{ tests: TestScenario[] }>("/api/test-design/approve", {
    method: "POST",
    body: JSON.stringify({ requirement_id: requirementId }),
  });
}

export function draftDefectAnalysis(executionId: string, mode: PipelineMode) {
  return request<{ defect: Defect; guardrail_result: GuardrailResult }>(
    "/api/defect-analysis/draft",
    {
      method: "POST",
      body: JSON.stringify({ execution_id: executionId, mode }),
    },
  );
}

export function confirmDefect(defectId: string) {
  return request<Defect>("/api/defect-analysis/confirm", {
    method: "POST",
    body: JSON.stringify({ defect_id: defectId }),
  });
}

export function fetchDocumentation(requirementId: string, mode: PipelineMode = "mock_clean") {
  return request<{ trace_record: TraceRecord; guardrail_result: GuardrailResult }>(
    `/api/documentation/${encodeURIComponent(requirementId)}?mode=${mode}`,
  );
}
