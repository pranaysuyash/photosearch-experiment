/**
 * /pair — the page a not-yet-paired browser lands on (via the 401 bridge in
 * MainRouter, or by typing the suggested URL). Accepts `?code=NNNN` so a
 * pasted link completes without typing.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Smartphone, CheckCircle2 } from 'lucide-react';
import { PairingCodeForm } from '@/components/settings/PairingPanel';
import { completePairing, pairingStatus, type PairStatus } from '@/platform/session';

export const PAIR_RETURN_KEY = 'lm:pairReturnTo';

function consumeReturnPath(): string {
  try {
    const stored = sessionStorage.getItem(PAIR_RETURN_KEY);
    sessionStorage.removeItem(PAIR_RETURN_KEY);
    if (stored && stored.startsWith('/') && !stored.startsWith('/pair')) return stored;
  } catch {
    // storage unavailable
  }
  return '/';
}

const PairPage = () => {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [status, setStatus] = useState<PairStatus | null | 'loading'>('loading');
  const [autoError, setAutoError] = useState<string | null>(null);

  const finish = useCallback(() => {
    navigate(consumeReturnPath(), { replace: true });
  }, [navigate]);

  useEffect(() => {
    let cancelled = false;
    pairingStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // A pasted link with ?code= pairs immediately.
  useEffect(() => {
    const code = params.get('code');
    if (!code || status === 'loading' || (status && status.paired)) return;
    completePairing(code).then((result) => {
      if (result.ok) finish();
      else setAutoError(result.error);
    });
  }, [params, status, finish]);

  if (status === 'loading') {
    return (
      <div className='flex items-center justify-center py-12 text-sm text-muted-foreground'>
        Checking connection…
      </div>
    );
  }

  if (status && status.paired) {
    return (
      <div className='mx-auto w-full max-w-md glass-surface rounded-2xl p-6 text-center space-y-4'>
        <CheckCircle2 className='mx-auto text-emerald-400' size={36} />
        <h1 className='text-lg font-semibold text-foreground'>This device is connected</h1>
        <p className='text-sm text-muted-foreground'>
          Signed in as {status.user_id}
          {status.via ? ` (${status.via})` : ''}.
        </p>
        <Link to='/' className='btn-glass btn-glass--primary inline-flex text-sm px-4 py-2'>
          Open library
        </Link>
      </div>
    );
  }

  return (
    <div className='mx-auto w-full max-w-md glass-surface rounded-2xl p-6 space-y-5'>
      <div className='text-center space-y-2'>
        <Smartphone className='mx-auto text-primary' size={36} />
        <h1 className='text-lg font-semibold text-foreground'>Connect this device</h1>
        <p className='text-sm text-muted-foreground'>
          On the computer running PhotoSearch, open Settings → Devices → “Connect a
          device” and enter the code it shows.
        </p>
        {status === null && (
          <p className='text-xs text-amber-300'>
            Couldn’t reach the server to check pairing state; you can still try a code.
          </p>
        )}
      </div>
      {autoError && (
        <div className='text-xs text-destructive text-center' role='alert'>
          {autoError}
        </div>
      )}
      <PairingCodeForm onDone={finish} />
    </div>
  );
};

export default PairPage;
