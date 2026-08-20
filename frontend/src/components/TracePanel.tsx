import type { TraceChain } from "../types";

interface TracePanelProps {
  trace: TraceChain;
}

function TraceNode({
  label,
  value,
  active,
}: {
  label: string;
  value?: string;
  active: boolean;
}) {
  return (
    <div
      className={`rounded-md border px-3 py-2 ${
        active ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-slate-50"
      }`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 font-mono text-sm text-slate-800">{value ?? "—"}</p>
    </div>
  );
}

export function TracePanel({ trace }: TracePanelProps) {
  return (
    <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-600">
        Traceability chain
      </h2>
      <div className="space-y-2">
        <TraceNode label="Requirement" value={trace.requirementId} active={!!trace.requirementId} />
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            Tests
          </p>
          {trace.testIds.length > 0 ? (
            <ul className="mt-1 space-y-1">
              {trace.testIds.map((testId) => (
                <li key={testId} className="font-mono text-sm text-slate-800">
                  {testId}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-0.5 font-mono text-sm text-slate-400">—</p>
          )}
        </div>
        <TraceNode label="Execution" value={trace.executionId} active={!!trace.executionId} />
        <TraceNode label="Defect" value={trace.defectId} active={!!trace.defectId} />
      </div>
    </aside>
  );
}
