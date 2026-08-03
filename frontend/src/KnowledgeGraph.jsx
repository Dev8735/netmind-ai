import { useMemo } from 'react';
import ReactFlow, { Background, Controls, MarkerType, Position } from 'reactflow';
import 'reactflow/dist/style.css';

const baseNodeStyle = {
  color: '#e2e8f0',
  borderRadius: 8,
  padding: 10,
  fontSize: 12,
  whiteSpace: 'pre-line',
  textAlign: 'center',
};

function KnowledgeGraph({ nodes: rawNodes, edges: rawEdges }) {
  const { nodes, edges } = useMemo(() => {
    if (!rawNodes || rawNodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    const devices = rawNodes.filter(n => n.type === 'device');
    const faultTypes = rawNodes.filter(n => n.type === 'fault_type');

    const deviceSpacing = 90;
    const faultSpacing = 110;

    const flowNodes = [
      ...devices.map((d, idx) => ({
        id: d.id,
        position: { x: 0, y: idx * deviceSpacing },
        data: { label: `${d.label}\n(${d.count} incident${d.count !== 1 ? 's' : ''})` },
        type: 'input',
        sourcePosition: Position.Right,
        style: {
          ...baseNodeStyle,
          width: 200,
          background: '#0f172a',
          border: '1px solid #3b82f6',
        },
      })),
      ...faultTypes.map((f, idx) => ({
        id: f.id,
        position: { x: 480, y: idx * faultSpacing },
        data: { label: `${f.label}\n(${f.count} incident${f.count !== 1 ? 's' : ''})` },
        type: 'output',
        targetPosition: Position.Left,
        style: {
          ...baseNodeStyle,
          width: 220,
          background: '#1e1033',
          border: '1px solid #a855f7',
        },
      })),
    ];

    // Edge thickness scales with weight so heavier relationships stand out.
    const maxWeight = Math.max(...rawEdges.map(e => e.weight), 1);
    const flowEdges = rawEdges.map((e, idx) => {
      const strokeWidth = 1 + (e.weight / maxWeight) * 4;
      return {
        id: `edge-${idx}`,
        source: e.source,
        target: e.target,
        label: `${e.weight}`,
        labelStyle: { fill: '#e2e8f0', fontWeight: 700, fontSize: 11 },
        labelBgStyle: { fill: '#0f172a' },
        style: { stroke: '#a855f7', strokeWidth },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [rawNodes, rawEdges]);

  if (nodes.length === 0) {
    return (
      <p style={{ color: '#64748b', fontSize: '13px' }}>
        No classified fault types in incident history yet - the graph will populate as more
        incidents are diagnosed with a recognized fault type.
      </p>
    );
  }

  const height = Math.max(320, nodes.length * 45);

  return (
    <div style={{ height, background: '#0f172a', borderRadius: 10 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default KnowledgeGraph;