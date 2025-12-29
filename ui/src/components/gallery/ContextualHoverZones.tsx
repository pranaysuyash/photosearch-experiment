import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Search,
  Edit3,
  Share,
  MapPin,
  Zap
} from 'lucide-react';
import type { Photo } from '../../api';

interface ContextualHoverZonesProps {
  photo: Photo;
  onAction: (action: string, data?: unknown) => void;
  children: React.ReactNode;
}

interface HoverZone {
  id: string;
  area: { x: number; y: number; width: number; height: number };
  action: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  color: string;
}

export const ContextualHoverZones: React.FC<ContextualHoverZonesProps> = ({
  photo,
  onAction,
  children
}) => {
  const [activeZone, setActiveZone] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Define hover zones based on photo content
  const hoverZones: HoverZone[] = [
    // Top-left: People detection
    {
      id: 'people',
      area: { x: 0, y: 0, width: 30, height: 30 },
      action: 'find-people',
      icon: Users,
      label: 'Find all photos of this person',
      color: 'bg-blue-500'
    },
    // Top-right: Quick actions
    {
      id: 'actions',
      area: { x: 70, y: 0, width: 30, height: 30 },
      action: 'quick-actions',
      icon: Zap,
      label: 'Quick actions',
      color: 'bg-purple-500'
    },
    // Bottom-left: Location
    {
      id: 'location',
      area: { x: 0, y: 70, width: 30, height: 30 },
      action: 'show-location',
      icon: MapPin,
      label: 'Show on map',
      color: 'bg-green-500'
    },
    // Bottom-right: Similar photos
    {
      id: 'similar',
      area: { x: 70, y: 70, width: 30, height: 30 },
      action: 'find-similar',
      icon: Search,
      label: 'Find similar photos',
      color: 'bg-orange-500'
    },
    // Center-left: Edit
    {
      id: 'edit',
      area: { x: 0, y: 35, width: 20, height: 30 },
      action: 'edit-photo',
      icon: Edit3,
      label: 'Edit photo',
      color: 'bg-red-500'
    },
    // Center-right: Share
    {
      id: 'share',
      area: { x: 80, y: 35, width: 20, height: 30 },
      action: 'share-photo',
      icon: Share,
      label: 'Share photo',
      color: 'bg-cyan-500'
    }
  ];

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    setMousePos({ x: e.clientX, y: e.clientY });

    // Check which zone we're in
    const zone = hoverZones.find(z =>
      x >= z.area.x && x <= z.area.x + z.area.width &&
      y >= z.area.y && y <= z.area.y + z.area.height
    );

    setActiveZone(zone?.id || null);
  };

  const handleZoneClick = (zone: HoverZone) => {
    onAction(zone.action, { photo, zone });
  };

  return (
    <div
      ref={containerRef}
      className="relative group cursor-pointer"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setActiveZone(null)}
    >
      {children}

      {/* Invisible hover zones */}
      {hoverZones.map(zone => (
        <div
          key={zone.id}
          className="absolute opacity-0 hover:opacity-10 transition-opacity"
          style={{
            left: `${zone.area.x}%`,
            top: `${zone.area.y}%`,
            width: `${zone.area.width}%`,
            height: `${zone.area.height}%`,
          }}
          onClick={() => handleZoneClick(zone)}
        />
      ))}

      {/* Active zone indicator */}
      <AnimatePresence>
        {activeZone && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="fixed z-50 pointer-events-none"
            style={{
              left: mousePos.x + 10,
              top: mousePos.y - 40
            }}
          >
            <div className="glass-surface rounded-lg px-3 py-2 flex items-center gap-2 shadow-xl">
              {(() => {
                const zone = hoverZones.find(z => z.id === activeZone);
                if (!zone) return null;
                const Icon = zone.icon;
                return (
                  <>
                    <div className={`w-2 h-2 rounded-full ${zone.color}`} />
                    <Icon size={14} className="text-white/80" />
                    <span className="text-sm text-white/90">{zone.label}</span>
                  </>
                );
              })()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
