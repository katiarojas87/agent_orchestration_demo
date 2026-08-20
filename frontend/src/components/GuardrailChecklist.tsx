import type { GuardrailResult } from "../types";

interface GuardrailChecklistProps {
  result: GuardrailResult;
}

export function GuardrailChecklist({ result }: GuardrailChecklistProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Guardrail checks
        </h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
            result.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
          }`}
        >
          {result.passed ? "All passed" : "Failures detected"}
        </span>
      </div>
      <ul className="space-y-2">
        {result.checks.map((check) => (
          <li
            key={check.name}
            className={`rounded-md border px-3 py-2 text-sm ${
              check.passed
                ? "border-emerald-200 bg-emerald-50"
                : "border-red-200 bg-red-50"
            }`}
          >
            <div className="flex items-start gap-2">
              <span
                aria-hidden
                className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  check.passed ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
                }`}
              >
                {check.passed ? "✓" : "✕"}
              </span>
              <div>
                <p className="font-medium text-slate-800">{check.name}</p>
                <p className={`mt-0.5 ${check.passed ? "text-slate-600" : "text-red-800"}`}>
                  {check.detail}
                </p>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
