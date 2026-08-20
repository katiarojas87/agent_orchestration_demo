import { useCallback, useEffect, useMemo, useState } from "react";
import {
  approveRequirement,
  approveTestDesign,
  confirmDefect,
  draftDefectAnalysis,
  draftRequirement,
  draftTestDesign,
  fetchDocumentation,
  fetchIntakes,
} from "./api";
import { DefectOutput } from "./components/DefectOutput";
import { DocumentationOutput } from "./components/DocumentationOutput";
import { GuardrailChecklist } from "./components/GuardrailChecklist";
import { RequirementsOutput } from "./components/RequirementsOutput";
import { Stepper } from "./components/Stepper";
import { TestDesignOutput } from "./components/TestDesignOutput";
import { TracePanel } from "./components/TracePanel";
import type {
  Defect,
  GuardrailResult,
  IntakeSummary,
  PipelineMode,
  Requirement,
  StageKey,
  StageView,
  TestScenario,
  TraceChain,
  TraceRecord,
} from "./types";

const STAGE_ORDER: StageKey[] = [
  "requirements",
  "test_design",
  "defect_analysis",
  "documentation",
];

const DEFAULT_EXECUTION_ID = "EXEC-ATO-014-004";

function stageIndex(stage: StageKey): number {
  return STAGE_ORDER.indexOf(stage);
}

export default function App() {
  const [intakes, setIntakes] = useState<IntakeSummary[]>([]);
  const [intakeId, setIntakeId] = useState("");
  const [currentStage, setCurrentStage] = useState<StageKey>("requirements");
  const [completedStages, setCompletedStages] = useState<Set<StageKey>>(new Set());
  const [staleFromStage, setStaleFromStage] = useState<StageKey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [requirementsView, setRequirementsView] = useState<StageView>("not_run");
  const [requirementsGuardrails, setRequirementsGuardrails] =
    useState<GuardrailResult | null>(null);

  const [tests, setTests] = useState<TestScenario[]>([]);
  const [coverageGaps, setCoverageGaps] = useState<string[]>([]);
  const [clarificationNeeded, setClarificationNeeded] = useState<string[]>([]);
  const [testDesignView, setTestDesignView] = useState<StageView>("not_run");
  const [testDesignGuardrails, setTestDesignGuardrails] =
    useState<GuardrailResult | null>(null);

  const [defect, setDefect] = useState<Defect | null>(null);
  const [defectView, setDefectView] = useState<StageView>("not_run");
  const [defectGuardrails, setDefectGuardrails] = useState<GuardrailResult | null>(null);

  const [traceRecord, setTraceRecord] = useState<TraceRecord | null>(null);
  const [documentationGuardrails, setDocumentationGuardrails] =
    useState<GuardrailResult | null>(null);
  const [documentationView, setDocumentationView] = useState<StageView>("not_run");

  useEffect(() => {
    fetchIntakes()
      .then((items) => {
        setIntakes(items);
        if (items.length > 0) {
          setIntakeId(items[0].intake_id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const traceChain: TraceChain = useMemo(
    () => ({
      requirementId: requirement?.requirement_id,
      testIds: tests.map((test) => test.test_id),
      executionId:
        completedStages.has("test_design") || currentStage === "defect_analysis"
          ? DEFAULT_EXECUTION_ID
          : undefined,
      defectId: defect?.defect_id,
    }),
    [requirement, tests, defect, completedStages, currentStage],
  );

  const markDownstreamStale = useCallback((stage: StageKey) => {
    const index = stageIndex(stage);
    const hasLaterComplete = STAGE_ORDER.some(
      (key, idx) => idx > index && completedStages.has(key),
    );
    if (hasLaterComplete) {
      setStaleFromStage(stage);
      setCompletedStages((prev) => {
        const next = new Set(prev);
        STAGE_ORDER.slice(index + 1).forEach((key) => next.delete(key));
        return next;
      });
    }
  }, [completedStages]);

  const runRequirements = async (mode: PipelineMode) => {
    if (!intakeId) return;
    markDownstreamStale("requirements");
    setLoading(true);
    setError(null);
    try {
      const result = await draftRequirement(intakeId, mode);
      setRequirement(result.requirement);
      setRequirementsGuardrails(result.guardrail_result);
      setRequirementsView(result.guardrail_result.passed ? "gate" : "failed");
      setTests([]);
      setDefect(null);
      setTraceRecord(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Requirements draft failed");
    } finally {
      setLoading(false);
    }
  };

  const approveRequirements = async () => {
    if (!requirement) return;
    setLoading(true);
    setError(null);
    try {
      const approved = await approveRequirement(requirement.requirement_id);
      setRequirement(approved);
      setCompletedStages((prev) => new Set(prev).add("requirements"));
      setCurrentStage("test_design");
      setTestDesignView("not_run");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setLoading(false);
    }
  };

  const runTestDesign = async (mode: PipelineMode) => {
    if (!requirement) return;
    markDownstreamStale("test_design");
    setLoading(true);
    setError(null);
    try {
      const result = await draftTestDesign(requirement.requirement_id, mode);
      setTests(result.tests);
      setCoverageGaps(result.coverage_gaps);
      setClarificationNeeded(result.clarification_needed);
      setTestDesignGuardrails(result.guardrail_result);
      setTestDesignView(result.guardrail_result.passed ? "gate" : "failed");
      setDefect(null);
      setTraceRecord(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test design draft failed");
    } finally {
      setLoading(false);
    }
  };

  const approveTests = async () => {
    if (!requirement) return;
    setLoading(true);
    setError(null);
    try {
      const result = await approveTestDesign(requirement.requirement_id);
      setTests(result.tests);
      setCompletedStages((prev) => new Set(prev).add("test_design"));
      setCurrentStage("defect_analysis");
      setDefectView("not_run");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test approval failed");
    } finally {
      setLoading(false);
    }
  };

  const runDefectAnalysis = async (mode: PipelineMode) => {
    markDownstreamStale("defect_analysis");
    setLoading(true);
    setError(null);
    try {
      const result = await draftDefectAnalysis(DEFAULT_EXECUTION_ID, mode);
      setDefect(result.defect);
      setDefectGuardrails(result.guardrail_result);
      setDefectView(result.guardrail_result.passed ? "gate" : "failed");
      setTraceRecord(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Defect analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmDefectTriage = async () => {
    if (!defect) return;
    setLoading(true);
    setError(null);
    try {
      const confirmed = await confirmDefect(defect.defect_id);
      setDefect(confirmed);
      setCompletedStages((prev) => new Set(prev).add("defect_analysis"));
      setCurrentStage("documentation");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Defect confirmation failed");
    } finally {
      setLoading(false);
    }
  };

  const loadDocumentation = useCallback(async (mode: PipelineMode = "mock_clean") => {
    if (!requirement) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchDocumentation(requirement.requirement_id, mode);
      setTraceRecord(result.trace_record);
      setDocumentationGuardrails(result.guardrail_result);
      setDocumentationView(result.guardrail_result.passed ? "result" : "failed");
      if (result.guardrail_result.passed) {
        setCompletedStages((prev) => new Set(prev).add("documentation"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Documentation failed");
      setDocumentationView("failed");
    } finally {
      setLoading(false);
    }
  }, [requirement]);

  useEffect(() => {
    if (
      currentStage === "documentation" &&
      documentationView === "not_run" &&
      requirement &&
      completedStages.has("defect_analysis")
    ) {
      void loadDocumentation("mock_clean");
    }
  }, [currentStage, documentationView, requirement, completedStages, loadDocumentation]);

  const staleWarning =
    staleFromStage &&
    STAGE_ORDER.some(
      (key, idx) =>
        idx > stageIndex(staleFromStage) &&
        (completedStages.has(key) || currentStage === key),
    );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-5">
          <h1 className="text-xl font-semibold text-slate-900">
            Fraud Requirements Pipeline
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Review AI agent output stage by stage with guardrails and human gates.
          </p>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          <Stepper
            currentStage={currentStage}
            completedStages={completedStages}
            onSelect={setCurrentStage}
          />

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}

          {staleWarning && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Downstream stages may be stale — re-running{" "}
              <span className="font-semibold">{staleFromStage?.replace("_", " ")}</span>{" "}
              invalidates later approvals. Re-run downstream agents before trusting the
              trace chain.
            </div>
          )}

          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            {currentStage === "requirements" && (
              <RequirementsStage
                intakes={intakes}
                intakeId={intakeId}
                onIntakeChange={setIntakeId}
                view={requirementsView}
                requirement={requirement}
                guardrails={requirementsGuardrails}
                loading={loading}
                onRun={runRequirements}
                onApprove={approveRequirements}
                onRetry={() => setRequirementsView("not_run")}
              />
            )}

            {currentStage === "test_design" && (
              <TestDesignStage
                view={testDesignView}
                requirementId={requirement?.requirement_id}
                tests={tests}
                coverageGaps={coverageGaps}
                clarificationNeeded={clarificationNeeded}
                guardrails={testDesignGuardrails}
                loading={loading}
                onRun={runTestDesign}
                onApprove={approveTests}
                onRetry={() => setTestDesignView("not_run")}
              />
            )}

            {currentStage === "defect_analysis" && (
              <DefectStage
                view={defectView}
                executionId={DEFAULT_EXECUTION_ID}
                defect={defect}
                guardrails={defectGuardrails}
                loading={loading}
                onRun={runDefectAnalysis}
                onConfirm={confirmDefectTriage}
                onRetry={() => setDefectView("not_run")}
                enabled={completedStages.has("test_design")}
              />
            )}

            {currentStage === "documentation" && (
              <DocumentationStage
                view={documentationView}
                trace={traceRecord}
                guardrails={documentationGuardrails}
                loading={loading}
                onRun={loadDocumentation}
                pipelineComplete={
                  completedStages.has("documentation") &&
                  (documentationGuardrails?.passed ?? false)
                }
              />
            )}
          </section>
        </div>

        <TracePanel trace={traceChain} />
      </main>
    </div>
  );
}

function RunControls({
  loading,
  onRunClean,
  onRunViolation,
}: {
  loading: boolean;
  onRunClean: () => void;
  onRunViolation: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <button
        type="button"
        disabled={loading}
        onClick={onRunClean}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        Run (clean)
      </button>
      <button
        type="button"
        disabled={loading}
        onClick={onRunViolation}
        className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-100 disabled:opacity-50"
      >
        Run (violation)
      </button>
    </div>
  );
}

function StageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
    </div>
  );
}

function RequirementsStage(props: {
  intakes: IntakeSummary[];
  intakeId: string;
  onIntakeChange: (id: string) => void;
  view: StageView;
  requirement: Requirement | null;
  guardrails: GuardrailResult | null;
  loading: boolean;
  onRun: (mode: PipelineMode) => void;
  onApprove: () => void;
  onRetry: () => void;
}) {
  const {
    intakes,
    intakeId,
    onIntakeChange,
    view,
    requirement,
    guardrails,
    loading,
    onRun,
    onApprove,
    onRetry,
  } = props;

  return (
    <>
      <StageHeader
        title="Requirements Analysis"
        subtitle="Draft a structured requirement from raw intake with source-backed acceptance criteria."
      />

      {view === "not_run" && (
        <div className="space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Intake incident</span>
            <select
              value={intakeId}
              onChange={(event) => onIntakeChange(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {intakes.map((intake) => (
                <option key={intake.intake_id} value={intake.intake_id}>
                  {intake.intake_id} — {intake.title}
                </option>
              ))}
            </select>
          </label>
          <RunControls
            loading={loading}
            onRunClean={() => onRun("mock_clean")}
            onRunViolation={() => onRun("mock_violation")}
          />
        </div>
      )}

      {view === "failed" && requirement && guardrails && (
        <div className="space-y-4">
          <FailedBanner onRetry={onRetry} />
          <RequirementsOutput requirement={requirement} />
          <GuardrailChecklist result={guardrails} />
        </div>
      )}

      {view === "gate" && requirement && guardrails && (
        <div className="space-y-4">
          <RequirementsOutput requirement={requirement} />
          <GuardrailChecklist result={guardrails} />
          {requirement.open_questions.length > 0 && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {requirement.open_questions.length} open question(s) must be resolved before
              approval.
            </div>
          )}
          <button
            type="button"
            disabled={loading || requirement.open_questions.length > 0}
            onClick={onApprove}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Approve &amp; Continue
          </button>
        </div>
      )}
    </>
  );
}

function TestDesignStage(props: {
  view: StageView;
  requirementId?: string;
  tests: TestScenario[];
  coverageGaps: string[];
  clarificationNeeded: string[];
  guardrails: GuardrailResult | null;
  loading: boolean;
  onRun: (mode: PipelineMode) => void;
  onApprove: () => void;
  onRetry: () => void;
}) {
  const {
    view,
    requirementId,
    tests,
    coverageGaps,
    clarificationNeeded,
    guardrails,
    loading,
    onRun,
    onApprove,
    onRetry,
  } = props;

  if (!requirementId) {
    return (
      <p className="text-sm text-slate-600">
        Approve a requirement first to design tests.
      </p>
    );
  }

  return (
    <>
      <StageHeader
        title="Test Design"
        subtitle={`Design test scenarios for ${requirementId}.`}
      />

      {view === "not_run" && (
        <RunControls
          loading={loading}
          onRunClean={() => onRun("mock_clean")}
          onRunViolation={() => onRun("mock_violation")}
        />
      )}

      {view === "failed" && guardrails && (
        <div className="space-y-4">
          <FailedBanner onRetry={onRetry} />
          <TestDesignOutput
            tests={tests}
            coverageGaps={coverageGaps}
            clarificationNeeded={clarificationNeeded}
          />
          <GuardrailChecklist result={guardrails} />
        </div>
      )}

      {view === "gate" && guardrails && (
        <div className="space-y-4">
          <TestDesignOutput
            tests={tests}
            coverageGaps={coverageGaps}
            clarificationNeeded={clarificationNeeded}
          />
          <GuardrailChecklist result={guardrails} />
          <button
            type="button"
            disabled={loading}
            onClick={onApprove}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Approve &amp; Continue
          </button>
        </div>
      )}
    </>
  );
}

function DefectStage(props: {
  view: StageView;
  executionId: string;
  defect: Defect | null;
  guardrails: GuardrailResult | null;
  loading: boolean;
  enabled: boolean;
  onRun: (mode: PipelineMode) => void;
  onConfirm: () => void;
  onRetry: () => void;
}) {
  const {
    view,
    executionId,
    defect,
    guardrails,
    loading,
    enabled,
    onRun,
    onConfirm,
    onRetry,
  } = props;

  if (!enabled) {
    return (
      <p className="text-sm text-slate-600">
        Approve test scenarios first to seed execution {executionId}.
      </p>
    );
  }

  return (
    <>
      <StageHeader
        title="Defect Analysis"
        subtitle={`Triage failed execution ${executionId}.`}
      />

      {view === "not_run" && (
        <RunControls
          loading={loading}
          onRunClean={() => onRun("mock_clean")}
          onRunViolation={() => onRun("mock_violation")}
        />
      )}

      {view === "failed" && defect && guardrails && (
        <div className="space-y-4">
          <FailedBanner onRetry={onRetry} />
          <DefectOutput defect={defect} />
          <GuardrailChecklist result={guardrails} />
        </div>
      )}

      {view === "gate" && defect && guardrails && (
        <div className="space-y-4">
          <DefectOutput defect={defect} />
          <GuardrailChecklist result={guardrails} />
          <button
            type="button"
            disabled={loading}
            onClick={onConfirm}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Confirm root cause &amp; severity
          </button>
        </div>
      )}
    </>
  );
}

function DocumentationStage(props: {
  view: StageView;
  trace: TraceRecord | null;
  guardrails: GuardrailResult | null;
  loading: boolean;
  pipelineComplete: boolean;
  onRun: (mode: PipelineMode) => void;
}) {
  const { view, trace, guardrails, loading, pipelineComplete, onRun } = props;

  return (
    <>
      <StageHeader
        title="Documentation"
        subtitle="Auto-generated traceability report — no human gate."
      />

      {view === "not_run" && (
        <p className="text-sm text-slate-600">Loading documentation report…</p>
      )}

      {loading && view !== "not_run" && (
        <p className="mb-4 text-sm text-slate-600">Refreshing report…</p>
      )}

      <div className="mb-4">
        <RunControls
          loading={loading}
          onRunClean={() => onRun("mock_clean")}
          onRunViolation={() => onRun("mock_violation")}
        />
      </div>

      {view === "failed" && trace && guardrails && (
        <div className="space-y-4">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
            Guardrail failed — documentation report rejected.
          </div>
          <DocumentationOutput trace={trace} pipelineComplete={false} />
          <GuardrailChecklist result={guardrails} />
        </div>
      )}

      {view === "result" && trace && guardrails && (
        <div className="space-y-4">
          <DocumentationOutput trace={trace} pipelineComplete={pipelineComplete} />
          <GuardrailChecklist result={guardrails} />
        </div>
      )}
    </>
  );
}

function FailedBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <p className="text-sm font-medium text-red-800">
        Guardrail failed — cannot proceed. Review failing checks below.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100"
      >
        Try again
      </button>
    </div>
  );
}
