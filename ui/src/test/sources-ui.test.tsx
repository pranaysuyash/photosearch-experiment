import { describe, expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';
import Settings from '../pages/Settings';
import { SourcesPanel } from '../components/sources/SourcesPanel';

describe('Sources UX', () => {
  it('renders a sources panel with a connect affordance', () => {
    const html = renderToString(<SourcesPanel />);
    expect(html).toContain('Connect source');
    expect(html).toContain('Sources');
  });

  it('does not render a manual folder path entry in Settings', () => {
    const html = renderToString(<Settings />);
    expect(html).not.toContain('Add a folder path');
    expect(html).not.toContain('Add a folder path…');
  });
});

