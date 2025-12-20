"""
Custom Electron Protocols

This module provides custom protocol handlers for Electron desktop app integration.
These protocols enable secure file access and custom URL schemes for the desktop version.

Features:
- Custom protocol registration (e.g., photosearch://)
- Secure file access protocols
- Protocol-based navigation
- Deep linking support
- Integration with Electron's protocol handlers

Note: This is a backend implementation that would be used with an Electron frontend.
The actual Electron integration would need to be implemented in the Electron main process.

Usage:
    protocol_handler = ElectronProtocolHandler()
    
    # Register custom protocols
    protocol_handler.register_protocols()
    
# Handle protocol requests
response = protocol_handler.handle_request('photosearch://images/123')
"""

import os
import json
import urllib.parse
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import mimetypes

class ElectronProtocolHandler:
    """Handle custom Electron protocols and secure file access."""
    
    def __init__(self, base_dir: str = "/"):
        """
        Initialize protocol handler.
        
        Args:
            base_dir: Base directory for file access (defaults to root)
        """
        self.base_dir = Path(base_dir).resolve()
        self.registered_protocols: List[str] = []
        self._initialize_protocols()
    
    def _initialize_protocols(self):
        """Initialize supported protocols."""
        # Define supported protocols
        self.supported_protocols = {
            'photosearch': {
                'description': 'PhotoSearch app protocol',
                'handler': self._handle_photosearch_protocol,
                'secure': True
            },
            'photos': {
                'description': 'Photo file access protocol',
                'handler': self._handle_photos_protocol,
                'secure': True
            },
            'search': {
                'description': 'Search protocol',
                'handler': self._handle_search_protocol,
                'secure': True
            },
            'file': {
                'description': 'Secure file access protocol',
                'handler': self._handle_file_protocol,
                'secure': True
            }
        }
    
    def register_protocols(self) -> List[str]:
        """
        Register all supported protocols.
        
        Returns:
            List of registered protocol names
        """
        for protocol_name in self.supported_protocols:
            self.registered_protocols.append(protocol_name)
        
        return self.registered_protocols
    
    def handle_request(self, url: str) -> Dict:
        """
        Handle a protocol request.
        
        Args:
            url: Full URL with protocol (e.g., 'photosearch://images/123')
            
        Returns:
            Dictionary with response data
        """
        try:
            # Parse URL
            parsed = urllib.parse.urlparse(url)
            protocol = parsed.scheme
            
            # Check if protocol is supported
            if protocol not in self.supported_protocols:
                return {
                    'status': 'error',
                    'code': 400,
                    'message': f'Unsupported protocol: {protocol}',
                    'protocol': protocol
                }
            
            # Get handler for this protocol
            handler = self.supported_protocols[protocol]['handler']
            
            # Handle the request
            return handler(parsed)
            
        except Exception as e:
            return {
                'status': 'error',
                'code': 500,
                'message': str(e),
                'protocol': protocol if 'protocol' in locals() else 'unknown'
            }
    
    def _handle_photosearch_protocol(self, parsed_url: urllib.parse.ParseResult) -> Dict:
        """
        Handle photosearch:// protocol requests.
        
        Args:
            parsed_url: Parsed URL object
            
        Returns:
            Dictionary with response data
        """
        path_parts = parsed_url.path.strip('/').split('/')
        
        if not path_parts or path_parts[0] == '':
            # Root request
            return {
                'status': 'success',
                'protocol': 'photosearch',
                'action': 'home',
                'data': {
                    'message': 'Welcome to PhotoSearch',
                    'version': '1.0.0'
                }
            }
        
        # Handle different path types
        if path_parts[0] == 'images':
            return self._handle_images_request(path_parts[1:])
        
        elif path_parts[0] == 'search':
            return self._handle_search_request(parsed_url, path_parts[1:])
        
        elif path_parts[0] == 'settings':
            return self._handle_settings_request(path_parts[1:])
        
        else:
            return {
                'status': 'error',
                'code': 404,
                'message': f'Unknown path: {parsed_url.path}',
                'protocol': 'photosearch'
            }
    
    def _handle_images_request(self, path_parts: List[str]) -> Dict:
        """
        Handle image-related requests.
        
        Args:
            path_parts: Remaining path parts after 'images/'
            
        Returns:
            Dictionary with response data
        """
        if not path_parts:
            # List all images
            return {
                'status': 'success',
                'action': 'list_images',
                'data': {
                    'images': [],  # Would be populated with actual image data
                    'count': 0
                }
            }
        
        image_id = path_parts[0]
        
        # Check if it's a specific image request
        if image_id.isdigit():
            return {
                'status': 'success',
                'action': 'get_image',
                'data': {
                    'image_id': image_id,
                    'path': f'/images/{image_id}.jpg',
                    'metadata': {}  # Would be populated with actual metadata
                }
            }
        
        # Handle sub-actions
        if len(path_parts) > 1:
            if path_parts[1] == 'metadata':
                return {
                    'status': 'success',
                    'action': 'get_image_metadata',
                    'data': {
                        'image_id': image_id,
                        'metadata': {}  # Would be populated with actual metadata
                    }
                }
            
            elif path_parts[1] == 'thumbnail':
                return {
                    'status': 'success',
                    'action': 'get_thumbnail',
                    'data': {
                        'image_id': image_id,
                        'thumbnail_path': f'/thumbnails/{image_id}.jpg'
                    }
                }
        
        return {
            'status': 'error',
            'code': 404,
            'message': f'Image not found: {image_id}'
        }
    
    def _handle_search_request(self, parsed_url: urllib.parse.ParseResult, path_parts: List[str]) -> Dict:
        """
        Handle search-related requests.
        
        Args:
            path_parts: Remaining path parts after 'search/'
            
        Returns:
            Dictionary with response data
        """
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if not path_parts:
            # Search form
            return {
                'status': 'success',
                'action': 'search_form',
                'data': {
                    'query': query_params.get('q', [''])[0],
                    'filters': {}
                }
            }
        
        # Handle search execution
        query = query_params.get('q', [''])[0]
        
        return {
            'status': 'success',
            'action': 'search_results',
            'data': {
                'query': query,
                'results': [],  # Would be populated with actual search results
                'count': 0,
                'suggestions': []
            }
        }
    
    def _handle_settings_request(self, path_parts: List[str]) -> Dict:
        """
        Handle settings-related requests.
        
        Args:
            path_parts: Remaining path parts after 'settings/'
            
        Returns:
            Dictionary with response data
        """
        if not path_parts:
            # Main settings
            return {
                'status': 'success',
                'action': 'settings',
                'data': {
                    'categories': ['general', 'search', 'privacy', 'advanced']
                }
            }
        
        category = path_parts[0]
        
        if category == 'general':
            return {
                'status': 'success',
                'action': 'general_settings',
                'data': {
                    'theme': 'system',
                    'language': 'en',
                    'startup_behavior': 'home'
                }
            }
        
        elif category == 'search':
            return {
                'status': 'success',
                'action': 'search_settings',
                'data': {
                    'default_mode': 'hybrid',
                    'results_per_page': 50,
                    'enable_intent_detection': True
                }
            }
        
        return {
            'status': 'error',
            'code': 404,
            'message': f'Settings category not found: {category}'
        }
    
    def _handle_photos_protocol(self, parsed_url: urllib.parse.ParseResult) -> Dict:
        """
        Handle photos:// protocol for secure file access.
        
        Args:
            parsed_url: Parsed URL object
            
        Returns:
            Dictionary with response data
        """
        # Extract path from URL
        file_path = parsed_url.path.lstrip('/')
        
        # Security check: ensure path is within allowed directory
        if not self._is_path_allowed(file_path):
            return {
                'status': 'error',
                'code': 403,
                'message': 'Access denied: Path outside allowed directory',
                'protocol': 'photos'
            }
        
        # Check if file exists
        full_path = self.base_dir / file_path
        
        if not full_path.exists():
            return {
                'status': 'error',
                'code': 404,
                'message': 'File not found',
                'protocol': 'photos'
            }
        
        # Check if it's a file
        if not full_path.is_file():
            return {
                'status': 'error',
                'code': 400,
                'message': 'Path is not a file',
                'protocol': 'photos'
            }
        
        # Get file info
        file_size = full_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(full_path))
        
        return {
            'status': 'success',
            'protocol': 'photos',
            'action': 'file_access',
            'data': {
                'path': str(full_path),
                'size': file_size,
                'mime_type': mime_type or 'application/octet-stream',
                'exists': True,
                'readable': True,
                'writable': os.access(str(full_path), os.W_OK)
            }
        }
    
    def _handle_search_protocol(self, parsed_url: urllib.parse.ParseResult) -> Dict:
        """
        Handle search:// protocol for search functionality.
        
        Args:
            parsed_url: Parsed URL object
            
        Returns:
            Dictionary with response data
        """
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query = query_params.get('q', [''])[0]
        mode = query_params.get('mode', ['hybrid'])[0]
        
        return {
            'status': 'success',
            'protocol': 'search',
            'action': 'execute_search',
            'data': {
                'query': query,
                'mode': mode,
                'results': [],  # Would be populated with actual results
                'intent': None  # Would be populated with intent detection
            }
        }
    
    def _handle_file_protocol(self, parsed_url: urllib.parse.ParseResult) -> Dict:
        """
        Handle file:// protocol with enhanced security.
        
        Args:
            parsed_url: Parsed URL object
            
        Returns:
            Dictionary with response data
        """
        # Extract path from URL
        file_path = parsed_url.path
        
        # Security check: ensure path is within allowed directory
        if not self._is_path_allowed(file_path):
            return {
                'status': 'error',
                'code': 403,
                'message': 'Access denied: Path outside allowed directory',
                'protocol': 'file'
            }
        
        # Check if file exists
        full_path = Path(file_path)
        
        if not full_path.exists():
            return {
                'status': 'error',
                'code': 404,
                'message': 'File not found',
                'protocol': 'file'
            }
        
        # Get file info
        file_size = full_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(full_path))
        
        return {
            'status': 'success',
            'protocol': 'file',
            'action': 'file_info',
            'data': {
                'path': str(full_path),
                'size': file_size,
                'mime_type': mime_type or 'application/octet-stream',
                'exists': True,
                'readable': True,
                'writable': os.access(str(full_path), os.W_OK)
            }
        }
    
    def _is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is within the allowed directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        try:
            # Convert to absolute path
            full_path = Path(path).resolve()
            
            # Check if path is within base directory
            return str(full_path).startswith(str(self.base_dir))
            
        except Exception:
            return False
    
    def generate_deep_link(self, action: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Generate a deep link URL for the application.
        
        Args:
            action: Action type (e.g., 'search', 'view_image')
            params: Dictionary of parameters
            
        Returns:
            Deep link URL
        """
        if params is None:
            params = {}
        
        if action == 'search':
            query = params.get('query', '')
            mode = params.get('mode', 'hybrid')
            return f'photosearch://search?q={urllib.parse.quote(query)}&mode={mode}'
        
        elif action == 'view_image':
            image_id = params.get('image_id', '')
            return f'photosearch://images/{image_id}'
        
        elif action == 'settings':
            category = params.get('category', '')
            return f'photosearch://settings/{category}'
        
        else:
            return f'photosearch://{action}'
    
    def parse_deep_link(self, url: str) -> Dict:
        """
        Parse a deep link URL.
        
        Args:
            url: Deep link URL
            
        Returns:
            Dictionary with parsed data
        """
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Parse query parameters
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Clean up query parameters (convert single-item lists to strings)
            clean_params: Dict[str, object] = {}
            for key, value in query_params.items():
                if len(value) == 1:
                    clean_params[key] = value[0]
                else:
                    clean_params[key] = value
            
            return {
                'protocol': parsed.scheme,
                'path': parsed.path,
                'action': parsed.path.strip('/').split('/')[0] if parsed.path else 'home',
                'params': clean_params,
                'fragment': parsed.fragment
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'url': url
            }
    
    def get_protocol_registration_info(self) -> Dict:
        """
        Get information needed to register protocols in Electron.
        
        Returns:
            Dictionary with protocol registration info
        """
        return {
            'protocols': [
                {
                    'name': 'photosearch',
                    'scheme': 'photosearch',
                    'description': 'PhotoSearch App Protocol',
                    'secure': True
                },
                {
                    'name': 'photos',
                    'scheme': 'photos',
                    'description': 'Photo File Access Protocol',
                    'secure': True
                },
                {
                    'name': 'search',
                    'scheme': 'search',
                    'description': 'Search Protocol',
                    'secure': True
                }
            ],
            'registration_code': {
                'main_process': """
                // In Electron main process
                const { protocol } = require('electron')
                
                // Register protocols
                protocol.registerSchemesAsPrivileged([
                    { scheme: 'photosearch', privileges: { secure: true, standard: true } },
                    { scheme: 'photos', privileges: { secure: true, standard: true } },
                    { scheme: 'search', privileges: { secure: true, standard: true } }
                ])
                
                // Handle protocol requests
                app.on('ready', () => {
                    protocol.handle('photosearch', (request) => {
                        // Handle photosearch protocol
                    })
                    
                    protocol.handle('photos', (request) => {
                        // Handle photos protocol
                    })
                    
                    protocol.handle('search', (request) => {
                        // Handle search protocol
                    })
                })
                """,
                'renderer_process': """
                // In Electron renderer process
                // Use protocol handler for secure file access
                const response = await fetch('photos://path/to/file.jpg')
                """
            }
        }
    
    def close(self):
        """Clean up resources."""
        self.registered_protocols = []


def main():
    """CLI interface for testing protocol handler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Electron Protocol Handler')
    parser.add_argument('--url', help='Test URL to handle')
    parser.add_argument('--deep-link', help='Generate deep link')
    parser.add_argument('--parse', help='Parse deep link')
    parser.add_argument('--info', action='store_true', help='Show protocol registration info')
    
    args = parser.parse_args()
    
    handler = ElectronProtocolHandler()
    
    if args.url:
        result = handler.handle_request(args.url)
        print(f"URL: {args.url}")
        print(f"Response: {json.dumps(result, indent=2)}")
    
    elif args.deep_link:
        # Parse action and params from deep_link if it's in format action:param1=value1,param2=value2
        if ':' in args.deep_link:
            action, params_str = args.deep_link.split(':', 1)
            params = {}
            for param_pair in params_str.split(','):
                if '=' in param_pair:
                    key, value = param_pair.split('=', 1)
                    params[key] = value
        else:
            action = args.deep_link
            params = {}
        
        deep_link = handler.generate_deep_link(action, params)
        print(f"Deep Link: {deep_link}")
    
    elif args.parse:
        parsed = handler.parse_deep_link(args.parse)
        print(f"Parsed Deep Link: {json.dumps(parsed, indent=2)}")
    
    elif args.info:
        info = handler.get_protocol_registration_info()
        print("Protocol Registration Information:")
        print("=" * 60)
        print(f"Protocols ({len(info['protocols'])}):")
        for protocol in info['protocols']:
            print(f"  {protocol['scheme']}: {protocol['description']}")
        
        print(f"\nMain Process Registration Code:")
        print(info['registration_code']['main_process'])
    
    else:
        # Test some example URLs
        test_urls = [
            'photosearch://',
            'photosearch://images/123',
            'photosearch://search?q=beach&mode=hybrid',
            'photos://images/vacation.jpg',
            'search://?q=family&mode=metadata'
        ]
        
        print("Testing Protocol Handler:")
        print("=" * 60)
        
        for url in test_urls:
            result = handler.handle_request(url)
            print(f"URL: {url}")
            print(f"Status: {result['status']}")
            if result['status'] == 'success':
                print(f"Action: {result.get('action', 'unknown')}")
            print("-" * 40)


if __name__ == "main":
    main()
