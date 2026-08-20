import type { TestScenario } from "../types";

interface TestDesignOutputProps {
  tests: TestScenario[];
  coverageGaps: string[];
  clarificationNeeded: string[];
}

export function TestDesignOutput({
  tests,
  coverageGaps,
  clarificationNeeded,
}: TestDesignOutputProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {tests.map((test) => (
          <article
            key={test.test_id}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-mono text-sm font-semibold text-blue-700">{test.test_id}</p>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs uppercase">
                {test.type}
              </span>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                {test.acceptance_criteria_id}
              </span>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                priority: {test.priority}
              </span>
            </div>
            <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Preconditions
            </p>
            <p className="text-sm text-slate-800">{test.preconditions}</p>
            <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Steps
            </p>
            <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-800">
              {test.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Test data spec
            </p>
            <p className="text-sm text-slate-800">{test.test_data_spec}</p>
            <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Expected result
            </p>
            <p className="text-sm text-slate-800">{test.expected_result}</p>
          </article>
        ))}
      </div>

      {coverageGaps.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
            Coverage gaps (informational)
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {coverageGaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </div>
      )}

      {clarificationNeeded.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            Clarification needed (informational)
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {clarificationNeeded.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
