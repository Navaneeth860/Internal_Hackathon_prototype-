import React, { useState, useRef } from "react";
import type { ExtractedField } from "../types/api";
import { ZoomIn, ZoomOut, Maximize2, Minimize2, Image as ImageIcon } from "lucide-react";

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
  const [zoom, setZoom] = useState<number>(100);
  const [fit, setFit] = useState<boolean>(true);
  const viewportRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = () => {
    setFit(false);
    setZoom((prev) => Math.min(prev + 25, 400));
  };

  const handleZoomOut = () => {
    setFit(false);
    setZoom((prev) => Math.max(prev - 25, 25));
  };

  const handleFit = () => {
    setFit(true);
    setZoom(100);
  };

  const handleActualSize = () => {
    setFit(false);
    setZoom(100);
  };

  if (!imageUrl) {
    return (
      <div className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl h-[550px] flex flex-col items-center justify-center p-6 text-slate-400">
        <ImageIcon className="w-10 h-10 mb-3 text-slate-300 animate-pulse" />
        <span className="font-semibold text-xs uppercase tracking-wider text-slate-500">Document Workspace</span>
        <span className="text-[11px] mt-1.5 text-slate-400 text-center max-w-xs leading-relaxed">
          Upload and run the extraction pipeline to populate this viewer canvas with spatial OCR overlays.
        </span>
      </div>
    );
  }

  const host = window.location.hostname || "localhost";
  const fullImageUrl = `http://${host}:8000${imageUrl}`;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
      {/* Interactive Toolbar */}
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-2 flex items-center justify-between">
        <span className="text-xs font-bold text-slate-700 tracking-wide uppercase flex items-center gap-1.5">
          <ImageIcon className="w-3.5 h-3.5 text-blue-600" />
          Document Canvas
        </span>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            disabled={!fit && zoom <= 25}
            className="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-200 transition-colors cursor-pointer disabled:opacity-40"
          >
            <ZoomOut className="w-4 h-4" />
          </button>

          <span className="text-[11px] font-mono font-bold text-slate-600 min-w-[40px] text-center">
            {fit ? "Fit" : `${zoom}%`}
          </span>

          <button
            onClick={handleZoomIn}
            title="Zoom In"
            disabled={!fit && zoom >= 400}
            className="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-200 transition-colors cursor-pointer disabled:opacity-40"
          >
            <ZoomIn className="w-4 h-4" />
          </button>

          <div className="h-4 w-[1px] bg-slate-300 mx-1" />

          <button
            onClick={handleFit}
            title="Fit to Container"
            className={`p-1 rounded transition-colors cursor-pointer ${
              fit
                ? "bg-blue-50 text-blue-600 font-bold"
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-200"
            }`}
          >
            <Minimize2 className="w-4 h-4" />
          </button>

          <button
            onClick={handleActualSize}
            title="Actual Size (100%)"
            className={`p-1 rounded transition-colors cursor-pointer ${
              !fit && zoom === 100
                ? "bg-blue-50 text-blue-600 font-bold"
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-200"
            }`}
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Document Viewport — scrollable when zoomed in */}
      <div
        ref={viewportRef}
        className="bg-slate-100 overflow-auto"
        style={{ minHeight: "500px", maxHeight: "650px" }}
      >
        {/* Inner wrapper: fit mode = full width constrained; zoom mode = explicit scaled size */}
        <div
          className="relative inline-block shadow-md rounded overflow-hidden bg-white"
          style={
            fit
              ? { width: "100%", display: "block" }
              : {
                  // Scale from top-left so scrolling to the zoomed area is natural
                  transformOrigin: "top left",
                  transform: `scale(${zoom / 100})`,
                  // Reserve the post-scale space so the scroll container knows the size
                  width: `${(100 / zoom) * 100}%`,
                  marginLeft: "auto",
                  marginRight: "auto",
                }
          }
        >
          {/* Preprocessed document image */}
          <img
            src={fullImageUrl}
            alt="Preprocessed Land Record"
            className="w-full h-auto block select-none"
            draggable={false}
          />

          {/* SVG Bounding Box Overlays — viewBox 0 0 1 1 with normalized coords */}
          <svg
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
          >
            {fields.map((field) => {
              const isSelected = field.name === selectedFieldName;
              const hasSelection = selectedFieldName !== null;
              const dimClass = hasSelection && !isSelected ? "opacity-20" : "opacity-100";

              return field.source_elements.map((element, elIdx) => {
                if (!element.normalized_bbox) return null;

                const points = element.normalized_bbox
                  .map(([x, y]) => `${x},${y}`)
                  .join(" ");

                return (
                  <polygon
                    key={`${field.name}-${elIdx}`}
                    points={points}
                    className={`pointer-events-auto cursor-pointer transition-all duration-200 ${dimClass} ${
                      isSelected
                        ? "fill-blue-500/20 stroke-blue-600 stroke-[0.005]"
                        : "fill-blue-500/0 hover:fill-blue-500/10 stroke-blue-500/30 stroke-[0.002]"
                    }`}
                    onClick={() => onFieldSelect(field.name)}
                  >
                    <title>{`${field.name.replace(/_/g, " ").toUpperCase()}: ${element.text}`}</title>
                  </polygon>
                );
              });
            })}
          </svg>
        </div>
      </div>

      <div className="bg-slate-50 border-t border-slate-200 px-4 py-2 text-[10px] text-slate-400 font-medium flex items-center justify-between">
        <span>💡 Click a region to highlight the field. Hover shows the schema name.</span>
        <span>{fit ? "Fit Mode" : `Zoom: ${zoom}%`}</span>
      </div>
    </div>
  );
};
