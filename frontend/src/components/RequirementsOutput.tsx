import { GuardrailChecklist } from "./GuardrailChecklist";
import type { Requirement } from "../types";

interface RequirementsOutputProps {
  requirement: Requirement;
}

export function RequirementsOutput({ requirement }: RequirementsOutputProps) {
  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Requirement ID
        </p>
        <p className="font-mono text-sm">{requirement.requirement_id}</p>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</p>
        <p className="text-sm">{requirement.status}</p>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Derived from
        </p>
        <p className="font-mono text-sm">{requirement.derived_from}</p>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Statement
        </p>
        <p className="text-sm leading-relaxed text-slate-800">{requirement.statement}</p>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Acceptance criteria
        </p>
        <ul className="space-y-3">
          {requirement.acceptance_criteria.map((ac) => (
            <li key={ac.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="font-mono text-xs font-semibold text-blue-700">{ac.id}</p>
              <p className="mt-1 text-sm text-slate-800">{ac.text}</p>
              <p className="mt-2 text-xs text-slate-500">source_ref</p>
              <p className="text-sm italic text-slate-700">{ac.source_ref || "—"}</p>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Open questions
        </p>
        {requirement.open_questions.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
            {requirement.open_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">None</p>
        )}
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Possible duplicates
        </p>
        {requirement.possible_duplicates.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {requirement.possible_duplicates.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">None</p>
        )}
      </div>
    </div>
  );
}

export { GuardrailChecklist };
