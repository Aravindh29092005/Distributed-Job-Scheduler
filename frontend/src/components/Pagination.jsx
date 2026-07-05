import React from 'react';
export function Pagination({ current, total, onChange }) {
  return <div className="pagination">Page {current} of {total}</div>;
}
export default Pagination;
