import React from 'react';
export function JobTable({ jobs }) {
  return <table><tbody>{jobs && jobs.map(j => <tr key={j.id}><td>{j.name}</td></tr>)}</tbody></table>;
}
export default JobTable;
