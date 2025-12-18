import { useEffect, useState } from 'react';
import { api } from '../api';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../utils/storage';

export function ServerConfigPanel() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [preferSigned, setPreferSigned] = useState(() => {
    if (!isLocalStorageAvailable()) return true;
    return localGetItem('lm:preferSigned') !== '0';
  });
  const [issuerKey, setIssuerKey] = useState(() =>
    isLocalStorageAvailable() ? localGetItem('lm:issuerKey') || '' : ''
  );
  const [authToken, setAuthToken] = useState(() =>
    isLocalStorageAvailable() ? localGetItem('lm:authToken') || '' : ''
  );

  useEffect(() => {
    let mounted = true;
    api
      .getServerConfig()
      .then((c) => {
        if (mounted) setConfig(c);
      })
      .catch(() => {
        if (mounted) setConfig(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const togglePreferSigned = () => {
    const next = !preferSigned;
    setPreferSigned(next);
    if (isLocalStorageAvailable())
      localSetItem('lm:preferSigned', next ? '1' : '0');
  };

  const saveIssuerKey = () => {
    if (isLocalStorageAvailable())
      localSetItem('lm:issuerKey', issuerKey || '');
    // set on api client
    api.setIssuerKey(issuerKey || null);
  };

  const saveAuthToken = () => {
    if (isLocalStorageAvailable())
      localSetItem('lm:authToken', authToken || '');
    api.setAuthToken(authToken || null);
  };

  return (
    <div className='glass-surface rounded-xl p-4'>
      <div className='flex items-center justify-between mb-2'>
        <div>
          <div className='text-sm font-medium'>Server Config</div>
          <div className='text-xs text-muted-foreground'>
            Displays non-sensitive server features
          </div>
        </div>
        <div>
          <button
            onClick={() => api.getServerConfig().then(setConfig)}
            className='btn-glass btn-glass--muted text-xs'
          >
            Refresh
          </button>
        </div>
      </div>

      <div className='text-xs space-y-1 mb-3'>
        <div>
          Signed URLs:{' '}
          <strong>
            {config ? String(config.signed_url_enabled) : 'unknown'}
          </strong>
        </div>
        <div>
          Sandbox Strict:{' '}
          <strong>{config ? String(config.sandbox_strict) : 'unknown'}</strong>
        </div>
        <div>
          JWT Auth:{' '}
          <strong>
            {config ? String(config.jwt_auth_enabled) : 'unknown'}
          </strong>
        </div>
        <div>
          Rate Limiting:{' '}
          <strong>
            {config ? String(config.rate_limit_enabled) : 'unknown'}
          </strong>
        </div>
      </div>

      <div className='flex items-center gap-3 mb-3'>
        <div className='min-w-0'>
          <div className='text-sm font-medium'>Prefer Signed Images</div>
          <div className='text-xs text-muted-foreground'>
            When enabled, the UI will attempt to obtain signed image URLs when
            available.
          </div>
        </div>
        <button
          onClick={togglePreferSigned}
          className={`btn-glass ${
            preferSigned ? 'btn-glass--primary' : 'btn-glass--muted'
          } text-xs px-3 py-2`}
        >
          {preferSigned ? 'On' : 'Off'}
        </button>
      </div>

      <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
        <div className='space-y-1'>
          <div className='text-xs font-medium'>
            Image Token Issuer Key (dev)
          </div>
          <div className='flex gap-2'>
            <input
              className='input w-full text-sm'
              value={issuerKey}
              onChange={(e) => setIssuerKey(e.target.value)}
              placeholder='Issuer API key'
            />
            <button
              className='btn-glass btn-glass--muted text-xs'
              onClick={saveIssuerKey}
            >
              Save
            </button>
          </div>
        </div>

        <div className='space-y-1'>
          <div className='text-xs font-medium'>Auth Token (Bearer JWT)</div>
          <div className='flex gap-2'>
            <input
              className='input w-full text-sm'
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              placeholder='Bearer token'
            />
            <button
              className='btn-glass btn-glass--muted text-xs'
              onClick={saveAuthToken}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ServerConfigPanel;
