import React from 'react';
import { AlertTriangle, RefreshCw, Scan } from 'lucide-react';

interface OfflineBannerProps {
  isOffline: boolean;
  onRetry: () => void;
  onScan: () => void;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({ isOffline, onRetry, onScan }) => {
  if (!isOffline) return null;

  return (
    <div className="bg-yellow-500 text-yellow-900 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <AlertTriangle className="w-5 h-5" />
        <span className="font-medium">Backend Offline</span>
        <span className="text-sm">Start the server to enable search and scan features.</span>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={onScan}
          className="flex items-center space-x-1 bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded text-sm"
        >
          <Scan className="w-4 h-4" />
          <span>Scan Now</span>
        </button>
        <button
          onClick={onRetry}
          className="flex items-center space-x-1 bg-yellow-700 hover:bg-yellow-800 text-white px-3 py-1 rounded text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Retry</span>
        </button>
      </div>
    </div>
  );
};