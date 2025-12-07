import { Zap, Moon } from "lucide-react";

export interface CommandItem {
  id: string;
  name: string;
  icon: any;
  shortcut?: string;
  action: () => void;
  keywords?: string; // Additional keywords for fuzzy search if needed
}

export const getSystemCommands = (setOpen: (open: boolean) => void): CommandItem[] => [
  {
    id: "scan",
    name: "Scan Library",
    icon: Zap,
    action: () => {
      console.log("Triggering scan...");
      // In future: call scanning API
      setOpen(false);
    }
  },
  {
    id: "toggle-theme",
    name: "Toggle Dark/Light Mode",
    icon: Moon, // Or dynamic icon
    action: () => {
      document.documentElement.classList.toggle("dark");
      setOpen(false);
    }
  }
];
