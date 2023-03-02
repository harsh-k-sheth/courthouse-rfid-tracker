import React from 'react';

const styles = {
  empty: {
    textAlign: 'center',
    color: '#4a5568',
    fontSize: '14px',
    padding: '80px 20px',
  },
  header: {
    marginBottom: '20px',
  },
  fileName: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#f7fafc',
  },
  fileCase: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    color: '#63b3ed',
    marginTop: '2px',
  },
  timeline: {
    position: 'relative',
    paddingLeft: '28px',
  },
  line: {
    position: 'absolute',
    left: '10px',
    top: '0',
    bottom: '0',
    width: '2px',
    background: 'rgba(99, 179, 237, 0.15)',
  },
  event: {
    position: 'relative',
    marginBottom: '16px',
    paddingBottom: '16px',
    borderBottom: '1px solid rgba(99, 179, 237, 0.05)',
  },
  dot: {
    position: 'absolute',
    left: '-22px',
    top: '4px',
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    border: '2px solid',
  },
  eventTime: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: '#4a5568',
  },
  eventLocation: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e2e8f0',
    marginTop: '2px',
  },
  eventType: {
    fontSize: '11px',
    fontWeight: 500,
    padding: '2px 8px',
    borderRadius: '10px',
    display: 'inline-block',
    marginTop: '4px',
  },
  rssiLabel: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: '#4a5568',
    marginTop: '4px',
  },
};

function getEventTypeStyle(type) {
  switch (type) {
    case 'ARRIVAL':
      return { background: 'rgba(72, 187, 120, 0.15)', color: '#48bb78', dotColor: '#48bb78' };
    case 'DEPARTURE':
      return { background: 'rgba(229, 62, 62, 0.15)', color: '#fc8181', dotColor: '#fc8181' };
    default:
      return { background: 'rgba(237, 137, 54, 0.15)', color: '#ed8936', dotColor: '#ed8936' };
  }
}

function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function formatDate(isoString) {
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function MovementTimeline({ movements, selectedFile }) {
  if (!selectedFile) {
    return (
      <div style={styles.empty}>
        <div style={{ fontSize: '40px', marginBottom: '12px' }}>📋</div>
        <div>Select a file to view its movement history</div>
      </div>
    );
  }

  if (movements.length === 0) {
    return (
      <div>
        <div style={styles.header}>
          <div style={styles.fileName}>{selectedFile.case_name}</div>
          <div style={styles.fileCase}>{selectedFile.case_number}</div>
        </div>
        <div style={styles.empty}>
          <div>No movement history recorded</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '8px 0', overflow: 'auto', flex: 1 }}>
      <div style={styles.header}>
        <div style={styles.fileName}>{selectedFile.case_name}</div>
        <div style={styles.fileCase}>{selectedFile.case_number}</div>
        <div style={{ fontSize: '12px', color: '#718096', marginTop: '4px' }}>
          {movements.length} events today
        </div>
      </div>

      <div style={styles.timeline}>
        <div style={styles.line} />

        {movements.map((event, idx) => {
          const typeStyle = getEventTypeStyle(event.event_type);
          return (
            <div key={idx} style={styles.event}>
              <div style={{ ...styles.dot, borderColor: typeStyle.dotColor, background: `${typeStyle.dotColor}30` }} />
              <div style={styles.eventTime}>
                {formatDate(event.timestamp)} {formatTime(event.timestamp)}
              </div>
              <div style={styles.eventLocation}>
                {event.location_label}
              </div>
              <span style={{ ...styles.eventType, ...{ background: typeStyle.background, color: typeStyle.color } }}>
                {event.event_type === 'ARRIVAL' ? '📥 Arrived' : event.event_type === 'DEPARTURE' ? '📤 Departed' : '⚠️ Ambiguous'}
              </span>
              <div style={styles.rssiLabel}>RSSI: {event.rssi} dBm</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
