import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import {
  Activity, AlertCircle, AlertTriangle, BarChart3, BrainCircuit,
  CheckCircle, ChevronRight, Clock, Copy, Database, FileText,
  LayoutDashboard, Lock, Network, Radio, RefreshCw, Search,
  Server, Settings, ShieldCheck, Terminal, Wifi, WifiOff, X, Zap
} from 'lucide-react';

import Topology from './Topology';
import AdminPanel from './AdminPanel';
import Login from './Login';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

const SEVERITY_COLORS = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#22c55e'
};

const TOOLTIP_STYLE = {
  background: '#0a0a0a',
  border: '1px solid #333333',
  borderRadius: 8,
  fontFamily: '"Times New Roman", Times, serif',
  color: '#ffffff'
};

const NAV = [
  ['overview', 'Overview', LayoutDashboard],
  ['incidents', 'Incidents', AlertTriangle],
  ['devices', 'Devices', Server],
  ['topology', 'Topology', Network],
  ['signals', 'Live Signals', Radio],
  ['ai', 'AI Diagnostics', BrainCircuit],
  ['analytics', 'Analytics', BarChart3],
  ['reports', 'Reports', FileText]
];

function StatusDot({ status = 'online' }) {
  return <span className={`status-dot ${status}`}><i /></span>;
}

function StatCard({ icon: Icon, label, value, detail, tone = 'blue' }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-icon"><Icon size={19} /></div>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
        {detail && <small>{detail}</small>}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="section-header">
      <div className="section-heading">
        {Icon && <span className="section-icon"><Icon size={15} /></span>}
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

function EmptyState({ icon: Icon = Activity, title, text }) {
  return (
    <div className="empty-state">
      <span><Icon size={23} /></span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    !!localStorage.getItem('netmind_token')
  );
  const [activeView, setActiveView] = useState('overview');

  const [incidents, setIncidents] = useState([]);
  const [signals, setSignals] = useState([]);
  const [recurringData, setRecurringData] = useState([]);
  const [performanceData, setPerformanceData] = useState(null);
  const [correctionsData, setCorrectionsData] = useState(null);
  const [escalatedIds, setEscalatedIds] = useState([]);

  const [incidentText, setIncidentText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [selectedDetail, setSelectedDetail] = useState(null);
  const [resolving, setResolving] = useState(false);

  const [similarIncidents, setSimilarIncidents] = useState([]);
  const [similarFaultType, setSimilarFaultType] = useState(null);

  const [alertText, setAlertText] = useState('');
  const [loadingAlert, setLoadingAlert] = useState(false);
  const [copied, setCopied] = useState(false);

  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);
  const [correctionChoice, setCorrectionChoice] = useState('');
  const [correctionText, setCorrectionText] = useState('');

  const [conversation, setConversation] = useState([]);
  const [askText, setAskText] = useState('');
  const [asking, setAsking] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const [testResults, setTestResults] = useState(null);
  const [runningTests, setRunningTests] = useState(false);

  const [wsStatus, setWsStatus] = useState('connecting');

  const fetchIncidents = () =>
    axios.get(`${API_BASE}/api/incidents`)
      .then(r => setIncidents(r.data))
      .catch(e => console.error('incidents:', e));

  const fetchSignals = () =>
    axios.get(`${API_BASE}/api/signals?limit=20`)
      .then(r => setSignals(r.data))
      .catch(e => console.error('signals:', e));

  const fetchRecurring = () =>
    axios.get(`${API_BASE}/api/analytics/recurring`)
      .then(r => setRecurringData(r.data))
      .catch(e => console.error('recurring:', e));

  const fetchPerformance = () =>
    axios.get(`${API_BASE}/api/analytics/performance`)
      .then(r => setPerformanceData(r.data))
      .catch(e => console.error('performance:', e));

  const fetchCorrections = () =>
    axios.get(`${API_BASE}/api/corrections`)
      .then(r => setCorrectionsData(r.data))
      .catch(e => console.error('corrections:', e));

  const fetchSimilar = id =>
    axios.get(`${API_BASE}/api/incidents/${id}/similar`)
      .then(r => {
        setSimilarFaultType(r.data.fault_type);
        setSimilarIncidents(r.data.similar || []);
      })
      .catch(() => {
        setSimilarFaultType(null);
        setSimilarIncidents([]);
      });

  useEffect(() => {
    fetchIncidents();
    fetchSignals();
    fetchRecurring();
    fetchPerformance();
    fetchCorrections();

    let ws;
    let timer;

    const connect = () => {
      setWsStatus('connecting');
      ws = new WebSocket('ws://127.0.0.1:8000/ws/incidents');

      ws.onopen = () => setWsStatus('connected');

      ws.onmessage = event => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'incident') {
            setIncidents(prev => {
              if (prev.some(i => i.id === data.id)) return prev;
              return [...prev, {
                id: data.id,
                device: data.device,
                issue: data.issue,
                severity: data.severity,
                status: data.status
              }];
            });
            fetchRecurring();
          }

          if (data.type === 'signal') {
            setSignals(prev => [{
              device: data.device,
              status: data.status,
              message: data.message,
              created_at: new Date().toLocaleTimeString()
            }, ...prev].slice(0, 20));
          }
        } catch (e) {
          console.error('websocket message:', e);
        }
      };

      ws.onerror = () => setWsStatus('error');

      ws.onclose = () => {
        setWsStatus('disconnected');
        timer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      clearTimeout(timer);
      if (ws) ws.close();
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get(`${API_BASE}/api/incidents/escalated`)
        .then(r => setEscalatedIds(r.data.map(i => i.id)))
        .catch(e => console.error('escalated:', e));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async () => {
    if (!incidentText.trim()) return;
    setSubmitting(true);
    setErrorMsg('');

    try {
      await axios.post(`${API_BASE}/api/incidents`, { text: incidentText });
      setIncidentText('');
      await fetchIncidents();
      setActiveView('incidents');
    } catch {
      setErrorMsg('Failed to submit incident. Is the backend running?');
    } finally {
      setSubmitting(false);
    }
  };

  const openDetail = async id => {
    try {
      const r = await axios.get(`${API_BASE}/api/incidents/${id}`);
      setSelectedDetail(r.data);
      setAlertText('');
      setCopied(false);
      setFeedbackGiven(false);
      setShowCorrectionForm(false);
      setCorrectionChoice('');
      setCorrectionText('');
      setConversation([]);
      setAskText('');
      fetchSimilar(id);
    } catch (e) {
      console.error('incident detail:', e);
    }
  };

  const resolveIncident = async () => {
    if (!selectedDetail) return;
    setResolving(true);
    try {
      await axios.post(`${API_BASE}/api/incidents/${selectedDetail.id}/resolve`);
      setSelectedDetail(prev => ({ ...prev, status: 'Resolved' }));
      setIncidents(prev => prev.map(i =>
        i.id === selectedDetail.id ? { ...i, status: 'Resolved' } : i
      ));
    } catch (e) {
      console.error('resolve:', e);
    } finally {
      setResolving(false);
    }
  };

  const submitFeedback = async (helpful, correctedCause = null) => {
    try {
      await axios.post(`${API_BASE}/api/incidents/${selectedDetail.id}/feedback`, {
        helpful,
        corrected_cause: correctedCause
      });
      setFeedbackGiven(true);
      setShowCorrectionForm(false);
      fetchPerformance();
      if (correctedCause) fetchCorrections();
    } catch (e) {
      console.error('feedback:', e);
    }
  };

  const submitCorrection = () => {
    const cause = correctionChoice === 'other'
      ? correctionText.trim()
      : correctionChoice;
    if (cause) submitFeedback('no', cause);
  };

  const askAI = async question => {
    if (!question.trim() || !selectedDetail) return;
    setAsking(true);
    try {
      const r = await axios.post(
        `${API_BASE}/api/incidents/${selectedDetail.id}/ask`,
        { question }
      );
      setConversation(prev => [...prev, {
        question,
        answer: r.data.answer
      }]);
      setAskText('');
    } catch {
      setConversation(prev => [...prev, {
        question,
        answer: 'Failed to get an answer. Check the backend.'
      }]);
    } finally {
      setAsking(false);
    }
  };

  const generateAlert = async () => {
    setLoadingAlert(true);
    try {
      const r = await axios.get(
        `${API_BASE}/api/incidents/${selectedDetail.id}/alert`
      );
      setAlertText(r.data.alert);
    } catch (e) {
      console.error('alert:', e);
    } finally {
      setLoadingAlert(false);
    }
  };

  const copyAlert = () => {
    navigator.clipboard.writeText(alertText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const runSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const r = await axios.get(`${API_BASE}/api/incidents/search`, {
        params: { text: searchQuery }
      });
      setSearchResults(r.data);
    } catch (e) {
      console.error('search:', e);
    } finally {
      setSearching(false);
    }
  };

  const runTests = async () => {
    setRunningTests(true);
    setTestResults(null);
    try {
      const r = await axios.post(`${API_BASE}/api/run-tests`);
      setTestResults(r.data);
      fetchIncidents();
    } catch (e) {
      console.error('tests:', e);
    } finally {
      setRunningTests(false);
    }
  };

  const totals = useMemo(() => ({
    total: incidents.length,
    open: incidents.filter(i => i.status === 'Open').length,
    resolved: incidents.filter(i =>
      i.status === 'Resolved' || i.status === 'Auto-Resolved'
    ).length,
    critical: incidents.filter(i => i.severity === 'Critical').length,
    escalated: escalatedIds.length
  }), [incidents, escalatedIds]);

  const devices = useMemo(() => {
    const map = new Map();

    incidents.forEach(i => {
      if (!i.device) return;
      if (!map.has(i.device)) {
        map.set(i.device, {
          device: i.device,
          incidents: 0,
          critical: 0,
          status: 'Unknown',
          lastSignal: '—'
        });
      }
      const d = map.get(i.device);
      d.incidents += 1;
      if (i.severity === 'Critical') d.critical += 1;
      if (i.status === 'Open') d.status = 'Fault';
    });

    signals.forEach(s => {
      if (!s.device) return;
      if (!map.has(s.device)) {
        map.set(s.device, {
          device: s.device,
          incidents: 0,
          critical: 0,
          status: 'Unknown',
          lastSignal: '—'
        });
      }
      const d = map.get(s.device);
      d.lastSignal = s.created_at || '—';
      if (s.status === 'fault') d.status = 'Fault';
      else if (d.status !== 'Fault') d.status = 'Online';
    });

    return [...map.values()];
  }, [incidents, signals]);

  const severityData = ['Critical', 'High', 'Medium', 'Low'].map(name => ({
    name,
    value: incidents.filter(i => i.severity === name).length,
    color: SEVERITY_COLORS[name]
  }));

  const healthyDevices = devices.filter(d => d.status === 'Online').length;
  const faultDevices = devices.filter(d => d.status === 'Fault').length;

  const go = view => setActiveView(view);

  const renderOverview = () => (
    <>
      <div className="page-heading">
        <div>
          <label>NETWORK OPERATIONS CENTER</label>
          <h1>Network Overview</h1>
          <p>Real-time fault monitoring, AI diagnosis and incident operations.</p>
        </div>
        <div className="connection-box">
          <StatusDot status={wsStatus === 'connected' ? 'online' : 'offline'} />
          <div><strong>{wsStatus === 'connected' ? 'LIVE' : 'RECONNECTING'}</strong><span>WebSocket stream</span></div>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard icon={Activity} label="Network Health" value={totals.open === 0 ? '100%' : `${Math.max(0, 100 - Math.min(99, totals.open * 5))}%`} detail="Incident-based indicator" tone="green" />
        <StatCard icon={Server} label="Monitored Devices" value={devices.length} detail={`${healthyDevices} online`} tone="blue" />
        <StatCard icon={AlertTriangle} label="Critical Incidents" value={totals.critical} detail={totals.critical ? 'Immediate attention' : 'No critical faults'} tone="red" />
        <StatCard icon={Clock} label="Open Incidents" value={totals.open} detail={`${totals.escalated} escalated`} tone="orange" />
        <StatCard icon={Wifi} label="Live Signals" value={signals.length} detail="Latest 20 events" tone="cyan" />
      </div>

      <div className="dashboard-grid two">
        <section className="panel">
          <SectionHeader icon={AlertTriangle} title="Active Incidents" subtitle="Highest priority faults" action={<button className="link-button" onClick={() => go('incidents')}>View all <ChevronRight size={13}/></button>} />
          <div className="incident-list">
            {incidents.filter(i => i.status !== 'Resolved' && i.status !== 'Auto-Resolved').slice(0, 7).map(i => (
              <button className="incident-row" key={i.id} onClick={() => openDetail(i.id)}>
                <span className={`severity-bar ${i.severity?.toLowerCase()}`} />
                <div className="incident-row-main">
                  <strong><Server size={13}/> {i.device}</strong>
                  <span>{i.issue}</span>
                  <small><b className={`badge ${i.severity?.toLowerCase()}`}>{i.severity}</b>{escalatedIds.includes(i.id) && <em>ESCALATED</em>} {i.status}</small>
                </div>
                <ChevronRight size={15}/>
              </button>
            ))}
            {totals.open === 0 && <EmptyState icon={CheckCircle} title="Network clear" text="No open incidents require attention." />}
          </div>
        </section>

        <section className="panel">
          <SectionHeader icon={BarChart3} title="Severity Distribution" subtitle="Current incident classification" />
          {incidents.length === 0 ? (
            <EmptyState icon={BarChart3} title="No incident data" text="The chart will populate as faults are detected." />
          ) : (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={235}>
                <PieChart>
                  <Pie data={severityData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={82} paddingAngle={3}>
                    {severityData.map((x, i) => <Cell key={i} fill={x.color} stroke="none" />)}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={{ fontFamily: '"Times New Roman", Times, serif' }} labelStyle={{ fontFamily: '"Times New Roman", Times, serif' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="severity-legend">
                {severityData.map(s => <span key={s.name}><i style={{background:s.color}}/>{s.name}<b>{s.value}</b></span>)}
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="dashboard-grid two">
        <section className="panel">
          <SectionHeader icon={Radio} title="Live Network Signals" subtitle="Latest device telemetry" action={<button className="link-button" onClick={() => go('signals')}>Open monitor <ChevronRight size={13}/></button>} />
          <div className="signal-list">
            {signals.slice(0, 8).map((s, i) => (
              <div className={`signal-row ${s.status}`} key={i}>
                <span className={`signal-dot ${s.status}`} />
                <time>{s.created_at}</time>
                <strong>{s.device}</strong>
                <span>{s.message}</span>
              </div>
            ))}
            {!signals.length && <EmptyState icon={Radio} title="Waiting for signals" text="No telemetry has been received." />}
          </div>
        </section>

        <section className="panel">
          <SectionHeader icon={RefreshCw} title="Recurring Faults" subtitle="Frequently observed patterns" action={<button className="link-button" onClick={() => go('analytics')}>Analytics <ChevronRight size={13}/></button>} />
          {recurringData.length ? (
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={recurringData.slice(0, 6)} layout="vertical" margin={{left:8,right:12}}>
                <CartesianGrid stroke="#1e2a3d" strokeDasharray="3 3" />
                <XAxis type="number" stroke="#68778f" tick={{fontSize:10, fontFamily: '"Times New Roman", Times, serif'}} />
                <YAxis type="category" dataKey="label" width={125} stroke="#68778f" tick={{fontSize:10, fontFamily: '"Times New Roman", Times, serif'}} />
                <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={{ fontFamily: '"Times New Roman", Times, serif' }} labelStyle={{ fontFamily: '"Times New Roman", Times, serif' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState icon={RefreshCw} title="No recurring patterns" text="Historical patterns will appear here." />}
        </section>
      </div>

      <section className="panel new-incident">
        <SectionHeader icon={BrainCircuit} title="Analyze New Network Incident" subtitle="Paste an incident email, alert or engineer observation." />
        <div className="new-incident-grid">
          <textarea value={incidentText} onChange={e => setIncidentText(e.target.value)} rows={5} placeholder="Example: SW-CORE-01 reports interface Gi0/24 down. Multiple downstream devices are unreachable..." />
          <div>
            <button className="primary-button" onClick={handleSubmit} disabled={submitting || !incidentText.trim()}><BrainCircuit size={15}/>{submitting ? 'Analyzing...' : 'Analyze Incident'}</button>
            <p>NetMind will classify severity, identify likely root cause and provide engineering verification steps.</p>
          </div>
        </div>
        {errorMsg && <div className="inline-error"><AlertCircle size={14}/>{errorMsg}</div>}
      </section>
    </>
  );

  const renderIncidents = () => (
    <>
      <div className="page-heading">
        <div><label>OPERATIONS</label><h1>Incident Management</h1><p>Investigate, prioritize and resolve network faults.</p></div>
        <div className="heading-metrics"><b>{totals.open} OPEN</b><b>{totals.critical} CRITICAL</b></div>
      </div>

      <section className="panel">
        <div className="toolbar">
          <div className="search-box"><Search size={15}/><input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search incident or diagnosed cause..." /><button onClick={runSearch} disabled={searching}>Search</button></div>
          <button className="secondary-button" onClick={fetchIncidents}><RefreshCw size={14}/> Refresh</button>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Device</th><th>Issue</th><th>Severity</th><th>Status</th><th>Priority</th><th>Action</th></tr></thead>
            <tbody>
              {incidents.map(i => (
                <tr key={i.id} onClick={() => openDetail(i.id)}>
                  <td className="device-cell"><Server size={13}/>{i.device}</td>
                  <td>{i.issue}</td>
                  <td><b className={`badge ${i.severity?.toLowerCase()}`}>{i.severity}</b></td>
                  <td><span className={`status-pill ${i.status?.toLowerCase().replace(' ','-')}`}>{i.status === 'Auto-Resolved' ? '⚡ Auto-Resolved' : i.status}</span></td>
                  <td>{escalatedIds.includes(i.id) ? <span className="escalated"><AlertTriangle size={12}/> ESCALATED</span> : <span className="muted">NORMAL</span>}</td>
                  <td><button className="table-action" onClick={e => {e.stopPropagation();openDetail(i.id)}}>Investigate <ChevronRight size={12}/></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!incidents.length && <EmptyState icon={FileText} title="No incidents" text="There are currently no incident records." />}
        </div>
      </section>

      {searchResults && (
        <section className="panel">
          <SectionHeader icon={Search} title="Search Results" subtitle={searchResults.fault_type ? `Matched cause: ${searchResults.fault_type}` : 'Historical incident search'} />
          {searchResults.results?.length ? (
            <div className="table-wrap"><table className="data-table"><thead><tr><th>Device</th><th>Issue</th><th>Status</th><th>Date</th></tr></thead><tbody>
              {searchResults.results.map(r => <tr key={r.id} onClick={() => openDetail(r.id)}><td>{r.device}</td><td>{r.issue}</td><td>{r.status}</td><td>{r.created_at}</td></tr>)}
            </tbody></table></div>
          ) : <EmptyState icon={Search} title="No matches" text="No historical incident matched the search." />}
        </section>
      )}
    </>
  );

  const renderDevices = () => (
    <>
      <div className="page-heading">
        <div><label>NETWORK</label><h1>Device Health</h1><p>Operational visibility from live signals and incident activity.</p></div>
      </div>

      <div className="stat-grid">
        <StatCard icon={Server} label="Detected Devices" value={devices.length} tone="blue"/>
        <StatCard icon={Wifi} label="Online" value={healthyDevices} tone="green"/>
        <StatCard icon={WifiOff} label="Fault" value={faultDevices} tone="red"/>
        <StatCard icon={Activity} label="Signals" value={signals.length} tone="cyan"/>
        <StatCard icon={AlertTriangle} label="Critical Device Events" value={devices.reduce((n,d)=>n+d.critical,0)} tone="orange"/>
      </div>

      <section className="panel">
        <SectionHeader icon={Server} title="Device Health Matrix" subtitle="Devices detected through incidents and live telemetry." />
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Device</th><th>State</th><th>Incidents</th><th>Critical</th><th>Last Signal</th><th>Risk</th></tr></thead>
            <tbody>
              {devices.map(d => (
                <tr key={d.device}>
                  <td className="device-cell"><Server size={13}/>{d.device}</td>
                  <td><span className="device-state"><StatusDot status={d.status === 'Online' ? 'online' : d.status === 'Fault' ? 'offline' : 'warning'}/>{d.status}</span></td>
                  <td>{d.incidents}</td>
                  <td className={d.critical ? 'danger-number' : 'healthy-number'}>{d.critical}</td>
                  <td className="mono">{d.lastSignal}</td>
                  <td><span className={`risk ${d.critical ? 'high' : d.incidents ? 'medium' : 'low'}`}>{d.critical ? 'HIGH' : d.incidents ? 'MEDIUM' : 'LOW'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!devices.length && <EmptyState icon={Server} title="No devices detected" text="Devices will appear when signals or incidents are received." />}
        </div>
      </section>
    </>
  );

  const renderSignals = () => (
    <>
      <div className="page-heading">
        <div><label>NETWORK TELEMETRY</label><h1>Live Signal Monitor</h1><p>Real-time device check-ins and fault signals.</p></div>
        <div className="connection-box"><StatusDot status={wsStatus === 'connected' ? 'online' : 'offline'}/><div><strong>{wsStatus.toUpperCase()}</strong><span>WebSocket</span></div></div>
      </div>

      <div className="stat-grid">
        <StatCard icon={Radio} label="Signals" value={signals.length} tone="cyan"/>
        <StatCard icon={CheckCircle} label="Healthy" value={signals.filter(s=>s.status==='ok').length} tone="green"/>
        <StatCard icon={AlertCircle} label="Fault" value={signals.filter(s=>s.status==='fault').length} tone="red"/>
        <StatCard icon={Activity} label="Stream" value={wsStatus === 'connected' ? 'LIVE' : 'OFFLINE'} tone={wsStatus === 'connected' ? 'green' : 'red'}/>
      </div>

      <section className="panel">
        <SectionHeader icon={Radio} title="Real-Time Signal Stream" subtitle="Newest events appear at the top." action={<button className="secondary-button" onClick={fetchSignals}><RefreshCw size={14}/> Refresh</button>} />
        <div className="signal-monitor">
          {signals.map((s,i) => (
            <div className={`signal-monitor-row ${s.status}`} key={i}>
              <span className={`signal-dot ${s.status}`}/>
              <time>{s.created_at}</time>
              <strong>{s.device}</strong>
              <span>{s.message}</span>
              <b>{s.status === 'ok' ? 'HEALTHY' : 'FAULT'}</b>
            </div>
          ))}
          {!signals.length && <EmptyState icon={Radio} title="No signals" text="Waiting for monitored device telemetry." />}
        </div>
      </section>
    </>
  );

  const renderTopology = () => (
    <>
      <div className="page-heading">
        <div><label>NETWORK</label><h1>Network Topology</h1><p>Visualize network relationships and affected devices.</p></div>
      </div>
      <section className="panel topology-panel">
        <SectionHeader icon={Network} title="Network Map" subtitle="Use incident details to highlight an affected device." />
        <div className="topology-canvas"><Topology /></div>
      </section>
    </>
  );

  const renderAI = () => (
    <>
      <div className="page-heading">
        <div><label>AI OPERATIONS</label><h1>NetMind AI Diagnostics</h1><p>Root-cause analysis, evidence, verification and engineer feedback.</p></div>
        <div className="ai-live"><BrainCircuit size={15}/> AI ENGINE ACTIVE</div>
      </div>

      <div className="stat-grid">
        <StatCard icon={BrainCircuit} label="Feedback Records" value={performanceData?.total_feedback ?? 0} tone="blue"/>
        <StatCard icon={CheckCircle} label="Overall Accuracy" value={performanceData ? `${performanceData.overall_accuracy}%` : '—'} tone="green"/>
        <StatCard icon={Database} label="Corrections" value={correctionsData?.total ?? 0} tone="orange"/>
        <StatCard icon={Zap} label="Auto-Resolved" value={incidents.filter(i=>i.status==='Auto-Resolved').length} tone="cyan"/>
      </div>

      <section className="panel">
        <SectionHeader icon={BrainCircuit} title="Recent AI-Diagnosed Incidents" subtitle="Open an incident to inspect reasoning and evidence." />
        <div className="ai-grid">
          {incidents.slice(0,10).map(i => (
            <button className="ai-card" key={i.id} onClick={() => openDetail(i.id)}>
              <div><strong><Server size={13}/> {i.device}</strong><b className={`badge ${i.severity?.toLowerCase()}`}>{i.severity}</b></div>
              <p>{i.issue}</p>
              <small>{i.status}<ChevronRight size={13}/></small>
            </button>
          ))}
        </div>
      </section>
    </>
  );

  const renderAnalytics = () => (
    <>
      <div className="page-heading">
        <div><label>ANALYTICS</label><h1>Network & AI Analytics</h1><p>Recurring faults and AI performance.</p></div>
      </div>

      <section className="panel">
        <SectionHeader icon={RefreshCw} title="Recurring Network Issues" subtitle="Most frequently observed fault patterns." />
        {recurringData.length ? (
          <ResponsiveContainer width="100%" height={310}>
            <BarChart data={recurringData} layout="vertical" margin={{left:20,right:20}}>
              <CartesianGrid stroke="#1e2a3d" strokeDasharray="3 3"/>
              <XAxis type="number" stroke="#68778f" tick={{ fontFamily: '"Times New Roman", Times, serif' }}/>
              <YAxis type="category" dataKey="label" width={190} stroke="#68778f" tick={{ fontFamily: '"Times New Roman", Times, serif' }}/>
              <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={{ fontFamily: '"Times New Roman", Times, serif' }} labelStyle={{ fontFamily: '"Times New Roman", Times, serif' }}/>
              <Bar dataKey="count" fill="#3b82f6" radius={[0,5,5,0]}/>
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyState icon={BarChart3} title="No analytics" text="Analytics will populate as incidents accumulate."/>}
      </section>

      <section className="panel">
        <SectionHeader icon={BrainCircuit} title="AI Performance" subtitle="Accuracy based on engineer feedback." />
        {performanceData ? (
          <div className="performance-grid">
            <div className="performance-kpi"><span>OVERALL ACCURACY</span><strong>{performanceData.overall_accuracy}%</strong></div>
            <div className="performance-kpi"><span>TOTAL FEEDBACK</span><strong>{performanceData.total_feedback}</strong></div>
            <div className="performance-kpi"><span>HIGH CONFIDENCE</span><strong>{performanceData.by_confidence?.high ?? 0}%</strong></div>
          </div>
        ) : <EmptyState icon={BrainCircuit} title="No performance data" text="Engineer feedback is required to calculate AI performance."/>}
      </section>

      <section className="panel">
        <SectionHeader icon={Database} title="Corrections Log" subtitle="Cases where engineers corrected the AI diagnosis." />
        {correctionsData?.corrections?.length ? (
          <div className="table-wrap"><table className="data-table"><thead><tr><th>Device</th><th>Issue</th><th>AI Said</th><th>Actual Cause</th><th>Date</th></tr></thead><tbody>
            {correctionsData.corrections.map((c,i)=><tr key={i} onClick={()=>openDetail(c.incident_id)}><td>{c.device}</td><td>{c.issue}</td><td className="wrong">{c.ai_said || '—'}</td><td className="correct">{c.corrected_to}</td><td>{c.created_at}</td></tr>)}
          </tbody></table></div>
        ) : <EmptyState icon={Database} title="No corrections logged" text="Engineer corrections will appear here."/>}
      </section>

      <section className="panel">
        <SectionHeader icon={Terminal} title="Developer System Test" subtitle="End-to-end backend and AI test suite." action={<button className="secondary-button" onClick={runTests} disabled={runningTests}><Terminal size={14}/>{runningTests ? 'Running...' : 'Run Tests'}</button>} />
        {testResults && <div className="test-results"><strong>{testResults.passed} / {testResults.total} passed</strong>{testResults.results?.map((r,i)=><div className={`test-row ${r.status.toLowerCase()}`} key={i}><b>{r.status}</b><span>{r.text}</span><small>{r.status === 'PASS' ? `${r.device || ''} ${r.severity || ''}` : r.error}</small></div>)}</div>}
      </section>
    </>
  );

  const renderReports = () => (
    <>
      <div className="page-heading">
        <div><label>DOCUMENTATION</label><h1>Incident Reports</h1><p>Generate detailed PDF reports from network incidents.</p></div>
      </div>
      <section className="panel">
        <SectionHeader icon={FileText} title="Available Reports" subtitle="Download a report for any incident." />
        <div className="report-grid">
          {incidents.map(i => (
            <div className="report-card" key={i.id}>
              <span><FileText size={18}/></span>
              <div><strong>{i.device}</strong><p>{i.issue}</p><small>{i.created_at || 'Incident report'}</small></div>
              <a href={`${API_BASE}/api/incidents/${i.id}/report`} download>PDF</a>
            </div>
          ))}
        </div>
      </section>
    </>
  );

  const renderAdmin = () => <div className="admin-shell"><AdminPanel onBack={() => go('overview')} /></div>;

  const renderModal = () => {
    if (!selectedDetail) return null;
    const d = selectedDetail;
    const diag = d.diagnosis;

    return (
      <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
        <div className="modal" onClick={e => e.stopPropagation()}>
          <button className="modal-close" onClick={() => setSelectedDetail(null)}><X size={17}/></button>

          <div className="modal-header">
            <div><label>INCIDENT WORKSPACE</label><h2>{d.device}</h2><p>{d.issue}</p></div>
            <b className={`badge ${d.severity?.toLowerCase()}`}>{d.severity}</b>
          </div>

          <div className={`severity-banner ${d.severity?.toLowerCase()}`}>
            {d.severity === 'Critical' ? 'Immediate action required' : d.severity === 'High' ? 'Prompt attention needed' : d.severity === 'Medium' ? 'Schedule investigation' : 'Monitor and review'}
          </div>

          <div className="resolve-row">
            <span className={`status-pill ${d.status?.toLowerCase().replace(' ','-')}`}>{d.status === 'Auto-Resolved' ? '⚡ Auto-Resolved' : d.status}</span>
            {d.status !== 'Resolved' && d.status !== 'Auto-Resolved' && <button className="resolve-button" onClick={resolveIncident} disabled={resolving}>{resolving ? 'Resolving...' : 'Mark Resolved'}</button>}
          </div>

          {d.remediation_log && <div className="remediation"><h3><Zap size={14}/> Automated Remediation</h3><p>Safe automated remediation was applied for this known issue.</p><pre>{d.remediation_log}</pre></div>}

          <div className="modal-section">
            <SectionHeader icon={Network} title="Network Topology" subtitle="Affected device context."/>
            <div className="modal-topology"><Topology affectedDevice={d.device}/></div>
          </div>

          {similarIncidents.length > 0 && <div className="modal-section">
            <SectionHeader icon={RefreshCw} title="Similar Past Incidents" subtitle={`Same diagnosed cause: ${similarFaultType || 'Unknown'}`}/>
            <div className="similar-list">{similarIncidents.map(s=><button key={s.id} onClick={()=>openDetail(s.id)}><strong>{s.device}</strong><span>{s.issue}</span><small>{s.status} · {s.created_at}</small></button>)}</div>
          </div>}

          <div className="modal-section">
            <SectionHeader icon={BrainCircuit} title="AI Diagnosis" subtitle="Root cause, confidence and engineering evidence."/>
            {diag?.matched ? (
              <>
                <div className="diagnosis-summary"><div><label>CONFIDENCE</label><strong>{diag.confidence_score}</strong></div><div><label>LEVEL</label><strong>{diag.confidence}</strong></div></div>
                {diag.causes?.filter((c,idx)=>diag.confidence === 'high' ? idx === 0 : true).map((c,i)=><div className="cause-block" key={i}>
                  <div className="cause-title"><strong>{i+1}. {c.cause}</strong><b>{c.probability}% likely</b></div>
                  <div className="evidence-row"><span>Similarity: {c.similarity_score}</span><span>{c.matched_keywords?.length ? `Matched: ${c.matched_keywords.join(', ')}` : 'Semantic match'}</span>{c.business_impact && <span className="impact">Impact: {c.business_impact}</span>}</div>
                  <p><label>VERIFY</label><code>{c.verification_command}</code></p>
                  <p><label>STEPS</label>{c.troubleshooting_steps}</p>
                </div>)}
                {diag.rejected_causes?.length > 0 && <details className="rejected"><summary>Other causes considered and ruled out ({diag.rejected_causes.length})</summary>{diag.rejected_causes.map((r,i)=><p key={i}><strong>{r.cause}</strong> — {r.reason}</p>)}</details>}
              </>
            ) : <div className="no-match"><AlertCircle size={15}/> No confident knowledge-base match. Manual engineer review is required.</div>}
          </div>

          {diag?.matched && <div className="feedback-box">
            {!feedbackGiven ? (!showCorrectionForm ? <div className="feedback-inline"><span>Was this diagnosis helpful?</span><button onClick={()=>submitFeedback('yes')}>Yes</button><button onClick={()=>setShowCorrectionForm(true)}>No / Correct</button></div> :
              <div className="correction-form"><label>Actual cause</label><select value={correctionChoice} onChange={e=>setCorrectionChoice(e.target.value)}><option value="">Select...</option>{diag.causes?.map((c,i)=><option key={i} value={c.cause}>{c.cause}</option>)}{diag.rejected_causes?.map((r,i)=><option key={i} value={r.cause}>{r.cause}</option>)}<option value="other">Other</option></select>{correctionChoice === 'other' && <textarea value={correctionText} onChange={e=>setCorrectionText(e.target.value)} rows={3} placeholder="Describe the actual cause..."/>}<div><button onClick={submitCorrection}>Submit Correction</button><button className="secondary-button" onClick={()=>setShowCorrectionForm(false)}>Cancel</button></div></div>
            ) : <span className="feedback-thanks">✓ Engineer feedback recorded.</span>}
          </div>}

          <div className="modal-section">
            <SectionHeader icon={BrainCircuit} title="Ask NetMind AI" subtitle="Investigate this incident interactively."/>
            <div className="question-chips">{['Why this cause?','How confident is this?','What should I check first?','What if remediation fails?','Are there similar past incidents?'].map(q=><button key={q} onClick={()=>askAI(q)} disabled={asking}>{q}</button>)}</div>
            <div className="ask-row"><textarea value={askText} onChange={e=>setAskText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();askAI(askText)}}} rows={2} placeholder="Ask a question about this incident..."/><button onClick={()=>askAI(askText)} disabled={asking||!askText.trim()}>{asking?'Asking...':'Ask'}</button></div>
            {conversation.map((c,i)=><div className="conversation" key={i}><p><b>Q</b>{c.question}</p><p><b>A</b>{c.answer}</p></div>)}
          </div>

          <div className="modal-actions">
            <a href={`${API_BASE}/api/incidents/${d.id}/report`} download><FileText size={14}/> Download PDF Report</a>
            {!alertText ? <button className="secondary-button" onClick={generateAlert} disabled={loadingAlert}><ShieldCheck size={14}/>{loadingAlert?'Generating...':'Generate Admin Alert'}</button> : <div className="alert-output"><pre>{alertText}</pre><button className="secondary-button" onClick={copyAlert}><Copy size={14}/>{copied?'Copied':'Copy Alert'}</button></div>}
          </div>
        </div>
      </div>
    );
  };

  if (!isAuthenticated) return <Login onLogin={() => setIsAuthenticated(true)} />;

  const page = {
    overview: renderOverview,
    incidents: renderIncidents,
    devices: renderDevices,
    topology: renderTopology,
    signals: renderSignals,
    ai: renderAI,
    analytics: renderAnalytics,
    reports: renderReports,
    admin: renderAdmin
  }[activeView] || renderOverview;

  return (
    <div className="app-shell dark-theme">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><Server size={19}/></span>
          <div><strong>NETMIND</strong><small>AI NETWORK OPERATIONS</small></div>
        </div>

        <div className="sidebar-status">
          <StatusDot status={wsStatus === 'connected' ? 'online' : 'offline'}/>
          <div><strong>{wsStatus === 'connected' ? 'System Online' : 'Connection Degraded'}</strong><span>Real-time monitoring</span></div>
        </div>

        <div className="nav-label">OPERATIONS</div>
        {NAV.slice(0,2).map(([id,label,Icon])=><button key={id} className={`nav-item ${activeView===id?'active':''}`} onClick={()=>go(id)}><Icon size={16}/><span>{label}</span>{id==='incidents'&&totals.open>0&&<em>{totals.open}</em>}</button>)}

        <div className="nav-label">NETWORK</div>
        {NAV.slice(2,5).map(([id,label,Icon])=><button key={id} className={`nav-item ${activeView===id?'active':''}`} onClick={()=>go(id)}><Icon size={16}/><span>{label}</span></button>)}

        <div className="nav-label">AI OPERATIONS</div>
        {NAV.slice(5,7).map(([id,label,Icon])=><button key={id} className={`nav-item ${activeView===id?'active':''}`} onClick={()=>go(id)}><Icon size={16}/><span>{label}</span></button>)}

        <div className="nav-label">TOOLS</div>
        <button className={`nav-item ${activeView==='reports'?'active':''}`} onClick={()=>go('reports')}><FileText size={16}/><span>Reports</span></button>

        <div className="sidebar-spacer"/>
        <button className={`nav-item ${activeView==='admin'?'active':''}`} onClick={()=>go('admin')}><Settings size={16}/><span>Developer / Admin</span></button>
        <div className="sidebar-footer">NetMind AI · NOC Platform<br/>Desktop Edition</div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>NETMIND</span><ChevronRight size={13}/><strong>{activeView === 'admin' ? 'Developer / Admin' : NAV.find(n=>n[0]===activeView)?.[1]}</strong></div>
          <div className="topbar-right">
            <span><StatusDot status="online"/> API ONLINE</span>
            <span><StatusDot status={wsStatus==='connected'?'online':'offline'}/> REAL-TIME</span>
            <span><Clock size={13}/> {new Date().toLocaleTimeString()}</span>
            <span><Lock size={13}/> Authenticated</span>
          </div>
        </header>
        <div className="content">{page()}</div>
      </main>

      {renderModal()}
    </div>
  );
}

export default App;