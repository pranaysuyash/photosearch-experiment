/**
 * Settings section for device pairing. On the desktop (loopback) this is the
 * control surface: generate a code, hand it to the other device. In a paired
 * browser it reports the connection state and offers sign-out.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  completePairing,
  pairingStatus,
  revokePairing,
  startPairing,
  type PairStart,
  type PairStatus,
} from '@/platform/session';
import { isDesktopApp } from '@/platform';

export function PairingPanel() {
  const [status, setStatus] = useState<PairStatus | null>(null);
  const [pending, setPending] = useState<PairStart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    pairingStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(refresh, [refresh]);

  if (status === null) return null;
  if (!status.pairing_enabled) return null;

  const begin = async () => {
    setBusy(true);
    setError(null);
    try {
      setPending(await startPairing());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start pairing.');
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    setBusy(true);
    setError(null);
    try {
      await revokePairing();
      setPending(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Revoke failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className='space-y-3'>
      <div className='flex items-center justify-between gap-4 glass-surface rounded-xl px-4 py-3'>
        <div className='min-w-0'>
          <div className='text-sm font-semibold text-foreground'>
            {status.paired
              ? status.via === 'loopback'
                ? 'This is the primary device'
                : 'This browser is connected'
              : 'Not connected'}
          </div>
          <div className='text-xs text-muted-foreground'>
            {status.paired
              ? `Signed in as ${status.user_id} (${status.via}).`
              : 'Open this server from another browser and pair to see your library.'}
          </div>
        </div>

        {status.via === 'loopback' && (
          <button
            type='button'
            onClick={begin}
            disabled={busy}
            className='btn-glass btn-glass--primary text-xs px-3 py-2 disabled:opacity-50'
          >
            Connect a device
          </button>
        )}
        {status.paired && status.via !== 'loopback' && (
          <button
            type='button'
            onClick={revoke}
            disabled={busy}
            className='btn-glass btn-glass--danger text-xs px-3 py-2 disabled:opacity-50'
          >
            Disconnect
          </button>
        )}
      </div>

      {pending && (
        <div className='glass-surface rounded-xl px-4 py-3 space-y-2'>
          <div className='text-xs text-muted-foreground'>
            On the other device, open{' '}
            {pending.suggested_url ? (
              <span className='font-mono break-all text-foreground'>
                {pending.suggested_url}
              </span>
            ) : (
              'this server’s address + /app/pair'
            )}{' '}
            and enter:
          </div>
          <div className='text-3xl font-semibold tracking-[0.4em] text-foreground font-mono'>
            {pending.code}
          </div>
          <div className='text-xs text-muted-foreground'>
            Valid for {Math.round(pending.expires_in / 60)} minutes, single use.
            {!isDesktopApp && ' (Pairing starts on the primary device.)'}
          </div>
        </div>
      )}

      {error && <div className='text-xs text-destructive'>{error}</div>}
    </div>
  );
}

/** Enter a pairing code (the /app/pair page on the device being connected). */
export function PairingCodeForm({ onDone }: { onDone: () => void }) {
  const [code, setCode] = useState('');
  const [state, setState] = useState<'idle' | 'busy' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (value: string) => {
      if (!/^\d{4}$/.test(value)) {
        setState('error');
        setError('Enter the 4-digit code shown on the primary device.');
        return;
      }
      setState('busy');
      const result = await completePairing(value);
      if (result.ok) {
        onDone();
        return;
      }
      setState('error');
      setError(result.error);
    },
    [onDone]
  );

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void submit(code);
      }}
      className='space-y-3'
    >
      <input
        value={code}
        onChange={(event) => {
          setCode(event.target.value.replace(/\D/g, '').slice(0, 4));
          setState('idle');
        }}
        inputMode='numeric'
        autoComplete='one-time-code'
        placeholder='0000'
        aria-label='Pairing code'
        className='w-full rounded-xl bg-transparent border border-border px-4 py-3 text-center text-2xl tracking-[0.5em] font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-ring'
      />
      <button
        type='submit'
        disabled={state === 'busy'}
        className='btn-glass btn-glass--primary w-full justify-center text-sm px-4 py-3 disabled:opacity-50'
      >
        {state === 'busy' ? 'Connecting…' : 'Connect'}
      </button>
      {state === 'error' && error && (
        <div className='text-xs text-destructive' role='alert'>
          {error}
        </div>
      )}
    </form>
  );
}
