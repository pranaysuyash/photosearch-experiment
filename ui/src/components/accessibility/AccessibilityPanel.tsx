/**
 * Accessibility Settings Component
 *
 * Provides controls for accessibility features like high contrast,
 * reduced motion, and keyboard navigation preferences.
 */
import { useState, useEffect } from 'react';
import { 
  Accessibility,
  Contrast,
  Moon,
  Monitor,
  Volume2,
  Palette,
  Keyboard,
  MousePointer
} from 'lucide-react';
import { glass } from '../../design/glass';

interface AccessibilitySettings {
  highContrast: boolean;
  reducedMotion: boolean;
  keyboardNavigation: boolean;
  fontSize: 'normal' | 'large' | 'largest';
  focusIndicator: 'default' | 'thick' | 'border';
  screenReaderFriendly: boolean;
  altTextSuggestions: boolean;
}

export function AccessibilityPanel() {
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    // Load settings from localStorage or defaults
    const saved = localStorage.getItem('accessibility-settings');
    if (saved) {
      return JSON.parse(saved);
    }
    return {
      highContrast: false,
      reducedMotion: false,
      keyboardNavigation: true,
      fontSize: 'normal',
      focusIndicator: 'default',
      screenReaderFriendly: true,
      altTextSuggestions: true
    };
  });
  
  const [showHelp, setShowHelp] = useState(false);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('accessibility-settings', JSON.stringify(settings));
    
    // Apply settings to document
    document.body.classList.toggle('high-contrast', settings.highContrast);
    document.body.classList.toggle('reduced-motion', settings.reducedMotion);
    document.documentElement.style.setProperty('--font-size-multiplier', 
      settings.fontSize === 'large' ? '1.2' : 
      settings.fontSize === 'largest' ? '1.5' : '1.0');
    document.documentElement.style.setProperty('--focus-indicator-width', 
      settings.focusIndicator === 'thick' ? '3px' : 
      settings.focusIndicator === 'border' ? '2px solid' : '2px');
  }, [settings]);

  const updateSetting = (key: keyof AccessibilitySettings, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const resetSettings = () => {
    const defaultSettings: AccessibilitySettings = {
      highContrast: false,
      reducedMotion: false,
      keyboardNavigation: true,
      fontSize: 'normal',
      focusIndicator: 'default',
      screenReaderFriendly: true,
      altTextSuggestions: true
    };
    
    setSettings(defaultSettings);
    localStorage.removeItem('accessibility-settings');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Accessibility className="text-foreground" size={28} />
          <div>
            <h1 className="text-2xl font-bold text-foreground">Accessibility</h1>
            <p className="text-sm text-muted-foreground">
              Customize settings to make the application easier to use
            </p>
          </div>
        </div>
        
        <button
          onClick={resetSettings}
          className="btn-glass btn-glass--muted text-sm px-3 py-2 flex items-center gap-2"
        >
          <Palette size={16} />
          Reset Defaults
        </button>
      </div>
      
      {/* Visual Adjustments */}
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-4">
          <Contrast size={20} className="text-foreground" />
          <h2 className="text-lg font-semibold text-foreground">Visual Adjustments</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-foreground flex items-center gap-2">
                <Monitor size={16} />
                High Contrast Mode
              </div>
              <p className="text-xs text-muted-foreground">Increase contrast between text and background</p>
            </div>
            <button
              onClick={() => updateSetting('highContrast', !settings.highContrast)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                settings.highContrast 
                  ? 'bg-primary' 
                  : 'bg-white/10'
              }`}
            >
              <div 
                className={`bg-white w-4 h-4 rounded-full transition-transform ${
                  settings.highContrast ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-foreground flex items-center gap-2">
                <Moon size={16} />
                Reduced Motion
              </div>
              <p className="text-xs text-muted-foreground">Minimize animations and transitions</p>
            </div>
            <button
              onClick={() => updateSetting('reducedMotion', !settings.reducedMotion)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                settings.reducedMotion 
                  ? 'bg-primary' 
                  : 'bg-white/10'
              }`}
            >
              <div 
                className={`bg-white w-4 h-4 rounded-full transition-transform ${
                  settings.reducedMotion ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
          
          <div>
            <div className="font-medium text-foreground flex items-center gap-2 mb-2">
              <MousePointer size={16} />
              Focus Indicator Style
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(['default', 'thick', 'border'] as const).map(option => (
                <button
                  key={option}
                  onClick={() => updateSetting('focusIndicator', option)}
                  className={`btn-glass py-2 text-sm ${
                    settings.focusIndicator === option 
                      ? 'btn-glass--primary' 
                      : 'btn-glass--muted'
                  }`}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <div className="font-medium text-foreground flex items-center gap-2 mb-2">
              <Keyboard size={16} />
              Text Size
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(['normal', 'large', 'largest'] as const).map(size => (
                <button
                  key={size}
                  onClick={() => updateSetting('fontSize', size)}
                  className={`btn-glass py-2 text-sm ${
                    settings.fontSize === size 
                      ? 'btn-glass--primary' 
                      : 'btn-glass--muted'
                  }`}
                >
                  {size.charAt(0).toUpperCase() + size.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Navigation Preferences */}
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-4">
          <Keyboard size={20} className="text-foreground" />
          <h2 className="text-lg font-semibold text-foreground">Navigation Preferences</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-foreground flex items-center gap-2">
                <Keyboard size={16} />
                Enhanced Keyboard Navigation
              </div>
              <p className="text-xs text-muted-foreground">Improved keyboard controls and shortcuts</p>
            </div>
            <button
              onClick={() => updateSetting('keyboardNavigation', !settings.keyboardNavigation)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                settings.keyboardNavigation 
                  ? 'bg-primary' 
                  : 'bg-white/10'
              }`}
            >
              <div 
                className={`bg-white w-4 h-4 rounded-full transition-transform ${
                  settings.keyboardNavigation ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-foreground flex items-center gap-2">
                <Volume2 size={16} />
                Screen Reader Friendly Interface
              </div>
              <p className="text-xs text-muted-foreground">Optimized for assistive technologies</p>
            </div>
            <button
              onClick={() => updateSetting('screenReaderFriendly', !settings.screenReaderFriendly)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                settings.screenReaderFriendly 
                  ? 'bg-primary' 
                  : 'bg-white/10'
              }`}
            >
              <div 
                className={`bg-white w-4 h-4 rounded-full transition-transform ${
                  settings.screenReaderFriendly ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-foreground flex items-center gap-2">
                <Accessibility size={16} />
                Alt Text Suggestions
              </div>
              <p className="text-xs text-muted-foreground">Auto-generate alternative text for images</p>
            </div>
            <button
              onClick={() => updateSetting('altTextSuggestions', !settings.altTextSuggestions)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                settings.altTextSuggestions 
                  ? 'bg-primary' 
                  : 'bg-white/10'
              }`}
            >
              <div 
                className={`bg-white w-4 h-4 rounded-full transition-transform ${
                  settings.altTextSuggestions ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      </div>
      
      {/* Accessibility Tips */}
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-3">
          <Accessibility size={20} className="text-foreground" />
          <h2 className="text-lg font-semibold text-foreground">Accessibility Tips</h2>
        </div>
        
        <div className="space-y-3 text-sm text-muted-foreground">
          <p><strong>Keyboard Shortcuts:</strong></p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><kbd className="kbd">Esc</kbd> - Close modals, cancel actions</li>
            <li><kbd className="kbd">F</kbd> - Focus search bar</li>
            <li><kbd className="kbd">←</kbd> <kbd className="kbd">→</kbd> - Navigate photos</li>
            <li><kbd className="kbd">Enter</kbd> - Select focused item</li>
            <li><kbd className="kbd">Ctrl</kbd>+<kbd className="kbd">+</kbd> - Zoom in</li>
            <li><kbd className="kbd">Ctrl</kbd>+<kbd className="kbd">-</kbd> - Zoom out</li>
          </ul>
          
          <div className="mt-3">
            <button 
              onClick={() => setShowHelp(!showHelp)}
              className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-2"
            >
              {showHelp ? 'Hide' : 'Show'} Additional Tips
            </button>
            
            {showHelp && (
              <div className="mt-3 p-3 rounded-lg bg-white/5 text-xs space-y-2">
                <p>• All interactive elements have visible focus indicators</p>
                <p>• Sufficient color contrast ratios meet WCAG AA standards</p>
                <p>• Alternative text is provided for all images</p>
                <p>• Page content is organized with logical heading structure</p>
                <p>• Forms have clear labels and error messages</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}