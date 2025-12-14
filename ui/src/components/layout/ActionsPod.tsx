import { Link } from 'react-router-dom';
import {
    Settings,
    Info,
    EyeOff,
    Clock,
} from 'lucide-react';
import { glass } from '../../design/glass';

interface ActionsPodProps {
    hasRecentJobs: boolean;
    toggleMinimalMode: () => void;
}

export function ActionsPod({ hasRecentJobs, toggleMinimalMode }: ActionsPodProps) {
    return (
        <div className={`${glass.surface} rounded-full p-1 header-actions flex items-center gap-1`}>
            <Link
                to='/jobs'
                className='p-2 rounded-full hover:bg-white/10 transition-colors relative text-muted-foreground hover:text-foreground'
                data-tooltip='Jobs'
                title='Jobs (background scans/indexing)'
                aria-label='Jobs'
            >
                <Clock size={18} />
                {hasRecentJobs && (
                    <span className='absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.65)]' />
                )}
            </Link>
            <button
                onClick={toggleMinimalMode}
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Focus'
                title='Focus mode (hide chrome)'
                aria-label='Toggle focus mode'
            >
                <EyeOff size={18} />
            </button>
            <Link
                to='/settings'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Settings'
                title='Settings'
                aria-label='Settings'
            >
                <Settings size={18} />
            </Link>
            <Link
                to='/about'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='About'
                title='About'
                aria-label='About'
            >
                <Info size={18} />
            </Link>
        </div>
    );
}
