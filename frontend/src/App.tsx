import { useState } from "react";
import { UploadPanel } from "./components/UploadPanel";
import { DocumentViewer } from "./components/DocumentViewer";
import { FieldList } from "./components/FieldList";
import { correctField, verifyField, verifyDocument } from "./services/api";
import type { ExtractionResult } from "./types/api";
import { FileText, CheckCircle, Shield, FileCheck, AlertCircle } from "lucide-react";

export default function App() {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [record, setRecord] = useState<ExtractionResult | null>(null);
  const [selectedFieldName, setSelectedFieldName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUploadSuccess = (id: string, name: string) => {
    setDocumentId(id);
    setFilename(name);
    setRecord(null);
    setError(null);
  };

  const handleProcessStart = () => {
    setIsProcessing(true);
    setError(null);
  };

  const handleProcessSuccess = (result: ExtractionResult) => {
    setRecord(result);
    setIsProcessing(false);
  };

  const handleProcessFailure = (err: string) => {
    setError(err);
    setIsProcessing(false);
  };

  const handleCorrectField = async (fieldName: string, newValue: string) => {
    if (!documentId) return;
    try {
      const updated = await correctField(documentId, fieldName, newValue);
      setRecord(updated);
    } catch (err: any) {
      alert(`Failed to correct field: ${err.message}`);
    }
  };

  const handleVerifyField = async (fieldName: string) => {
    if (!documentId) return;
    try {
      const updated = await verifyField(documentId, fieldName);
      setRecord(updated);
    } catch (err: any) {
      alert(`Failed to verify field: ${err.message}`);
    }
  };

  const handleApproveDocument = async () => {
    if (!documentId) return;
    try {
      const updated = await verifyDocument(documentId);
      setRecord(updated);
    } catch (err: any) {
      alert(`Failed to approve document: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-slate-900 text-white py-4 px-6 shadow-lg border-b border-slate-950 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-650 p-2 rounded-lg">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Intelligent Land Record Digitalisation & Validation</h1>
            <p className="text-xs text-slate-400 font-medium">SIH 2026 - Document Extraction & Audit System</p>
          </div>
        </div>
        
        {record && (
          <div className="bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-mono font-bold text-slate-300">{filename}</span>
          </div>
        )}
      </header>

      {/* Main Grid Layout */}
      <main className="flex-grow p-6 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {error && (
          <div className="lg:col-span-12 bg-red-50 text-red-700 text-sm p-4 rounded-xl border border-red-200 flex gap-2 items-start shadow-sm mb-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">System Error: </span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Left Column - Document Viewer & Controls */}
        <div className="lg:col-span-7 flex flex-col gap-6 w-full">
          <UploadPanel
            onUploadSuccess={handleUploadSuccess}
            onProcessStart={handleProcessStart}
            onProcessSuccess={handleProcessSuccess}
            onProcessFailure={handleProcessFailure}
          />
          
          <DocumentViewer
            imageUrl={record ? record.image_url : null}
            fields={record ? record.fields : []}
            selectedFieldName={selectedFieldName}
            onFieldSelect={setSelectedFieldName}
          />
        </div>

        {/* Right Column - Extraction Metadata */}
        <div className="lg:col-span-5 w-full">
          {!record && !isProcessing ? (
            <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 text-center h-[500px] flex flex-col items-center justify-center text-slate-455">
              <FileCheck className="w-16 h-16 text-slate-300 mb-4 animate-bounce" />
              <h3 className="text-slate-850 font-bold text-lg mb-2">No Document Loaded</h3>
              <p className="text-sm text-slate-400 max-w-xs mx-auto leading-relaxed">
                Please upload a document on the left and trigger the core intelligence pipeline to begin extraction and audit validation checks.
              </p>
            </div>
          ) : isProcessing ? (
            <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 text-center h-[500px] flex flex-col items-center justify-center text-slate-455">
              <svg className="animate-spin h-12 w-12 text-indigo-650 mb-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <h3 className="text-slate-800 font-bold text-lg mb-1">OCR Analysis in Progress</h3>
              <p className="text-sm text-slate-450 max-w-xs mx-auto leading-relaxed">
                Running OpenCV filters, PaddleOCR, and cross-registry validations. This will take about 30 seconds...
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200 flex flex-col gap-4">
              <div className="flex justify-between items-center border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">Extracted Schema Values</h2>
                  <p className="text-xs text-slate-455 mt-0.5">Auditing land record attributes</p>
                </div>
                <span className="bg-indigo-50 text-indigo-700 text-[10px] font-bold px-2 py-0.5 rounded border border-indigo-200">
                  {record!.document_type}
                </span>
              </div>

              {/* Fields List */}
              <FieldList
                fields={record!.fields}
                selectedFieldName={selectedFieldName}
                onFieldSelect={setSelectedFieldName}
                onCorrectField={handleCorrectField}
                onVerifyField={handleVerifyField}
              />

              {/* Global Verification Action */}
              <button
                onClick={handleApproveDocument}
                className="w-full mt-4 bg-emerald-650 hover:bg-emerald-700 text-white font-bold py-3 px-4 rounded-xl transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-5 h-5 text-white" />
                Approve Entire Document
              </button>
            </div>
          )}
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-slate-900 text-slate-500 text-center py-4 border-t border-slate-950 text-xs mt-8">
        © 2026 Smart India Hackathon Prototype (SIH26018).
      </footer>
    </div>
  );
}
