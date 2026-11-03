import React from 'react';

export function FairScanLogo({ className = "w-7 h-7" }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Background container */}
      <rect width="40" height="40" rx="9" fill="#0A0A0C" stroke="#26262E" strokeWidth="1.5" />
      
      {/* Stylized Modern Monogram F + Scanning Beam */}
      {/* Vertical Spine */}
      <rect x="11" y="10" width="4" height="20" rx="2" fill="#FACC15" />
      
      {/* Top Arm */}
      <rect x="11" y="10" width="18" height="4" rx="2" fill="#FACC15" />
      
      {/* Center Scan Beam */}
      <rect x="11" y="18" width="13" height="4" rx="2" fill="#FFFFFF" />
      
      {/* Dynamic Data Balance Nodes */}
      <circle cx="27" cy="18" r="2.5" fill="#FACC15" />
      <circle cx="21" cy="27" r="2.5" fill="#FFFFFF" />
      <circle cx="27" cy="27" r="2.5" fill="#FACC15" />
    </svg>
  );
}

