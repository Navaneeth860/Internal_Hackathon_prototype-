import React from "react";
import type { ExtractedField } from "../types/api";

interface DocumentViewerProps {
  imageUrl: string | null;
  fields: ExtractedField[];
  selectedFieldName: string | null;
  onFieldSelect: (fieldName: string) => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  imageUrl,
  fields,
  selectedFieldName,
  onFieldSelect,
}) => {
  if (!imageUrl) {
    return (
      <div className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl h-[600px] flex flex-col items-center justify-center p-6 text-slate-400">
        <svg className="w-12 h-12 mb-3 text-slate-300 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span className="font-medium text-sm">No processed document image to display.</span>
        <span className="text-xs mt-1 text-slate-350 text-center">Run the intelligence pipeline to view coordinate evidence.</span>
      </div>
    );
  }

  const host = window.location.hostname || "localhost";
  const fullImageUrl = `http://${host}:8000${imageUrl}`;

  return (
    <div className="bg-white rounded-xl shadow-md p-4 border border-slate-200">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Document Coordinate Evidence</h3>
      
      <div className="relative w-full overflow-hidden border border-slate-100 rounded-lg bg-slate-50">
        {/* Render preprocessed document image */}
        <img
          src={fullImageUrl}
          alt="Preprocessed Land Record"
          className="w-full h-auto block select-none"
        />

        {/* SVG Bounding Box Overlays */}
        <svg
          viewBox="0 0 1 1"
          preserveAspectRatio="none"
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
        >
          {fields.map((field) => {
            const isSelected = field.name === selectedFieldName;
            return field.source_elements.map((element, elIdx) => {
              if (!element.normalized_bbox) return null;
              
              // Convert coordinate array to string "x,y x,y x,y x,y"
              const points = element.normalized_bbox
                .map(([x, y]) => `${x},${y}`)
                .join(" ");

              return (
                <polygon
                  key={`${field.name}-${elIdx}`}
                  points={points}
                  className={`pointer-events-auto cursor-pointer transition-all duration-200 ${
                    isSelected
                      ? "fill-indigo-500/20 stroke-indigo-600 stroke-[0.005]"
                      : "fill-indigo-500/0 hover:fill-indigo-500/15 stroke-indigo-500/40 stroke-[0.002]"
                  }`}
                  onClick={() => onFieldSelect(field.name)}
                >
                  <title>{`${field.name}: ${element.text}`}</title>
                </polygon>
              );
            });
          })}
        </svg>
      </div>
      
      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
        <span>💡 Hover/Click bounding boxes to locate metadata.</span>
        <span>Coordinates: 0.0 - 1.0 Normalized</span>
      </div>
    </div>
  );
};
