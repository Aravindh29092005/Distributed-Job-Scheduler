import React from 'react';
export function RetryModal({ isOpen, onClose }) {
  if (!isOpen) return null;
  return <div className="modal"><button onClick={onClose}>Close</button></div>;
}
export default RetryModal;
