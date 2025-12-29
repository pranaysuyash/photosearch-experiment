/**
 * ReviewInbox - Trust & Review entry point
 *
 * Aggregates key review queues into a single place:
 * - Unassigned faces (unknown bucket)
 * - Needs Review (gray-zone assignments)
 * - Mixed clusters (low coherence)
 * - Merge suggestions (potential duplicates)
 * - Low confidence detections
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Users,
  UserMinus,
  BadgeAlert,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

type QueueCounts = {
  unassignedTotal: number;
  reviewTotal: number;
  mixedClustersCount: number;
  mergeSuggestionsCount: number;
  lowConfidenceTotal: number;
};

const DEFAULTS = {
  mixedThreshold: 0.5,
  mergeThreshold: 0.62,
  mergeMax: 10,
  lowConfidenceThreshold: 0.8,
} as const;

export default function ReviewInbox(props: {
  onOpenNeedsReview: () => void;
  onOpenMergeSuggestions: () => void;
}) {
  const navigate = useNavigate();

  const [counts, setCounts] = useState<QueueCounts>({
    unassignedTotal: 0,
    reviewTotal: 0,
    mixedClustersCount: 0,
    mergeSuggestionsCount: 0,
    lowConfidenceTotal: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        unassigned,
        reviewCount,
        mixed,
        merge,
        lowConfidence,
      ] = await Promise.all([
        api.getUnassignedFaces(1, 0),
        api.getReviewQueueCount(),
        api.getMixedClusters(DEFAULTS.mixedThreshold),
        api.getMergeSuggestions(DEFAULTS.mergeThreshold, DEFAULTS.mergeMax),
        api.getLowConfidenceFaces(DEFAULTS.lowConfidenceThreshold, 1, 0),
      ]);

      setCounts({
        unassignedTotal: Number(unassigned?.total ?? 0),
        reviewTotal: Number(reviewCount ?? 0),
        mixedClustersCount: Number(mixed?.count ?? (mixed?.clusters?.length ?? 0)),
        mergeSuggestionsCount: Number(merge?.count ?? (merge?.suggestions?.length ?? 0)),
        lowConfidenceTotal: Number(lowConfidence?.total ?? lowConfidence?.count ?? 0),
      });
    } catch (err) {
      console.error('Failed to refresh review inbox counts:', err);
      setError('Failed to load review inbox');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const cards = useMemo(
    () =>
      [
        {
          key: 'unassigned',
          title: 'Unassigned',
          subtitle: 'Faces not yet assigned to a person',
          count: counts.unassignedTotal,
          icon: <UserMinus size={18} className='text-orange-400' />,
          onOpen: () => navigate('/people/unassigned'),
        },
        {
          key: 'needsReview',
          title: 'Needs Review',
          subtitle: 'Confirm or reject suggested matches',
          count: counts.reviewTotal,
          icon: <CheckCircle size={18} className='text-emerald-400' />,
          onOpen: props.onOpenNeedsReview,
        },
        {
          key: 'mixed',
          title: 'Mixed Clusters',
          subtitle: 'Clusters that may contain multiple people',
          count: counts.mixedClustersCount,
          icon: <AlertTriangle size={18} className='text-yellow-400' />,
          onOpen: () => navigate('/people?tab=mixed'),
          disabled: true,
        },
        {
          key: 'merge',
          title: 'Merge Suggestions',
          subtitle: `Top ${DEFAULTS.mergeMax} conservative duplicates`,
          count: counts.mergeSuggestionsCount,
          icon: <Users size={18} className='text-sky-400' />,
          onOpen: props.onOpenMergeSuggestions,
        },
        {
          key: 'lowConfidence',
          title: 'Low Confidence',
          subtitle: 'Detections below confidence threshold',
          count: counts.lowConfidenceTotal,
          icon: <BadgeAlert size={18} className='text-red-400' />,
          onOpen: () => navigate('/people/low-confidence'),
        },
      ] as const,
    [
      counts.lowConfidenceTotal,
      counts.mergeSuggestionsCount,
      counts.mixedClustersCount,
      counts.reviewTotal,
      counts.unassignedTotal,
      navigate,
      props.onOpenMergeSuggestions,
      props.onOpenNeedsReview,
    ]
  );

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between gap-3 flex-wrap'>
        <div>
          <h2 className='text-lg font-semibold text-foreground m-0'>Review Inbox</h2>
          <p className='text-sm text-muted-foreground m-0'>
            One place to keep face recognition clean and trustworthy.
          </p>
        </div>
        <button
          onClick={refresh}
          className={glass.button}
          disabled={loading}
          title='Refresh counts'
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {error && (
        <div
          className={`${glass.surface} rounded-xl border border-white/10 p-4`}
        >
          <div className='flex items-center gap-2'>
            <AlertTriangle size={16} className='text-yellow-400' />
            <div className='text-sm text-foreground'>{error}</div>
          </div>
        </div>
      )}

      <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3'>
        {cards.map((card) => {
          const disabled = Boolean((card as { disabled?: boolean }).disabled);

          return (
            <div
              key={card.key}
              className={`${glass.surface} rounded-xl border border-white/10 p-4 ${disabled ? 'opacity-60' : ''}`}
            >
              <div className='flex items-start justify-between gap-3'>
                <div className='min-w-0'>
                  <div className='flex items-center gap-2'>
                    <div className='w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center'>
                      {card.icon}
                    </div>
                    <div className='font-medium text-foreground truncate'>
                      {card.title}
                    </div>
                  </div>
                  <div className='text-xs text-muted-foreground mt-1'>
                    {card.subtitle}
                  </div>
                </div>

                <div className='text-right'>
                  <div className='text-2xl font-bold text-foreground'>
                    {loading ? '—' : card.count.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className='mt-3 flex justify-end'>
                <button
                  className='btn-glass btn-glass--muted text-sm px-3 py-2'
                  onClick={() => {
                    if (!disabled) card.onOpen();
                  }}
                  disabled={disabled}
                >
                  Open
                </button>
              </div>

              {disabled && (
                <div className='text-[11px] text-muted-foreground mt-2'>
                  Coming next: dedicated Mixed Clusters queue view.
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className='text-xs text-muted-foreground'>
        Tip: “Needs Review” is for gray-zone matches; “Unassigned” is for faces that aren’t in any person yet.
      </div>
    </div>
  );
}
