import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
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
    Menu,
} from 'lucide-react';

interface ActionsPodProps {
    hasRecentJobs: boolean;
    toggleMinimalMode: () => void;
}

// Get the current page icon based on pathname
function getCurrentIcon(pathname: string) {
    if (pathname.startsWith('/albums')) return FolderOpen;
    if (pathname.startsWith('/people')) return Users;
    if (pathname.startsWith('/import')) return Download;
    if (pathname.startsWith('/favorites')) return Star;
    if (pathname.startsWith('/videos')) return Film;
    if (pathname.startsWith('/trash')) return Trash2;
    if (pathname.startsWith('/tags')) return Hash;
    if (pathname.startsWith('/jobs')) return Clock;
    if (pathname.startsWith('/performance')) return BarChart3;
    if (pathname.startsWith('/settings')) return Settings;
    if (pathname.startsWith('/about')) return Info;
    return Menu; // Default icon
}

export function ActionsPod({ hasRecentJobs, toggleMinimalMode }: ActionsPodProps) {
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const closeTimerRef = useRef<number | null>(null);

    const CurrentIcon = getCurrentIcon(location.pathname);

    useEffect(() => {
        // Close the rail when navigation occurs
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

    const linkClass = 'p-2 rounded-full hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground flex-shrink-0';

    return (
        <div
            className={`${open ? 'glass-surface' : ''} rounded-full p-1 flex flex-row-reverse items-center ${open ? 'gap-1' : ''} overflow-hidden`}
            onMouseEnter={() => {
                cancelClose();
                setOpen(true);
            }}
            onMouseLeave={scheduleClose}
        >
            {/* Trigger button - shows current page icon or menu (positioned on RIGHT with flex-row-reverse) */}
            <button
                className='btn-glass btn-glass--muted w-[36px] h-[36px] p-0 justify-center flex-shrink-0'
                onClick={() => setOpen((v) => !v)}
                title='Navigation'
                aria-label='Toggle navigation'
            >
                <CurrentIcon size={18} />
            </button>

            {/* Expandable nav items - expands LEFTWARD due to flex-row-reverse */}
            <div
                className={`transition-all duration-200 ease-out flex flex-row-reverse items-center ${open ? 'max-w-[500px] opacity-100 gap-0.5' : 'max-w-0 opacity-0'
                    } overflow-hidden`}
            >
                <Link to='/albums' className={linkClass} title='Albums' aria-label='Albums'>
                    <FolderOpen size={18} />
                </Link>
                <Link to='/people' className={linkClass} title='People' aria-label='People'>
                    <Users size={18} />
                </Link>
                <Link to='/import' className={linkClass} title='Import' aria-label='Import'>
                    <Download size={18} />
                </Link>
                <Link to='/favorites' className={linkClass} title='Favorites' aria-label='Favorites'>
                    <Star size={18} />
                </Link>
                <Link to='/videos' className={linkClass} title='Videos' aria-label='Videos'>
                    <Film size={18} />
                </Link>
                <Link to='/trash' className={linkClass} title='Trash' aria-label='Trash'>
                    <Trash2 size={18} />
                </Link>
                <Link to='/tags' className={linkClass} title='Tags' aria-label='Tags'>
                    <Hash size={18} />
                </Link>
                <Link to='/jobs' className={`${linkClass} relative`} title='Jobs' aria-label='Jobs'>
                    <Clock size={18} />
                    {hasRecentJobs && (
                        <span className='absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.65)]' />
                    )}
                </Link>
                <Link to='/performance' className={linkClass} title='Performance' aria-label='Performance'>
                    <BarChart3 size={18} />
                </Link>
                <button onClick={toggleMinimalMode} className={linkClass} title='Focus mode' aria-label='Focus mode'>
                    <EyeOff size={18} />
                </button>
                <Link to='/settings' className={linkClass} title='Settings' aria-label='Settings'>
                    <Settings size={18} />
                </Link>
                <Link to='/about' className={`${linkClass} pl-1`} title='About' aria-label='About'>
                    <Info size={18} />
                </Link>
            </div>
        </div>
    );
}
