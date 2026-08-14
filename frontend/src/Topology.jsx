import { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
} from 'reactflow';

import 'reactflow/dist/style.css';


// ============================================================
// NETWORK TOPOLOGY
// ============================================================

const BASE_NODES = [
  {
    id: 'core-switch',
    position: { x: 360, y: 40 },
    data: {
      label: 'SW-CORE-01',
      type: 'CORE SWITCH',
      interfaces: 48,
    },
  },

  {
    id: 'router-1',
    position: { x: 120, y: 190 },
    data: {
      label: 'RTR-CORE-01',
      type: 'ROUTER',
      interfaces: 8,
    },
  },

  {
    id: 'router-2',
    position: { x: 600, y: 190 },
    data: {
      label: 'Router-Branch-02',
      type: 'ROUTER',
      interfaces: 8,
    },
  },

  {
    id: 'access-switch-1',
    position: { x: 40, y: 350 },
    data: {
      label: 'SW-ACCESS-01',
      type: 'ACCESS SWITCH',
      interfaces: 24,
    },
  },

  {
    id: 'access-switch-2',
    position: { x: 280, y: 350 },
    data: {
      label: 'SW-ACCESS-02',
      type: 'ACCESS SWITCH',
      interfaces: 16,
    },
  },

  {
    id: 'firewall',
    position: { x: 540, y: 350 },
    data: {
      label: 'FW-MAIN-01',
      type: 'FIREWALL',
      interfaces: 8,
    },
  },

  {
    id: 'server',
    position: { x: 780, y: 350 },
    data: {
      label: 'SERVER-01',
      type: 'SERVER',
      interfaces: 2,
    },
  },

  {
    id: 'ap',
    position: { x: 280, y: 510 },
    data: {
      label: 'AP-FLOOR-01',
      type: 'ACCESS POINT',
      interfaces: 2,
    },
  },
];


// ============================================================
// TOPOLOGY CONNECTIONS
// ============================================================

const BASE_EDGES = [
  {
    id: 'core-router-1',
    source: 'core-switch',
    target: 'router-1',
  },

  {
    id: 'core-router-2',
    source: 'core-switch',
    target: 'router-2',
  },

  {
    id: 'core-access-1',
    source: 'core-switch',
    target: 'access-switch-1',
  },

  {
    id: 'core-access-2',
    source: 'core-switch',
    target: 'access-switch-2',
  },

  {
    id: 'router-firewall',
    source: 'router-2',
    target: 'firewall',
  },

  {
    id: 'firewall-server',
    source: 'firewall',
    target: 'server',
  },

  {
    id: 'access-ap',
    source: 'access-switch-2',
    target: 'ap',
  },
];


// ============================================================
// NORMALIZE DEVICE NAMES
// ============================================================

function normalize(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}


// ============================================================
// DEVICE MATCHING
// ============================================================

function deviceMatches(deviceName, signalDevice) {
  if (!deviceName || !signalDevice) {
    return false;
  }

  const a = normalize(deviceName);
  const b = normalize(signalDevice);

  return (
    a === b ||
    a.includes(b) ||
    b.includes(a)
  );
}


// ============================================================
// DEVICE STATUS
// ============================================================

function getDeviceState(
  node,
  signals = [],
  incidents = [],
  affectedDevice = ''
) {
  const deviceName = node.data.label;

  // Latest signal for this device
  const latestSignal = signals.find(signal =>
    deviceMatches(deviceName, signal.device)
  );

  // Any active incident for this device
  const activeIncident = incidents.find(incident =>
    deviceMatches(deviceName, incident.device) &&
    !['resolved', 'auto-resolved', 'closed'].includes(
      String(incident.status || '').toLowerCase()
    )
  );

  // Currently selected/affected device
  const isAffected =
    affectedDevice &&
    deviceMatches(deviceName, affectedDevice);

  // Critical / High incident
  const severity = String(
    activeIncident?.severity || ''
  ).toLowerCase();

  if (
    severity === 'critical' ||
    severity === 'high'
  ) {
    return {
      state: 'fault',
      label: severity.toUpperCase(),
      incident: activeIncident,
    };
  }

  // Fault signal
  if (
    latestSignal &&
    String(latestSignal.status).toLowerCase() === 'fault'
  ) {
    return {
      state: 'fault',
      label: 'FAULT',
      incident: activeIncident,
    };
  }

  // Selected affected device
  if (isAffected) {
    return {
      state: 'fault',
      label: 'AFFECTED',
      incident: activeIncident,
    };
  }

  // Healthy signal
  if (
    latestSignal &&
    String(latestSignal.status).toLowerCase() === 'ok'
  ) {
    return {
      state: 'online',
      label: 'ONLINE',
      incident: null,
    };
  }

  // Default simulator state
  return {
    state: 'online',
    label: 'ONLINE',
    incident: null,
  };
}


// ============================================================
// NODE STYLE
// ============================================================

function getNodeStyle(state) {
  if (state === 'fault') {
    return {
      background: '#160808',
      border: '2px solid #ef4444',
      boxShadow:
        '0 0 18px rgba(239,68,68,0.45)',
      color: '#ffffff',
    };
  }

  return {
    background: '#0d0d0d',
    border: '1px solid #3a3a3a',
    boxShadow:
      '0 0 12px rgba(255,255,255,0.04)',
    color: '#ffffff',
  };
}


// ============================================================
// TOPOLOGY COMPONENT
// ============================================================

function Topology({
  signals = [],
  incidents = [],
  affectedDevice = '',
}) {

  // ----------------------------------------------------------
  // BUILD LIVE NODES
  // ----------------------------------------------------------

  const nodes = useMemo(() => {

    return BASE_NODES.map(node => {

      const deviceState = getDeviceState(
        node,
        signals,
        incidents,
        affectedDevice
      );

      const stateColor =
        deviceState.state === 'fault'
          ? '#ef4444'
          : '#22c55e';

      return {
        ...node,

        data: {
          ...node.data,

          label: (
            <div
              style={{
                width: 155,
                padding: '4px 2px',
                fontFamily:
                  'Inter, Arial, sans-serif',
              }}
            >

              {/* DEVICE HEADER */}

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 7,
                  marginBottom: 7,
                }}
              >

                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: '50%',
                    background: stateColor,
                    boxShadow:
                      deviceState.state === 'fault'
                        ? '0 0 10px #ef4444'
                        : '0 0 8px #22c55e',
                    flexShrink: 0,
                  }}
                />

                <strong
                  style={{
                    fontSize: 12,
                    color: '#ffffff',
                    letterSpacing: 0.3,
                  }}
                >
                  {node.data.label}
                </strong>

              </div>

              {/* DEVICE TYPE */}

              <div
                style={{
                  fontSize: 9,
                  color: '#888888',
                  marginBottom: 7,
                }}
              >
                {node.data.type}
              </div>

              {/* STATUS */}

              <div
                style={{
                  display: 'flex',
                  justifyContent:
                    'space-between',
                  alignItems: 'center',
                  borderTop:
                    '1px solid #252525',
                  paddingTop: 6,
                }}
              >

                <span
                  style={{
                    fontSize: 9,
                    color: stateColor,
                    fontWeight: 800,
                  }}
                >
                  {deviceState.label}
                </span>

                <span
                  style={{
                    fontSize: 8,
                    color: '#666666',
                  }}
                >
                  {node.data.interfaces} PORTS
                </span>

              </div>

            </div>
          ),
        },

        style: getNodeStyle(
          deviceState.state
        ),

        className:
          deviceState.state === 'fault'
            ? 'netmind-topology-node topology-fault'
            : 'netmind-topology-node',

      };
    });

  }, [
    signals,
    incidents,
    affectedDevice,
  ]);


  // ----------------------------------------------------------
  // BUILD LIVE EDGES
  // ----------------------------------------------------------

  const edges = useMemo(() => {

    return BASE_EDGES.map(edge => {

      const sourceNode = BASE_NODES.find(
        n => n.id === edge.source
      );

      const targetNode = BASE_NODES.find(
        n => n.id === edge.target
      );

      const sourceState = sourceNode
        ? getDeviceState(
            sourceNode,
            signals,
            incidents,
            affectedDevice
          ).state
        : 'online';

      const targetState = targetNode
        ? getDeviceState(
            targetNode,
            signals,
            incidents,
            affectedDevice
          ).state
        : 'online';

      const isFault =
        sourceState === 'fault' ||
        targetState === 'fault';

      return {
        ...edge,

        animated: isFault,

        style: {
          stroke: isFault
            ? '#ef4444'
            : '#ffffff',

          strokeWidth: isFault
            ? 4
            : 2.5,

          filter: isFault
            ? 'drop-shadow(0 0 5px rgba(239,68,68,.8))'
            : 'none',
        },
      };
    });

  }, [
    signals,
    incidents,
    affectedDevice,
  ]);


  // ----------------------------------------------------------
  // RENDER
  // ----------------------------------------------------------

  return (
    <div
      style={{
        height: '100%',
        minHeight: 520,
        width: '100%',
        background: '#000000',
        borderRadius: 7,
        overflow: 'hidden',
        position: 'relative',
      }}
    >

      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{
          padding: 0.18,
        }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        zoomOnScroll
        panOnScroll
        attributionPosition="bottom-left"
      >

        <Background
          color="#202020"
          gap={28}
          size={1}
        />

        <Controls />

        <MiniMap
          pannable
          zoomable
          nodeColor={node => {

            if (
              node.className?.includes(
                'topology-fault'
              )
            ) {
              return '#ef4444';
            }

            return '#22c55e';
          }}
          maskColor="rgba(0,0,0,0.65)"
        />

      </ReactFlow>


      {/* LIVE LEGEND */}

      <div
        style={{
          position: 'absolute',
          top: 14,
          right: 14,
          zIndex: 10,
          background: 'rgba(8,8,8,.92)',
          border: '1px solid #292929',
          borderRadius: 7,
          padding: '9px 12px',
          fontFamily:
            'Inter, Arial, sans-serif',
        }}
      >

        <div
          style={{
            fontSize: 9,
            color: '#777',
            marginBottom: 7,
            letterSpacing: 1,
            fontWeight: 800,
          }}
        >
          LIVE NETWORK
        </div>

        <div
          style={{
            display: 'flex',
            gap: 12,
            fontSize: 9,
          }}
        >

          <span
            style={{
              color: '#22c55e',
            }}
          >
            ● ONLINE
          </span>

          <span
            style={{
              color: '#ef4444',
            }}
          >
            ● FAULT
          </span>

        </div>

      </div>

    </div>
  );
}

export default Topology;