import { AlertTriangle, RefreshCcw } from 'lucide-react';
import { Link } from 'react-router-dom';

export type ApiStatus = 'unknown' | 'online' | 'offline';

export function ApiStatusBanner({
  status,
  apiBase,
  onRetry,
}: {
  status: ApiStatus;
  apiBase: string;
  onRetry: () => void;
}) {
  if (status !== 'offline') return null;

  return (
    <div role='alert' className='pointer-events-auto w-full'>
      <div className='mx-auto w-full max-w-[1600px] px-2 sm:px-4 md:px-6'>
        <div className='mt-2 rounded-xl border border-amber-500/30 bg-amber-500/10 backdrop-blur px-4 py-3 shadow-sm'>
          <div className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
            <div className='flex items-start gap-3'>
              <div className='mt-0.5 text-amber-300'>
                <AlertTriangle size={18} />
              </div>
              <div className='space-y-0.5'>
                <div className='text-sm font-medium text-amber-100'>
                  Can’t reach the backend
                </div>
                <div className='text-xs text-amber-100/80'>
                  No response from the API at <span className='font-mono'>{apiBase}</span>.
                  Either the server isn’t running, or this page’s origin isn’t allowed to call it.
                </div>
              </div>
            </div>

            <div className='flex flex-wrap items-center gap-2'>
              <button
                type='button'
                onClick={onRetry}
                className='btn-glass btn-glass--muted text-xs px-3 py-2'
              >
                <RefreshCcw size={14} />
                Retry
              </button>
              <Link
                to='/import'
                className='btn-glass text-xs px-3 py-2'
                title='Go to Import'
              >
                Import
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
