import { useMemo } from 'react';
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';

const SEVERITY_COLORS = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#22c55e',
};

const baseNodeStyle = {
  background: '#1e293b',
  color: '#e2e8f0',
  border: '1px solid #334155',
  borderRadius: 8,
  padding: 10,
  fontSize: 12,
  whiteSpace: 'pre-line',
  textAlign: 'center',
};

// ---------- Static pipeline diagram: how the engine actually decides ----------

const pipelineNodes = [
  { id: 'p1', position: { x: 0, y: 120 }, data: { label: 'Incident Text\n(free-form description)' }, type: 'input',
    style: { ...baseNodeStyle, background: '#0f172a', width: 170 } },
  { id: 'p2', position: { x: 230, y: 120 }, data: { label: 'NLP Parsing\n(device, category, keywords)' },
    style: { ...baseNodeStyle, width: 170 } },
  { id: 'p3', position: { x: 460, y: 120 }, data: { label: 'Embedding Match\nvs Knowledge Base' },
    style: { ...baseNodeStyle, width: 170 } },
  { id: 'p4', position: { x: 690, y: 120 }, data: { label: 'Ranked Causes\n+ Confidence Score' },
    style: { ...baseNodeStyle, width: 170 } },
  { id: 'p5', position: { x: 920, y: 120 }, data: { label: 'High confidence AND\nfault_type whitelisted?' },
    style: { ...baseNodeStyle, width: 180, border: '1px solid #eab308' } },
  { id: 'p6', position: { x: 1170, y: 30 }, data: { label: 'Auto-Remediation\n(zero-touch fix)' }, type: 'output',
    style: { ...baseNodeStyle, width: 170, background: '#14532d', border: '1px solid #22c55e' } },
  { id: 'p7', position: { x: 1170, y: 220 }, data: { label: 'Manual Engineer Review\n(ranked causes shown)' }, type: 'output',
    style: { ...baseNodeStyle, width: 170, background: '#1e293b', border: '1px solid #64748b' } },
];

const pipelineEdges = [
  { id: 'pe1', source: 'p1', target: 'p2', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'pe2', source: 'p2', target: 'p3', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'pe3', source: 'p3', target: 'p4', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'pe4', source: 'p4', target: 'p5', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'pe5', source: 'p5', target: 'p6', label: 'Yes', labelStyle: { fill: '#22c55e', fontWeight: 700 },
    style: { stroke: '#22c55e' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#22c55e' } },
  { id: 'pe6', source: 'p5', target: 'p7', label: 'No', labelStyle: { fill: '#94a3b8', fontWeight: 700 },
    style: { stroke: '#64748b' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' } },
];

export function PipelineFlow() {
  return (
    <div style={{ height: 320, background: '#0f172a', borderRadius: 10 }}>
      <ReactFlow nodes={pipelineNodes} edges={pipelineEdges} fitView>
        <Background color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
}

// ---------- Dynamic branching tree: one symptom group's ranked causes ----------

export function CauseTree({ symptom, causes }) {
  const { nodes, edges } = useMemo(() => {
    if (!symptom || !causes || causes.length === 0) {
      return { nodes: [], edges: [] };
    }

    const n = causes.length;
    const spacing = 260;
    const totalWidth = (n - 1) * spacing;
    const startX = -totalWidth / 2;

    const rootNode = {
      id: 'root',
      position: { x: -90, y: 0 },
      data: { label: `Symptom:\n${symptom}` },
      type: 'input',
      style: { ...baseNodeStyle, background: '#0f172a', width: 220, border: '1px solid #3b82f6' },
    };

    const causeNodes = [];
    const detailNodes = [];
    const treeEdges = [];

    causes.forEach((c, idx) => {
      const x = startX + idx * spacing;
      const severityColor = SEVERITY_COLORS[c.severity] || '#64748b';

      causeNodes.push({
        id: `cause-${idx}`,
        position: { x, y: 150 },
        data: { label: `${c.cause}\n(${c.probability}% likely)` },
        style: { ...baseNodeStyle, width: 220, border: `1px solid ${severityColor}` },
      });

      detailNodes.push({
        id: `detail-${idx}`,
        position: { x, y: 320 },
        data: { label: `Verify: ${c.verification_command}\n\nSteps: ${c.troubleshooting_steps}` },
        type: 'output',
        style: { ...baseNodeStyle, width: 220, fontSize: 10.5, textAlign: 'left', background: '#1e293b' },
      });

      treeEdges.push({
        id: `e-root-${idx}`,
        source: 'root',
        target: `cause-${idx}`,
        label: `${c.probability}%`,
        labelStyle: { fill: severityColor, fontWeight: 700 },
        style: { stroke: severityColor },
        markerEnd: { type: MarkerType.ArrowClosed, color: severityColor },
      });

      treeEdges.push({
        id: `e-cause-detail-${idx}`,
        source: `cause-${idx}`,
        target: `detail-${idx}`,
        style: { stroke: '#334155' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#334155' },
      });
    });

    return { nodes: [rootNode, ...causeNodes, ...detailNodes], edges: treeEdges };
  }, [symptom, causes]);

  if (nodes.length === 0) {
    return (
      <p style={{ color: '#64748b', fontSize: '13px' }}>
        Select a symptom group above to view its decision tree.
      </p>
    );
  }

  return (
    <div style={{ height: 460, background: '#0f172a', borderRadius: 10 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
}