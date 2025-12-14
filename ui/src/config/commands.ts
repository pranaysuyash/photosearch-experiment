import { Zap, Moon } from 'lucide-react';

import type { ComponentType } from 'react';

export interface CommandItem {
  id: string;
  name: string;
  icon: ComponentType<Record<string, unknown>>;
  shortcut?: string;
  action: () => void;
  keywords?: string; // Additional keywords for fuzzy search if needed
}

export const getSystemCommands = (
  setOpen: (open: boolean) => void,
  onScan?: () => void
): CommandItem[] => [
  {
    id: 'scan',
    name: 'Scan Library',
    icon: Zap,
    action: () => {
      if (onScan) {
        onScan();
        // Don't close immediately if we want to show feedback
      } else {
        console.log('No scan handler provided');
        setOpen(false);
      }
    },
  },
  {
    id: 'toggle-theme',
    name: 'Toggle Dark/Light Mode',
    icon: Moon, // Or dynamic icon
    action: () => {
      document.documentElement.classList.toggle('dark');
      setOpen(false);
    },
  },
];
