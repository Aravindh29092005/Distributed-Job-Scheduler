/**
 * Status badge colors and labels
 */

export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    succeeded: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    retrying: 'bg-orange-100 text-orange-800',
    cancelled: 'bg-gray-100 text-gray-800',
    scheduled: 'bg-purple-100 text-purple-800',
  };
  return colors[status.toLowerCase()] || 'bg-gray-100 text-gray-800';
};

export const getStatusLabel = (status: string): string => {
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
};
