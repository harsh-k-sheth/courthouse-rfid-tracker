import React from 'react';

const styles = {
  searchInput: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(99, 179, 237, 0.2)',
    background: 'rgba(99, 179, 237, 0.05)',
    color: '#e2e8f0',
    fontSize: '13px',
    fontFamily: "'DM Sans', sans-serif",
    outline: 'none',
    marginBottom: '16px',
    transition: 'border-color 0.15s',
  },
  fileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  fileCard: {
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid rgba(99, 179, 237, 0.1)',
    background: 'rgba(99, 179, 237, 0.03)',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  fileCardSelected: {
    border: '1px solid rgba(99, 179, 237, 0.4)',
    background: 'rgba(99, 179, 237, 0.08)',
  },
  caseNumber: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: '#63b3ed',
    fontWeight: 500,
  },
  caseName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#f7fafc',
    marginTop: '2px',
  },
  locationRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: '8px',
  },
  locationText: {
    fontSize: '12px',
    color: '#a0aec0',
  },
  confidenceBadge: {
    fontSize: '10px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  tagId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '10px',
    color: '#4a5568',
    marginTop: '4px',
  },
  rssiBar: {
    height: '3px',
    borderRadius: '2px',
    marginTop: '6px',
    background: 'rgba(99, 179, 237, 0.1)',
    overflow: 'hidden',
  },
  rssiValue: {
    height: '100%',
    borderRadius: '2px',
    transition: 'width 0.3s',
  },
  noResults: {
    textAlign: 'center',
    color: '#4a5568',
    fontSize: '13px',
    padding: '40px 0',
  },
};

function getConfidenceStyle(confidence) {
  if (confidence === 'HIGH') {
    return { background: 'rgba(72, 187, 120, 0.15)', color: '#48bb78' };
  }
  return { background: 'rgba(237, 137, 54, 0.15)', color: '#ed8936' };
}

function getRSSIPercent(rssi) {
  // Map -90 to -20 dBm range to 0-100%
  return Math.max(0, Math.min(100, ((rssi + 90) / 70) * 100));
}

function getRSSIColor(rssi) {
  if (rssi > -40) return '#48bb78';
  if (rssi > -55) return '#ecc94b';
  return '#fc8181';
}

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function FileSearch({ files, searchQuery, onSearchChange, onFileSelect, selectedFile }) {
  return (
    <div>
      <input
        type="text"
        placeholder="Search by case number, name, or tag ID..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        style={styles.searchInput}
        onFocus={(e) => { e.target.style.borderColor = 'rgba(99, 179, 237, 0.5)'; }}
        onBlur={(e) => { e.target.style.borderColor = 'rgba(99, 179, 237, 0.2)'; }}
      />

      <div style={{ fontSize: '11px', color: '#4a5568', marginBottom: '10px' }}>
        {files.length} file{files.length !== 1 ? 's' : ''}
      </div>

      <div style={styles.fileList}>
        {files.length === 0 ? (
          <div style={styles.noResults}>No files match your search</div>
        ) : (
          files.map(file => {
            const isSelected = selectedFile?.tag_id === file.tag_id;
            return (
              <div
                key={file.tag_id}
                onClick={() => onFileSelect(file)}
                style={{
                  ...styles.fileCard,
                  ...(isSelected ? styles.fileCardSelected : {}),
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'rgba(99,179,237,0.05)';
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'rgba(99,179,237,0.03)';
                }}
              >
                <div style={styles.caseNumber}>{file.case_number}</div>
                <div style={styles.caseName}>{file.case_name}</div>

                <div style={styles.locationRow}>
                  <div style={styles.locationText}>
                    📍 {file.location_label}
                  </div>
                  <div style={{ ...styles.confidenceBadge, ...getConfidenceStyle(file.confidence) }}>
                    {file.confidence}
                  </div>
                </div>

                <div style={styles.rssiBar}>
                  <div
                    style={{
                      ...styles.rssiValue,
                      width: `${getRSSIPercent(file.rssi)}%`,
                      background: getRSSIColor(file.rssi),
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                  <div style={styles.tagId}>{file.tag_id}</div>
                  <div style={{ fontSize: '10px', color: '#4a5568' }}>
                    {timeAgo(file.last_seen)}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
