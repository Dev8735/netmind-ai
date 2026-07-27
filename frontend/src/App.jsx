import { useState, useEffect } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { AlertCircle, CheckCircle, Clock, Server, X, Copy } from 'lucide-react';
import Topology from './Topology';
import Login from './Login';
import './App.css';

const SEVERITY_COLORS = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#22c55e',
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('netmind_token'));
  const [incidentText, setIncidentText] = useState('');
  const [incidents, setIncidents] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [alertText, setAlertText] = useState('');
  const [loadingAlert, setLoadingAlert] = useState(false);
  const [copied, setCopied] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [runningTests, setRunningTests] = useState(false);
  const [signals, setSignals] = useState([]);
  const [resolving, setResolving] = useState(false);
  const [escalatedIds, setEscalatedIds] = useState([]);
  const [recurringData, setRecurringData] = useState([]);
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const fetchIncidents = () => {
    axios.get('http://127.0.0.1:8000/api/incidents')
      .then(res => setIncidents(res.data))
      .catch(err => console.error('Failed to fetch incidents:', err));
  };

  const fetchSignals = () => {
    axios.get('http://127.0.0.1:8000/api/signals?limit=20')
      .then(res => setSignals(res.data))
      .catch(err => console.error('Failed to fetch signals:', err));
  };

  const fetchRecurring = () => {
    axios.get('http://127.0.0.1:8000/api/analytics/recurring')
      .then(res => setRecurringData(res.data))
      .catch(err => console.error('Failed to fetch analytics:', err));
  };

  useEffect(() => {
    fetchIncidents();
    fetchSignals();
    fetchRecurring();

    let ws;
    let reconnectTimeout;

    const connectWebSocket = () => {
      ws = new WebSocket('ws://127.0.0.1:8000/ws/incidents');

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'incident') {
          setIncidents(prev => {
            const exists = prev.some(i => i.id === data.id);
            if (exists) return prev;
            return [...prev, { id: data.id, device: data.device, issue: data.issue, severity: data.severity, status: data.status }];
          });
          fetchRecurring();
        }

        if (data.type === 'signal') {
          setSignals(prev => [
            { device: data.device, status: data.status, message: data.message, created_at: new Date().toLocaleTimeString() },
            ...prev
          ].slice(0, 20));
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected, retrying in 3s...');
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get('http://127.0.0.1:8000/api/incidents/escalated')
        .then(res => setEscalatedIds(res.data.map(i => i.id)))
        .catch(err => console.error('Failed to fetch escalations:', err));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async () => {
    if (!incidentText.trim()) return;
    setSubmitting(true);
    setErrorMsg('');
    try {
      await axios.post('http://127.0.0.1:8000/api/incidents', { text: incidentText });
      setIncidentText('');
      fetchIncidents();
    } catch (err) {
      console.error('Failed to submit incident:', err);
      setErrorMsg('Failed to submit incident. Is the backend running?');
    } finally {
      setSubmitting(false);
    }
  };

  const openDetail = async (id) => {
    setAlertText('');
    setCopied(false);
    setFeedbackGiven(false);
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/incidents/${id}`);
      setSelectedDetail(res.data);
    } catch (err) {
      console.error('Failed to fetch detail:', err);
    }
  };

  const generateAlert = async () => {
    setLoadingAlert(true);
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/incidents/${selectedDetail.id}/alert`);
      setAlertText(res.data.alert);
    } catch (err) {
      console.error('Failed to generate alert:', err);
    } finally {
      setLoadingAlert(false);
    }
  };

  const copyAlert = () => {
    navigator.clipboard.writeText(alertText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const resolveIncident = async () => {
    setResolving(true);
    try {
      await axios.post(`http://127.0.0.1:8000/api/incidents/${selectedDetail.id}/resolve`);
      setSelectedDetail(prev => ({ ...prev, status: 'Resolved' }));
      setIncidents(prev => prev.map(i => i.id === selectedDetail.id ? { ...i, status: 'Resolved' } : i));
    } catch (err) {
      console.error('Failed to resolve incident:', err);
    } finally {
      setResolving(false);
    }
  };

  const submitFeedback = async (helpful) => {
    try {
      await axios.post(`http://127.0.0.1:8000/api/incidents/${selectedDetail.id}/feedback`, { helpful });
      setFeedbackGiven(true);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };


  const runTests = async () => {
    setRunningTests(true);
    setTestResults(null);
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/run-tests');
      setTestResults(res.data);
      fetchIncidents();
    } catch (err) {
      console.error('Test run failed:', err);
    } finally {
      setRunningTests(false);
    }
  };

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />;
  }

  const severityData = ['Critical', 'High', 'Medium', 'Low'].map(name => ({
    name,
    value: incidents.filter(i => i.severity === name).length,
    color: SEVERITY_COLORS[name],
  }));
  const hasSeverityData = severityData.some(s => s.value > 0);

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1><Server size={24} /> NetMind AI - Network Fault Diagnosis Assistant</h1>
      </header>

      <section className="summary-cards">
        <div className="card">
          <AlertCircle color="#ef4444" />
          <div><span className="card-number">{incidents.length}</span><p>Total Incidents</p></div>
        </div>
        <div className="card">
          <Clock color="#f97316" />
          <div><span className="card-number">{incidents.filter(i => i.status === 'Open').length}</span><p>Open</p></div>
        </div>
        <div className="card">
          <CheckCircle color="#22c55e" />
          <div><span className="card-number">{incidents.filter(i => i.status === 'Resolved').length}</span><p>Resolved</p></div>
        </div>
      </section>

      <section className="main-grid">
        <div className="panel">
          <h2>New Incident</h2>
          <textarea
            value={incidentText}
            onChange={(e) => setIncidentText(e.target.value)}
            placeholder="Paste incident email or describe the issue..."
            rows={6}
            disabled={submitting}
          />
          <button onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Analyzing...' : 'Analyze Incident'}
          </button>
          {errorMsg && <p style={{ color: '#ef4444', marginTop: '8px' }}>{errorMsg}</p>}
        </div>

        <div className="panel">
          <h2>Severity Breakdown <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(live, from detected signals)</span></h2>
          {!hasSeverityData ? (
            <p style={{color:'#64748b', fontSize:'13px'}}>No incidents yet - severity breakdown will populate as faults are detected.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={severityData} dataKey="value" nameKey="name" outerRadius={80} label>
                    {severityData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="severity-legend">
                {severityData.map((s, i) => (
                  <div key={i} className="severity-legend-item">
                    <span className="severity-dot" style={{background: s.color}}></span>
                    {s.name}: <strong>{s.value}</strong>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="panel">
        <h2>Top Recurring Issues</h2>
        {recurringData.length === 0 ? (
          <p style={{color:'#64748b', fontSize:'13px'}}>No data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={recurringData} layout="vertical" margin={{left: 20}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#94a3b8" />
              <YAxis type="category" dataKey="label" stroke="#94a3b8" width={140} tick={{fontSize: 11}} />
              <Tooltip contentStyle={{background:'#1e293b', border:'1px solid #334155'}} />
              <Bar dataKey="count" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <section className="panel">
        <h2>Incident History <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(click a row for details)</span></h2>
        <table>
          <thead>
            <tr><th>Device</th><th>Issue</th><th>Severity</th><th>Status</th></tr>
          </thead>
          <tbody>
            {incidents.map(i => (
              <tr key={i.id} onClick={() => openDetail(i.id)} style={{ cursor: 'pointer' }}>
                <td>{i.device}</td><td>{i.issue}</td>
                <td>
                  <span className={`badge ${i.severity.toLowerCase()}`}>{i.severity}</span>
                  {escalatedIds.includes(i.id) && <span className="escalated-badge">ESCALATED</span>}
                </td>
                <td>{i.status === 'Auto-Resolved' ? '⚡ Auto-Resolved' : i.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Live Signal Monitor <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(every 15s check-in from monitored devices)</span></h2>
        {signals.length === 0 ? (
          <p style={{color:'#64748b', fontSize:'13px'}}>No signals yet - start the log generator to see live device check-ins.</p>
        ) : (
          <div className="signal-list">
            {signals.map((s, idx) => (
              <div key={idx} className={`signal-row ${s.status}`}>
                <span className={`signal-dot ${s.status}`}></span>
                <span className="signal-time">{s.created_at}</span>
                <span className="signal-device">{s.device}</span>
                <span className="signal-message">{s.message}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2>System Test</h2>
        <button onClick={runTests} disabled={runningTests}>
          {runningTests ? 'Running Tests...' : 'Run End-to-End Tests'}
        </button>
        {testResults && (
          <div className="test-results">
            <p className="test-summary">
              {testResults.passed} / {testResults.total} passed
            </p>
            {testResults.results.map((r, idx) => (
              <div key={idx} className={`test-row ${r.status.toLowerCase()}`}>
                <span className="test-status">{r.status}</span>
                <span className="test-text">{r.text}</span>
                {r.status === 'PASS' && (
                  <span className="test-meta">{r.device} | {r.severity} | {r.matched ? 'Matched' : 'No match'}</span>
                )}
                {r.status === 'FAIL' && <span className="test-meta">{r.error}</span>}
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedDetail && (
        <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedDetail(null)}><X size={18} /></button>
            <h2>{selectedDetail.device} - {selectedDetail.severity}</h2>
            <div className={`severity-banner ${selectedDetail.severity.toLowerCase()}`}>
              {selectedDetail.severity === 'Critical' && 'Immediate action required'}
              {selectedDetail.severity === 'High' && 'Prompt attention needed'}
              {selectedDetail.severity === 'Medium' && 'Schedule investigation'}
            </div>
            <p className="modal-issue">{selectedDetail.issue}</p>

            <div className="resolve-row">
              <span className={`status-pill ${selectedDetail.status.toLowerCase().replace(' ', '-')}`}>
                {selectedDetail.status === 'Auto-Resolved' ? '⚡ Auto-Resolved' : selectedDetail.status}
              </span>
              {selectedDetail.status !== 'Resolved' && selectedDetail.status !== 'Auto-Resolved' && (
                <button onClick={resolveIncident} disabled={resolving} className="resolve-btn">
                  {resolving ? 'Marking Resolved...' : 'Mark as Resolved'}
                </button>
              )}
            </div>

            {selectedDetail.remediation_log && (
              <div className="remediation-panel">
                <h3>⚡ Automated Remediation</h3>
                <p className="remediation-note">
                  This fault matched a known safe, config-only issue type and was
                  automatically fixed with no engineer action required.
                </p>
                <pre className="remediation-log">{selectedDetail.remediation_log}</pre>
              </div>
            )}

            <h3>Network Topology</h3>
            <Topology affectedDevice={selectedDetail.device} />

            {selectedDetail.diagnosis && selectedDetail.diagnosis.matched ? (
              <div>
                <h3>
                  {selectedDetail.diagnosis.confidence === 'high' ? 'Diagnosed Cause' : 'Ranked Possible Causes'}
                  <span className={`confidence-tag ${selectedDetail.diagnosis.confidence}`}>
                    {selectedDetail.diagnosis.confidence} confidence ({selectedDetail.diagnosis.confidence_score})
                  </span>
                </h3>
                {selectedDetail.diagnosis.causes
                  .filter((c, idx) => selectedDetail.diagnosis.confidence === 'high' ? idx === 0 : true)
                  .map((c, idx) => (
                  <div key={idx} className="cause-block">
                    <p><strong>{idx + 1}. {c.cause}</strong> ({c.probability}% likely)</p>
                    <div className="evidence-row">
                      <span className="evidence-chip">Similarity: {c.similarity_score}</span>
                      <span className="evidence-chip">
                        {c.matched_keywords && c.matched_keywords.length > 0
                          ? `Matched: ${c.matched_keywords.join(', ')}`
                          : 'Matched: semantic (no exact keyword overlap)'}
                      </span>
                      {c.business_impact && (
                        <span className="evidence-chip impact-chip">Impact: {c.business_impact}</span>
                      )}
                    </div>
                    <p className="cause-detail">Verify: <code>{c.verification_command}</code></p>
                    <p className="cause-detail">Steps: {c.troubleshooting_steps}</p>
                  </div>
                ))}

                {selectedDetail.diagnosis.rejected_causes && selectedDetail.diagnosis.rejected_causes.length > 0 && (
                  <details className="rejected-causes">
                    <summary>Other causes considered and ruled out ({selectedDetail.diagnosis.rejected_causes.length})</summary>
                    {selectedDetail.diagnosis.rejected_causes.map((r, idx) => (
                      <p key={idx} className="rejected-cause-item">
                        <strong>{r.cause}</strong> — {r.reason}
                      </p>
                    ))}
                  </details>
                )}
              </div>
            ) : (
              <div className="no-match-banner">
                No confident match found in knowledge base. This incident requires manual engineer review.
              </div>
            )}

            {selectedDetail.diagnosis && selectedDetail.diagnosis.matched && (
              <div className="feedback-row">
                {!feedbackGiven ? (
                  <>
                    <span className="feedback-label">Was this diagnosis helpful?</span>
                    <button onClick={() => submitFeedback('yes')} className="feedback-btn yes">👍 Yes</button>
                    <button onClick={() => submitFeedback('no')} className="feedback-btn no">👎 No</button>
                  </>
                ) : (
                  <span className="feedback-thanks">Thanks for the feedback!</span>
                )}
              </div>
            )}

            <div className="report-section">
              <a
                href={`http://127.0.0.1:8000/api/incidents/${selectedDetail.id}/report`}
                className="download-btn"
                download
              >
                Download PDF Report
              </a>
            </div>

            <div className="alert-section">
              <h3>Admin Alert</h3>
              {!alertText ? (
                <button onClick={generateAlert} disabled={loadingAlert}>
                  {loadingAlert ? 'Generating...' : 'Generate Admin Alert'}
                </button>
              ) : (
                <div>
                  <pre className="alert-text">{alertText}</pre>
                  <button onClick={copyAlert} className="copy-btn">
                    <Copy size={14} /> {copied ? 'Copied!' : 'Copy to Clipboard'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;