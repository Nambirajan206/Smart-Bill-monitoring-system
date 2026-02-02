import React, { useState, useRef, useEffect } from 'react';
import { analyzeFile, chatWithAI } from '../api';

/* ─────────────────────────────────────────────────────────────────────────
   STYLES + KEYFRAMES
   ───────────────────────────────────────────────────────────────────────── */
const styleTag = document.createElement('style');
styleTag.textContent = `
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
  .analyzer-row:nth-child(even) { background:#f8fafc; }
  .analyzer-row:hover { background:#eef2ff !important; }
  .suggest-btn:hover { background:#eef2ff !important; border-color:#93c5fd !important; }
`;
if (!document.querySelector('#analyzer-styles')) {
  styleTag.id = 'analyzer-styles';
  document.head.appendChild(styleTag);
}

/* ─────────────────────────────────────────────────────────────────────────
   HELPER: Extract month name from malformed Pandas string
   ───────────────────────────────────────────────────────────────────────── */
const cleanMonthName = (rawMonth) => {
  if (!rawMonth) return '—';
  const match = String(rawMonth).match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/i);
  return match ? match[0] : String(rawMonth).trim().split(/[\s\n]/)[0];
};

/* ─────────────────────────────────────────────────────────────────────────
   SUGGESTED QUESTIONS
   ───────────────────────────────────────────────────────────────────────── */
const SUGGESTIONS = [
  'How many anomalies were detected?',
  'Which houses should I inspect first?',
  'What are the residential vs commercial stats?',
  'What do you recommend?',
  'Are there any low-bill meter issues?',
];

/* ─────────────────────────────────────────────────────────────────────────
   LOCALSTORAGE HELPERS
   ───────────────────────────────────────────────────────────────────────── */
const STORAGE_KEY = 'analyzerState';

const saveState = (state) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    console.warn('Failed to save analyzer state:', err);
  }
};

const loadState = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : null;
  } catch (err) {
    console.warn('Failed to load analyzer state:', err);
    return null;
  }
};

const clearState = () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.warn('Failed to clear analyzer state:', err);
  }
};

/* ─────────────────────────────────────────────────────────────────────────
   COMPONENT
   ───────────────────────────────────────────────────────────────────────── */
const Analyzer = () => {
  // Initialize state from localStorage or defaults
  const [state, setState] = useState(() => {
    const saved = loadState();
    return {
      file: null,
      areaName: saved?.areaName || '',
      fileName: saved?.fileName || null,
      dragging: false,
      analyzing: false,
      result: saved?.result || null,
      error: null,
      messages: saved?.messages || [],
      question: '',
      chatLoading: false,
      showMonthly: false,
    };
  });

  const fileInputRef  = useRef(null);
  const chatBottomRef = useRef(null);

  // Auto-scroll chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.chatLoading]);

  // Persist critical state to localStorage whenever it changes
  useEffect(() => {
    if (state.result) {
      saveState({
        areaName: state.areaName,
        fileName: state.fileName,
        result: state.result,
        messages: state.messages,
      });
    }
  }, [state.result, state.messages, state.areaName, state.fileName]);

  // Helper to update state
  const updateState = (updates) => setState(prev => ({ ...prev, ...updates }));

  // ── FILE HANDLERS ─────────────────────────────────────────────────────
  const acceptFile = (f) => {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['xlsx','xls','csv'].includes(ext)) {
      updateState({ error: 'Only .xlsx, .xls, or .csv files are allowed.' });
      return;
    }
    updateState({ file: f, fileName: f.name, error: null });
  };

  const onDrop = (e) => {
    e.preventDefault();
    updateState({ dragging: false });
    acceptFile(e.dataTransfer.files[0]);
  };

  const removeFile = (e) => {
    e.stopPropagation();
    updateState({ file: null, fileName: null });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const clearAnalysis = () => {
    updateState({
      result: null,
      messages: [],
      error: null,
      file: null,
      fileName: null,
      areaName: '',
    });
    clearState();
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ── ANALYZE ───────────────────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!state.file) return;
    updateState({ analyzing: true, error: null, result: null, messages: [], showMonthly: false });

    try {
      const apiRes = await analyzeFile(state.file, state.areaName);
      const data   = apiRes.data;

      // Seed chat with AI's analysis text
      const aiText = data.analysis || '';
      let initialMessages = [];
      
      if (aiText && aiText.length > 50 && !aiText.toLowerCase().startsWith('error')) {
        initialMessages = [{ role: 'ai', text: aiText }];
      } else {
        const s   = data.summary || {};
        const res = s.residential || {};
        const com = s.commercial  || {};
        const msg =
          `Analysis Complete\n\n` +
          `Analyzed ${data.filename} — ${s.total_records || 0} total records.\n\n` +
          `Residential: ${res.count || 0} houses  |  Avg ₹${(res.mean || 0).toFixed(2)}  |  Median ₹${(res.median || 0).toFixed(2)}\n` +
          `Commercial: ${com.count || 0} properties  |  Avg ₹${(com.mean || 0).toFixed(2)}\n` +
          `Anomalies: ${s.anomalies_count || 0} detected\n\n` +
          `Ask me anything about the data!`;
        initialMessages = [{ role: 'ai', text: msg }];
      }

      updateState({ result: data, messages: initialMessages, analyzing: false });
    } catch (err) {
      const detail = err.response?.data?.details || err.response?.data?.error || err.message;
      updateState({ error: detail, analyzing: false });
    }
  };

  // ── CHAT ──────────────────────────────────────────────────────────────
  const sendQuestion = async (q) => {
    const text = (q || state.question).trim();
    if (!text || !state.result || state.chatLoading) return;

    updateState({
      messages: [...state.messages, { role: 'user', text }],
      question: '',
      chatLoading: true,
    });

    try {
      const apiRes = await chatWithAI(text, state.result);
      updateState({
        messages: [...state.messages, { role: 'user', text }, { role: 'ai', text: apiRes.data.answer }],
        chatLoading: false,
      });
    } catch {
      updateState({
        messages: [...state.messages, { role: 'user', text }, { role: 'ai', text: 'Failed to get a response. Please try again.' }],
        chatLoading: false,
      });
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  };

  // ── EXTRACT DATA FROM RESULT ──────────────────────────────────────────
  const summary     = state.result?.summary || {};
  const residential = summary.residential || {};
  const commercial  = summary.commercial  || {};
  const thresholds  = summary.thresholds  || {};
  const monthlyData = summary.monthly_data || [];
  const anomalies   = state.result?.anomalies || [];

  // ══════════════════════════════════════════════════════════════════════
  //  RENDER
  // ══════════════════════════════════════════════════════════════════════
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem', fontFamily: "'Segoe UI', sans-serif", color: '#1e293b' }}>

      {/* ── HEADER ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.65rem' }}>AI Bill Analyzer</h1>
          <p style={{ margin: '3px 0 0', fontSize: '0.83rem', color: '#64748b' }}>
            Upload an Excel file and let AI detect anomalies across residential &amp; commercial properties
          </p>
        </div>
        {state.result && (
          <button
            onClick={clearAnalysis}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #cbd5e1', background: '#fff', color: '#dc2626', fontSize: '0.82rem', cursor: 'pointer', fontWeight: 600 }}
          >
            New Analysis
          </button>
        )}
      </div>

      {/* ── ERROR BANNER ── */}
      {state.error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '11px 15px', color: '#dc2626', fontSize: '0.83rem', marginBottom: '0.75rem' }}>
          {state.error}
        </div>
      )}

      {/* ── DROPZONE (only show if no result) ── */}
      {!state.result && (
        <>
          <div
            style={{
              border: `2px dashed ${state.dragging ? '#2563eb' : state.file ? '#16a34a' : '#cbd5e1'}`,
              borderRadius: 12, padding: '2.3rem 1.5rem', textAlign: 'center', cursor: 'pointer',
              background: state.dragging ? '#eff6ff' : state.file ? '#f0fdf4' : '#f8fafc',
              transition: 'all 0.2s', marginBottom: '0.75rem',
            }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); updateState({ dragging: true }); }}
            onDragLeave={() => updateState({ dragging: false })}
            onDrop={onDrop}
          >
            <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={(e) => acceptFile(e.target.files[0])} />
            <div style={{ fontSize: '2rem', marginBottom: 7, fontWeight: 600, color: state.file ? '#16a34a' : '#94a3b8' }}>
              {state.file ? 'FILE SELECTED' : 'DROP FILE HERE'}
            </div>
            <p style={{ margin: '0.25rem 0', fontSize: '0.93rem', color: '#475569' }}>
              {state.file ? 'File selected — click to change' : 'Drag & drop your Excel file here or click to browse'}
            </p>
            <p style={{ margin: 0, fontSize: '0.76rem', color: '#94a3b8' }}>.xlsx, .xls, or .csv  |  12 months of bill data</p>
            {state.file && (
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e0f2fe', color: '#0369a1', padding: '6px 12px', borderRadius: 20, fontSize: '0.81rem', marginTop: 9 }}>
                {state.file.name}
                <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#0369a1', fontSize: 16, padding: 0, lineHeight: 1 }} onClick={removeFile}>✕</button>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: '1rem' }}>
            <input
              style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid #cbd5e1', fontSize: '0.88rem', outline: 'none' }}
              placeholder="Area / Street name (optional)"
              value={state.areaName}
              onChange={(e) => updateState({ areaName: e.target.value })}
            />
            <button
              disabled={!state.file || state.analyzing}
              onClick={handleAnalyze}
              style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: (!state.file || state.analyzing) ? '#94a3b8' : '#2563eb',
                color: '#fff', fontWeight: 600, fontSize: '0.88rem',
                cursor: (!state.file || state.analyzing) ? 'not-allowed' : 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: 8,
              }}
            >
              {state.analyzing && <span style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.3)', borderTop: '2px solid #fff', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />}
              {state.analyzing ? 'Analyzing…' : 'Analyze with AI'}
            </button>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          RESULTS SECTION
          ══════════════════════════════════════════════════════════════════ */}
      {state.result && (
        <div style={{ animation: 'fadeIn 0.4s ease' }}>

          {/* File info banner */}
          <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8, padding: '10px 14px', marginBottom: '0.9rem', fontSize: '0.82rem', color: '#0369a1' }}>
            <strong>{state.result.filename}</strong> {state.areaName && `• ${state.areaName}`} • Analyzed on {new Date(state.result.timestamp || Date.now()).toLocaleString()}
          </div>

          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.7rem', marginBottom: '0.9rem' }}>
            {[
              { label: 'Total Records',   value: summary.total_records ?? 0,                  color: '#6366f1' },
              { label: 'Anomalies Found', value: summary.anomalies_count ?? 0,                color: '#dc2626' },
              { label: 'Residential Avg', value: `₹${(residential.mean || 0).toFixed(2)}`,    color: '#2563eb' },
              { label: 'Commercial Avg',  value: `₹${(commercial.mean || 0).toFixed(2)}`,     color: '#16a34a' },
            ].map((c, i) => (
              <div key={i} style={{ background: '#fff', borderRadius: 10, padding: '13px 15px', borderLeft: `4px solid ${c.color}`, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' }}>
                <p style={{ margin: 0, fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{c.label}</p>
                <p style={{ margin: '4px 0 0', fontSize: '1.28rem', fontWeight: 700 }}>{c.value}</p>
              </div>
            ))}
          </div>

          {/* Residential & Commercial stat boxes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.7rem', marginBottom: '0.9rem' }}>
            {/* Residential */}
            <div style={{ background: '#fff', borderRadius: 10, padding: '14px 16px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: '0.88rem', color: '#1e40af' }}>Residential</p>
                <span style={{ fontSize: '0.7rem', background: '#dbeafe', color: '#1e40af', padding: '3px 9px', borderRadius: 10, fontWeight: 600 }}>
                  {residential.count || 0} records
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '7px 12px', fontSize: '0.78rem' }}>
                {[
                  ['Mean',   residential.mean],
                  ['Median', residential.median],
                  ['Min',    residential.min],
                  ['Max',    residential.max],
                ].map(([label, val]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>{label}</span>
                    <span style={{ fontWeight: 600, color: '#1e293b' }}>₹{(val || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 9, fontSize: '0.72rem', color: '#64748b', borderTop: '1px solid #e2e8f0', paddingTop: 7 }}>
                Normal range: ₹{(thresholds.residential_min || 500).toLocaleString()} – ₹{(thresholds.residential_max || 5000).toLocaleString()}
              </div>
            </div>

            {/* Commercial */}
            <div style={{ background: '#fff', borderRadius: 10, padding: '14px 16px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: '0.88rem', color: '#15803d' }}>Commercial</p>
                <span style={{ fontSize: '0.7rem', background: '#dcfce7', color: '#15803d', padding: '3px 9px', borderRadius: 10, fontWeight: 600 }}>
                  {commercial.count || 0} records
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '7px 12px', fontSize: '0.78rem' }}>
                {[
                  ['Mean',   commercial.mean],
                  ['Median', commercial.median],
                  ['Min',    commercial.min],
                  ['Max',    commercial.max],
                ].map(([label, val]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>{label}</span>
                    <span style={{ fontWeight: 600, color: '#1e293b' }}>₹{(val || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 9, fontSize: '0.72rem', color: '#64748b', borderTop: '1px solid #e2e8f0', paddingTop: 7 }}>
                Commercial properties excluded from anomaly detection
              </div>
            </div>
          </div>

          {/* Monthly data toggle */}
          {monthlyData.length > 0 && (
            <div style={{ marginBottom: '0.9rem' }}>
              <button
                onClick={() => updateState({ showMonthly: !state.showMonthly })}
                style={{ background: 'none', border: '1px solid #cbd5e1', borderRadius: 8, padding: '8px 15px', cursor: 'pointer', fontSize: '0.8rem', color: '#475569', fontWeight: 600, transition: 'background 0.15s' }}
                onMouseEnter={(e) => e.target.style.background = '#f1f5f9'}
                onMouseLeave={(e) => e.target.style.background = 'none'}
              >
                {state.showMonthly ? '▼ Hide' : '▶ Show'} Monthly Breakdown ({monthlyData.length} months)
              </button>

              {state.showMonthly && (
                <div style={{ overflowX: 'auto', marginTop: 9 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        {['Month','Bills','Total ₹','Avg ₹','Max ₹','Units'].map(h => (
                          <th key={h} style={{ padding: '9px 11px', background: '#f1f5f9', color: '#475569', textAlign: 'left', borderBottom: '2px solid #e2e8f0', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {monthlyData.map((m, i) => (
                        <tr key={i} className="analyzer-row">
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7', fontWeight: 600 }}>
                            {cleanMonthName(m.month)}
                          </td>
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7' }}>
                            {(m.count || 0).toLocaleString()}
                          </td>
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7' }}>
                            ₹{(m.total_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </td>
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7' }}>
                            ₹{(m.average_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          </td>
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7', color: '#dc2626', fontWeight: 600 }}>
                            ₹{(m.max_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </td>
                          <td style={{ padding: '8px 11px', borderBottom: '1px solid #eef2f7' }}>
                            {(m.total_units || 0).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Anomaly table */}
          {anomalies.length > 0 && (
            <div style={{ overflowX: 'auto', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                <p style={{ margin: 0, fontSize: '0.92rem', fontWeight: 600, color: '#1e293b' }}>
                  Detected Anomalies
                </p>
                <span style={{ fontSize: '0.72rem', background: '#fef2f2', color: '#dc2626', padding: '4px 11px', borderRadius: 12, fontWeight: 700 }}>
                  {anomalies.length} total
                </span>
              </div>

              <div style={{ maxHeight: 500, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#f1f5f9', zIndex: 1 }}>
                    <tr>
                      {['#','House ID','Address','Month','Bill ₹','Units','Severity','Reason'].map(h => (
                        <th key={h} style={{ padding: '10px 12px', color: '#475569', textAlign: 'left', borderBottom: '2px solid #cbd5e1', fontWeight: 600, whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.map((a, i) => (
                      <tr key={i} className="analyzer-row">
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7', color: '#94a3b8', fontSize: '0.72rem' }}>
                          {i + 1}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7', fontWeight: 600 }}>
                          {a.house_id}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7', color: '#64748b', maxWidth: 150, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {a.address || '—'}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7' }}>
                          {a.month}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7', fontWeight: 700, color: a.severity === 'high' ? '#dc2626' : '#ca8a04' }}>
                          ₹{(a.bill_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7' }}>
                          {(a.units_consumed || 0).toLocaleString()}
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7' }}>
                          <span style={{
                            display: 'inline-block', padding: '3px 10px', borderRadius: 12, fontSize: '0.68rem', fontWeight: 700,
                            background: a.severity === 'high' ? '#fef2f2' : '#fefce8',
                            color:      a.severity === 'high' ? '#dc2626' : '#ca8a04',
                            textTransform: 'uppercase',
                          }}>
                            {a.severity}
                          </span>
                        </td>
                        <td style={{ padding: '9px 12px', borderBottom: '1px solid #eef2f7', color: '#64748b', minWidth: 220 }}>
                          {a.reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Chat section */}
          <div style={{ marginTop: '1.3rem' }}>
            <p style={{ margin: '0 0 0.6rem', fontSize: '0.96rem', fontWeight: 600 }}>Ask AI about the results</p>

            <div style={{ background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', height: 380, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: 11 }}>
              {state.messages.length === 0 && (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '50px 0', fontSize: '0.83rem' }}>
                  Analysis complete — ask a question below
                </div>
              )}
              {state.messages.map((m, i) => (
                <div key={i} style={{
                  maxWidth: '88%', padding: '11px 15px',
                  borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: m.role === 'user' ? '#2563eb' : '#fff',
                  color:      m.role === 'user' ? '#fff'     : '#1e293b',
                  fontSize: '0.84rem', lineHeight: 1.6,
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {m.text}
                </div>
              ))}
              {state.chatLoading && (
                <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{ width: 16, height: 16, border: '2px solid #dbeafe', borderTop: '2px solid #2563eb', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block' }} />
                  <span style={{ fontSize: '0.76rem', color: '#94a3b8' }}>AI is thinking…</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: '0.6rem' }}>
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="suggest-btn"
                  disabled={state.chatLoading}
                  onClick={() => sendQuestion(s)}
                  style={{ padding: '6px 12px', borderRadius: 16, border: '1px solid #cbd5e1', background: '#fff', color: '#475569', fontSize: '0.73rem', cursor: state.chatLoading ? 'not-allowed' : 'pointer', fontWeight: 500, transition: 'all 0.15s' }}
                >
                  {s}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 9, marginTop: '0.6rem' }}>
              <textarea
                style={{ flex: 1, padding: '11px 14px', borderRadius: 8, border: '1px solid #cbd5e1', fontSize: '0.84rem', outline: 'none', resize: 'none', fontFamily: 'inherit' }}
                rows={2}
                placeholder="Ask anything about this analysis… (Enter to send)"
                value={state.question}
                onChange={(e) => updateState({ question: e.target.value })}
                onKeyDown={onKeyDown}
                disabled={state.chatLoading}
              />
              <button
                disabled={!state.question.trim() || state.chatLoading}
                onClick={() => sendQuestion()}
                style={{
                  padding: '11px 22px', borderRadius: 8, border: 'none',
                  background: (!state.question.trim() || state.chatLoading) ? '#94a3b8' : '#2563eb',
                  color: '#fff', fontWeight: 600, fontSize: '0.86rem',
                  cursor: (!state.question.trim() || state.chatLoading) ? 'not-allowed' : 'pointer',
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!state.result && !state.analyzing && (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: '60px 0', fontSize: '0.86rem' }}>
          Upload a file and click <strong>Analyze with AI</strong> to get started
        </div>
      )}
    </div>
  );
};

export default Analyzer;