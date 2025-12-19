/**
 * Mobile Navigation Component
 *
 * A responsive navigation that adapts to mobile screens with touch-friendly controls.
 */
import React, { useState } from 'react';
import { 
  Home,
  Search,
  Images,
  Video,
  Heart,
  Bookmark,
  User,
  Users,
  Map,
  Settings,
  Menu,
  X,
  Copy,
  FolderInput,
  Camera,
  FileText,
  Download,
  Share2
} from 'lucide-react';
import { glass } from '../design/glass';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
}

interface MobileNavigationProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

export function MobileNavigation({ currentPath, onNavigate }: MobileNavigationProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('main');

  const navItems: NavItem[] = [
    { id: 'home', label: 'Home', icon: <Home size={20} />, path: '/' },
    { id: 'search', label: 'Search', icon: <Search size={20} />, path: '/search' },
    { id: 'gallery', label: 'Gallery', icon: <Images size={20} />, path: '/gallery' },
    { id: 'videos', label: 'Videos', icon: <Video size={20} />, path: '/videos' },
    { id: 'favorites', label: 'Favorites', icon: <Heart size={20} />, path: '/favorites', badge: 12 },
    { id: 'collections', label: 'Collections', icon: <Bookmark size={20} />, path: '/collections' },
    { id: 'people', label: 'People', icon: <Users size={20} />, path: '/people' },
    { id: 'places', label: 'Places', icon: <Map size={20} />, path: '/places' },
    { id: 'duplicates', label: 'Duplicates', icon: <Copy size={20} />, path: '/duplicates' },
    { id: 'import', label: 'Import', icon: <FolderInput size={20} />, path: '/import' },
    { id: 'camera', label: 'Capture', icon: <Camera size={20} />, path: '/capture' },
    { id: 'notes', label: 'Notes', icon: <FileText size={20} />, path: '/notes' }
  ];

  const actionItems: NavItem[] = [
    { id: 'export', label: 'Export', icon: <Download size={16} />, path: '/export' },
    { id: 'share', label: 'Share', icon: <Share2 size={16} />, path: '/share' },
    { id: 'settings', label: 'Settings', icon: <Settings size={16} />, path: '/settings' }
  ];

  const isActive = (path: string) => currentPath === path;

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="relative">
      {/* Mobile sidebar - slides in from left */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-[2000] bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={closeSidebar}
        />
      )}
      
      <div 
        className={`fixed top-0 left-0 h-full w-64 bg-background z-[2001] transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:h-auto lg:flex ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className={`${glass.surfaceStrong} h-full flex flex-col border-r border-white/10`}>
          {/* Sidebar header */}
          <div className="p-4 border-b border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                  <img 
                    src="/logo.svg" 
                    alt="Logo" 
                    className="w-5 h-5 text-white"
                  />
                </div>
                <h2 className="font-bold text-foreground">Living Museum</h2>
              </div>
              <button 
                onClick={closeSidebar}
                className="btn-glass btn-glass--muted p-2 rounded-lg lg:hidden"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          {/* Navigation sections */}
          <div className="flex-1 p-2 overflow-y-auto">
            <div className="mb-4">
              <h3 className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Main
              </h3>
              <div className="space-y-1">
                {navItems.slice(0, 5).map(item => (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.path);
                      closeSidebar();
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      isActive(item.path)
                        ? 'bg-primary/20 text-primary'
                        : 'hover:bg-white/5 text-foreground'
                    }`}
                  >
                    <div className={`p-1.5 rounded-lg ${
                      isActive(item.path) ? 'bg-primary/10' : 'bg-white/5'
                    }`}>
                      {item.icon}
                    </div>
                    <span className="font-medium">{item.label}</span>
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-auto bg-primary text-primary-foreground text-xs rounded-full px-2 py-0.5 h-5 min-w-[20px] flex items-center justify-center">
                        {item.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="mb-4">
              <h3 className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Organization
              </h3>
              <div className="space-y-1">
                {navItems.slice(5, 8).map(item => (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.path);
                      closeSidebar();
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      isActive(item.path)
                        ? 'bg-primary/20 text-primary'
                        : 'hover:bg-white/5 text-foreground'
                    }`}
                  >
                    <div className={`p-1.5 rounded-lg ${
                      isActive(item.path) ? 'bg-primary/10' : 'bg-white/5'
                    }`}>
                      {item.icon}
                    </div>
                    <span className="font-medium">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
            
            <div className="mb-4">
              <h3 className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Management
              </h3>
              <div className="space-y-1">
                {navItems.slice(8).map(item => (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.path);
                      closeSidebar();
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      isActive(item.path)
                        ? 'bg-primary/20 text-primary'
                        : 'hover:bg-white/5 text-foreground'
                    }`}
                  >
                    <div className={`p-1.5 rounded-lg ${
                      isActive(item.path) ? 'bg-primary/10' : 'bg-white/5'
                    }`}>
                      {item.icon}
                    </div>
                    <span className="font-medium">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          {/* Action section */}
          <div className="p-2 border-t border-white/10">
            <div className="space-y-1">
              {actionItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.path);
                    closeSidebar();
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                    isActive(item.path)
                      ? 'bg-primary/20 text-primary'
                      : 'hover:bg-white/5 text-foreground'
                  }`}
                >
                  <div className={`p-1.5 rounded-lg ${
                    isActive(item.path) ? 'bg-primary/10' : 'bg-white/5'
                  }`}>
                    {item.icon}
                  </div>
                  <span className="font-medium">{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile bottom navigation bar */}
      <div className="fixed bottom-0 left-0 right-0 z-[1000] lg:hidden">
        <div className={`${glass.surface} border-t border-white/10`}>
          <div className="flex justify-around items-center p-2">
            {navItems.slice(0, 4).map(item => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.path)}
                className={`flex flex-col items-center gap-1 p-2 rounded-lg flex-1 ${
                  isActive(item.path) ? 'text-primary' : 'text-foreground/70'
                }`}
              >
                <div className={`p-2 rounded-lg ${
                  isActive(item.path) ? 'bg-primary/10' : 'bg-transparent'
                }`}>
                  {item.icon}
                </div>
                <span className="text-xs">{item.label}</span>
              </button>
            ))}
            
            <button
              onClick={toggleSidebar}
              className="flex flex-col items-center gap-1 p-2 rounded-lg flex-1 text-foreground/70"
            >
              <div className="p-2 rounded-lg bg-white/5">
                <Menu size={20} />
              </div>
              <span className="text-xs">More</span>
            </button>
          </div>
        </div>
      </div>
      
      {/* Toggle button for sidebar on desktop */}
      <div className="hidden lg:block absolute top-4 left-4 z-[1001]">
        <button
          onClick={toggleSidebar}
          className="btn-glass btn-glass--primary p-3 rounded-xl"
          aria-label={sidebarOpen ? "Close menu" : "Open menu"}
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
    </div>
  );
}