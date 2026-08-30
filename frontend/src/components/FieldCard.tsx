import React, { useState } from "react";
import { Edit2, Check, X, CheckCircle, ChevronDown, ChevronUp, AlertTriangle, FileText } from "lucide-react";
import type { ExtractedField } from "../types/api";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ValidationWarnings } from "./ValidationWarnings";

interface FieldCardProps {
  field: ExtractedField;
  isSelected: boolean;
  onSelect: () => void;
  onCorrect: (newValue: string) => Promise<void>;
  onVerify: () => Promise<void>;
  canCorrect: boolean;
  canVerify: boolean;
}

export const FieldCard: React.FC<FieldCardProps> = ({
  field,
  isSelected,
  onSelect,
  onCorrect,
  onVerify,
  canCorrect,
  canVerify,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(field.value || "");
  const [showEvidence, setShowEvidence] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const formatFieldName = (name: string) => {
    return name
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  const handleCorrectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onCorrect(editValue);
      setIsEditing(false);
    } catch (err) {
      alert("Failed to submit correction.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyClick = async () => {
    setIsSubmitting(true);
    try {
      await onVerify();
    } catch (err) {
      alert("Failed to verify field.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Determine border and background accents based on validation and verification state
  const hasWarnings = field.validation_warnings.length > 0;
  const isVerified = field.verification_status === "VERIFIED";
  const isCorrected = field.verification_status === "CORRECTED";
  const isLowConfidence = field.confidence < 0.70;

  let stateBorderClass = "border-slate-200";
  let stateBgClass = "bg-white";
  let statusBadge = null;

  if (isVerified) {
    stateBorderClass = "border-emerald-300 ring-1 ring-emerald-50";
    stateBgClass = "bg-emerald-50/10";
    statusBadge = (
      <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200">
        <CheckCircle className="w-3 h-3 text-emerald-600" /> VERIFIED
      </span>
    );
  } else if (isCorrected) {
    stateBorderClass = "border-indigo-300 ring-1 ring-indigo-50";
    stateBgClass = "bg-indigo-50/10";
    statusBadge = (
      <span className="bg-indigo-50 text-indigo-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1">
        ✏ CORRECTED
      </span>
    );
  } else if (hasWarnings || isLowConfidence) {
    stateBorderClass = "border-amber-300 ring-1 ring-amber-50";
    stateBgClass = "bg-amber-50/10";
    statusBadge = (
      <span className="bg-amber-50 text-amber-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-250 flex items-center gap-1">
        <AlertTriangle className="w-3 h-3 text-amber-600" /> REVIEW REQUIRED
      </span>
    );
  } else {
    // Normal parsed unverified
    stateBorderClass = "border-slate-200";
    stateBgClass = "bg-white";
    statusBadge = (
      <span className="bg-slate-50 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full border border-slate-200">
        UNVERIFIED
      </span>
    );
  }

  // Double down on highlight borders when selected
  const activeClass = isSelected 
    ? "border-blue-600 ring-2 ring-blue-100" 
    : stateBorderClass;

  return (
    <div
      onClick={onSelect}
      className={`rounded-xl p-4.5 border transition-all duration-200 cursor-pointer ${stateBgClass} ${activeClass}`}
    >
      {/* Field Identification Header */}
      <div className="flex justify-between items-start gap-2 mb-2">
        <div className="flex flex-col w-full">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            {formatFieldName(field.name)}
          </span>
          
          {/* Field Values */}
          {!isEditing ? (
            <div className="flex flex-col mt-0.5">
              <span className={`text-sm font-bold break-all ${field.value ? "text-slate-800" : "text-slate-400 italic"}`}>
                {field.value || "Not Detected"}
              </span>
              
              {/* Provenance Trail */}
              {isCorrected && (
                <span className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-medium">
                  Original: <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-500 font-semibold">{field.original_value || "[None]"}</span>
                </span>
              )}
            </div>
          ) : (
            <form onSubmit={handleCorrectSubmit} className="flex gap-2 mt-1.5 w-full items-center" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-blue-650 w-full"
                disabled={isSubmitting}
                autoFocus
              />
              <button
                type="submit"
                disabled={isSubmitting}
                className="bg-blue-600 text-white p-1 rounded hover:bg-blue-700 transition-colors cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                disabled={isSubmitting}
                className="bg-slate-100 text-slate-600 p-1 rounded hover:bg-slate-200 transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </form>
          )}
        </div>

        {/* Status Badges */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          {statusBadge}
        </div>
      </div>

      {/* Confidence Indicator */}
      <ConfidenceBadge score={field.confidence} />

      {/* Validation Warning Cards */}
      <ValidationWarnings warnings={field.validation_warnings} />

      {/* Audit Action Controls */}
      {!isEditing && (
      {!isEditing && (canCorrect || (canVerify && field.verification_status !== "VERIFIED")) && (
        <div className="flex gap-3 mt-3 pt-2.5 border-t border-slate-100 justify-end" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => setIsEditing(true)}
            disabled={isSubmitting}
            className="text-xs text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1 transition-colors cursor-pointer"
          >
            <Edit2 className="w-3 h-3" /> Correct
          </button>
          {canCorrect && (
            <button
              onClick={() => setIsEditing(true)}
              disabled={isSubmitting}
              className="text-xs text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Edit2 className="w-3 h-3" /> Correct
            </button>
          )}
          
          {field.verification_status !== "VERIFIED" && (
          {canVerify && field.verification_status !== "VERIFIED" && (
            <button
              onClick={handleVerifyClick}
              disabled={isSubmitting}
              className="text-xs text-emerald-600 hover:text-emerald-800 font-bold flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Check className="w-3 h-3" /> Approve
            </button>
          )}
        </div>
      )}

      {/* Audit Evidence Expansion */}
      <div className="mt-2.5" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => setShowEvidence(!showEvidence)}
          className="w-full text-left text-[10px] text-slate-400 hover:text-slate-600 flex items-center gap-0.5 py-1 font-semibold tracking-wide"
        >
          {showEvidence ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {showEvidence ? "Hide Audit Evidence" : "View Audit Evidence"}
        </button>

        {showEvidence && (
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[10px] text-slate-500 mt-2 space-y-2 leading-relaxed shadow-inner">
            <div className="flex items-center gap-1 border-b border-slate-200 pb-1 text-slate-600 font-bold uppercase tracking-wider text-[9px]">
              <FileText className="w-3 h-3 text-blue-500" />
              Extraction Details
            </div>
            
            <div className="grid grid-cols-2 gap-1.5">
              <div>
                <span className="font-bold text-slate-600 block">Extraction Mode</span>
                <span className="text-slate-450 font-medium">Regex Rules / Spatial Mapping</span>
              </div>
              <div>
                <span className="font-bold text-slate-600 block">Overlay BBox</span>
                <span className="text-emerald-600 font-bold">✓ Available</span>
              </div>
            </div>

            <div>
              <span className="font-bold text-slate-600 block mb-1">OCR Raw Detections</span>
              {field.source_elements.length === 0 ? (
                <div className="text-slate-400 italic">No spatial source blocks linked to this field.</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {field.source_elements.map((el, index) => (
                    <div key={index} className="bg-white border border-slate-200 p-1.5 rounded font-mono text-[9px] break-all flex justify-between shadow-sm">
                      <span className="text-slate-700">"{el.text}"</span>
                      <span className="text-blue-600 font-bold ml-2">Conf: {Math.round(el.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {field.explanation && (
              <div>
                <span className="font-bold text-slate-600 block mb-0.5">Pipeline Logic Notes</span>
                <p className="text-slate-500 font-medium bg-white border border-slate-250 p-2 rounded text-[9.5px]">
                  {field.explanation}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
