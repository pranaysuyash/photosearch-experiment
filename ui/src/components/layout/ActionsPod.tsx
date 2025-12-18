import { Link } from 'react-router-dom';
import {
    Settings,
    Info,
    EyeOff,
    Clock,
    FolderOpen,
    Star,
    Film,
    Trash2,
    Hash,
    BarChart3,
    Users,
    Download,
} from 'lucide-react';
import { glass } from '../../design/glass';

interface ActionsPodProps {
    hasRecentJobs: boolean;
    toggleMinimalMode: () => void;
}

export function ActionsPod({ hasRecentJobs, toggleMinimalMode }: ActionsPodProps) {
    return (
        <div className={`${glass.surface} rounded-full px-1 h-11 header-actions flex items-center gap-1`}>
            <Link
                to='/albums'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Albums'
                title='Albums (photo collections)'
                aria-label='Albums'
            >
                <FolderOpen size={18} />
            </Link>
            <Link
                to='/people'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='People'
                title='People (face recognition)'
                aria-label='People'
            >
                <Users size={18} />
            </Link>
            <Link
                to='/import'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Import'
                title='Import photos'
                aria-label='Import'
            >
                <Download size={18} />
            </Link>
            <Link
                to='/favorites'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Favorites'
                title='Favorites'
                aria-label='Favorites'
            >
                <Star size={18} />
            </Link>
            <Link
                to='/videos'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Videos'
                title='Videos'
                aria-label='Videos'
            >
                <Film size={18} />
            </Link>
            <Link
                to='/trash'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Trash'
                title='Trash (recently deleted)'
                aria-label='Trash'
            >
                <Trash2 size={18} />
            </Link>
            <Link
                to='/tags'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Tags'
                title='Tags'
                aria-label='Tags'
            >
                <Hash size={18} />
            </Link>
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
            <Link
                to='/performance'
                className='p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground'
                data-tooltip='Performance'
                title='Performance Dashboard'
                aria-label='Performance Dashboard'
            >
                <BarChart3 size={18} />
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
