import { useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, CheckCircle, Clock, Server } from 'lucide-react';
import './App.css';

const mockIncidents = [
  { id: 1, device: 'Core-Switch-01', issue: 'No ping response', severity: 'Critical', status: 'Open' },
  { id: 2, device: 'Router-Branch-02', issue: 'High CPU usage', severity: 'High', status: 'In Progress' },
  { id: 3, device: 'AP-Floor3-05', issue: 'Intermittent drops', severity: 'Medium', status: 'Resolved' },
];

const severityData = [
  { name: 'Critical', value: 1, color: '#ef4444' },
  { name: 'High', value: 1, color: '#f97316' },
  { name: 'Medium', value: 1, color: '#eab308' },
  { name: 'Low', value: 0, color: '#22c55e' },
];

function App() {
  const [incidentText, setIncidentText] = useState('');
  const [incidents] = useState(mockIncidents);

  const handleSubmit = () => {
    alert(`Will send to backend: "${incidentText}"`);
    setIncidentText('');
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
          />
          <button onClick={handleSubmit}>Analyze Incident</button>
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