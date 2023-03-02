import React from 'react';

const styles = {
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  item: {
    padding: '8px 10px',
    borderRadius: '6px',
    borderLeft: '3px solid',
    background: 'rgba(99, 179, 237, 0.03)',
    fontSize: '12px',
  },
  time: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '10px',
    color: '#4a5568',
  },
  caseName: {
    fontWeight: 600,
    color: '#e2e8f0',
    fontSize: '12px',
  },
  event: {
    color: '#a0aec0',
    fontSize: '11px',
    marginTop: '2px',
  },
};

function getColor(confidence) {
  switch (confidence) {
    case 'HIGH': return '#48bb78';
    case 'AMBIGUOUS': return '#ed8936';
    case 'ALERT': return '#fc8181';
    default: return '#63b3ed';
  }
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export default function LiveFeed({ feed }) {
  return (
    <div style={styles.list}>
      {feed.map((item, idx) => {
        const color = getColor(item.confidence);
        return (
          <div key={idx} style={{ ...styles.item, borderLeftColor: color }}>
            <div style={styles.time}>{formatTime(item.time)}</div>
            {item.case_name && <div style={styles.caseName}>{item.case_name}</div>}
            <div style={styles.event}>{item.event}</div>
          </div>
        );
      })}
    </div>
  );
}
