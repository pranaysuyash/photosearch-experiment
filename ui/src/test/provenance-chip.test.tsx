import { describe, expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';
import { ProvenanceChip } from '../components/provenance/ProvenanceChip';
import type { PhotoAttribution } from '../api';

const cloud: PhotoAttribution = {
  origin: 'source',
  kind: 'cloud',
  match: 'source_item',
  source_id: 'src-1',
  source_type: 'google_drive',
  source_name: 'Drive',
  source_status: 'connected',
  last_sync_at: '2026-10-21T00:00:00+00:00',
  item_status: 'active',
  remote_id: 'r1',
};

const local: PhotoAttribution = {
  origin: 'media_root',
  kind: 'local',
  match: 'media_root',
  source_type: 'local_library',
  source_name: 'Local library',
};

const unknown: PhotoAttribution = {
  origin: 'unattributed',
  kind: 'unknown',
  match: 'none',
};

describe('ProvenanceChip', () => {
  it('renders a cloud origin with the real source name', () => {
    const html = renderToString(<ProvenanceChip attribution={cloud} />);
    expect(html).toContain('Cloud');
    expect(html).toContain('Drive');
    expect(html).toContain('data-kind="cloud"');
  });

  it('renders a local origin', () => {
    const html = renderToString(<ProvenanceChip attribution={local} />);
    expect(html).toContain('Local');
    expect(html).toContain('Local library');
    expect(html).toContain('data-kind="local"');
  });

  it('renders unattributed files honestly instead of guessing', () => {
    const html = renderToString(<ProvenanceChip attribution={unknown} />);
    expect(html).toContain('Unattributed');
    expect(html).toContain('data-kind="unknown"');
    expect(html).not.toContain('Cloud');
  });

  it('does not invent a source when attribution is missing entirely', () => {
    const html = renderToString(<ProvenanceChip />);
    expect(html).toContain('Unattributed');
    expect(html).toContain('data-kind="unknown"');
  });

  it('marks a content-provenance manifest without claiming verification', () => {
    const html = renderToString(
      <ProvenanceChip
        attribution={{
          ...cloud,
          content: {
            present: true,
            markers: ['c2pa_uuid_box'],
            verified: false,
            verifier: null,
            scan_scope: 'head_and_tail',
            note: 'Manifest markers detected.',
          },
        }}
      />
    );
    expect(html).toContain('aria-label="Content-provenance manifest marker detected (not verified)"');
  });

  it('flags a source that reported an error', () => {
    const html = renderToString(
      <ProvenanceChip attribution={{ ...cloud, source_status: 'error' }} />
    );
    expect(html).toContain('aria-label="Source has an error"');
  });
});
