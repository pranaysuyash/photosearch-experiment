import { useEffect, useState, useMemo } from "react";
import { Command } from "cmdk";
import { Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";
import { usePhotoSearch } from "../hooks/usePhotoSearch";
import { getSystemCommands } from "../config/commands";

export function Spotlight() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  
  // Use shared hook for photo results
  const { results, loading, setQuery: setSearchQuery } = usePhotoSearch({ 
    initialQuery: "",
    debounceMs: 300 
  });

  // Get system commands
  const systemCommands = useMemo(() => getSystemCommands(setOpen), []);

  // Toggle with Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Update hook query when input changes
  useEffect(() => {
    if (open) {
        setSearchQuery(query);
    }
  }, [query, open, setSearchQuery]);

  return (
    <AnimatePresence>
        {open && (
            <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh] px-4">
                {/* Backdrop */}
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setOpen(false)}
                    className="absolute inset-0 bg-background/80 backdrop-blur-sm"
                />

                {/* Modal */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: -20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -20 }}
                    className="relative w-full max-w-2xl bg-popover border border-border rounded-xl shadow-2xl overflow-hidden"
                >
                    <Command className="w-full bg-transparent">
                        <div className="flex items-center border-b border-border px-4" cmdk-input-wrapper="">
                            <Search className="w-5 h-5 text-muted-foreground mr-3" />
                            <Command.Input 
                                value={query}
                                onValueChange={setQuery}
                                placeholder="Search photos or run commands..."
                                className="w-full h-14 bg-transparent outline-none text-lg placeholder:text-muted-foreground/50"
                            />
                            {loading && <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full" />}
                            <div className="text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5 ml-2">ESC</div>
                        </div>

                        <Command.List className="max-h-[60vh] overflow-y-auto p-2 scrollbar-hide">
                            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                                No results found.
                            </Command.Empty>

                            {/* System Commands Group */}
                            {!query && (
                                <Command.Group heading="Suggestions" className="mb-2">
                                    {systemCommands.map((cmd) => (
                                        <Command.Item 
                                            key={cmd.id} 
                                            onSelect={cmd.action} 
                                            className="flex items-center px-2 py-2 rounded-lg cursor-pointer hover:bg-accent hover:text-accent-foreground aria-selected:bg-accent aria-selected:text-accent-foreground"
                                        >
                                            <cmd.icon className="w-4 h-4 mr-2" />
                                            <span>{cmd.name}</span>
                                        </Command.Item>
                                    ))}
                                </Command.Group>
                            )}

                            {/* Photo Results Group */}
                            {results.length > 0 && (
                                <Command.Group heading="Photos">
                                    {results.map((photo) => (
                                        <Command.Item 
                                            key={photo.path} 
                                            onSelect={() => {
                                                // Handle selection (e.g. open detail view)
                                                console.log("Selected:", photo.filename);
                                                setOpen(false);
                                            }}
                                            className="flex items-center px-2 py-2 rounded-lg cursor-pointer hover:bg-accent hover:text-accent-foreground aria-selected:bg-accent aria-selected:text-accent-foreground"
                                        >
                                            <div className="w-8 h-8 rounded bg-secondary mr-3 overflow-hidden flex-shrink-0">
                                                <img src={api.getImageUrl(photo.path)} alt="" className="w-full h-full object-cover" />
                                            </div>
                                            <div className="flex flex-col overflow-hidden">
                                                <span className="truncate text-sm font-medium">{photo.filename}</span>
                                                <span className="truncate text-[10px] text-muted-foreground">{photo.path}</span>
                                            </div>
                                        </Command.Item>
                                    ))}
                                </Command.Group>
                            )}
                        </Command.List>
                    </Command>
                </motion.div>
            </div>
        )}
    </AnimatePresence>
  );
}
