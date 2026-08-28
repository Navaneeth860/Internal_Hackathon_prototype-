import React from "react";
import { AlertTriangle } from "lucide-react";

interface ValidationWarningsProps {
  warnings: string[];
}

export const ValidationWarnings: React.FC<ValidationWarningsProps> = ({ warnings }) => {
  if (warnings.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mt-3">
      {warnings.map((w, idx) => (
        <div 
          key={idx} 
          className="bg-amber-50/70 text-amber-800 text-[11px] px-3 py-2.5 rounded-lg border border-amber-200/80 flex items-start gap-2 shadow-sm"
        >
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex flex-col">
            <span className="font-bold text-amber-900 mb-0.5">Validation Alert</span>
            <span className="leading-relaxed font-medium text-slate-700">{w}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
