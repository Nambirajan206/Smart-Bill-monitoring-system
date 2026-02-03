import React, { useState, useRef, useEffect } from 'react';
import { analyzeFile, chatWithAI } from '../api';

const styleTag = document.createElement('style');
styleTag.textContent = `
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  .spike-row:nth-child(even) { background:#f8fafc; }
  .spike-row:hover { background:#fef3c7 !important; }
  .suggest-btn:hover { background:#eef2ff !important; border-color:#93c5fd !important; }
`;
if (!document.querySelector('#analyzer-styles')) {
  styleTag.id = 'analyzer-styles';
  document.head.appendChild(styleTag);
}

const STORAGE_KEY = 'analyzerState';

const SUGGESTED_QUESTIONS = [
  'How many spikes were detected?',
  'Which consumer has the highest spike?',
  'Show me details for consumer C002',
  'What do you recommend?',
  'Compare residential vs commercial spikes'
];

const saveState = (state) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    console.warn('Failed to save state:', err);
  }
};

const loadState = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : null;
  } catch (err) {
    console.warn('Failed to load state:', err);
    return null;
  }
};

const clearState = () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.warn('Failed to clear state:', err);
  }
};

const Analyzer = () => {
  const [state, setState] = useState(() => {
    const saved = loadState();
    return {
      file: null,
      fileName: saved?.fileName || null,
      dragging: false,
      analyzing: false,
      result: saved?.result || null,
      error: null,
      messages: saved?.messages || [],
      question: '',
      chatLoading: false,
    };
  });

  const fileInputRef = useRef(null);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.chatLoading]);

  useEffect(() => {
    if (state.result) {
      saveState({
        fileName: state.fileName,
        result: state.result,
        messages: state.messages,
      });
    }
  }, [state.result, state.fileName, state.messages]);

  const updateState = (updates) => setState(prev => ({ ...prev, ...updates }));

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
      error: null,
      file: null,
      fileName: null,
      messages: [],
      question: '',
    });
    clearState();
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleAnalyze = async () => {
    if (!state.file) return;
    updateState({ analyzing: true, error: null, result: null, messages: [] });

    try {
      const apiRes = await analyzeFile(state.file, '');
      updateState({ result: apiRes.data, analyzing: false });
    } catch (err) {
      const detail = err.response?.data?.details || err.response?.data?.error || err.message;
      updateState({ error: detail, analyzing: false });
    }
  };

  const sendQuestion = async (q) => {
    const text = (q || state.question).trim();
    if (!text || !state.result || state.chatLoading) return;

    updateState({
      messages: [...state.messages, { role: 'user', text }],
      question: '',
      chatLoading: true,
    });

    try {
      const chatContext = {
        summary: state.result.summary,
        spikes: state.result.spikes,
        analysis: state.result.analysis,
        raw_data: state.result.raw_data || []
      };

      const apiRes = await chatWithAI(text, chatContext);
      
      updateState({
        messages: [...state.messages, { role: 'user', text }, { role: 'ai', text: apiRes.data.answer }],
        chatLoading: false,
      });
    } catch (err) {
      updateState({
        messages: [...state.messages, { role: 'user', text }, { role: 'ai', text: 'Failed to get response. Please try again.' }],
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

  const summary = state.result?.summary || {};
  const spikes = state.result?.spikes || [];
  const analysis = state.result?.analysis || '';

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 1.5rem', fontFamily: "'Segoe UI', sans-serif", color: '#1e293b' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.7rem' }}>Bill Spike Analyzer</h1>
        </div>
        {state.result && (
          <button
            onClick={clearAnalysis}
            style={{ padding: '9px 18px', borderRadius: 8, border: '1px solid #cbd5e1', background: '#fff', color: '#dc2626', fontSize: '0.82rem', cursor: 'pointer', fontWeight: 600 }}
          >
            New Analysis
          </button>
        )}
      </div>

      {state.error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '12px 16px', color: '#dc2626', fontSize: '0.84rem', marginBottom: '0.9rem' }}>
          {state.error}
        </div>
      )}

      {!state.result && (
        <>
          <div
            style={{
              border: `2px dashed ${state.dragging ? '#2563eb' : state.file ? '#16a34a' : '#cbd5e1'}`,
              borderRadius: 12, padding: '2.5rem 1.5rem', textAlign: 'center', cursor: 'pointer',
              background: state.dragging ? '#eff6ff' : state.file ? '#f0fdf4' : '#f8fafc',
              transition: 'all 0.2s', marginBottom: '0.9rem',
            }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); updateState({ dragging: true }); }}
            onDragLeave={() => updateState({ dragging: false })}
            onDrop={onDrop}
          >
            <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={(e) => acceptFile(e.target.files[0])} />
            <div style={{ fontSize: '2.2rem', marginBottom: 8, fontWeight: 600, color: state.file ? '#16a34a' : '#94a3b8' }}>
              {state.file ? 'FILE READY' : 'DROP FILE HERE'}
            </div>
            <p style={{ margin: '0.3rem 0', fontSize: '0.95rem', color: '#475569' }}>
              {state.file ? 'File selected — click to change' : 'Drag & drop your Excel file or click to browse'}
            </p>
            <p style={{ margin: 0, fontSize: '0.77rem', color: '#94a3b8' }}>.xlsx, .xls, or .csv</p>
            {state.file && (
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 9, background: '#e0f2fe', color: '#0369a1', padding: '7px 14px', borderRadius: 20, fontSize: '0.82rem', marginTop: 10 }}>
                {state.file.name}
                <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#0369a1', fontSize: 17, padding: 0, lineHeight: 1 }} onClick={removeFile}>✕</button>
              </div>
            )}
          </div>

          <button
            disabled={!state.file || state.analyzing}
            onClick={handleAnalyze}
            style={{
              padding: '11px 26px', borderRadius: 8, border: 'none',
              background: (!state.file || state.analyzing) ? '#94a3b8' : '#2563eb',
              color: '#fff', fontWeight: 600, fontSize: '0.9rem',
              cursor: (!state.file || state.analyzing) ? 'not-allowed' : 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 9, width: '100%',
              justifyContent: 'center',
            }}
          >
            {state.analyzing && <span style={{ width: 19, height: 19, border: '2px solid rgba(255,255,255,0.3)', borderTop: '2px solid #fff', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />}
            {state.analyzing ? 'Analyzing Each Consumer...' : 'Start Analysis'}
          </button>

          {state.analyzing && (
            <div style={{ marginTop: '1.5rem', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 10, padding: '1.2rem', fontSize: '0.84rem', color: '#1e40af' }}>
              <div style={{ display: 'flex', alignItems: 'normal', gap: 10, marginBottom: '0.5rem' }}>
                <span style={{ animation: 'pulse 1.5s ease-in-out infinite', fontSize: '1.3rem' }}></span>
                <p style={{ margin: 0, fontWeight: 600 }}>Analyzing...</p>
              </div>
              <p style={{ margin: 0, fontSize: '0.79rem', color: '#1e40af', opacity: 0.9 }}>
                This may take a moment.
              </p>
            </div>
          )}
        </>
      )}

      {state.result && (
        <div style={{ animation: 'fadeIn 0.4s ease' }}>

          <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8, padding: '11px 16px', marginBottom: '1rem', fontSize: '0.83rem', color: '#0369a1' }}>
            <strong>{state.result.filename}</strong> • Analysis completed at {new Date().toLocaleString()}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.8rem', marginBottom: '1rem' }}>
            {[
              { label: 'Total Consumers',     value: summary.total_consumers ?? 0,         color: '#6366f1' },
              { label: 'Spikes Detected',     value: summary.spike_count ?? 0,             color: '#dc2626' },
              { label: 'Consumers w/ Spikes', value: summary.consumers_with_spikes ?? 0,   color: '#ea580c' },
              { label: 'Residential',         value: summary.residential_count ?? 0,       color: '#2563eb' },
            ].map((c, i) => (
              <div key={i} style={{ background: '#fff', borderRadius: 10, padding: '14px 16px', borderLeft: `4px solid ${c.color}`, boxShadow: '0 1px 3px rgba(0,0,0,0.09)', border: '1px solid #e2e8f0' }}>
                <p style={{ margin: 0, fontSize: '0.69rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{c.label}</p>
                <p style={{ margin: '5px 0 0', fontSize: '1.32rem', fontWeight: 700 }}>{c.value}</p>
              </div>
            ))}
          </div>

          {analysis && (
            <div style={{ background: '#fff', borderRadius: 10, padding: '1.3rem', border: '1px solid #e2e8f0', marginBottom: '1rem', boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
              <h2 style={{ margin: '0 0 0.8rem', fontSize: '1.05rem', fontWeight: 600, color: '#1e293b' }}>AI Insights & Analysis</h2>
              <div style={{ fontSize: '0.86rem', lineHeight: 1.7, color: '#475569', whiteSpace: 'pre-wrap' }}>
                {analysis}
              </div>
            </div>
          )}

          {spikes.length > 0 && (
            <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#1e293b' }}>
                  Detected Spikes
                </h2>
                <span style={{ fontSize: '0.73rem', background: '#fef2f2', color: '#dc2626', padding: '5px 12px', borderRadius: 12, fontWeight: 700 }}>
                  {spikes.length} spikes found
                </span>
              </div>

              <div style={{ maxHeight: 450, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 10 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.81rem' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#fef9c3', zIndex: 1 }}>
                    <tr>
                      {['#','Consumer ID','Type','Spike Month','Current Bill','Baseline','Increase %','Reason'].map(h => (
                        <th key={h} style={{ padding: '11px 13px', color: '#713f12', textAlign: 'left', borderBottom: '2px solid #fde047', fontWeight: 600, whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {spikes.map((spike, i) => (
                      <tr key={i} className="spike-row">
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', color: '#94a3b8', fontSize: '0.73rem' }}>{i + 1}</td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', fontWeight: 600 }}>{spike.consumer_id}</td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7' }}>
                          <span style={{
                            display: 'inline-block', padding: '3px 10px', borderRadius: 12, fontSize: '0.69rem', fontWeight: 700,
                            background: spike.consumer_type === 'Commercial' ? '#dcfce7' : '#dbeafe',
                            color: spike.consumer_type === 'Commercial' ? '#15803d' : '#1e40af',
                            textTransform: 'uppercase',
                          }}>
                            {spike.consumer_type}
                          </span>
                        </td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', fontWeight: 600 }}>{spike.month}</td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', fontWeight: 700, color: '#dc2626' }}>
                          ₹{spike.bill_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', color: '#64748b' }}>
                          ₹{spike.previous_bill.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7' }}>
                          <span style={{
                            display: 'inline-block', padding: '3px 10px', borderRadius: 12, fontSize: '0.73rem', fontWeight: 700,
                            background: spike.increase_percentage > 100 ? '#fee2e2' : '#fef3c7',
                            color: spike.increase_percentage > 100 ? '#991b1b' : '#854d0e',
                          }}>
                            +{spike.increase_percentage.toFixed(1)}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 13px', borderBottom: '1px solid #eef2f7', color: '#64748b', minWidth: 250 }}>{spike.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {spikes.length === 0 && (
            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, padding: '2rem', textAlign: 'center', color: '#15803d', marginBottom: '1.5rem' }}>
              <p style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>No Spikes Detected</p>
              <p style={{ fontSize: '0.85rem', margin: '0.5rem 0 0', color: '#166534' }}>
                All consumers show stable, predictable usage patterns.
              </p>
            </div>
          )}

          {/* CHAT SECTION - AFTER SPIKE TABLE */}
          <div style={{ marginTop: '1.5rem' }}>
            <h2 style={{ margin: '0 0 0.9rem', fontSize: '1.05rem', fontWeight: 600, color: '#1e293b' }}>
              💬 Ask Questions About the Analysis
            </h2>

            <div style={{ background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', height: 400, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: 11, marginBottom: '0.8rem' }}>
              {state.messages.length === 0 && (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '50px 0', fontSize: '0.83rem' }}>
                  <p style={{ margin: 0, fontSize: '1.1rem', marginBottom: '0.5rem' }}>💡 Ask me anything!</p>
                  <p style={{ margin: 0 }}>Try the suggested questions below or type your own</p>
                </div>
              )}
              {state.messages.map((m, i) => (
                <div key={i} style={{
                  maxWidth: '85%', padding: '11px 15px',
                  borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: m.role === 'user' ? '#2563eb' : '#fff',
                  color: m.role === 'user' ? '#fff' : '#1e293b',
                  fontSize: '0.84rem', lineHeight: 1.6,
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {m.text}
                </div>
              ))}
              {state.chatLoading && (
                <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{ width: 16, height: 16, border: '2px solid #dbeafe', borderTop: '2px solid #2563eb', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block' }} />
                  <span style={{ fontSize: '0.76rem', color: '#94a3b8' }}>AI is thinking...</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: '0.8rem' }}>
              {SUGGESTED_QUESTIONS.map((sq, i) => (
                <button
                  key={i}
                  className="suggest-btn"
                  disabled={state.chatLoading}
                  onClick={() => sendQuestion(sq)}
                  style={{ 
                    padding: '7px 13px', 
                    borderRadius: 16, 
                    border: '1px solid #cbd5e1', 
                    background: '#fff', 
                    color: '#475569', 
                    fontSize: '0.75rem', 
                    cursor: state.chatLoading ? 'not-allowed' : 'pointer', 
                    fontWeight: 500,
                    transition: 'all 0.15s',
                  }}
                >
                  {sq}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 9 }}>
              <textarea
                style={{ 
                  flex: 1, 
                  padding: '12px 14px', 
                  borderRadius: 8, 
                  border: '1px solid #cbd5e1', 
                  fontSize: '0.84rem', 
                  outline: 'none', 
                  resize: 'none', 
                  fontFamily: 'inherit',
                  minHeight: '50px',
                }}
                rows={2}
                placeholder="Ask anything about the analysis... (Press Enter to send)"
                value={state.question}
                onChange={(e) => updateState({ question: e.target.value })}
                onKeyDown={onKeyDown}
                disabled={state.chatLoading}
              />
              <button
                disabled={!state.question.trim() || state.chatLoading}
                onClick={() => sendQuestion()}
                style={{
                  padding: '12px 24px', 
                  borderRadius: 8, 
                  border: 'none',
                  background: (!state.question.trim() || state.chatLoading) ? '#94a3b8' : '#2563eb',
                  color: '#fff', 
                  fontWeight: 600, 
                  fontSize: '0.86rem',
                  cursor: (!state.question.trim() || state.chatLoading) ? 'not-allowed' : 'pointer',
                  alignSelf: 'stretch',
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {!state.result && !state.analyzing && (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: '70px 0', fontSize: '0.88rem' }}>
          Upload a file to start spike detection
        </div>
      )}
    </div>
  );
};

export default Analyzer;
