import type { Defect } from "../types";

interface DefectOutputProps {
  defect: Defect;
}

const confidenceColor: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-slate-100 text-slate-700",
};

export function DefectOutput({ defect }: DefectOutputProps) {
  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Defect ID" value={defect.defect_id} mono />
        <Field label="Status" value={defect.status} />
        <Field label="Execution ID" value={defect.execution_id} mono />
        <Field label="Test ID" value={defect.test_id} mono />
        <Field label="Classification" value={defect.classification} />
        <Field label="Severity suggestion" value={defect.severity_suggestion} />
        <Field label="Pattern flag" value={defect.pattern_flag ?? "None"} />
        <Field label="Duplicate of" value={defect.duplicate_of ?? "None"} />
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Root cause hypotheses
        </p>
        <ul className="space-y-3">
          {defect.root_cause_hypotheses.map((hypothesis, index) => (
            <li key={`${hypothesis.hypothesis}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">#{index + 1}</span>
                {hypothesis.confidence && (
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${
                      confidenceColor[hypothesis.confidence] ?? "bg-slate-100"
                    }`}
                  >
                    {hypothesis.confidence}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm text-slate-800">{hypothesis.hypothesis}</p>
              <p className="mt-2 text-xs text-slate-500">evidence_ref</p>
              <p className="font-mono text-sm text-slate-700">
                {hypothesis.evidence_ref || "—"}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
