import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, ArrowRight } from 'lucide-react';

interface CommandItem {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  action: () => void;
  shortcut?: string;
  category: string;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  commands: CommandItem[];
}

function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredCommands = commands.filter(
    (command) =>
      command.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      command.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      command.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            Math.min(prev + 1, filteredCommands.length - 1)
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
            onClose();
          }
          break;
      }
    },
    [isOpen, onClose, filteredCommands, selectedIndex]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Opening mounts the component (it returns null when closed),
      // so local state will be initialized to defaults; explicit reset
      // is not required and can trigger a lint rule for setState-in-effect.
    } else {
      document.removeEventListener('keydown', handleKeyDown);
    }

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className='fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-20'
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          className='bg-background border border-border rounded-lg shadow-2xl w-full max-w-2xl mx-4 max-h-96 overflow-hidden'
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className='flex items-center gap-3 p-4 border-b border-border'>
            <Search size={20} className='text-muted-foreground' />
            <input
              type='text'
              placeholder='Type a command or search...'
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSelectedIndex(0);
              }}
              className='flex-1 bg-transparent border-0 outline-none text-foreground placeholder:text-muted-foreground'
              autoFocus
            />
            <div className='flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded'>
              <Command size={12} />
              <span>K</span>
            </div>
          </div>

          {/* Commands List */}
          <div className='max-h-80 overflow-y-auto'>
            {filteredCommands.length === 0 ? (
              <div className='p-4 text-center text-muted-foreground'>
                No commands found
              </div>
            ) : (
              filteredCommands.map((command, index) => {
                const Icon = command.icon;
                return (
                  <div
                    key={command.id}
                    className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                      index === selectedIndex ? 'bg-muted' : ''
                    }`}
                    onClick={() => {
                      command.action();
                      onClose();
                    }}
                  >
                    <Icon
                      size={18}
                      className='text-muted-foreground flex-shrink-0'
                    />
                    <div className='flex-1 min-w-0'>
                      <div className='font-medium text-foreground truncate'>
                        {command.title}
                      </div>
                      <div className='text-sm text-muted-foreground truncate'>
                        {command.description}
                      </div>
                    </div>
                    {command.shortcut && (
                      <div className='text-xs text-muted-foreground bg-muted px-2 py-1 rounded flex-shrink-0'>
                        {command.shortcut}
                      </div>
                    )}
                    <ArrowRight
                      size={16}
                      className='text-muted-foreground flex-shrink-0'
                    />
                  </div>
                );
              })
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export { CommandPalette, type CommandItem };
