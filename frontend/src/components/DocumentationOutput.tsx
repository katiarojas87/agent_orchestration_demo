import type { TraceRecord } from "../types";

interface DocumentationOutputProps {
  trace: TraceRecord;
  pipelineComplete: boolean;
}

const ID_PATTERN =
  /(REQ-[A-Z]+-\d+|TC-[A-Z]+-\d+-\d+|EXEC-[A-Z]+-\d+-\d+|DEF-[A-Z]+-\d+)/g;

function renderNarrative(narrative: string) {
  const parts = narrative.split(ID_PATTERN);
  return parts.map((part, index) =>
    ID_PATTERN.test(part) ? (
      <span key={`${part}-${index}`} className="rounded bg-blue-100 px-1 font-mono text-sm text-blue-800">
        {part}
      </span>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    ),
  );
}

export function DocumentationOutput({ trace, pipelineComplete }: DocumentationOutputProps) {
  return (
    <div className="space-y-4">
      {pipelineComplete && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
          Pipeline complete — traceability report generated.
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Requirement ID
            </p>
            <p className="font-mono text-sm">{trace.requirement_id}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Status
            </p>
            <p className="text-sm">{trace.status}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Last synced
            </p>
            <p className="font-mono text-sm">{trace.last_synced}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Narrative
        </p>
        <p className="text-sm leading-relaxed text-slate-800">{renderNarrative(trace.narrative)}</p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Trace
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <TraceList title="Tests" items={trace.trace.tests} />
          <TraceList title="Executions" items={trace.trace.executions} />
          <TraceList title="Defects" items={trace.trace.defects} />
        </div>
      </div>

      {trace.gaps.length > 0 ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Gaps</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {trace.gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          No gaps reported.
        </div>
      )}
    </div>
  );
}

function TraceList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item) => (
          <li key={item} className="font-mono text-sm text-slate-800">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
