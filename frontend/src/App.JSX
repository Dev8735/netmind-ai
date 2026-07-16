import { useState, useEffect } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, CheckCircle, Clock, Server, X, Copy } from 'lucide-react';
import Topology from './Topology';
import './App.css';

const severityData = [
  { name: 'Critical', value: 1, color: '#ef4444' },
  { name: 'High', value: 1, color: '#f97316' },
  { name: 'Medium', value: 1, color: '#eab308' },
  { name: 'Low', value: 0, color: '#22c55e' },
];

function App() {
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

  const fetchIncidents = () => {
    axios.get('http://127.0.0.1:8000/api/incidents')
      .then(res => setIncidents(res.data))
      .catch(err => console.error('Failed to fetch incidents:', err));
  };

  useEffect(() => {
    fetchIncidents();
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
          <h2>Severity Breakdown</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={severityData} dataKey="value" nameKey="name" outerRadius={80} label>
                {severityData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
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
                <td><span className={`badge ${i.severity.toLowerCase()}`}>{i.severity}</span></td>
                <td>{i.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
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

            <h3>Network Topology</h3>
            <Topology affectedDevice={selectedDetail.device} />

            {selectedDetail.diagnosis && selectedDetail.diagnosis.matched ? (
              <div>
                <h3>Ranked Possible Causes</h3>
                {selectedDetail.diagnosis.causes.map((c, idx) => (
                  <div key={idx} className="cause-block">
                    <p><strong>{idx + 1}. {c.cause}</strong> ({c.probability}% likely)</p>
                    <p className="cause-detail">Verify: <code>{c.verification_command}</code></p>
                    <p className="cause-detail">Steps: {c.troubleshooting_steps}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-match-banner">
                No confident match found in knowledge base. This incident requires manual engineer review.
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