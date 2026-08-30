import React from 'react';
import { Database, RefreshCw, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface RecordItem {
  id: string;
  filename: string;
  document_subtype: string;
  extraction_method: string;
  average_confidence: number;
  verification_status: 'VERIFIED' | 'PENDING';
  upload_date: string;
}

interface RepositoryPanelProps {
  records: RecordItem[];
  onSelectRecord: (recordId: string) => void;
  onRefresh: () => void;
  selectedId?: string | null;
}

export const RepositoryPanel: React.FC<RepositoryPanelProps> = ({
  records,
  onSelectRecord,
  onRefresh,
  selectedId
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col h-[280px]">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-indigo-600" />
          <h2 className="text-slate-800 font-bold text-sm uppercase tracking-wider">Document Repository</h2>
          <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full font-medium">
            {records.length}
          </span>
        </div>
        <button
          onClick={onRefresh}
          className="p-1.5 hover:bg-slate-50 active:bg-slate-100 rounded text-slate-500 transition-colors"
          title="Refresh repository"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="overflow-y-auto flex-1 pr-1">
        {records.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 text-xs py-4 text-center">
            <p>No documents processed yet.</p>
            <p className="text-slate-400 mt-1">Upload a document to add it to the repository.</p>
          </div>
        ) : (
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-100">
                <th className="py-2 font-semibold">Filename</th>
                <th className="py-2 font-semibold">Subtype</th>
                <th className="py-2 font-semibold text-center">Avg Conf</th>
                <th className="py-2 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {records.map((rec) => {
                const isSelected = selectedId === rec.id;
                return (
                  <tr
                    key={rec.id}
                    onClick={() => onSelectRecord(rec.id)}
                    className={`cursor-pointer hover:bg-slate-50 transition-colors ${
                      isSelected ? 'bg-indigo-50/50 hover:bg-indigo-50 font-medium' : ''
                    }`}
                  >
                    <td className="py-2.5 max-w-[180px] truncate pr-2 flex items-center gap-1.5 font-mono">
                      <FileText className={`w-3.5 h-3.5 ${isSelected ? 'text-indigo-600' : 'text-slate-400'}`} />
                      {rec.filename}
                    </td>
                    <td className="py-2.5 text-slate-600 font-medium">{rec.document_subtype}</td>
                    <td className="py-2.5 text-center font-mono">
                      {Math.round(rec.average_confidence * 100)}%
                    </td>
                    <td className="py-2.5 text-right">
                      {rec.verification_status === 'VERIFIED' ? (
                        <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium text-[10px]">
                          <CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium text-[10px]">
                          <AlertCircle className="w-2.5 h-2.5" /> PENDING
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

