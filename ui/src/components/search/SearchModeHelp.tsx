import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { HelpCircle } from 'lucide-react';

export function SearchModeHelp({ variant = 'icon' }: { variant?: 'icon' | 'link' }) {
  const [open, setOpen] = useState(false);

  return (
    <div className='relative'>
      {variant === 'icon' ? (
        <button
          onClick={() => setOpen((v) => !v)}
          className='btn-glass btn-glass--muted w-9 h-9 p-0 justify-center'
          title='Search help'
          aria-label='Search help'
        >
          <HelpCircle size={16} />
        </button>
      ) : (
        <button
          onClick={() => setOpen((v) => !v)}
          className='text-xs text-muted-foreground hover:text-foreground underline underline-offset-4'
        >
          How to search
        </button>
      )}

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className='fixed inset-0 z-[90]'
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18 }}
              className='absolute right-0 mt-2 z-[100] w-[360px] max-w-[90vw] glass-surface glass-surface--strong rounded-2xl p-4 text-sm'
            >
              <div className='text-foreground font-semibold mb-2'>Search modes</div>
              <div className='space-y-2 text-muted-foreground'>
                <div>
                  <span className='text-foreground font-semibold'>Metadata</span>{' '}
                  is fastest and most precise for filenames, dates, cameras, folders.
                </div>
                <div>
                  <span className='text-foreground font-semibold'>Semantic</span>{' '}
                  finds meaning (e.g. “sunset in paris”) using embeddings.
                </div>
                <div>
                  <span className='text-foreground font-semibold'>Hybrid</span>{' '}
                  blends both for better recall.
                </div>
              </div>

              <div className='mt-4 text-xs text-muted-foreground'>
                Examples: <span className='text-foreground'>“receipt 2023”</span>,{' '}
                <span className='text-foreground'>“beach at night”</span>,{' '}
                <span className='text-foreground'>“IMG_1234”</span>.
              </div>

              <div className='mt-3 flex justify-end'>
                <button
                  onClick={() => setOpen(false)}
                  className='btn-glass btn-glass--muted text-xs px-3 py-2'
                >
                  Close
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

