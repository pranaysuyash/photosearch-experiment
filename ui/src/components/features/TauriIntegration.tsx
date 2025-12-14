/**
 * Tauri Integration Component
 *
 * Manages Tauri desktop integration and provides setup guidance
 */

import { useState, useEffect } from 'react';
import './TauriIntegration.css';

interface TauriCommand {
  name: string;
  type: string;
  description?: string;
  parameters?: Record<string, unknown>;
  returns?: Record<string, unknown>;
}

interface SetupGuideStep {
  title: string;
  description?: string;
  code?: string;
}

interface SetupGuide {
  title?: string;
  description?: string;
  steps?: SetupGuideStep[];
  requirements?: string[];
  tips?: string[];
}

const TauriIntegration: React.FC = () => {
  const [commands, setCommands] = useState<TauriCommand[]>([]);
  const [rustSkeleton, setRustSkeleton] = useState<string>('');
  const [frontendHooks, setFrontendHooks] = useState<string>('');
  const [tauriConfig, setTauriConfig] = useState<string>('');
  const [securityTips, setSecurityTips] = useState<string[]>([]);
  const [performanceTips, setPerformanceTips] = useState<string[]>([]);
  const [checklist, setChecklist] = useState<string[]>([]);
  const [setupGuide, setSetupGuide] = useState<SetupGuide | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('commands');

  // Fetch all Tauri integration data
  const fetchTauriData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch commands
      const commandsResponse = await fetch('/api/tauri/commands');
      if (commandsResponse.ok) {
        const commandsData = await commandsResponse.json();
        setCommands(commandsData.commands || []);
      }

      // Fetch Rust skeleton
      const skeletonResponse = await fetch('/api/tauri/rust-skeleton');
      if (skeletonResponse.ok) {
        const skeletonData = await skeletonResponse.json();
        setRustSkeleton(skeletonData.skeleton || '');
      }

      // Fetch frontend hooks
      const hooksResponse = await fetch('/api/tauri/frontend-hooks');
      if (hooksResponse.ok) {
        const hooksData = await hooksResponse.json();
        setFrontendHooks(hooksData.hooks || '');
      }

      // Fetch Tauri config
      const configResponse = await fetch('/api/tauri/config');
      if (configResponse.ok) {
        const configData = await configResponse.json();
        setTauriConfig(configData.config || '');
      }

      // Fetch security tips
      const securityResponse = await fetch('/api/tauri/security');
      if (securityResponse.ok) {
        const securityData = await securityResponse.json();
        setSecurityTips(securityData.recommendations || []);
      }

      // Fetch performance tips
      const performanceResponse = await fetch('/api/tauri/performance');
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json();
        setPerformanceTips(performanceData.tips || []);
      }

      // Fetch checklist
      const checklistResponse = await fetch('/api/tauri/checklist');
      if (checklistResponse.ok) {
        const checklistData = await checklistResponse.json();
        setChecklist(checklistData.checklist || []);
      }

      // Fetch setup guide
      const guideResponse = await fetch('/api/tauri/setup-guide');
      if (guideResponse.ok) {
        const guideData = await guideResponse.json();
        setSetupGuide(guideData.guide);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching Tauri integration data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTauriData();
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        alert('Copied to clipboard!');
      })
      .catch((err) => {
        console.error('Failed to copy:', err);
      });
  };

  if (loading) {
    return <div className='loading'>Loading Tauri integration data...</div>;
  }

  if (error) {
    return <div className='error'>Error: {error}</div>;
  }

  return (
    <div className='tauri-integration'>
      <div className='header'>
        <h2>Tauri Integration</h2>
        <div className='controls'>
          <button onClick={fetchTauriData} className='refresh-btn'>
            Refresh
          </button>
        </div>
      </div>

      <div className='tabs'>
        <button
          className={`tab-btn ${activeTab === 'commands' ? 'active' : ''}`}
          onClick={() => setActiveTab('commands')}
        >
          Commands
        </button>
        <button
          className={`tab-btn ${activeTab === 'rust' ? 'active' : ''}`}
          onClick={() => setActiveTab('rust')}
        >
          Rust Skeleton
        </button>
        <button
          className={`tab-btn ${activeTab === 'hooks' ? 'active' : ''}`}
          onClick={() => setActiveTab('hooks')}
        >
          Frontend Hooks
        </button>
        <button
          className={`tab-btn ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          Config
        </button>
        <button
          className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          Security
        </button>
        <button
          className={`tab-btn ${activeTab === 'performance' ? 'active' : ''}`}
          onClick={() => setActiveTab('performance')}
        >
          Performance
        </button>
        <button
          className={`tab-btn ${activeTab === 'checklist' ? 'active' : ''}`}
          onClick={() => setActiveTab('checklist')}
        >
          Checklist
        </button>
        <button
          className={`tab-btn ${activeTab === 'guide' ? 'active' : ''}`}
          onClick={() => setActiveTab('guide')}
        >
          Setup Guide
        </button>
      </div>

      <div className='tab-content'>
        {activeTab === 'commands' && (
          <div className='commands-tab'>
            <h3>Available Tauri Commands ({commands.length})</h3>
            {commands.length > 0 ? (
              <div className='commands-list'>
                {commands.map((command, index) => (
                  <div key={index} className='command-item'>
                    <div className='command-header'>
                      <h4>{command.name}</h4>
                      <span className='command-type'>{command.type}</span>
                    </div>
                    <div className='command-details'>
                      <p>{command.description}</p>
                      {command.parameters && (
                        <div className='command-params'>
                          <strong>Parameters:</strong>
                          <pre>
                            {JSON.stringify(command.parameters, null, 2)}
                          </pre>
                        </div>
                      )}
                      {command.returns && (
                        <div className='command-returns'>
                          <strong>Returns:</strong>
                          <pre>{JSON.stringify(command.returns, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className='empty-state'>
                <p>No Tauri commands available.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'rust' && (
          <div className='code-tab'>
            <div className='code-header'>
              <h3>Rust Skeleton Code</h3>
              <button
                onClick={() => copyToClipboard(rustSkeleton)}
                className='copy-btn'
              >
                Copy to Clipboard
              </button>
            </div>
            <pre className='code-block rust-code'>{rustSkeleton}</pre>
          </div>
        )}

        {activeTab === 'hooks' && (
          <div className='code-tab'>
            <div className='code-header'>
              <h3>Frontend Hooks</h3>
              <button
                onClick={() => copyToClipboard(frontendHooks)}
                className='copy-btn'
              >
                Copy to Clipboard
              </button>
            </div>
            <pre className='code-block js-code'>{frontendHooks}</pre>
          </div>
        )}

        {activeTab === 'config' && (
          <div className='code-tab'>
            <div className='code-header'>
              <h3>Tauri Configuration</h3>
              <button
                onClick={() => copyToClipboard(tauriConfig)}
                className='copy-btn'
              >
                Copy to Clipboard
              </button>
            </div>
            <pre className='code-block toml-code'>{tauriConfig}</pre>
          </div>
        )}

        {activeTab === 'security' && (
          <div className='tips-tab'>
            <h3>Security Recommendations</h3>
            {securityTips.length > 0 ? (
              <ul className='tips-list'>
                {securityTips.map((tip, index) => (
                  <li key={index} className='tip-item'>
                    <span className='tip-number'>{index + 1}.</span>
                    <span className='tip-text'>{tip}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className='empty-state'>
                <p>No security recommendations available.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'performance' && (
          <div className='tips-tab'>
            <h3>Performance Tips</h3>
            {performanceTips.length > 0 ? (
              <ul className='tips-list'>
                {performanceTips.map((tip, index) => (
                  <li key={index} className='tip-item'>
                    <span className='tip-number'>{index + 1}.</span>
                    <span className='tip-text'>{tip}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className='empty-state'>
                <p>No performance tips available.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'checklist' && (
          <div className='checklist-tab'>
            <h3>Integration Checklist</h3>
            {checklist.length > 0 ? (
              <ul className='checklist'>
                {checklist.map((item, index) => (
                  <li key={index} className='checklist-item'>
                    <input type='checkbox' id={`check-${index}`} />
                    <label htmlFor={`check-${index}`}>{item}</label>
                  </li>
                ))}
              </ul>
            ) : (
              <div className='empty-state'>
                <p>No checklist items available.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'guide' && (
          <div className='guide-tab'>
            {setupGuide ? (
              <div className='guide-content'>
                <h3>{setupGuide.title}</h3>
                <p className='guide-description'>{setupGuide.description}</p>

                <div className='guide-steps'>
                  <h4>Steps:</h4>
                  <ol className='steps-list'>
                    {setupGuide?.steps?.map(
                      (step: SetupGuideStep, index: number) => (
                        <li key={index} className='step-item'>
                          <strong>{step.title}</strong>
                          <p>{step.description}</p>
                          {step.code && (
                            <pre className='step-code'>{step.code}</pre>
                          )}
                        </li>
                      )
                    )}
                  </ol>
                </div>

                {setupGuide.requirements && (
                  <div className='guide-requirements'>
                    <h4>Requirements:</h4>
                    <ul>
                      {setupGuide.requirements?.map(
                        (req: string, index: number) => (
                          <li key={index}>{req}</li>
                        )
                      )}
                    </ul>
                  </div>
                )}

                {setupGuide.tips && (
                  <div className='guide-tips'>
                    <h4>Tips:</h4>
                    <ul>
                      {setupGuide.tips?.map((tip: string, index: number) => (
                        <li key={index}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className='empty-state'>
                <p>No setup guide available.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TauriIntegration;
