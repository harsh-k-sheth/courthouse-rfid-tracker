import React from 'react';

const styles = {
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid rgba(99, 179, 237, 0.1)',
    background: 'rgba(99, 179, 237, 0.03)',
  },
  topRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  readerName: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  location: {
    fontSize: '11px',
    color: '#718096',
    marginTop: '2px',
  },
  statsRow: {
    display: 'flex',
    gap: '12px',
    marginTop: '8px',
  },
  stat: {
    fontSize: '10px',
    color: '#4a5568',
    fontFamily: "'JetBrains Mono', monospace",
  },
  statValue: {
    color: '#a0aec0',
    fontWeight: 500,
  },
};

function timeAgo(isoString) {
  if (!isoString) return 'never';
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export default function ReaderStatus({ readers }) {
  const sorted = [...readers].sort((a, b) => {
    if (a.status === 'OFFLINE' && b.status !== 'OFFLINE') return -1;
    if (a.status !== 'OFFLINE' && b.status === 'OFFLINE') return 1;
    return a.reader_id.localeCompare(b.reader_id);
  });

  return (
    <div style={styles.list}>
      {sorted.map(reader => {
        const isOnline = reader.status === 'ONLINE';
        const tags = reader.metadata?.tags_detected || 0;
        const temp = reader.metadata?.temperature_c;

        return (
          <div
            key={reader.reader_id}
            style={{
              ...styles.card,
              ...(isOnline ? {} : { borderColor: 'rgba(229, 62, 62, 0.3)', background: 'rgba(229, 62, 62, 0.05)' }),
            }}
          >
            <div style={styles.topRow}>
              <div style={styles.readerName}>
                <span
                  style={{
                    ...styles.statusDot,
                    background: isOnline ? '#48bb78' : '#e53e3e',
                    marginRight: '8px',
                    ...(isOnline ? {} : { animation: 'pulse 1.5s infinite' }),
                  }}
                />
                {reader.reader_id}
              </div>
              <div style={{ fontSize: '10px', color: isOnline ? '#48bb78' : '#fc8181', fontWeight: 600 }}>
                {reader.status}
              </div>
            </div>

            <div style={styles.location}>{reader.location_label}</div>

            <div style={styles.statsRow}>
              <div style={styles.stat}>
                Tags: <span style={styles.statValue}>{tags}</span>
              </div>
              {temp != null && (
                <div style={styles.stat}>
                  Temp: <span style={styles.statValue}>{temp.toFixed(1)}°C</span>
                </div>
              )}
              <div style={styles.stat}>
                HB: <span style={styles.statValue}>{timeAgo(reader.last_heartbeat)}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
