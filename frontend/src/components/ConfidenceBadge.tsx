import React from "react";

interface ConfidenceBadgeProps {
  score: number;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score }) => {
  const percentage = Math.round(score * 100);
  
  let colorBg = "bg-rose-500";
  let colorText = "text-rose-700";
  
  if (score >= 0.85) {
    colorBg = "bg-emerald-500";
    colorText = "text-emerald-700";
  } else if (score >= 0.70) {
    colorBg = "bg-amber-500";
    colorText = "text-amber-700";
  }

  return (
    <div className="w-full mt-2">
      <div className="flex justify-between items-center text-[11px] text-slate-500 font-semibold mb-1">
        <span>Heuristic Confidence</span>
        <span className={`font-bold ${colorText}`}>{percentage}%</span>
      </div>
      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ${colorBg}`} 
          style={{ width: `${percentage}%` }} 
        />
      </div>
    </div>
  );
};
