import React from 'react';
import { cn } from '../../../lib/utils'; // Assuming typical shadcn utility, else use template literal
import {
    Info,
    Edit3,
    FileText
} from 'lucide-react';
import { motion } from 'framer-motion';

export type TabName = 'info' | 'edit' | 'details';

interface PhotoDetailTabsProps {
    activeTab: TabName;
    onTabChange: (tab: TabName) => void;
    children: React.ReactNode;
}

export function PhotoDetailTabs({ activeTab, onTabChange, children }: PhotoDetailTabsProps) {

    const tabs: { id: TabName; label: string; icon: any }[] = [
        { id: 'info', label: 'Info', icon: Info },
        { id: 'edit', label: 'Edit', icon: Edit3 },
        { id: 'details', label: 'Details', icon: FileText },
    ];

    return (
        <div className="flex flex-col h-full w-96 max-h-[90vh] glass-surface rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
            {/* Header / Tab Switcher */}
            <div className="flex bg-black/20 p-1 m-3 rounded-xl backdrop-blur-md border border-white/5 relative z-10 shrink-0">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 relative ${activeTab === tab.id
                            ? 'text-white' // Active text
                            : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                            }`}
                    >
                        {activeTab === tab.id && (
                            <motion.div
                                layoutId="tab-pill"
                                className="absolute inset-0 bg-white/10 rounded-lg shadow-sm border border-white/5"
                                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            <tab.icon size={14} />
                            {tab.label}
                        </span>
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 pt-0 custom-scrollbar">
                {/* We can animate transition between tabs if we want, but simple for now */}
                {children}
            </div>
        </div>
    );
}
