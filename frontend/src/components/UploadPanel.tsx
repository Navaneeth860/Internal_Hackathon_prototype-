import React, { useState } from "react";
import { Upload, AlertCircle, FileText } from "lucide-react";

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
      const result = await processDocument(docId);
      onProcessSuccess(result);
    } catch (err: any) {
      setError(err.message || "Failed to process document.");
      onProcessFailure(err.message || "Failed to process document.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <Upload className="w-5 h-5 text-indigo-600" />
        Upload & Process Document
      </h2>

      <div className="flex flex-col gap-4">
        {/* File Select Input */}
        <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg p-6 cursor-pointer hover:border-indigo-500 hover:bg-indigo-50 transition-colors">
          <FileText className="w-8 h-8 text-slate-400 mb-2" />
          <span className="text-sm font-medium text-slate-600 text-center break-all max-w-full">
            {file ? file.name : "Select PNG, JPG, JPEG, or PDF"}
          </span>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            className="hidden"
            onChange={handleFileChange}
          />
        </label>

        {/* Upload Button */}
        {file && !docId && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:bg-indigo-400"
          >
            {isUploading ? "Uploading file..." : "Upload Document"}
          </button>
        )}

        {/* Process Button */}
        {docId && (
          <div className="flex flex-col gap-2">
            <div className="bg-green-50 text-green-700 text-sm font-medium p-3 rounded-lg border border-green-200">
              ✓ Document uploaded! ID: <span className="font-mono text-xs">{docId}</span>
            </div>
            <button
              onClick={handleProcess}
              disabled={isProcessing}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors disabled:bg-emerald-400 flex items-center justify-center gap-2"
            >
              {isProcessing ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing OCR (takes ~30s)...
                </>
              ) : (
                "Run Core Intelligence Pipeline"
              )}
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200 flex gap-2 items-start">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

