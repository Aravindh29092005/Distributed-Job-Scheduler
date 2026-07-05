import React from 'react';
export function WorkerCard({ hostname, status }) {
  return <div className="card"><h4>{hostname}</h4><span>{status}</span></div>;
}
export default WorkerCard;
