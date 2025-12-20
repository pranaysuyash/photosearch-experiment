"""
Code Splitting and Lazy Loading Configuration

This module provides configuration and support for code splitting and lazy loading
in the PhotoSearch application. While code splitting is primarily a frontend concern,
this module provides the backend configuration and API support needed.

Features:
- Configuration for code splitting chunks
- API endpoints for lazy-loaded components
- Performance monitoring for code splitting
- Documentation for frontend integration

Note: This module provides backend support. Actual code splitting would be
implemented in the frontend (React/Vue) using dynamic imports and lazy loading.

Usage:
    # Get code splitting configuration
    config = get_code_splitting_config()
    
    # Monitor performance of lazy-loaded components
    monitor_lazy_load('component_name', load_time_ms)
"""

import json
import time
from typing import Dict, List, Optional, Any, cast
from datetime import datetime

class CodeSplittingConfig:
    """Configuration for code splitting and lazy loading."""
    
    def __init__(self):
        """Initialize code splitting configuration."""
        self.config = {
            'enabled': True,
            'chunks': {
                'main': {
                    'name': 'main',
                    'description': 'Main application bundle',
                    'priority': 'high',
                    'preload': True
                },
                'search': {
                    'name': 'search',
                    'description': 'Search functionality',
                    'priority': 'medium',
                    'preload': False,
                    'lazy': True
                },
                'gallery': {
                    'name': 'gallery',
                    'description': 'Photo gallery views',
                    'priority': 'medium',
                    'preload': False,
                    'lazy': True
                },
                'editor': {
                    'name': 'editor',
                    'description': 'Photo editor',
                    'priority': 'low',
                    'preload': False,
                    'lazy': True
                },
                'admin': {
                    'name': 'admin',
                    'description': 'Admin functionality',
                    'priority': 'low',
                    'preload': False,
                    'lazy': True
                },
                'analytics': {
                    'name': 'analytics',
                    'description': 'Analytics dashboard',
                    'priority': 'low',
                    'preload': False,
                    'lazy': True
                }
            },
            'performance': {
                'monitoring_enabled': True,
                'max_load_time_warning': 1000,  # 1 second
                'max_load_time_error': 3000,   # 3 seconds
                'cache_duration_days': 30
            }
        }
    
    def get_config(self) -> Dict:
        """Get the complete code splitting configuration."""
        return self.config
    
    def get_chunk_config(self, chunk_name: str) -> Optional[Dict]:
        """Get configuration for a specific chunk."""
        return self.config['chunks'].get(chunk_name)
    
    def set_chunk_config(self, chunk_name: str, config: Dict) -> bool:
        """Update configuration for a specific chunk."""
        if chunk_name in self.config['chunks']:
            self.config['chunks'][chunk_name].update(config)
            return True
        return False
    
    def enable_code_splitting(self, enabled: bool) -> None:
        """Enable or disable code splitting."""
        self.config['enabled'] = enabled
    
    def is_code_splitting_enabled(self) -> bool:
        """Check if code splitting is enabled."""
        return self.config['enabled']


class LazyLoadMonitor:
    """Monitor performance of lazy-loaded components."""
    
    def __init__(self, storage_path: str = "lazy_load_performance.json"):
        """Initialize lazy load monitor."""
        self.storage_path = storage_path
        # component_name -> stats dict
        self.load_times: Dict[str, Dict[str, Any]] = {}
        self._load_performance_data()
    
    def _load_performance_data(self) -> None:
        """Load performance data from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                self.load_times = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.load_times = {}
    
    def _save_performance_data(self) -> None:
        """Save performance data to storage."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.load_times, f, indent=2)
    
    def record_lazy_load(
        self,
        component_name: str,
        load_time_ms: float,
        chunk_name: str = "unknown",
        success: bool = True
    ) -> None:
        """Record lazy load performance."""
        timestamp = datetime.now().isoformat()
        
        if component_name not in self.load_times:
            self.load_times[component_name] = {
                'total_loads': 0,
                'total_time_ms': 0,
                'min_time_ms': float('inf'),
                'max_time_ms': 0,
                'load_history': [],
                'chunks': {}
            }
        
        component_data = self.load_times[component_name]
        component_data['total_loads'] += 1
        component_data['total_time_ms'] += load_time_ms
        component_data['min_time_ms'] = min(component_data['min_time_ms'], load_time_ms)
        component_data['max_time_ms'] = max(component_data['max_time_ms'], load_time_ms)
        
        # Record individual load
        load_record = {
            'timestamp': timestamp,
            'load_time_ms': load_time_ms,
            'chunk': chunk_name,
            'success': success
        }
        component_data['load_history'].append(load_record)
        
        # Update chunk-specific stats
        if chunk_name not in component_data['chunks']:
            component_data['chunks'][chunk_name] = {
                'count': 0,
                'total_time_ms': 0,
                'avg_time_ms': 0
            }
        
        chunk_data = component_data['chunks'][chunk_name]
        chunk_data['count'] += 1
        chunk_data['total_time_ms'] += load_time_ms
        chunk_data['avg_time_ms'] = chunk_data['total_time_ms'] / chunk_data['count']
        
        self._save_performance_data()
    
    def get_performance_stats(self, component_name: str | None = None) -> Dict[str, Any]:
        """Get performance statistics for lazy-loaded components."""
        if component_name:
            if component_name in self.load_times:
                data = self.load_times[component_name]
                avg_time = data['total_time_ms'] / data['total_loads'] if data['total_loads'] > 0 else 0
                
                return {
                    'component': component_name,
                    'total_loads': data['total_loads'],
                    'avg_load_time_ms': round(avg_time, 2),
                    'min_load_time_ms': round(data['min_time_ms'], 2),
                    'max_load_time_ms': round(data['max_time_ms'], 2),
                    'chunks': data['chunks'],
                    'recent_loads': data['load_history'][-10:]  # Last 10 loads
                }
            return {'error': 'Component not found'}
        
        # Return overall statistics
        total_loads = sum(data['total_loads'] for data in self.load_times.values())
        total_time = sum(data['total_time_ms'] for data in self.load_times.values())
        avg_time = total_time / total_loads if total_loads > 0 else 0
        
        # Get slowest components
        slow_components = []
        for name, data in self.load_times.items():
            if data['total_loads'] > 0:
                avg = data['total_time_ms'] / data['total_loads']
                slow_components.append((name, avg))
        
        slow_components.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_components': len(self.load_times),
            'total_loads': total_loads,
            'avg_load_time_ms': round(avg_time, 2),
            'slowest_components': slow_components[:5],
            'components': list(self.load_times.keys())
        }
    
    def get_chunk_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics by chunk."""
        chunk_stats: Dict[str, Dict[str, Any]] = {}
        
        for component_name, component_data in self.load_times.items():
            for chunk_name, chunk_data in component_data['chunks'].items():
                if chunk_name not in chunk_stats:
                    chunk_stats[chunk_name] = {
                        'components': [],
                        'total_loads': 0,
                        'total_time_ms': 0.0,
                        'avg_time_ms': 0.0,
                    }

                stats = chunk_stats[chunk_name]
                components = cast(List[str], stats['components'])
                components.append(component_name)

                # Keep numeric fields well-typed
                stats['total_loads'] = int(stats.get('total_loads', 0)) + int(chunk_data.get('count', 0))
                stats['total_time_ms'] = float(stats.get('total_time_ms', 0.0)) + float(chunk_data.get('total_time_ms', 0.0))
        
        # Calculate averages
        for _chunk_name, stats in chunk_stats.items():
            total_loads = int(stats.get('total_loads', 0))
            total_time = float(stats.get('total_time_ms', 0.0))
            stats['avg_time_ms'] = (total_time / total_loads) if total_loads > 0 else 0.0
        
        return chunk_stats


# Backwards-compatible name used by server imports
class LazyLoadPerformanceTracker(LazyLoadMonitor):
    """Compatibility alias for legacy name LazyLoadPerformanceTracker."""
    pass


def get_code_splitting_config() -> Dict:
    """Get code splitting configuration for frontend use."""
    config = CodeSplittingConfig()
    return config.get_config()


def get_lazy_load_performance() -> Dict:
    """Get lazy load performance statistics."""
    monitor = LazyLoadMonitor()
    return monitor.get_performance_stats()


def get_chunk_performance() -> Dict:
    """Get performance statistics by chunk."""
    monitor = LazyLoadMonitor()
    return monitor.get_chunk_performance()


def get_frontend_integration_guide() -> Dict:
    """Get integration guide for frontend code splitting."""
    return {
        'description': 'Code Splitting Integration Guide for PhotoSearch',
        'frontend_frameworks': ['React', 'Vue', 'Svelte', 'Angular'],
        'implementation_examples': {
            'react': """
            // React example using React.lazy and Suspense
            import React, { lazy, Suspense } from 'react';
            
            // Lazy load the search component
            const SearchComponent = lazy(() => import('./SearchComponent'));
            
            function App() {
                return (
                    <div>
                        <Suspense fallback={<div>Loading search...</div>}>
                            <SearchComponent />
                        </Suspense>
                    </div>
                );
            }
            """,
            'vue': """
            // Vue example using dynamic imports
            <template>
                <component 
                    :is="currentComponent" 
                    v-if="currentComponent"
                />
                <div v-else>Loading component...</div>
            </template>
            
            <script>
            export default {
                data() {
                    return {
                        currentComponent: null
                    }
                },
                async mounted() {
                    // Lazy load the gallery component
                    const GalleryComponent = await import('./GalleryComponent.vue');
                    this.currentComponent = GalleryComponent.default;
                }
            }
            </script>
            """,
            'webpack': """
            // Webpack configuration for code splitting
            module.exports = {
                optimization: {
                    splitChunks: {
                        chunks: 'all',
                        cacheGroups: {
                            search: {
                                test: /[\\/]src[\\/]components[\\/]search[\\/]/,
                                name: 'search',
                                chunks: 'all'
                            },
                            gallery: {
                                test: /[\\/]src[\\/]components[\\/]gallery[\\/]/,
                                name: 'gallery',
                                chunks: 'all'
                            }
                        }
                    }
                }
            };
            """
        },
        'best_practices': [
            'Use code splitting for large components that are not immediately needed',
            'Preload critical chunks to improve perceived performance',
            'Monitor lazy load performance and optimize slow chunks',
            'Use loading indicators during lazy loading',
            'Consider error boundaries for failed lazy loads',
            'Test code splitting in production-like environments'
        ],
        'performance_targets': {
            'ideal_load_time_ms': 300,
            'acceptable_load_time_ms': 1000,
            'needs_optimization_load_time_ms': 2000
        }
    }


def get_api_endpoints() -> Dict:
    """Get API endpoints related to code splitting."""
    return {
        'endpoints': [
            {
                'path': '/api/code-splitting/config',
                'method': 'GET',
                'description': 'Get code splitting configuration',
                'response': {
                    'chunks': 'List of available chunks',
                    'preload_strategy': 'Strategy for preloading chunks'
                }
            },
            {
                'path': '/api/lazy-load/performance',
                'method': 'GET',
                'description': 'Get lazy load performance statistics',
                'response': {
                    'component_stats': 'Performance by component',
                    'chunk_stats': 'Performance by chunk',
                    'recommendations': 'Optimization recommendations'
                }
            },
            {
                'path': '/api/lazy-load/monitor',
                'method': 'POST',
                'description': 'Record lazy load performance',
                'request': {
                    'component': 'Component name',
                    'chunk': 'Chunk name',
                    'load_time_ms': 'Load time in milliseconds',
                    'success': 'Whether load was successful'
                },
                'response': {
                    'status': 'Recording status',
                    'message': 'Additional information'
                }
            }
        ]
    }


def main():
    """CLI interface for code splitting configuration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Splitting Configuration')
    parser.add_argument('--config', action='store_true', help='Show code splitting config')
    parser.add_argument('--performance', action='store_true', help='Show lazy load performance')
    parser.add_argument('--chunks', action='store_true', help='Show chunk performance')
    parser.add_argument('--guide', action='store_true', help='Show frontend integration guide')
    parser.add_argument('--api', action='store_true', help='Show API endpoints')
    
    args = parser.parse_args()
    
    if args.config:
        config = get_code_splitting_config()
        print("Code Splitting Configuration:")
        print("=" * 60)
        print(f"Enabled: {config['enabled']}")
        print(f"\nConfigured Chunks ({len(config['chunks'])}):")
        for chunk_name, chunk_config in config['chunks'].items():
            print(f"  {chunk_name}:")
            print(f"    Description: {chunk_config['description']}")
            print(f"    Priority: {chunk_config['priority']}")
            print(f"    Preload: {chunk_config['preload']}")
            print(f"    Lazy: {chunk_config.get('lazy', False)}")
    
    elif args.performance:
        performance = get_lazy_load_performance()
        print("Lazy Load Performance:")
        print("=" * 60)
        print(f"Total Components: {performance['total_components']}")
        print(f"Total Loads: {performance['total_loads']}")
        print(f"Average Load Time: {performance['avg_load_time_ms']}ms")
        
        if performance['slowest_components']:
            print(f"\nSlowest Components:")
            for name, avg_time in performance['slowest_components']:
                print(f"  {name}: {round(avg_time, 2)}ms")
    
    elif args.chunks:
        chunk_perf = get_chunk_performance()
        print("Chunk Performance:")
        print("=" * 60)
        
        for chunk_name, stats in chunk_perf.items():
            print(f"\n{chunk_name}:")
            print(f"  Components: {len(stats['components'])}")
            print(f"  Total Loads: {stats['total_loads']}")
            print(f"  Avg Load Time: {round(stats['avg_time_ms'], 2)}ms")
            print(f"  Components: {', '.join(stats['components'][:5])}")
    
    elif args.guide:
        guide = get_frontend_integration_guide()
        print("Frontend Integration Guide:")
        print("=" * 60)
        print(f"Description: {guide['description']}")
        print(f"\nSupported Frameworks: {', '.join(guide['frontend_frameworks'])}")
        
        print(f"\nBest Practices:")
        for i, practice in enumerate(guide['best_practices'], 1):
            print(f"  {i}. {practice}")
        
        print(f"\nPerformance Targets:")
        for target, value in guide['performance_targets'].items():
            print(f"  {target}: {value}ms")
    
    elif args.api:
        endpoints = get_api_endpoints()
        print("Code Splitting API Endpoints:")
        print("=" * 60)
        
        for endpoint in endpoints['endpoints']:
            print(f"\n{endpoint['method']} {endpoint['path']}")
            print(f"  Description: {endpoint['description']}")
            print(f"  Response: {endpoint['response']}")
    
    else:
        print("Code Splitting and Lazy Loading Configuration")
        print("=" * 60)
        print("This module provides backend support for frontend code splitting.")
        print("Use --config, --performance, --chunks, --guide, or --api for details.")


if __name__ == "main":
    main()