import React, { useState } from "react";
import { Edit2, Check, X, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";
import type { ExtractedField } from "../types/api";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ValidationWarnings } from "./ValidationWarnings";

interface FieldCardProps {
  field: ExtractedField;
  isSelected: boolean;
  onSelect: () => void;
  onCorrect: (newValue: string) => Promise<void>;
  onVerify: () => Promise<void>;
}

export const FieldCard: React.FC<FieldCardProps> = ({
  field,
  isSelected,
  onSelect,
  onCorrect,
  onVerify,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(field.value || "");
  const [showEvidence, setShowEvidence] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Format field names (e.g., owner_name -> Owner Name)
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

  // Status badge styling
  const getStatusBadge = () => {
    switch (field.verification_status) {
      case "VERIFIED":
        return (
          <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 border border-emerald-200">
            <CheckCircle className="w-3 h-3 text-emerald-600" /> APPROVED
          </span>
        );
      case "CORRECTED":
        return (
          <span className="bg-amber-50 text-amber-700 text-[10px] font-bold px-2 py-0.5 rounded border border-amber-250">
            ✏ CORRECTED
          </span>
        );
      default:
        return (
          <span className="bg-slate-50 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded border border-slate-200">
            UNVERIFIED
          </span>
        );
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-xl p-5 border transition-all duration-200 cursor-pointer ${
        isSelected
          ? "border-indigo-600 ring-2 ring-indigo-100"
          : "border-slate-200 hover:border-slate-350 hover:shadow-sm"
      }`}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div className="flex flex-col w-full">
          <span className="text-[11px] font-bold text-indigo-650 uppercase tracking-wider">
            {formatFieldName(field.name)}
          </span>
          {/* Active Value */}
          {!isEditing ? (
            <span className={`text-base font-bold mt-1 break-all ${field.value ? "text-slate-800" : "text-slate-400 italic"}`}>
              {field.value || "[Field Not Detected]"}
            </span>
          ) : (
            <form onSubmit={handleCorrectSubmit} className="flex gap-2 mt-1.5 w-full items-center" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="border border-slate-300 rounded px-2.5 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-650 w-full"
                disabled={isSubmitting}
                autoFocus
              />
              <button
                type="submit"
                disabled={isSubmitting}
                className="bg-indigo-655 text-white p-1 rounded hover:bg-indigo-700 transition-colors"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                disabled={isSubmitting}
                className="bg-slate-100 text-slate-600 p-1 rounded hover:bg-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </form>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          {getStatusBadge()}
          <ConfidenceBadge score={field.confidence} />
        </div>
      </div>

      {/* Provenance: show original value if corrected */}
      {field.verification_status === "CORRECTED" && (
        <div className="text-[11px] text-slate-400 mt-1.5">
          Original extracted: <span className="font-mono bg-slate-50 px-1 py-0.5 rounded border border-slate-100 text-slate-500 font-semibold">{field.original_value || "[None]"}</span>
        </div>
      )}

      {/* Warnings */}
      <ValidationWarnings warnings={field.validation_warnings} />

      {/* Field Actions */}
      {!isEditing && (
        <div className="flex gap-3 mt-3 pt-3 border-t border-slate-100 justify-end" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => setIsEditing(true)}
            disabled={isSubmitting}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1"
          >
            <Edit2 className="w-3 h-3" /> Correct
          </button>
          
          {field.verification_status !== "VERIFIED" && (
            <button
              onClick={handleVerifyClick}
              disabled={isSubmitting}
              className="text-xs text-emerald-600 hover:text-emerald-800 font-bold flex items-center gap-1"
            >
              <Check className="w-3 h-3" /> Approve
            </button>
          )}
        </div>
      )}

      {/* Evidence details drawer toggle */}
      <div className="mt-2" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => setShowEvidence(!showEvidence)}
          className="w-full text-left text-[11px] text-slate-400 hover:text-slate-655 flex items-center gap-0.5 py-1"
        >
          {showEvidence ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {showEvidence ? "Hide Evidence Details" : "Show Evidence Details"}
        </button>

        {showEvidence && (
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] text-slate-500 mt-1.5 space-y-1.5 font-medium leading-relaxed">
            <div>
              <span className="font-bold text-slate-600">OCR Evidence Block(s):</span>
              {field.source_elements.length === 0 ? (
                <div className="text-slate-400 italic">No spatial source blocks linked to this field.</div>
              ) : (
                field.source_elements.map((el, index) => (
                  <div key={index} className="bg-white border border-slate-100 p-1.5 rounded mt-1.5 font-mono text-[9px] break-words shadow-sm">
                    "{el.text}" (Conf: {Math.round(el.confidence * 100)}%)
                  </div>
                ))
              )}
            </div>
            {field.explanation && (
              <div>
                <span className="font-bold text-slate-600">Pipeline Reasoning:</span>
                <p className="text-slate-450 mt-0.5">{field.explanation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
