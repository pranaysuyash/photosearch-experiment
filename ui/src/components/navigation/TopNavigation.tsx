/**
 * Top Navigation Bar Component
 *
 * Provides navigation links to various features including the new performance dashboard
 */

import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home as HomeIcon,
  Search as SearchIcon,
  Image as PhotoIcon,
  Heart as HeartIcon,
  Film as VideoCameraIcon,
  Tag as TagIcon,
  Folder as FolderIcon,
  Trash2 as TrashIcon,
  Settings as CogIcon,
  Info as InformationCircleIcon,
  BarChart3 as ChartBarIcon,
  Command as CommandLineIcon,
  Menu as MenuIcon
} from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  current: boolean;
}

const TopNavigation = () => {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const navigation = [
    { name: 'Home', href: '/', icon: HomeIcon },
    { name: 'Search', href: '/search', icon: SearchIcon },
    { name: 'Albums', href: '/albums', icon: PhotoIcon },
    { name: 'Favorites', href: '/favorites', icon: HeartIcon },
    { name: 'Videos', href: '/videos', icon: VideoCameraIcon },
    { name: 'Tags', href: '/tags', icon: TagIcon },
    { name: 'Trash', href: '/trash', icon: TrashIcon },
    { name: 'Sources', href: '/sources', icon: FolderIcon },
    { name: 'Saved Searches', href: '/saved-searches', icon: CommandLineIcon },
    { name: 'Performance', href: '/performance', icon: ChartBarIcon },
    { name: 'Jobs', href: '/jobs', icon: CogIcon },
    { name: 'Settings', href: '/settings', icon: CogIcon },
    { name: 'About', href: '/about', icon: InformationCircleIcon },
  ];

  // Determine current nav item
  const navItems: NavItem[] = navigation.map(item => ({
    ...item,
    icon: item.icon,
    current: location.pathname === item.href
  }));

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0 flex items-center">
              <span className="text-xl font-bold text-blue-600 dark:text-blue-400">PhotoSearch</span>
            </div>
            <nav className="hidden md:ml-6 md:flex md:space-x-4">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`${
                      item.current
                        ? 'bg-gray-100 text-blue-800 dark:bg-gray-700 dark:text-white'
                        : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                    } group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200`}
                  >
                    <Icon
                      className={`${
                        item.current
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-300'
                      } mr-2 h-4 w-4 flex-shrink-0`}
                      aria-hidden="true"
                    />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center md:hidden">
            {/* Mobile menu button */}
            <button
              type="button"
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-expanded="false"
            >
              <span className="sr-only">Open main menu</span>
              <MenuIcon className="block h-6 w-6" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu, show/hide based on menu state */}
      {isMenuOpen && (
        <div className="md:hidden">
          <div className="pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    item.current
                      ? 'bg-blue-50 border-blue-500 text-blue-700 dark:bg-blue-900/50 dark:border-blue-900 dark:text-white'
                      : 'border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'
                  } group flex items-center px-4 py-2 text-base font-medium border-l-4`}
                >
                  <Icon
                    className={`${
                      item.current
                        ? 'text-blue-500 dark:text-blue-400'
                        : 'text-gray-400 group-hover:text-gray-500 dark:text-gray-400 dark:group-hover:text-gray-300'
                    } mr-3 h-5 w-5 flex-shrink-0`}
                    aria-hidden="true"
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
};

export default TopNavigation;
