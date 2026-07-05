import React from 'react';
export function QueueCard({ name, description }) {
  return <div className="card"><h3>{name}</h3><p>{description}</p></div>;
}
export default QueueCard;
