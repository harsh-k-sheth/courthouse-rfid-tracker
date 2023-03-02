import React, { useState } from 'react';

// Courthouse floor layout coordinates for each zone/reader
const LAYOUT = {
  'COURTROOM-1': { x: 60, y: 60, w: 200, h: 140, label: 'Courtroom 1', color: '#4299e1' },
  'COURTROOM-2': { x: 60, y: 240, w: 200, h: 140, label: 'Courtroom 2', color: '#805ad5' },
  'CLK-RM3-CLUSTER': { x: 320, y: 60, w: 180, h: 140, label: 'Clerk Room 3', color: '#48bb78' },
  'ARCHIVE': { x: 320, y: 240, w: 180, h: 140, label: 'Archive Room', color: '#ed8936' },
  'ATTY-REVIEW': { x: 560, y: 60, w: 160, h: 140, label: 'Attorney Review', color: '#e53e3e' },
};

// Reader positions within zones
const READER_POSITIONS = {
  'JUDGE-MARTINEZ-BENCH': { zoneKey: 'COURTROOM-1', rx: 0.5, ry: 0.35 },
  'CLK-RM3-T1': { zoneKey: 'CLK-RM3-CLUSTER', rx: 0.3, ry: 0.5 },
  'CLK-RM3-T2': { zoneKey: 'CLK-RM3-CLUSTER', rx: 0.7, ry: 0.5 },
  'ARCHIVE-SHELF-A': { zoneKey: 'ARCHIVE', rx: 0.3, ry: 0.4 },
  'ARCHIVE-SHELF-B': { zoneKey: 'ARCHIVE', rx: 0.7, ry: 0.4 },
  'COURTROOM2-TABLE': { zoneKey: 'COURTROOM-2', rx: 0.5, ry: 0.5 },
  'ATTY-REVIEW-1': { zoneKey: 'ATTY-REVIEW', rx: 0.5, ry: 0.5 },
};

function getReaderAbsPos(readerId) {
  const rp = READER_POSITIONS[readerId];
  if (!rp) return null;
  const zone = LAYOUT[rp.zoneKey];
  if (!zone) return null;
  return {
    x: zone.x + zone.w * rp.rx,
    y: zone.y + zone.h * rp.ry,
    zone: rp.zoneKey,
    color: zone.color,
  };
}

export default function FloorMap({ files, readers, selectedFile, onFileSelect }) {
  const [hoveredFile, setHoveredFile] = useState(null);

  // Group files by reader
  const filesByReader = {};
  files.forEach(f => {
    if (!filesByReader[f.reader_id]) filesByReader[f.reader_id] = [];
    filesByReader[f.reader_id].push(f);
  });

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <svg
        viewBox="0 0 780 420"
        style={{
          flex: 1,
          width: '100%',
          background: 'rgba(99,179,237,0.02)',
          borderRadius: '10px',
          border: '1px solid rgba(99,179,237,0.1)',
        }}
      >
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Zones */}
        {Object.entries(LAYOUT).map(([key, zone]) => (
          <g key={key}>
            <rect
              x={zone.x}
              y={zone.y}
              width={zone.w}
              height={zone.h}
              rx={8}
              fill={`${zone.color}08`}
              stroke={`${zone.color}30`}
              strokeWidth={1.5}
            />
            <text
              x={zone.x + 12}
              y={zone.y + 20}
              fill={`${zone.color}90`}
              fontSize={11}
              fontWeight={600}
              fontFamily="'DM Sans', sans-serif"
            >
              {zone.label}
            </text>
          </g>
        ))}

        {/* Readers */}
        {readers.map(reader => {
          const pos = getReaderAbsPos(reader.reader_id);
          if (!pos) return null;
          const isOnline = reader.status === 'ONLINE';

          return (
            <g key={reader.reader_id}>
              {/* Reader range circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={35}
                fill={isOnline ? `${pos.color}08` : 'rgba(229,62,62,0.05)'}
                stroke={isOnline ? `${pos.color}20` : 'rgba(229,62,62,0.2)'}
                strokeWidth={1}
                strokeDasharray={isOnline ? 'none' : '4 4'}
              />
              {/* Reader dot */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={4}
                fill={isOnline ? pos.color : '#e53e3e'}
                opacity={0.6}
              />
              {/* Reader label */}
              <text
                x={pos.x}
                y={pos.y + 50}
                fill="#4a5568"
                fontSize={8}
                fontFamily="'JetBrains Mono', monospace"
                textAnchor="middle"
              >
                {reader.reader_id}
              </text>
            </g>
          );
        })}

        {/* Files at readers */}
        {Object.entries(filesByReader).map(([readerId, readerFiles]) => {
          const pos = getReaderAbsPos(readerId);
          if (!pos) return null;

          return readerFiles.map((file, idx) => {
            const isSelected = selectedFile?.tag_id === file.tag_id;
            const isHovered = hoveredFile === file.tag_id;
            const offset = (idx - (readerFiles.length - 1) / 2) * 18;

            return (
              <g
                key={file.tag_id}
                onClick={() => onFileSelect(file)}
                onMouseEnter={() => setHoveredFile(file.tag_id)}
                onMouseLeave={() => setHoveredFile(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* File icon */}
                <rect
                  x={pos.x + offset - 7}
                  y={pos.y - 22}
                  width={14}
                  height={18}
                  rx={2}
                  fill={isSelected ? pos.color : `${pos.color}60`}
                  stroke={isSelected ? '#fff' : pos.color}
                  strokeWidth={isSelected ? 2 : 1}
                  filter={isSelected || isHovered ? 'url(#glow)' : 'none'}
                />
                {/* Fold corner */}
                <path
                  d={`M ${pos.x + offset + 3} ${pos.y - 22} L ${pos.x + offset + 7} ${pos.y - 18}`}
                  stroke={isSelected ? '#fff' : pos.color}
                  strokeWidth={0.8}
                  fill="none"
                />

                {/* Confidence indicator */}
                {file.confidence === 'AMBIGUOUS' && (
                  <circle
                    cx={pos.x + offset}
                    cy={pos.y - 26}
                    r={3}
                    fill="#ed8936"
                  />
                )}

                {/* Tooltip on hover */}
                {(isHovered || isSelected) && (
                  <g>
                    <rect
                      x={pos.x + offset - 60}
                      y={pos.y - 60}
                      width={120}
                      height={30}
                      rx={4}
                      fill="#1a202c"
                      stroke={`${pos.color}40`}
                      strokeWidth={1}
                    />
                    <text
                      x={pos.x + offset}
                      y={pos.y - 48}
                      fill="#f7fafc"
                      fontSize={9}
                      fontWeight={600}
                      fontFamily="'DM Sans', sans-serif"
                      textAnchor="middle"
                    >
                      {file.case_name}
                    </text>
                    <text
                      x={pos.x + offset}
                      y={pos.y - 37}
                      fill="#63b3ed"
                      fontSize={8}
                      fontFamily="'JetBrains Mono', monospace"
                      textAnchor="middle"
                    >
                      {file.case_number} ({file.rssi} dBm)
                    </text>
                  </g>
                )}
              </g>
            );
          });
        })}

        {/* Legend */}
        <g transform="translate(560, 260)">
          <text fill="#4a5568" fontSize={10} fontWeight={600} fontFamily="'DM Sans', sans-serif">
            Legend
          </text>
          <rect x={0} y={12} width={10} height={13} rx={1.5} fill="#63b3ed" stroke="#63b3ed" strokeWidth={0.5} />
          <text x={16} y={22} fill="#718096" fontSize={9} fontFamily="'DM Sans', sans-serif">Case File</text>

          <circle cx={5} cy={39} r={3} fill="#48bb78" />
          <text x={16} y={42} fill="#718096" fontSize={9} fontFamily="'DM Sans', sans-serif">Reader (online)</text>

          <circle cx={5} cy={56} r={3} fill="#e53e3e" />
          <text x={16} y={59} fill="#718096" fontSize={9} fontFamily="'DM Sans', sans-serif">Reader (offline)</text>

          <circle cx={5} cy={73} r={3} fill="#ed8936" />
          <text x={16} y={76} fill="#718096" fontSize={9} fontFamily="'DM Sans', sans-serif">Ambiguous</text>
        </g>
      </svg>
    </div>
  );
}
