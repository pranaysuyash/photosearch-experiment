export async function pickDirectory(): Promise<string | null> {
  // @ts-expect-error Tauri global injected at runtime in desktop builds
  const isTauri = typeof window !== 'undefined' && !!window.__TAURI__;
  if (!isTauri) return null;

  try {
    const dialog = await import('@tauri-apps/plugin-dialog');
    const selected = await dialog.open({
      directory: true,
      multiple: false,
      title: 'Choose a folder',
    });
    return typeof selected === 'string' ? selected : null;
  } catch {
    return null;
  }
}
