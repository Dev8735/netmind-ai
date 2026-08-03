import { useState, useEffect } from 'react';
import axios from 'axios';
import { Lock, ArrowLeft } from 'lucide-react';
import { PipelineFlow, CauseTree } from './DecisionTree';
import KnowledgeGraph from './KnowledgeGraph';

function AdminPanel() {
  const [isVerified, setIsVerified] = useState(!!localStorage.getItem('netmind_admin_verified'));
  const [password, setPassword] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');

  const [symptomGroups, setSymptomGroups] = useState([]);
  const [selectedSymptom, setSelectedSymptom] = useState('');
  const [treeData, setTreeData] = useState(null);
  const [graphData, setGraphData] = useState(null);

  const goBack = () => {
    window.location.hash = '';
  };

  const handleVerify = async () => {
    if (!password.trim()) return;
    setVerifying(true);
    setError('');
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/admin/verify', { password });
      if (res.data.valid) {
        localStorage.setItem('netmind_admin_verified', '1');
        setIsVerified(true);
      } else {
        setError('Incorrect admin password.');
      }
    } catch (err) {
      console.error('Admin verification failed:', err);
      setError('Failed to verify. Is the backend running?');
    } finally {
      setVerifying(false);
    }
  };

  const lockPanel = () => {
    localStorage.removeItem('netmind_admin_verified');
    setIsVerified(false);
    setPassword('');
  };

  const fetchSymptomGroups = () => {
    axios.get('http://127.0.0.1:8000/api/knowledge-base/symptom-groups')
      .then(res => setSymptomGroups(res.data))
      .catch(err => console.error('Failed to fetch symptom groups:', err));
  };

  const fetchTree = (symptom) => {
    if (!symptom) {
      setTreeData(null);
      return;
    }
    axios.get('http://127.0.0.1:8000/api/knowledge-base/tree', { params: { symptom } })
      .then(res => setTreeData(res.data))
      .catch(err => console.error('Failed to fetch decision tree:', err));
  };

  const fetchKnowledgeGraph = () => {
    axios.get('http://127.0.0.1:8000/api/knowledge-graph')
      .then(res => setGraphData(res.data))
      .catch(err => console.error('Failed to fetch knowledge graph:', err));
  };

  useEffect(() => {
    if (isVerified) {
      fetchSymptomGroups();
      fetchKnowledgeGraph();
    }
  }, [isVerified]);

  if (!isVerified) {
    return (
      <div className="dashboard">
        <header className="topbar">
          <h1><Lock size={22} /> NetMind AI - Admin Panel</h1>
        </header>
        <section className="main-grid">
          <div className="panel" style={{ maxWidth: 420, margin: '40px auto' }}>
            <h2>Admin Password Required</h2>
            <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '12px' }}>
              This section contains internal diagnosis-engine tooling (decision logic,
              decision tree explorer, knowledge graph) and requires a separate admin password.
            </p>
            <textarea
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleVerify(); } }}
              placeholder="Admin password..."
              rows={1}
              disabled={verifying}
              style={{ fontFamily: 'inherit' }}
            />
            <button onClick={handleVerify} disabled={verifying} style={{ marginTop: '10px' }}>
              {verifying ? 'Verifying...' : 'Unlock Admin Panel'}
            </button>
            {error && <p style={{ color: '#ef4444', marginTop: '8px' }}>{error}</p>}
            <button
              onClick={goBack}
              style={{ marginTop: '16px', background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={14} /> Back to Dashboard
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="topbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1><Lock size={22} /> NetMind AI - Admin Panel</h1>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={goBack} style={{ background: '#334155' }}>
            <ArrowLeft size={14} style={{ marginRight: '4px' }} /> Back to Dashboard
          </button>
          <button onClick={lockPanel} style={{ background: '#334155' }}>
            <Lock size={14} style={{ marginRight: '4px' }} /> Lock Panel
          </button>
        </div>
      </header>

      <section className="panel">
        <h2>How NetMind AI Diagnoses a Fault <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(the engine's decision logic)</span></h2>
        <PipelineFlow />
      </section>

      <section className="panel">
        <h2>Decision Tree Explorer <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(branching causes per symptom)</span></h2>
        <select
          value={selectedSymptom}
          onChange={(e) => {
            setSelectedSymptom(e.target.value);
            fetchTree(e.target.value);
          }}
          style={{
            width: '100%', padding: '8px', marginBottom: '12px',
            background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155',
            borderRadius: '6px', fontSize: '13px'
          }}
        >
          <option value="">Select a symptom group...</option>
          {symptomGroups.map((g, idx) => (
            <option key={idx} value={g.symptom}>
              {g.symptom} ({g.cause_count} possible cause{g.cause_count !== 1 ? 's' : ''})
            </option>
          ))}
        </select>
        <CauseTree symptom={treeData?.symptom} causes={treeData?.causes} />
      </section>

      <section className="panel">
        <h2>Knowledge Graph <span style={{fontWeight:400, fontSize:'12px', color:'#94a3b8'}}>(devices ↔ diagnosed fault types, from real incident history)</span></h2>
        <KnowledgeGraph nodes={graphData?.nodes} edges={graphData?.edges} />
      </section>
    </div>
  );
}

export default AdminPanel;