import React from "react";
import { AlertTriangle } from "lucide-react";

interface ValidationWarningsProps {
  warnings: string[];
}

export const ValidationWarnings: React.FC<ValidationWarningsProps> = ({ warnings }) => {
  if (warnings.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5 mt-2">
      {warnings.map((w, idx) => (
        <div 
          key={idx} 
          className="bg-rose-50 text-rose-700 text-xs px-3 py-2 rounded-lg border border-rose-100 flex items-start gap-2"
        >
          <AlertTriangle className="w-4.5 h-4.5 text-rose-500 flex-shrink-0 mt-0.5" />
          <span className="leading-relaxed font-medium">{w}</span>
        </div>
      ))}
    </div>
  );
};

