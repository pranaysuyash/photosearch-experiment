export function isLocalStorageAvailable() {
  try {
    if (
      typeof window === 'undefined' ||
      typeof window.localStorage === 'undefined'
    )
      return false;
    const testKey = '__ps_test__';
    window.localStorage.setItem(testKey, '1');
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

export function localGetItem(key: string): string | null {
  if (!isLocalStorageAvailable()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function localSetItem(key: string, value: string) {
  if (!isLocalStorageAvailable()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

export function localRemoveItem(key: string) {
  if (!isLocalStorageAvailable()) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}
