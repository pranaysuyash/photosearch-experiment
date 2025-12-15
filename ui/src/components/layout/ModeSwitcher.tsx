import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Film, Globe, Grid3x3 } from 'lucide-react';

type Mode = 'grid' | 'globe' | 'story';

function getActiveMode(pathname: string): Mode | null {
  if (pathname.startsWith('/globe')) return 'globe';
  if (pathname.startsWith('/story-mode')) return 'story';
  if (pathname === '/') return 'grid';
  return null;
}

type ModeSwitcherProps = {
  size?: 'compact' | 'hero';
  exclude?: Mode | null;
};

export function ModeSwitcher({
  size = 'compact',
  exclude = null,
}: ModeSwitcherProps) {
  const location = useLocation();
  const active = getActiveMode(location.pathname);

  const containerClasses =
    size === 'hero'
      ? 'glass-surface rounded-full p-1 flex gap-1'
      : 'rounded-full p-1 flex gap-1';

  const buttonClasses =
    size === 'hero'
      ? 'text-sm px-4 py-2'
      : 'w-10 h-10 p-0 justify-center';

  const labelClasses = size === 'hero' ? '' : 'sr-only';

  const items: Array<{
    mode: Mode;
    to: string;
    title: string;
    label: string;
    icon: ReactNode;
  }> = [
      {
        mode: 'grid',
        to: '/',
        title: 'Grid: browse as a dense gallery',
        label: 'Grid',
        icon: <Grid3x3 size={16} />,
      },
      {
        mode: 'globe',
        to: '/globe',
        title: 'Globe: explore by place/time',
        label: 'Globe',
        icon: <Globe size={16} />,
      },
      {
        mode: 'story',
        to: '/story-mode',
        title: 'Story: immersive browsing',
        label: 'Story',
        icon: <Film size={16} />,
      },
    ];

  return (
    <div className={containerClasses} aria-label='View mode'>
      {items
        .filter((item) => item.mode !== exclude)
        .map((item) => (
          <Link
            key={item.mode}
            to={item.to}
            className={`btn-glass ${active === item.mode ? 'btn-glass--primary' : 'btn-glass--muted'
              } ${buttonClasses}`}
            title={item.title}
            aria-label={item.label}
            aria-current={active === item.mode ? 'page' : undefined}
          >
            {item.icon}
            <span className={labelClasses}>{item.label}</span>
          </Link>
        ))}
    </div>
  );
}
