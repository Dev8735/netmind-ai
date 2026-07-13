import { useMemo } from 'react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

const baseNodes = [
  { id: 'core-switch', position: { x: 250, y: 0 }, data: { label: 'Core Switch' }, type: 'input' },
  { id: 'router-1', position: { x: 100, y: 120 }, data: { label: 'Router-Branch-01' } },
  { id: 'router-2', position: { x: 400, y: 120 }, data: { label: 'Router-Branch-02' } },
  { id: 'ap-1', position: { x: 0, y: 240 }, data: { label: 'Access Point - Floor 1' } },
  { id: 'ap-2', position: { x: 200, y: 240 }, data: { label: 'Access Point - Floor 2' } },
  { id: 'server-1', position: { x: 400, y: 240 }, data: { label: 'Server Room' } },
  { id: 'firewall', position: { x: 550, y: 240 }, data: { label: 'Firewall' } },
];

const edges = [
  { id: 'e1', source: 'core-switch', target: 'router-1' },
  { id: 'e2', source: 'core-switch', target: 'router-2' },
  { id: 'e3', source: 'router-1', target: 'ap-1' },
  { id: 'e4', source: 'router-1', target: 'ap-2' },
  { id: 'e5', source: 'router-2', target: 'server-1' },
  { id: 'e6', source: 'router-2', target: 'firewall' },
];

function Topology({ affectedDevice }) {
  const nodes = useMemo(() => {
    return baseNodes.map(n => {
      const isAffected = affectedDevice &&
        n.data.label.toLowerCase().includes(affectedDevice.toLowerCase());
      return {
        ...n,
        style: isAffected
          ? { background: '#ef4444', color: 'white', border: '2px solid #fff', fontWeight: 'bold' }
          : { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
      };
    });
  }, [affectedDevice]);

  return (
    <div style={{ height: 320, background: '#0f172a', borderRadius: 10 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default Topology;
