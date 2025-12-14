import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Film, Globe, Grid3x3 } from 'lucide-react';
import { ModeSwitcher } from './ModeSwitcher';

type Mode = 'grid' | 'globe' | 'story';
type Variant = 'standalone' | 'inline';

function getMode(pathname: string): Mode {
  if (pathname.startsWith('/globe')) return 'globe';
  if (pathname.startsWith('/story-mode')) return 'story';
  return 'grid';
}

function ModeIcon({ mode }: { mode: Mode }) {
  if (mode === 'globe') return <Globe size={18} />;
  if (mode === 'story') return <Film size={18} />;
  return <Grid3x3 size={18} />;
}

export function ModeRail({ variant = 'standalone' }: { variant?: Variant }) {
  const location = useLocation();
  const mode = getMode(location.pathname);
  const [open, setOpen] = useState(false);
  const closeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    // Close the mode rail when navigation occurs. Schedule the setState
    // async to avoid the lint rule complaining about calling setState
    // synchronously in an effect.
    const id = requestAnimationFrame(() => setOpen(false));
    return () => cancelAnimationFrame(id);
  }, [location.pathname]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    };
  }, []);

  const scheduleClose = () => {
    if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = window.setTimeout(() => setOpen(false), 1200);
  };

  const cancelClose = () => {
    if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
  };

  const rootClassName =
    variant === 'inline'
      ? `rounded-full p-1 flex items-center ${open ? 'gap-2' : ''} overflow-hidden`
      : `${open ? 'glass-surface' : ''} rounded-full p-1 flex items-center ${open ? 'gap-2' : ''} overflow-hidden`;

  return (
    <div
      className={rootClassName}
      onMouseEnter={() => {
        cancelClose();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
    >
      <button
        className='btn-glass btn-glass--muted w-[34px] h-[34px] p-0 justify-center'
        onClick={() => setOpen((v) => !v)}
        title='View modes'
        aria-label='View modes'
      >
        <ModeIcon mode={mode} />
      </button>

      <div
        className={`transition-all duration-200 ease-out ${open ? 'max-w-[420px] opacity-100' : 'max-w-0 opacity-0'
          } overflow-hidden`}
      >
        <div className='pr-1'>
          <ModeSwitcher size='compact' exclude={mode} />
        </div>
      </div>
    </div>
  );
}
