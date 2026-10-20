import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { useModalBehavior } from '../hooks/useModalBehavior';

// Flush helper (matches photogrid.test.tsx pattern)
const flush = () => new Promise((r) => setTimeout(r, 0));

function Host({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const panelRef = useModalBehavior(open, onClose);
  return (
    <div>
      <button id='trigger'>Trigger</button>
      {open && (
        <div
          ref={panelRef}
          role='dialog'
          aria-modal='true'
          aria-label='Test dialog'
        >
          <button id='first'>First</button>
          <button id='last'>Last</button>
        </div>
      )}
    </div>
  );
}

describe('useModalBehavior', () => {
  let container: HTMLDivElement;
  let root: Root;

  // jsdom has no layout engine: getClientRects() is always empty, which would
  // make the hook's hidden-element filter treat every focusable as invisible.
  // Stub it so connected elements report as visible.
  beforeEach(() => {
    vi.spyOn(
      HTMLElement.prototype,
      'getClientRects'
    ).mockImplementation(function (this: HTMLElement) {
      return this.isConnected
        ? ([{ width: 10, height: 10 }] as unknown as DOMRectList)
        : ([] as unknown as DOMRectList);
    });
  });

  const mount = async (open: boolean, onClose: () => void) => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root.render(<Host open={open} onClose={onClose} />);
    });
    await flush();
  };

  const rerender = async (open: boolean, onClose: () => void) => {
    await act(async () => {
      root.render(<Host open={open} onClose={onClose} />);
    });
    await flush();
  };

  const pressKey = (key: string, target?: Element) => {
    const event = new KeyboardEvent('keydown', {
      key,
      bubbles: true,
      cancelable: true,
    });
    (target ?? document).dispatchEvent(event);
    return event;
  };

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });

  test('moves focus into the dialog on open (first focusable)', async () => {
    await mount(false, vi.fn());
    await rerender(true, vi.fn());

    expect(document.getElementById('first')).not.toBeNull();
    expect(document.activeElement?.id).toBe('first');
  });

  test('closes on Escape', async () => {
    const onClose = vi.fn();
    await mount(true, onClose);

    const event = pressKey('Escape');
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(false);
  });

  test('traps Tab inside the panel (Tab from last wraps to first)', async () => {
    await mount(true, vi.fn());

    // Focus the last focusable, then press Tab — focus must wrap to first
    await act(async () => {
      (document.getElementById('last') as HTMLElement).focus();
    });
    pressKey('Tab');

    expect(document.activeElement?.id).toBe('first');
  });

  test('Shift+Tab from the first element wraps to the last', async () => {
    await mount(true, vi.fn());

    await act(async () => {
      (document.getElementById('first') as HTMLElement).focus();
    });
    const shiftTab = new KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(shiftTab); // Shift+Tab from first wraps to last

    expect(shiftTab.defaultPrevented).toBe(true);
    expect(document.activeElement?.id).toBe('last');
  });

  test('restores focus to the previously focused element on close', async () => {
    await mount(false, vi.fn());
    await act(async () => {
      (document.getElementById('trigger') as HTMLElement).focus();
    });
    await rerender(true, vi.fn());
    expect(document.activeElement?.id).toBe('first');

    await rerender(false, vi.fn());
    expect(
      document.getElementById('dialog-gone') // dialog unmounted
    ).toBeNull();
    expect(document.activeElement?.id).toBe('trigger');
  });

  test('does nothing while closed', async () => {
    const onClose = vi.fn();
    await mount(false, onClose);

    pressKey('Escape');
    expect(onClose).not.toHaveBeenCalled();
  });
});
