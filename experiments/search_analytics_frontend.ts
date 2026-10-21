/**
 * Search Analytics Frontend - Privacy-First User Behavior Tracking
 * Experimental implementation for capturing search interactions
 */

// Types for search analytics
interface SearchInteraction {
  type: 'click' | 'hover' | 'select' | 'export' | 'skip' | 'view_detail';
  photoPath: string;
  resultPosition: number; // 1-based position in search results
  timestamp: number;
  dwellTime?: number; // Time spent on interaction (ms)
  originalScore: number; // Original search relevance score
  metadata?: {
    scrollDepth?: number; // How far user scrolled before interaction
    viewportVisible?: boolean; // Was item visible when interacted with
    previousInteractions?: number; // Number of previous interactions in session
  };
}

interface SearchEvent {
  // Core search data
  query: string;
  searchMode: 'metadata' | 'semantic' | 'hybrid';
  timestamp: number;
  sessionId: string;

  // Context information
  collectionSize: number;
  resultCount: number;
  searchDuration: number; // Time from query start to results display

  // User journey
  previousQuery?: string;
  querySource: 'manual' | 'timeline' | 'suggestion' | 'refinement';

  // Results and interactions
  interactions: SearchInteraction[];

  // Performance metrics
  timeToFirstResult: number;
  timeToFirstInteraction?: number;
}

interface UserSession {
  sessionId: string;
  startTime: number;
  endTime?: number;
  totalSearches: number;
  successfulSearches: number; // Searches that led to interactions
  userType?: 'professional' | 'casual' | 'power_user';
  preferences?: {
    preferredMode?: string;
    avgQueryLength?: number;
    interactionPatterns?: string[];
  };
}

interface AnalyticsSettings {
  enabled: boolean;
  shareAggregatedData: boolean;
  personalizedRecommendations: boolean;
  dataRetentionDays: number;
  privacyLevel: 'minimal' | 'standard' | 'detailed';
}

class SearchAnalytics {
  private readonly STORAGE_KEY = 'search_analytics_v1';
  private readonly SESSION_KEY = 'search_session_v1';
  private readonly SETTINGS_KEY = 'analytics_settings_v1';
  private readonly MAX_EVENTS = 5000; // Limit local storage usage

  private currentSession: UserSession;
  private currentSearchEvent?: SearchEvent;
  private settings: AnalyticsSettings;
  private interactionObserver?: IntersectionObserver;
  private hoverTimers: Map<string, number> = new Map();

  constructor() {
    this.settings = this.loadSettings();
    this.currentSession = this.initializeSession();
    this.setupInteractionObserver();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.endSession();
    });
  }

  private loadSettings(): AnalyticsSettings {
    const stored = localStorage.getItem(this.SETTINGS_KEY);
    if (stored) {
      return JSON.parse(stored);
    }

    // Default settings - privacy-first
    return {
      enabled: false, // Opt-in required
      shareAggregatedData: false,
      personalizedRecommendations: false,
      dataRetentionDays: 30,
      privacyLevel: 'standard'
    };
  }

  private initializeSession(): UserSession {
    const stored = sessionStorage.getItem(this.SESSION_KEY);
    if (stored) {
      const session = JSON.parse(stored);
      return {
        ...session,
        // Update session activity
        endTime: Date.now()
      };
    }

    // Create new session
    const session: UserSession = {
      sessionId: this.generateSessionId(),
      startTime: Date.now(),
      totalSearches: 0,
      successfulSearches: 0
    };

    this.saveSession(session);
    return session;
  }

  private generateSessionId(): string {
    // Generate privacy-preserving session ID
    const timestamp = Date.now().toString();
    const random = Math.random().toString(36).substring(2);
    return `session_${timestamp}_${random}`;
  }

  private setupInteractionObserver() {
    // Observe when search result items come into view
    this.interactionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const element = entry.target as HTMLElement;
          const photoPath = element.dataset.photoPath;
          const position = parseInt(element.dataset.position || '0');

          if (entry.isIntersecting && photoPath) {
            // Item became visible
            this.trackInteraction({
              type: 'skip', // Will be updated if user actually interacts
              photoPath,
              resultPosition: position,
              timestamp: Date.now(),
              originalScore: parseFloat(element.dataset.score || '0'),
              metadata: {
                viewportVisible: true,
                scrollDepth: window.scrollY
              }
            });
          }
        });
      },
      { threshold: 0.5 } // Item is 50% visible
    );
  }

  // Public API Methods

  updateSettings(newSettings: Partial<AnalyticsSettings>) {
    this.settings = { ...this.settings, ...newSettings };
    localStorage.setItem(this.SETTINGS_KEY, JSON.stringify(this.settings));
  }

  startSearch(query: string, mode: 'metadata' | 'semantic' | 'hybrid', context?: {
    previousQuery?: string;
    querySource?: string;
    collectionSize?: number;
  }) {
    if (!this.settings.enabled) return;

    const searchStartTime = Date.now();

    this.currentSearchEvent = {
      query: this.anonymizeQuery(query),
      searchMode: mode,
      timestamp: searchStartTime,
      sessionId: this.currentSession.sessionId,
      collectionSize: context?.collectionSize || 0,
      resultCount: 0, // Will be updated when results arrive
      searchDuration: 0, // Will be calculated when results arrive
      previousQuery: context?.previousQuery ? this.anonymizeQuery(context.previousQuery) : undefined,
      querySource: context?.querySource as any || 'manual',
      interactions: [],
      timeToFirstResult: 0
    };

    // Update session stats
    this.currentSession.totalSearches++;
    this.saveSession(this.currentSession);
  }

  completeSearch(results: any[], searchDuration: number) {
    if (!this.settings.enabled || !this.currentSearchEvent) return;

    this.currentSearchEvent.resultCount = results.length;
    this.currentSearchEvent.searchDuration = searchDuration;
    this.currentSearchEvent.timeToFirstResult = searchDuration;

    // Observe search result elements for interaction tracking
    this.observeSearchResults();
  }

  trackInteraction(interaction: Omit<SearchInteraction, 'timestamp'> & { timestamp?: number }) {
    if (!this.settings.enabled || !this.currentSearchEvent) return;

    const fullInteraction: SearchInteraction = {
      ...interaction,
      timestamp: interaction.timestamp || Date.now(),
      photoPath: this.anonymizePath(interaction.photoPath)
    };

    this.currentSearchEvent.interactions.push(fullInteraction);

    // Update time to first interaction if this is the first
    if (this.currentSearchEvent.interactions.length === 1) {
      this.currentSearchEvent.timeToFirstInteraction =
        fullInteraction.timestamp - this.currentSearchEvent.timestamp;
    }

    // Mark search as successful if user clicked or exported
    if (['click', 'select', 'export', 'view_detail'].includes(interaction.type)) {
      this.markSearchSuccessful();
    }
  }

  // Specific interaction tracking methods

  trackPhotoClick(photoPath: string, position: number, score: number) {
    this.trackInteraction({
      type: 'click',
      photoPath,
      resultPosition: position,
      originalScore: score
    });
  }

  trackPhotoHover(photoPath: string, position: number, score: number) {
    const hoverId = `${photoPath}_${position}`;
    const startTime = Date.now();

    this.hoverTimers.set(hoverId, startTime);

    // Track hover end after a delay
    setTimeout(() => {
      const endTime = Date.now();
      const dwellTime = endTime - startTime;

      if (dwellTime > 500) { // Only track meaningful hovers
        this.trackInteraction({
          type: 'hover',
          photoPath,
          resultPosition: position,
          originalScore: score,
          dwellTime
        });
      }

      this.hoverTimers.delete(hoverId);
    }, 100);
  }

  trackPhotoSelection(photoPath: string, position: number, score: number, isSelected: boolean) {
    this.trackInteraction({
      type: isSelected ? 'select' : 'skip',
      photoPath,
      resultPosition: position,
      originalScore: score
    });
  }

  trackExport(photoPaths: string[], searchQuery?: string) {
    if (!this.settings.enabled) return;

    // Track export as high-value interaction
    photoPaths.forEach((path, index) => {
      this.trackInteraction({
        type: 'export',
        photoPath: path,
        resultPosition: index + 1, // Approximate position
        originalScore: 1.0 // High value interaction
      });
    });

    this.markSearchSuccessful();
  }

  // Search completion and analysis

  endSearch() {
    if (!this.settings.enabled || !this.currentSearchEvent) return;

    // Store completed search event
    this.storeSearchEvent(this.currentSearchEvent);

    // Clean up
    this.currentSearchEvent = undefined;
    this.clearObservers();
  }

  endSession() {
    if (!this.settings.enabled) return;

    this.currentSession.endTime = Date.now();
    this.saveSession(this.currentSession);

    // Analyze session and update user preferences
    this.analyzeSession();
  }

  // Analytics and insights

  getSearchInsights(): {
    totalSearches: number;
    successRate: number;
    preferredMode: string;
    avgQueryLength: number;
    commonPatterns: string[];
  } {
    const events = this.getStoredEvents();

    if (events.length === 0) {
      return {
        totalSearches: 0,
        successRate: 0,
        preferredMode: 'metadata',
        avgQueryLength: 0,
        commonPatterns: []
      };
    }

    const successfulSearches = events.filter(e => e.interactions.some(i =>
      ['click', 'select', 'export', 'view_detail'].includes(i.type)
    ));

    const modeCount = events.reduce((acc, event) => {
      acc[event.searchMode] = (acc[event.searchMode] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const preferredMode = Object.entries(modeCount)
      .sort(([,a], [,b]) => b - a)[0]?.[0] || 'metadata';

    const avgQueryLength = events.reduce((sum, e) => sum + e.query.length, 0) / events.length;

    return {
      totalSearches: events.length,
      successRate: successfulSearches.length / events.length,
      preferredMode,
      avgQueryLength,
      commonPatterns: this.extractCommonPatterns(events)
    };
  }

  getModeRecommendation(query: string): {
    recommendedMode: string;
    confidence: number;
    reasoning: string;
  } {
    const insights = this.getSearchInsights();
    const queryFeatures = this.analyzeQuery(query);

    // Simple heuristic-based recommendation
    // In production, this would use the trained ML model

    if (queryFeatures.hasSQLOperators || queryFeatures.hasTechnicalTerms) {
      return {
        recommendedMode: 'metadata',
        confidence: 0.8,
        reasoning: 'Query contains technical terms or SQL operators'
      };
    }

    if (queryFeatures.hasEmotionalWords || queryFeatures.hasColorWords) {
      return {
        recommendedMode: 'semantic',
        confidence: 0.7,
        reasoning: 'Query describes visual or emotional content'
      };
    }

    if (queryFeatures.complexity > 0.5) {
      return {
        recommendedMode: 'hybrid',
        confidence: 0.6,
        reasoning: 'Complex query benefits from combined approach'
      };
    }

    // Fall back to user preference
    return {
      recommendedMode: insights.preferredMode,
      confidence: 0.4,
      reasoning: 'Based on your search history'
    };
  }

  // Privacy and data management

  exportData(): string {
    const data = {
      settings: this.settings,
      events: this.getStoredEvents(),
      sessions: this.getStoredSessions(),
      insights: this.getSearchInsights(),
      exportDate: new Date().toISOString()
    };

    return JSON.stringify(data, null, 2);
  }

  clearAllData() {
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.SETTINGS_KEY);
    sessionStorage.removeItem(this.SESSION_KEY);

    // Reinitialize
    this.settings = this.loadSettings();
    this.currentSession = this.initializeSession();
  }

  // Private helper methods

  private markSearchSuccessful() {
    if (this.currentSearchEvent &&
        !this.currentSearchEvent.interactions.some(i =>
          ['click', 'select', 'export', 'view_detail'].includes(i.type)
        )) {
      this.currentSession.successfulSearches++;
      this.saveSession(this.currentSession);
    }
  }

  private observeSearchResults() {
    // Find all search result elements and observe them
    const resultElements = document.querySelectorAll('[data-photo-path]');
    resultElements.forEach(element => {
      this.interactionObserver?.observe(element);
    });
  }

  private clearObservers() {
    this.interactionObserver?.disconnect();
    this.hoverTimers.clear();
  }

  private storeSearchEvent(event: SearchEvent) {
    const events = this.getStoredEvents();
    events.push(event);

    // Maintain storage limit
    if (events.length > this.MAX_EVENTS) {
      events.splice(0, events.length - this.MAX_EVENTS);
    }

    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(events));
  }

  private getStoredEvents(): SearchEvent[] {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  }

  private getStoredSessions(): UserSession[] {
    // In a real implementation, this would retrieve historical sessions
    return [this.currentSession];
  }

  private saveSession(session: UserSession) {
    sessionStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
  }

  private anonymizeQuery(query: string): string {
    if (this.settings.privacyLevel === 'minimal') {
      // Only keep query structure, not content
      return query.replace(/[a-zA-Z0-9]/g, 'X');
    }

    // Remove potentially identifying information
    return query
      .replace(/\b\d{4}-\d{2}-\d{2}\b/g, 'DATE') // Dates
      .replace(/\b[A-Z]{2,}\d+\b/g, 'SERIAL') // Serial numbers
      .replace(/\b\w+@\w+\.\w+\b/g, 'EMAIL'); // Email addresses
  }

  private anonymizePath(path: string): string {
    // Keep only relative structure, remove identifying directory names
    const parts = path.split('/');
    return parts.map((part, index) => {
      if (index === parts.length - 1) {
        // Keep filename structure but anonymize
        const ext = part.split('.').pop();
        return `file_${Math.abs(this.hashString(part))}.${ext}`;
      }
      return `dir_${index}`;
    }).join('/');
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash;
  }

  private analyzeQuery(query: string): {
    hasSQLOperators: boolean;
    hasTechnicalTerms: boolean;
    hasEmotionalWords: boolean;
    hasColorWords: boolean;
    complexity: number;
  } {
    const queryLower = query.toLowerCase();

    return {
      hasSQLOperators: /[=<>]|AND|OR|LIKE/i.test(query),
      hasTechnicalTerms: /\d+mm|f\/\d|ISO|Canon|Sony|Nikon/i.test(query),
      hasEmotionalWords: /beautiful|stunning|dramatic|peaceful|happy/i.test(queryLower),
      hasColorWords: /red|blue|green|yellow|colorful|vibrant/i.test(queryLower),
      complexity: Math.min(query.split(' ').length / 10, 1)
    };
  }

  private extractCommonPatterns(events: SearchEvent[]): string[] {
    // Extract common query patterns for insights
    const patterns = new Map<string, number>();

    events.forEach(event => {
      const features = this.analyzeQuery(event.query);

      if (features.hasTechnicalTerms) patterns.set('technical_queries', (patterns.get('technical_queries') || 0) + 1);
      if (features.hasEmotionalWords) patterns.set('emotional_queries', (patterns.get('emotional_queries') || 0) + 1);
      if (features.hasColorWords) patterns.set('color_queries', (patterns.get('color_queries') || 0) + 1);
      if (event.querySource === 'timeline') patterns.set('timeline_usage', (patterns.get('timeline_usage') || 0) + 1);
    });

    return Array.from(patterns.entries())
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([pattern]) => pattern);
  }

  private analyzeSession() {
    // Analyze current session to update user preferences
    const events = this.getStoredEvents().filter(e => e.sessionId === this.currentSession.sessionId);

    if (events.length > 0) {
      const modeUsage = events.reduce((acc, event) => {
        acc[event.searchMode] = (acc[event.searchMode] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const avgQueryLength = events.reduce((sum, e) => sum + e.query.length, 0) / events.length;

      // Update session preferences
      this.currentSession.preferences = {
        preferredMode: Object.entries(modeUsage).sort(([,a], [,b]) => b - a)[0]?.[0],
        avgQueryLength,
        interactionPatterns: this.extractCommonPatterns(events)
      };

      this.saveSession(this.currentSession);
    }
  }
}

// Usage example and integration
class SearchAnalyticsIntegration {
  private analytics: SearchAnalytics;

  constructor() {
    this.analytics = new SearchAnalytics();
  }

  // Integration with existing search context
  integrateWithPhotoSearchContext(photoSearchContext: any) {
    const originalSearch = photoSearchContext.search;

    photoSearchContext.search = (query: string) => {
      // Start analytics tracking
      this.analytics.startSearch(query, photoSearchContext.searchMode, {
        previousQuery: photoSearchContext.searchQuery,
        collectionSize: photoSearchContext.photos.length
      });

      const startTime = Date.now();

      // Call original search
      const result = originalSearch.call(photoSearchContext, query);

      // Track completion
      Promise.resolve(result).then(() => {
        const duration = Date.now() - startTime;
        this.analytics.completeSearch(photoSearchContext.photos, duration);
      });

      return result;
    };
  }

  // Add analytics attributes to photo elements
  enhancePhotoElements() {
    const photoElements = document.querySelectorAll('.photo-card, .gallery-item');

    photoElements.forEach((element, index) => {
      const photoPath = element.getAttribute('data-photo-path') ||
                       element.querySelector('img')?.src || '';
      const score = element.getAttribute('data-score') || '0';

      // Add analytics attributes
      element.setAttribute('data-photo-path', photoPath);
      element.setAttribute('data-position', (index + 1).toString());
      element.setAttribute('data-score', score);

      // Add event listeners
      element.addEventListener('click', () => {
        this.analytics.trackPhotoClick(photoPath, index + 1, parseFloat(score));
      });

      element.addEventListener('mouseenter', () => {
        this.analytics.trackPhotoHover(photoPath, index + 1, parseFloat(score));
      });
    });
  }

  // Settings UI integration
  createSettingsPanel(): HTMLElement {
    const panel = document.createElement('div');
    panel.className = 'analytics-settings-panel';

    const insights = this.analytics.getSearchInsights();

    panel.innerHTML = `
      <div class="settings-section">
        <h3>Search Analytics</h3>
        <label>
          <input type="checkbox" id="analytics-enabled" ${this.analytics['settings'].enabled ? 'checked' : ''}>
          Enable search analytics (improves recommendations)
        </label>

        <div class="insights-summary">
          <p>Total searches: ${insights.totalSearches}</p>
          <p>Success rate: ${(insights.successRate * 100).toFixed(1)}%</p>
          <p>Preferred mode: ${insights.preferredMode}</p>
        </div>

        <button id="export-data">Export My Data</button>
        <button id="clear-data">Clear All Data</button>
      </div>
    `;

    // Add event listeners
    panel.querySelector('#analytics-enabled')?.addEventListener('change', (e) => {
      const enabled = (e.target as HTMLInputElement).checked;
      this.analytics.updateSettings({ enabled });
    });

    panel.querySelector('#export-data')?.addEventListener('click', () => {
      const data = this.analytics.exportData();
      this.downloadData(data, 'search-analytics.json');
    });

    panel.querySelector('#clear-data')?.addEventListener('click', () => {
      if (confirm('Clear all analytics data? This cannot be undone.')) {
        this.analytics.clearAllData();
      }
    });

    return panel;
  }

  private downloadData(data: string, filename: string) {
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}

// Export for use in the main application
export { SearchAnalytics, SearchAnalyticsIntegration };
export type { SearchEvent, SearchInteraction, AnalyticsSettings };
