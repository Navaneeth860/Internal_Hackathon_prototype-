import { useState } from "react";
import { UploadPanel } from "./components/UploadPanel";
import { DocumentViewer } from "./components/DocumentViewer";
import { FieldList } from "./components/FieldList";
import { correctField, verifyField, verifyDocument, getAuditLogs } from "./services/api";
import type { ExtractionResult } from "./types/api";
import { FileText, Shield, FileCheck, AlertCircle, CheckSquare, RefreshCw, History } from "lucide-react";

export default function App() {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [record, setRecord] = useState<ExtractionResult | null>(null);
  const [selectedFieldName, setSelectedFieldName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<"OPERATOR" | "REGISTRAR">("OPERATOR");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  const handleUploadSuccess = (id: string, name: string) => {
    setDocumentId(id);
    setFilename(name);
    setRecord(null);
    setAuditLogs([]);
    setError(null);
  };

  const handleProcessStart = () => {
    setIsProcessing(true);
    setError(null);
  };

  const fetchAuditLogs = async (id: string) => {
    try {
      const logs = await getAuditLogs(id);
      setAuditLogs(logs);
    } catch (err: any) {
      console.error("Failed to fetch audit logs:", err);
    }
  };

  const handleProcessSuccess = async (result: ExtractionResult) => {
    setRecord(result);
    setIsProcessing(false);
    setAuditLogs([]);
    if (documentId) {
      await fetchAuditLogs(documentId);
    }
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
      await fetchAuditLogs(documentId);
    } catch (err: any) {
      alert(`Failed to correct field: ${err.message}`);
    }
  };

  const handleVerifyField = async (fieldName: string) => {
    if (!documentId) return;
    try {
      const updated = await verifyField(documentId, fieldName);
      setRecord(updated);
      await fetchAuditLogs(documentId);
    } catch (err: any) {
      alert(`Failed to verify field: ${err.message}`);
    }
  };

  const handleApproveDocument = async () => {
    if (!documentId) return;
    try {
      const updated = await verifyDocument(documentId);
      setRecord(updated);
      await fetchAuditLogs(documentId);
    } catch (err: any) {
      alert(`Failed to approve document: ${err.message}`);
    }
  };

  // Compute summary metrics dynamically for SIH live score review
  const fields = record?.fields || [];
  const fieldsCount = fields.length;
  const verifiedCount = fields.filter(
    (f) => f.verification_status === "VERIFIED" || f.verification_status === "CORRECTED"
  ).length;
  const needsReviewCount = fieldsCount - verifiedCount;
  const avgConfidence = fieldsCount > 0
    ? Math.round((fields.reduce((sum, f) => sum + f.confidence, 0) / fieldsCount) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800 antialiased selection:bg-blue-100">
      
      {/* Compact Corporate Header */}
      <header className="bg-slate-900 text-white border-b border-slate-950 py-3.5 px-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg shadow-inner">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-md font-extrabold tracking-tight leading-tight flex items-center gap-2">
              Intelligent Land Record Digitalisation
              <span className="bg-blue-800 text-blue-200 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                SIH 2026
              </span>
            </h1>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wide uppercase mt-0.5">
              Secure Document Auditing & Verification Workspace
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3 flex-wrap">
          {record && (
            <div className="bg-slate-800 border border-slate-700 px-3 py-1 rounded-md flex items-center gap-1.5 max-w-[200px] sm:max-w-none">
              <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
              <span className="text-[10px] font-mono text-slate-300 truncate font-semibold">{filename}</span>
            </div>
          )}

          {/* User Role Switcher */}
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1 rounded-md">
            <span className="text-[9px] font-bold text-slate-400 uppercase">Role:</span>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value as "OPERATOR" | "REGISTRAR")}
              className="bg-transparent border-none text-[10px] text-white font-bold outline-none cursor-pointer p-0 select-none pr-1 focus:ring-0"
            >
              <option value="OPERATOR" className="bg-slate-900 text-white">Operator (Edit Only)</option>
              <option value="REGISTRAR" className="bg-slate-900 text-white">Registrar (Approve Only)</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 px-3 py-1 rounded-md text-[10px] font-bold text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            System Status: Online
          </div>
        </div>
      </header>

      {/* Main Grid Viewport */}
      <main className="flex-grow p-5 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        
        {/* Dynamic System Alert Messaging */}
        {error && (
          <div className="lg:col-span-12 bg-rose-50 text-rose-800 text-xs p-4 rounded-xl border border-rose-200 flex gap-3 items-start shadow-sm mb-1">
            <AlertCircle className="w-4.5 h-4.5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">System Error: </span>
              <span className="font-medium text-slate-700">{error}</span>
            </div>
          </div>
        )}

        {/* Left Column: workspace container */}
        <div className="lg:col-span-7 flex flex-col gap-5 w-full">
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

        {/* Right Column: panel container */}
        <div className="lg:col-span-5 w-full flex flex-col gap-4">
          {!record && !isProcessing ? (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 text-center h-[500px] flex flex-col items-center justify-center p-8 text-slate-400">
              <FileCheck className="w-12 h-12 text-slate-300 mb-3" />
              <h3 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-1">Audit Stream Idle</h3>
              <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                Ingest a land document scan and click "Run Intelligent Pipeline" to trigger OCR parsing, registry validations, and confidence metrics.
              </p>
            </div>
          ) : isProcessing ? (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 text-center h-[500px] flex flex-col items-center justify-center p-8 text-slate-400">
              <RefreshCw className="animate-spin h-10 w-10 text-blue-600 mb-4" />
              <h3 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-1">Analyzing Document</h3>
              <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                Applying OpenCV adaptive thresholding, running PaddleOCR localization engines, and matching records against official state registries.
              </p>
            </div>
          ) : (
            <>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col gap-4">
                
                {/* Document Overview Summary Box */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                    Document Analysis Summary
                  </span>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="flex flex-col border-r border-slate-200">
                      <span className="text-sm font-extrabold text-slate-800">{fieldsCount}</span>
                      <span className="text-[9px] text-slate-450 font-bold uppercase mt-0.5">Schema Fields</span>
                    </div>
                    <div className="flex flex-col border-r border-slate-200">
                      <span className="text-sm font-extrabold text-emerald-600">{verifiedCount}</span>
                      <span className="text-[9px] text-slate-455 font-bold uppercase mt-0.5">Approved</span>
                    </div>
                    <div className="flex flex-col border-r border-slate-200">
                      <span className="text-sm font-extrabold text-amber-600">{needsReviewCount}</span>
                      <span className="text-[9px] text-slate-455 font-bold uppercase mt-0.5">Needs Review</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-extrabold text-blue-600">{avgConfidence}%</span>
                      <span className="text-[9px] text-slate-455 font-bold uppercase mt-0.5">Avg Conf</span>
                    </div>
                  </div>
                </div>

                {/* Header Title */}
                <div className="flex justify-between items-center pb-2.5 border-b border-slate-100">
                  <div>
                    <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Extracted Schema Attributes
                    </h2>
                    <p className="text-[10px] text-slate-400 mt-0.5 font-medium">Verify or correct values relative to source text.</p>
                  </div>
                  <span className="bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blue-200 tracking-wide uppercase">
                    {record!.document_type}
                  </span>
                </div>

                {/* Scrollable Fields List */}
                <FieldList
                  fields={record!.fields}
                  selectedFieldName={selectedFieldName}
                  onFieldSelect={setSelectedFieldName}
                  onCorrectField={handleCorrectField}
                  onVerifyField={handleVerifyField}
                  canCorrect={userRole === "OPERATOR"}
                  canVerify={userRole === "REGISTRAR"}
                />

                {/* Global Verification Footer Action */}
                <div className="mt-2 border-t border-slate-100 pt-4 flex flex-col gap-2.5">
                  <div className="flex justify-between items-center text-[11px] text-slate-500 font-semibold px-1">
                    <span>Audit Progress:</span>
                    <span>{verifiedCount} of {fieldsCount} fields approved</span>
                  </div>
                  
                  <button
                    onClick={handleApproveDocument}
                    disabled={userRole !== "REGISTRAR"}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 px-4 rounded-lg transition-all shadow-sm hover:shadow flex items-center justify-center gap-1.5 cursor-pointer text-xs uppercase tracking-wider disabled:bg-slate-200 disabled:text-slate-450 disabled:cursor-not-allowed"
                  >
                    <CheckSquare className="w-4 h-4 text-white" />
                    Approve Entire Document
                  </button>
                </div>
              </div>

              {/* Collapsible Persistent Audit Trail History Panel */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col gap-3">
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
                  <History className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  Audit Trail History Logs
                </span>
                {auditLogs.length === 0 ? (
                  <div className="text-xs text-slate-400 italic text-center py-4">
                    No actions logged for this record yet.
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 max-h-[160px] overflow-y-auto pr-1">
                    {auditLogs.map((log) => (
                      <div key={log.id} className="bg-slate-50 border border-slate-200 p-2 rounded text-[11px] leading-relaxed shadow-sm">
                        <div className="flex justify-between font-bold text-slate-500 mb-1 text-[9px] uppercase tracking-wide">
                          <span className={log.user_role === "REGISTRAR" ? "text-emerald-700" : "text-blue-700"}>
                            {log.user_role} - {log.action}
                          </span>
                          <span className="text-slate-400 font-medium normal-case">
                            {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                        <div className="text-slate-700 font-medium">
                          <span className="font-bold text-slate-800 mr-1 uppercase text-[9px] tracking-wide">
                            {log.field_name.replace("_", " ")}:
                          </span>
                          {log.action === "CORRECTED" ? (
                            <span>
                              Changed from <span className="line-through text-rose-500 bg-rose-50/50 px-1 py-0.5 rounded font-mono font-semibold">"{log.old_value || "[None]"}"</span> to <span className="font-semibold text-emerald-700 bg-emerald-50/50 px-1 py-0.5 rounded font-mono">"{log.new_value}"</span>
                            </span>
                          ) : (
                            <span>
                              Approved value <span className="font-semibold text-emerald-700 bg-emerald-50/50 px-1 py-0.5 rounded font-mono">"{log.new_value}"</span>
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-slate-900 text-slate-500 text-center py-3.5 border-t border-slate-950 text-[10px] font-medium tracking-wide uppercase mt-8">
        Smart India Hackathon 2026 • Problem SIH26018 Prototype System
      </footer>
    </div>
  );
}
