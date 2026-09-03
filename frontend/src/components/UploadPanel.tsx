import React, { useState } from "react";
import { Upload, AlertCircle, FileText, CheckCircle2, RefreshCw } from "lucide-react";

interface UploadPanelProps {
  onUploadSuccess: (docId: string, filename: string) => void;
  onProcessStart: () => void;
  onProcessSuccess: (result: any) => void;
  onProcessFailure: (err: string) => void;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  onUploadSuccess,
  onProcessStart,
  onProcessSuccess,
  onProcessFailure,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [docId, setDocId] = useState<string | null>(null);
  const [ocrLanguage, setOcrLanguage] = useState<"auto" | "en" | "ka">("auto");
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setDocId(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a document first.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const { uploadDocument } = await import("../services/api");
      const res = await uploadDocument(file);
      setDocId(res.document_id);
      onUploadSuccess(res.document_id, res.filename);
    } catch (err: any) {
      setError(err.message || "Failed to upload file.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleProcess = async () => {
    if (!docId) return;

    setIsProcessing(true);
    setError(null);
    onProcessStart();

    try {
      const { processDocument } = await import("../services/api");
      const result = await processDocument(docId, ocrLanguage);
      onProcessSuccess(result);
    } catch (err: any) {
      setError(err.message || "Failed to process document.");
      onProcessFailure(err.message || "Failed to process document.");
    } finally {
      setIsProcessing(false);
    }
  };

  const formatBytes = (bytes: number, decimals = 2) => {
    if (!bytes) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      <h2 className="text-xs font-bold text-slate-800 mb-3.5 flex items-center gap-2 tracking-wide uppercase">
        <Upload className="w-4 h-4 text-blue-600" />
        Document Intake
      </h2>

      <div className="flex flex-col gap-4">
        {/* Compact Drag-and-Drop Area */}
        {!docId ? (
          <div className="flex flex-col gap-3">
            <label className="flex flex-col items-center justify-center border border-dashed border-slate-300 rounded-lg p-5 cursor-pointer hover:border-blue-500 hover:bg-slate-50 transition-colors">
              <Upload className="w-6 h-6 text-slate-400 mb-2" />
              <span className="text-xs font-semibold text-slate-700 text-center mb-0.5">
                {file ? file.name : "Drag & drop a land record here"}
              </span>
              <span className="text-[10px] text-slate-400 text-center">
                {file ? formatBytes(file.size) : "or click to choose file"}
              </span>
              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mt-1.5">
                PNG • JPG • JPEG • PDF
              </span>
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.pdf"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>

            <label className="flex flex-col gap-1 text-[10px] font-bold text-slate-500 uppercase tracking-wide">
              Document language
              <select
                value={ocrLanguage}
                onChange={(e) => setOcrLanguage(e.target.value as "auto" | "en" | "ka")}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-2 text-xs font-semibold normal-case text-slate-700 outline-none focus:border-blue-500"
              >
                <option value="auto">Auto detect (recommended)</option>
                <option value="en">English</option>
                <option value="ka">Kannada Sale Deed</option>
              </select>
              <span className="normal-case font-medium text-slate-400">For this, Kannada forces the Karnataka Sale Deed schema and prevents Partition Deed guesses.</span>
            </label>

            {file && (
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2.5 px-4 rounded-lg transition-colors disabled:bg-blue-450 shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Uploading Document...
                  </>
                ) : (
                  "Upload File"
                )}
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 flex items-start gap-3">
              <FileText className="w-8 h-8 text-blue-500 flex-shrink-0" />
              <div className="flex flex-col min-w-0 flex-grow">
                <span className="text-xs font-bold text-slate-700 truncate">{file?.name}</span>
                <span className="text-[10px] text-slate-450 mt-0.5">
                  Size: {file ? formatBytes(file.size) : "N/A"} • ID: <span className="font-mono">{docId.substring(0, 8)}...</span>
                </span>
                <div className="flex items-center gap-1 mt-1 text-[10px] text-emerald-700 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Uploaded and Ready
                </div>
                <span className="text-[10px] text-slate-500 mt-1">OCR language: <strong>{ocrLanguage === "ka" ? "Kannada Sale Deed" : ocrLanguage === "en" ? "English" : "Auto detect"}</strong></span>
              </div>
            </div>

            <button
              onClick={handleProcess}
              disabled={isProcessing}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold py-2.5 px-4 rounded-lg transition-colors disabled:bg-emerald-450 shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Running OCR Pipeline (takes ~30s)...
                </>
              ) : (
                "Run Intelligent Pipeline"
              )}
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-rose-50 text-rose-700 text-[11px] p-3 rounded-lg border border-rose-150 flex gap-2 items-start shadow-sm font-medium">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
