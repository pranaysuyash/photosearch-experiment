import { useEffect, useState, useMemo, useRef } from "react";
import { Command } from "cmdk";
import { Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";
import { usePhotoSearch } from "../hooks/usePhotoSearch";
import { getSystemCommands } from "../config/commands";

export function Spotlight() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // Use shared hook for photo results
  const { results, loading, setQuery: setSearchQuery } = usePhotoSearch({ 
    initialQuery: "",
    debounceMs: 300 
  });

  const [status, setStatus] = useState<{ message: string; type: 'success' | 'error' | 'info'; details?: any } | null>(null);
  const [scanPath, setScanPath] = useState<string>("");
  const [showScanInput, setShowScanInput] = useState(false);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const handleScan = async (pathToScan?: string) => {
     const path = pathToScan || scanPath;
     
     if (!path) {
       // Show input for path
       setShowScanInput(true);
       setStatus({ message: "Enter folder path to scan", type: 'info' });
       return;
     }
     
     setShowScanInput(false);
     setStatus({ message: "Starting scan...", type: 'info' });
     
     try {
       const res = await api.scan(path, true);
       const jobId = res.job_id;
       
       setStatus({ message: "Scan started. Processing...", type: 'info' });

       // Clear any existing poll
       if (pollRef.current) {
         clearInterval(pollRef.current);
       }

       // Polling with ref tracking
       pollRef.current = setInterval(async () => {
          try {
             const job = await api.getJobStatus(jobId);
             if (job.status === 'completed') {
                if (pollRef.current) clearInterval(pollRef.current);
                pollRef.current = null;
                setStatus({ message: "Scan Complete!", type: 'success' });
                setTimeout(() => {
                  setOpen(false);
                  setStatus(null);
                }, 2000);
                // Refresh results
                setSearchQuery(query); 
             } else if (job.status === 'failed') {
                if (pollRef.current) clearInterval(pollRef.current);
                pollRef.current = null;
                setStatus({ message: `Failed: ${job.message}`, type: 'error' });
             } else {
                setStatus({ message: job.message || "Processing...", type: 'info' });
             }
          } catch (e) {
             if (pollRef.current) clearInterval(pollRef.current);
             pollRef.current = null;
             setStatus({ message: "Error tracking job", type: 'error' });
          }
       }, 1000);

     } catch (e) {
       setStatus({ message: "Failed to start scan", type: 'error' });
     }
  };

  // Get system commands - use callback to stabilize reference
  const systemCommands = useMemo(() => getSystemCommands(setOpen, () => handleScan()), []);

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

                        {status && (
                            <div className={`px-4 py-2 text-sm border-b border-border flex items-center ${
                                status.type === 'error' ? 'text-destructive bg-destructive/10' : 
                                status.type === 'success' ? 'text-green-500 bg-green-500/10' : 
                                'text-muted-foreground bg-muted/50'
                            }`}>
                                <div className={`w-2 h-2 rounded-full mr-2 ${
                                    status.type === 'error' ? 'bg-destructive' : 
                                    status.type === 'success' ? 'bg-green-500' : 
                                    'animate-pulse bg-blue-500'
                                }`} />
                                {status.message}
                            </div>
                        )}

                        {showScanInput && (
                            <div className="px-4 py-3 border-b border-border bg-muted/30">
                                <label className="text-xs text-muted-foreground mb-1 block">Folder path to scan:</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={scanPath}
                                        onChange={(e) => setScanPath(e.target.value)}
                                        placeholder="/Users/you/Pictures"
                                        className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm outline-none focus:ring-2 focus:ring-primary"
                                        autoFocus
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && scanPath) {
                                                handleScan(scanPath);
                                            }
                                        }}
                                    />
                                    <button
                                        onClick={() => handleScan(scanPath)}
                                        disabled={!scanPath}
                                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
                                    >
                                        Scan
                                    </button>
                                </div>
                            </div>
                        )}

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
