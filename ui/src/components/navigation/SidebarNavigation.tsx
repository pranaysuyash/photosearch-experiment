/**
 * Sidebar Navigation Component
 *
 * Provides navigation links to various features including the new performance dashboard
 */

import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  Search,
  Image,
  Heart,
  Film,
  Tag,
  Folder,
  Trash2,
  Settings,
  Info,
  BarChart3,
  Terminal
} from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  current: boolean;
}

const SidebarNavigation = () => {
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(true);

  const navigation = [
    { name: 'Home', href: '/', icon: Home },
    { name: 'Search', href: '/search', icon: Search },
    { name: 'Albums', href: '/albums', icon: Image },
    { name: 'Favorites', href: '/favorites', icon: Heart },
    { name: 'Videos', href: '/videos', icon: Film },
    { name: 'Tags', href: '/tags', icon: Tag },
    { name: 'Trash', href: '/trash', icon: Trash2 },
    { name: 'Sources', href: '/sources', icon: Folder },
    { name: 'Saved Searches', href: '/saved-searches', icon: Terminal },
    { name: 'Performance', href: '/performance', icon: BarChart3 },
    { name: 'Jobs', href: '/jobs', icon: Settings },
    { name: 'Settings', href: '/settings', icon: Settings },
    { name: 'About', href: '/about', icon: Info },
  ];

  // Determine current nav item
  const navItems: NavItem[] = navigation.map(item => ({
    ...item,
    icon: item.icon,
    current: location.pathname === item.href
  }));

  return (
    <div className={`bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ${isExpanded ? 'w-64' : 'w-20'}`}>
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <span className="sr-only">Toggle sidebar</span>
            <div className="flex items-center justify-between">
              {isExpanded && <span className="text-xl font-bold text-blue-600 dark:text-blue-400">PhotoSearch</span>}
            </div>
          </button>
        </div>

        <nav className="flex-1 px-2 py-4">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    item.current
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-white'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  } group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200`}
                >
                  <Icon
                    className={`${
                      item.current
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-300'
                    } mr-3 h-5 w-5 flex-shrink-0`}
                    aria-hidden="true"
                  />
                  {isExpanded && <span>{item.name}</span>}
                </Link>
              );
            })}
          </div>
        </nav>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="bg-gray-200 dark:bg-gray-600 border-2 border-dashed rounded-xl w-8 h-8" />
            {isExpanded && (
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-200">User</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Admin</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SidebarNavigation;
