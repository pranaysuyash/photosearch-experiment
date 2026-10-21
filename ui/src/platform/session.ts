/**
 * Pairing/session calls for the web companion. Loopback clients (the desktop
 * shell) are the owner by virtue of their socket address and never need these
 * except to pair *other* devices.
 */
import { apiFetch } from '@/api';

export interface PairStatus {
  pairing_enabled: boolean;
  paired: boolean;
  via: 'loopback' | 'cookie' | 'bearer' | null;
  user_id: string | null;
}

export interface PairStart {
  code: string;
  expires_in: number;
  suggested_url: string | null;
}

export async function pairingStatus(): Promise<PairStatus> {
  const response = await apiFetch('/pair/status');
  if (!response.ok) throw new Error(`pair/status failed: ${response.status}`);
  return (await response.json()) as PairStatus;
}

export async function startPairing(): Promise<PairStart> {
  const response = await apiFetch('/pair/start', { method: 'POST' });
  if (response.status === 403) {
    throw new Error('Pairing starts from the desktop app, not from another device.');
  }
  if (!response.ok) throw new Error(`pair/start failed: ${response.status}`);
  return (await response.json()) as PairStart;
}

/** Resolves to the paired user id, or an error message safe to show. */
export async function completePairing(
  code: string
): Promise<{ ok: true; user_id: string } | { ok: false; error: string }> {
  const response = await apiFetch('/pair/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (response.ok) {
    const body = (await response.json()) as { user_id: string };
    return { ok: true, user_id: body.user_id };
  }
  if (response.status === 400) {
    return { ok: false, error: 'That code is unknown or has expired.' };
  }
  return { ok: false, error: `Pairing failed (${response.status}).` };
}

export async function revokePairing(): Promise<void> {
  const response = await apiFetch('/pair/revoke', { method: 'POST' });
  if (!response.ok) throw new Error(`pair/revoke failed: ${response.status}`);
}
