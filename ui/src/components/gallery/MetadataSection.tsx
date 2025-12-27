import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export function MetadataSection({
  icon: Icon,
  title,
  children,
  defaultOpen = false,
}: {
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className='mb-3 glass-surface rounded-xl overflow-hidden'>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className='w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors text-left'
      >
        <div className='flex items-center gap-2.5'>
          {Icon && (
            <div className='w-6 h-6 rounded-lg bg-white/5 flex items-center justify-center text-white/70'>
              <Icon size={14} />
            </div>
          )}
          <span className='text-white/80 font-medium text-sm uppercase tracking-wider'>
            {title}
          </span>
        </div>
        <div
          className='transition-transform duration-200'
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <ChevronDown size={16} className='text-white/50' />
        </div>
      </button>

      {isOpen && (
        <div className='px-3 pb-3 space-y-1 text-sm border-t border-white/5'>
          {children}
        </div>
      )}
    </div>
  );
}

export function MetadataRow({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  if (value === undefined || value === null || value === '') return null;

  let displayValue: string;
  if (typeof value === 'string') displayValue = value;
  else if (typeof value === 'number')
    displayValue = Number.isFinite(value) ? String(value) : 'Unknown';
  else if (typeof value === 'boolean') displayValue = value ? 'Yes' : 'No';
  else {
    try {
      displayValue = JSON.stringify(value);
    } catch {
      displayValue = String(value);
    }
  }

  return (
    <div className='flex justify-between items-start py-1.5 border-b border-white/5 last:border-0'>
      <span className='text-white/40 text-xs mt-0.5'>{label}</span>
      <span className='text-white/90 font-mono text-xs text-right max-w-[60%] break-words select-text'>
        {displayValue}
      </span>
    </div>
  );
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: unknown) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error('MetadataSection Error:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className='p-2 text-xs text-red-400'>Error loading section</div>
        )
      );
    }
    return this.props.children;
  }
}
