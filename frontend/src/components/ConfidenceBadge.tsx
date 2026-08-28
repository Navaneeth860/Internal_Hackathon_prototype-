import React from "react";

interface ConfidenceBadgeProps {
  score: number;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score }) => {
  // Multiply by 100 since confidence values are floats [0.0, 1.0]
  const percentage = Math.round(score * 100);
  
  let colorClass = "bg-red-50 text-red-700 border-red-200";
  if (score >= 0.85) {
    colorClass = "bg-green-50 text-green-700 border-green-200";
  } else if (score >= 0.70) {
    colorClass = "bg-amber-50 text-amber-700 border-amber-200";
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${colorClass}`}>
      {percentage}% Heuristic
    </span>
  );
};

