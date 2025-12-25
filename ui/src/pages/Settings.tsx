/**
 * Settings Page
 *
 * Application settings and configuration
 */

import { useState } from 'react';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../utils/storage';
import { SourcesPanel } from '../components/sources/SourcesPanel';
import ServerConfigPanel from '../components/ServerConfigPanel';
import { PrivacyPanel } from '../components/settings/PrivacyPanel';

const Settings = () => {
  const [focusMode, setFocusMode] = useState(() => {
    if (!isLocalStorageAvailable()) return false;
    return localGetItem('lm:minimalMode') === '1';
  });

  const [developerMode, setDeveloperMode] = useState(() => {
    if (!isLocalStorageAvailable()) return false;
    return localGetItem('lm:developerMode') === '1';
  });

  const toggleFocusMode = () => {
    const next = !focusMode;
    setFocusMode(next);
    if (isLocalStorageAvailable()) {
      localSetItem('lm:minimalMode', next ? '1' : '0');
      window.dispatchEvent(new Event('lm:prefChange'));
    }
  };

  const toggleDeveloperMode = () => {
    const next = !developerMode;
    setDeveloperMode(next);
    if (isLocalStorageAvailable()) {
      localSetItem('lm:developerMode', next ? '1' : '0');
      window.dispatchEvent(new Event('lm:prefChange'));
    }
  };

  return (
    <div className='mx-auto w-full max-w-3xl'>
      <div className='mb-6'>
        <h1 className='text-2xl font-semibold tracking-tight text-foreground'>
          Settings
        </h1>
        <p className='text-sm text-muted-foreground'>
          Tune the UI to match how you browse.
        </p>
      </div>

      <div className='glass-surface rounded-2xl p-5 sm:p-7 space-y-6'>
        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>UI</h2>

          <div className='flex items-center justify-between gap-4 glass-surface rounded-xl px-4 py-3'>
            <div className='min-w-0'>
              <div className='text-sm font-semibold text-foreground'>
                Focus mode
              </div>
              <div className='text-xs text-muted-foreground'>
                Hide the floating command bar and extra chrome for a pure
                gallery view.
              </div>
            </div>

            <button
              onClick={toggleFocusMode}
              className={`btn-glass ${focusMode ? 'btn-glass--primary' : 'btn-glass--muted'
                } text-xs px-3 py-2`}
            >
              {focusMode ? 'On' : 'Off'}
            </button>
          </div>

          <div className='flex items-center justify-between gap-4 glass-surface rounded-xl px-4 py-3'>
            <div className='min-w-0'>
              <div className='text-sm font-semibold text-foreground'>
                Developer Mode
              </div>
              <div className='text-xs text-muted-foreground'>
                Show technical output like raw JSON data, debug info, and API responses.
              </div>
            </div>

            <button
              onClick={toggleDeveloperMode}
              className={`btn-glass ${developerMode ? 'btn-glass--primary' : 'btn-glass--muted'
                } text-xs px-3 py-2`}
            >
              {developerMode ? 'On' : 'Off'}
            </button>
          </div>
        </section>

        <section id='sources' className='space-y-2 scroll-mt-24'>
          <SourcesPanel />
        </section>

        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>
            Sync & Security
          </h2>

          <ServerConfigPanel />
        </section>

        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>
            Privacy
          </h2>
          <PrivacyPanel />
        </section>

        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>About</h2>
          <div className='text-sm text-muted-foreground'>Living Museum</div>
        </section>
      </div>
    </div>
  );
};

export default Settings;
