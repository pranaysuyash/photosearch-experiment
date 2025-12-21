import { X, Minus, Maximize2, Minimize2 } from 'lucide-react';

interface TrafficLightButtonsProps {
    onClose: () => void;
    onMinimize?: () => void;
    onMaximize?: () => void;
    isMinimized?: boolean;
    isMaximized?: boolean;
    showMinimize?: boolean;
    showMaximize?: boolean;
    minimizeTooltip?: string;
    maximizeTooltip?: string;
    className?: string;
}

/**
 * Mac-style traffic light buttons component for modals and panels.
 * Provides consistent close/minimize/maximize controls across the app.
 */
export function TrafficLightButtons({
    onClose,
    onMinimize,
    onMaximize,
    isMinimized = false,
    isMaximized = false,
    showMinimize = true,
    showMaximize = true,
    minimizeTooltip,
    maximizeTooltip,
    className = '',
}: TrafficLightButtonsProps) {
    return (
        <div className={`flex items-center gap-2 group/traffic-lights ${className}`}>
            {/* Close button - Red */}
            <button
                onClick={onClose}
                className='w-3 h-3 rounded-full bg-red-500 hover:bg-red-600 transition-colors flex items-center justify-center group relative'
                aria-label='Close'
            >
                <X size={8} className='text-red-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50'>
                    Close
                </span>
            </button>

            {/* Minimize button - Yellow */}
            {showMinimize && onMinimize && (
                <button
                    onClick={onMinimize}
                    className='w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-600 transition-colors flex items-center justify-center group relative'
                    aria-label={minimizeTooltip || (isMinimized ? 'Show panel' : 'Hide panel')}
                >
                    <Minus size={8} className='text-yellow-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                    <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50'>
                        {minimizeTooltip || (isMinimized ? 'Show' : 'Hide')}
                    </span>
                </button>
            )}

            {/* Maximize button - Green */}
            {showMaximize && onMaximize && (
                <button
                    onClick={onMaximize}
                    className='w-3 h-3 rounded-full bg-green-500 hover:bg-green-600 transition-colors flex items-center justify-center group relative'
                    aria-label={maximizeTooltip || (isMaximized ? 'Exit fullscreen' : 'Fullscreen')}
                >
                    {isMaximized ? (
                        <Minimize2 size={8} className='text-green-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                    ) : (
                        <Maximize2 size={8} className='text-green-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                    )}
                    <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50'>
                        {maximizeTooltip || (isMaximized ? 'Exit Full' : 'Fullscreen')}
                    </span>
                </button>
            )}
        </div>
    );
}
