import React, { useState, useEffect, useCallback } from 'react';
import FileSearch from './components/FileSearch';
import FloorMap from './components/FloorMap';
import MovementTimeline from './components/MovementTimeline';
import ReaderStatus from './components/ReaderStatus';
import LiveFeed from './components/LiveFeed';

const API_BASE = import.meta.env.VITE_API_URL || '';

const styles = {
  app: {
    fontFamily: "'DM Sans', sans-serif",
    background: '#0a0e1a',
    color: '#e2e8f0',
    minHeight: '100vh',
  },
  header: {
    background: 'linear-gradient(135deg, #0f1629 0%, #1a1f3a 100%)',
    borderBottom: '1px solid rgba(99, 179, 237, 0.15)',
    padding: '16px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    width: '36px',
    height: '36px',
    background: 'linear-gradient(135deg, #63b3ed, #4299e1)',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
  },
  logoText: {
    fontSize: '18px',
    fontWeight: 700,
    letterSpacing: '-0.02em',
    color: '#f7fafc',
  },
  logoSub: {
    fontSize: '12px',
    color: '#718096',
    fontWeight: 400,
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 500,
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    animation: 'pulse 2s infinite',
  },
  main: {
    display: 'grid',
    gridTemplateColumns: '340px 1fr 320px',
    gridTemplateRows: 'auto 1fr',
    gap: '1px',
    background: 'rgba(99, 179, 237, 0.08)',
    minHeight: 'calc(100vh - 69px)',
  },
  panel: {
    background: '#0f1629',
    padding: '20px',
    overflow: 'auto',
  },
  panelHeader: {
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#63b3ed',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  mapPanel: {
    background: '#0f1629',
    gridRow: '1 / 3',
    gridColumn: '2',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
  },
  tabBar: {
    display: 'flex',
    gap: '4px',
    marginBottom: '16px',
  },
  tab: {
    padding: '8px 16px',
    borderRadius: '6px',
    border: 'none',
    background: 'transparent',
    color: '#718096',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  tabActive: {
    background: 'rgba(99, 179, 237, 0.15)',
    color: '#63b3ed',
  },
};

// Demo data for the dashboard
const DEMO_FILES = [
  { tag_id: '4A:7B:2C:9F', case_number: '2024-CR-1042', case_name: 'Johnson v. State', reader_id: 'CLK-RM3-T1', location_label: 'Clerk Room 3 - Table 1', zone: 'CLK-RM3-CLUSTER', rssi: -35, confidence: 'HIGH', last_seen: new Date().toISOString() },
  { tag_id: '3E:8D:1A:5B', case_number: '2024-PR-0087', case_name: 'Martinez Estate', reader_id: 'JUDGE-MARTINEZ-BENCH', location_label: 'Judge Martinez - Bench', zone: 'COURTROOM-1', rssi: -31, confidence: 'HIGH', last_seen: new Date().toISOString() },
  { tag_id: '7C:2F:9E:4D', case_number: '2024-DR-0234', case_name: 'Smith v. Smith', reader_id: 'ARCHIVE-SHELF-A', location_label: 'Archive Room - Shelf A', zone: 'ARCHIVE', rssi: -42, confidence: 'HIGH', last_seen: new Date(Date.now() - 3600000).toISOString() },
  { tag_id: '1B:6A:3C:8E', case_number: '2024-CR-0891', case_name: 'City v. Thompson', reader_id: 'CLK-RM3-T2', location_label: 'Clerk Room 3 - Table 2', zone: 'CLK-RM3-CLUSTER', rssi: -44, confidence: 'AMBIGUOUS', last_seen: new Date().toISOString() },
  { tag_id: '5D:4E:7F:2A', case_number: '2024-PR-0156', case_name: 'Williams Trust', reader_id: 'COURTROOM2-TABLE', location_label: 'Courtroom 2 - Counsel Table', zone: 'COURTROOM-2', rssi: -38, confidence: 'HIGH', last_seen: new Date().toISOString() },
  { tag_id: '9F:1C:6B:3D', case_number: '2024-CV-0543', case_name: 'Davis v. County', reader_id: 'ATTY-REVIEW-1', location_label: 'Attorney Review Room 1', zone: 'ATTY-REVIEW', rssi: -40, confidence: 'HIGH', last_seen: new Date(Date.now() - 172800000).toISOString() },
  { tag_id: '2A:8E:5C:7B', case_number: '2024-CR-1198', case_name: 'Rodriguez Hearing', reader_id: 'ARCHIVE-SHELF-B', location_label: 'Archive Room - Shelf B', zone: 'ARCHIVE', rssi: -45, confidence: 'HIGH', last_seen: new Date(Date.now() - 7200000).toISOString() },
  { tag_id: '6D:3F:4A:1E', case_number: '2024-CV-0312', case_name: 'Chen v. Global Corp', reader_id: 'JUDGE-MARTINEZ-BENCH', location_label: 'Judge Martinez - Bench', zone: 'COURTROOM-1', rssi: -33, confidence: 'HIGH', last_seen: new Date().toISOString() },
];

const DEMO_READERS = [
  { reader_id: 'JUDGE-MARTINEZ-BENCH', location_label: 'Judge Martinez - Bench', zone: 'COURTROOM-1', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 14, temperature_c: 36.2 } },
  { reader_id: 'CLK-RM3-T1', location_label: 'Clerk Room 3 - Table 1', zone: 'CLK-RM3-CLUSTER', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 8, temperature_c: 34.8 } },
  { reader_id: 'CLK-RM3-T2', location_label: 'Clerk Room 3 - Table 2', zone: 'CLK-RM3-CLUSTER', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 6, temperature_c: 35.1 } },
  { reader_id: 'ARCHIVE-SHELF-A', location_label: 'Archive Room - Shelf A', zone: 'ARCHIVE', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 22, temperature_c: 31.5 } },
  { reader_id: 'ARCHIVE-SHELF-B', location_label: 'Archive Room - Shelf B', zone: 'ARCHIVE', status: 'OFFLINE', last_heartbeat: new Date(Date.now() - 300000).toISOString(), metadata: { tags_detected: 0, temperature_c: null } },
  { reader_id: 'COURTROOM2-TABLE', location_label: 'Courtroom 2 - Counsel Table', zone: 'COURTROOM-2', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 4, temperature_c: 37.0 } },
  { reader_id: 'ATTY-REVIEW-1', location_label: 'Attorney Review Room 1', zone: 'ATTY-REVIEW', status: 'ONLINE', last_heartbeat: new Date().toISOString(), metadata: { tags_detected: 3, temperature_c: 33.9 } },
];

const DEMO_MOVEMENTS = [
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 14400000).toISOString(), location_label: 'Archive Room - Shelf A', event_type: 'DEPARTURE', rssi: -42 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 14100000).toISOString(), location_label: 'Clerk Room 3 - Table 1', event_type: 'ARRIVAL', rssi: -36 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 10800000).toISOString(), location_label: 'Clerk Room 3 - Table 1', event_type: 'DEPARTURE', rssi: -35 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 10500000).toISOString(), location_label: 'Judge Martinez - Bench', event_type: 'ARRIVAL', rssi: -30 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 7200000).toISOString(), location_label: 'Judge Martinez - Bench', event_type: 'DEPARTURE', rssi: -31 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 6900000).toISOString(), location_label: 'Attorney Review Room 1', event_type: 'ARRIVAL', rssi: -39 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 3600000).toISOString(), location_label: 'Attorney Review Room 1', event_type: 'DEPARTURE', rssi: -40 },
  { tag_id: '4A:7B:2C:9F', timestamp: new Date(Date.now() - 3300000).toISOString(), location_label: 'Clerk Room 3 - Table 1', event_type: 'ARRIVAL', rssi: -35 },
];

const DEMO_FEED = [
  { time: new Date(), tag_id: '4A:7B:2C:9F', case_name: 'Johnson v. State', event: 'Detected at Clerk Room 3 - Table 1', confidence: 'HIGH' },
  { time: new Date(Date.now() - 30000), tag_id: '3E:8D:1A:5B', case_name: 'Martinez Estate', event: 'Moved to Judge Martinez - Bench', confidence: 'HIGH' },
  { time: new Date(Date.now() - 120000), tag_id: '1B:6A:3C:8E', case_name: 'City v. Thompson', event: 'Ambiguous between CLK-RM3-T1 and CLK-RM3-T2', confidence: 'AMBIGUOUS' },
  { time: new Date(Date.now() - 300000), tag_id: 'SYSTEM', case_name: '', event: 'Reader ARCHIVE-SHELF-B went OFFLINE', confidence: 'ALERT' },
  { time: new Date(Date.now() - 600000), tag_id: '5D:4E:7F:2A', case_name: 'Williams Trust', event: 'Arrived at Courtroom 2 - Counsel Table', confidence: 'HIGH' },
  { time: new Date(Date.now() - 900000), tag_id: '6D:3F:4A:1E', case_name: 'Chen v. Global Corp', event: 'Moved to Judge Martinez - Bench', confidence: 'HIGH' },
];

export default function App() {
  const [files, setFiles] = useState(DEMO_FILES);
  const [readers, setReaders] = useState(DEMO_READERS);
  const [selectedFile, setSelectedFile] = useState(null);
  const [movements, setMovements] = useState([]);
  const [feed, setFeed] = useState(DEMO_FEED);
  const [activeTab, setActiveTab] = useState('map');
  const [searchQuery, setSearchQuery] = useState('');

  const handleFileSelect = useCallback((file) => {
    setSelectedFile(file);
    // Load movement history for selected file
    const fileMovements = DEMO_MOVEMENTS.filter(m => m.tag_id === file.tag_id);
    setMovements(fileMovements);
  }, []);

  const filteredFiles = files.filter(f => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      f.case_number.toLowerCase().includes(q) ||
      f.case_name.toLowerCase().includes(q) ||
      f.tag_id.toLowerCase().includes(q) ||
      f.location_label.toLowerCase().includes(q)
    );
  });

  const onlineReaders = readers.filter(r => r.status === 'ONLINE').length;
  const trackedFiles = files.length;

  return (
    <div style={styles.app}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.2); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(99,179,237,0.4); }
      `}</style>

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <div style={styles.logoIcon}>📋</div>
          <div>
            <div style={styles.logoText}>Courthouse File Tracker</div>
            <div style={styles.logoSub}>RFID Location System</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ ...styles.statusBadge, background: 'rgba(72, 187, 120, 0.1)', color: '#48bb78' }}>
            <div style={{ ...styles.statusDot, background: '#48bb78' }} />
            {onlineReaders}/{readers.length} Readers Online
          </div>
          <div style={{ ...styles.statusBadge, background: 'rgba(99, 179, 237, 0.1)', color: '#63b3ed' }}>
            📄 {trackedFiles} Files Tracked
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main style={styles.main}>
        {/* Left Panel: Search + File List */}
        <div style={{ ...styles.panel, gridRow: '1 / 3' }}>
          <div style={styles.panelHeader}>
            <span>🔍</span> File Search
          </div>
          <FileSearch
            files={filteredFiles}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
          />
        </div>

        {/* Center: Map + Timeline */}
        <div style={styles.mapPanel}>
          <div style={styles.tabBar}>
            {['map', 'timeline'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  ...styles.tab,
                  ...(activeTab === tab ? styles.tabActive : {}),
                }}
              >
                {tab === 'map' ? '🗺️ Floor Map' : '📊 Movement Timeline'}
              </button>
            ))}
          </div>

          {activeTab === 'map' ? (
            <FloorMap
              files={files}
              readers={readers}
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
            />
          ) : (
            <MovementTimeline
              movements={movements}
              selectedFile={selectedFile}
            />
          )}
        </div>

        {/* Right Panel: Reader Status */}
        <div style={{ ...styles.panel, borderBottom: '1px solid rgba(99,179,237,0.08)' }}>
          <div style={styles.panelHeader}>
            <span>📡</span> Reader Status
          </div>
          <ReaderStatus readers={readers} />
        </div>

        {/* Right Panel: Live Feed */}
        <div style={styles.panel}>
          <div style={styles.panelHeader}>
            <span>⚡</span> Live Feed
          </div>
          <LiveFeed feed={feed} />
        </div>
      </main>
    </div>
  );
}
