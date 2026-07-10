import { useState, useEffect } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, CheckCircle, Clock, Server } from 'lucide-react';
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

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1><Server size={24} /> NetMind AI — Network Fault Diagnosis Assistant</h1>
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
        <h2>Incident History</h2>
        <table>
          <thead>
            <tr><th>Device</th><th>Issue</th><th>Severity</th><th>Status</th></tr>
          </thead>
          <tbody>
            {incidents.map(i => (
              <tr key={i.id}>
                <td>{i.device}</td><td>{i.issue}</td>
                <td><span className={`badge ${i.severity.toLowerCase()}`}>{i.severity}</span></td>
                <td>{i.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export default App;