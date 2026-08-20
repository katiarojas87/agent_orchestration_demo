import type { StageKey } from "../types";

const STAGES: { key: StageKey; label: string; chip: "GATE" | "AUDIT" }[] = [
  { key: "requirements", label: "Requirements Analysis", chip: "GATE" },
  { key: "test_design", label: "Test Design", chip: "GATE" },
  { key: "defect_analysis", label: "Defect Analysis", chip: "GATE" },
  { key: "documentation", label: "Documentation", chip: "AUDIT" },
];

interface StepperProps {
  currentStage: StageKey;
  completedStages: Set<StageKey>;
  onSelect: (stage: StageKey) => void;
}

export function Stepper({ currentStage, completedStages, onSelect }: StepperProps) {
  return (
    <nav className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ol className="flex flex-wrap items-center gap-3">
        {STAGES.map((stage, index) => {
          const isCurrent = stage.key === currentStage;
          const isComplete = completedStages.has(stage.key);
          const chipClass =
            stage.chip === "GATE"
              ? "bg-orange-100 text-orange-800"
              : "bg-teal-100 text-teal-800";

          return (
            <li key={stage.key} className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => onSelect(stage.key)}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-left transition ${
                  isCurrent
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                    isCurrent
                      ? "bg-white/20 text-white"
                      : isComplete
                        ? "bg-emerald-600 text-white"
                        : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {isComplete ? "✓" : index + 1}
                </span>
                <span className="text-sm font-medium">{stage.label}</span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    isCurrent ? "bg-white/20 text-white" : chipClass
                  }`}
                >
                  {stage.chip}
                </span>
              </button>
              {index < STAGES.length - 1 && (
                <span className="hidden text-slate-300 sm:inline">→</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
