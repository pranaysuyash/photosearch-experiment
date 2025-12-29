import { useState, useEffect } from 'react';
import { Smile, Users, Activity, Baby, User, HelpCircle } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface EmotionData {
    emotion: string;
    count: number;
    avg_confidence: number;
}

interface AgeData {
    age_group: string;
    count: number;
    avg_age: number;
    avg_confidence: number;
}

interface RelationshipData {
  person1: string;
  person2: string;
  shared_count: number;
}

interface FaceStats {
  clusters_found?: number;
  unidentified_faces?: number;
}

export default function PersonAnalytics() {
  const [loading, setLoading] = useState(true);
  const [emotions, setEmotions] = useState<EmotionData[]>([]);
  const [ages, setAges] = useState<AgeData[]>([]);
  const [relationships, setRelationships] = useState<RelationshipData[]>([]);
  const [totalFaces, setTotalFaces] = useState(0);
  const [stats, setStats] = useState<FaceStats | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [emotionRes, ageRes, statsRes, relationshipRes] =
        await Promise.all([
          api.getFaceEmotionDistribution(),
          api.getFaceAgeDistribution(),
          api.getFaceStats(),
          api.getFaceRelationships(),
        ]);

      setEmotions(emotionRes.emotions);
      setAges(ageRes.age_groups);
      setRelationships(relationshipRes.relationships || []);
      setTotalFaces(Math.max(emotionRes.total_faces, ageRes.total_faces));
      setStats(statsRes);
    } catch (err) {
      console.error('Failed to load analytics', err);
    } finally {
      setLoading(false);
    }
  };

  const getAgeLabel = (group: string) => {
    switch (group) {
      case 'child':
        return 'Children (<13)';
      case 'teen':
        return 'Teens (13-19)';
      case 'young_adult':
        return 'Young Adults (20-34)';
      case 'middle_age':
        return 'Middle Age (35-54)';
      case 'senior':
        return 'Seniors (55+)';
      default:
        return group;
    }
  };

  const getEmotionColor = (emotion: string) => {
    switch (emotion) {
      case 'happy':
        return 'bg-green-500';
      case 'sad':
        return 'bg-blue-500';
      case 'angry':
        return 'bg-red-500';
      case 'surprise':
        return 'bg-yellow-500';
      case 'fear':
        return 'bg-purple-500';
      case 'neutral':
        return 'bg-gray-400';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-primary' />
      </div>
    );
  }

  return (
    <div className='space-y-6 animate-in fade-in duration-500'>
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <div
          className={`${glass.card} p-4 flex flex-col items-center justify-center text-center`}
        >
          <div className='p-2 bg-primary/10 rounded-full mb-2'>
            <Users className='text-primary w-6 h-6' />
          </div>
          <div className='text-2xl font-bold text-foreground'>
            {totalFaces}
          </div>
          <div className='text-xs text-muted-foreground uppercase tracking-wide'>
            Faces Analyzed
          </div>
        </div>

        <div
          className={`${glass.card} p-4 flex flex-col items-center justify-center text-center`}
        >
          <div className='p-2 bg-green-500/10 rounded-full mb-2'>
            <User className='text-green-500 w-6 h-6' />
          </div>
          <div className='text-2xl font-bold text-foreground'>
            {stats?.clusters_found || 0}
          </div>
          <div className='text-xs text-muted-foreground uppercase tracking-wide'>
            Unique People
          </div>
        </div>

        <div
          className={`${glass.card} p-4 flex flex-col items-center justify-center text-center`}
        >
          <div className='p-2 bg-yellow-500/10 rounded-full mb-2'>
            <HelpCircle className='text-yellow-500 w-6 h-6' />
          </div>
          <div className='text-2xl font-bold text-foreground'>
            {stats?.unidentified_faces || 0}
          </div>
          <div className='text-xs text-muted-foreground uppercase tracking-wide'>
            Unidentified
          </div>
        </div>

        <div
          className={`${glass.card} p-4 flex flex-col items-center justify-center text-center`}
        >
          <div className='p-2 bg-purple-500/10 rounded-full mb-2'>
            <Smile className='text-purple-500 w-6 h-6' />
          </div>
          <div className='text-2xl font-bold text-foreground'>
            {emotions.find((e) => e.emotion === 'happy')?.count || 0}
          </div>
          <div className='text-xs text-muted-foreground uppercase tracking-wide'>
            Happy Moments
          </div>
        </div>
      </div>

      <div className='grid md:grid-cols-2 gap-6'>
        <div className={`${glass.surface} p-6 rounded-xl`}>
          <div className='flex items-center gap-2 mb-6'>
            <Smile className='text-primary w-5 h-5' />
            <h3 className='text-lg font-semibold text-foreground'>
              Emotion Analysis
            </h3>
          </div>

          <div className='space-y-4'>
            {emotions.map((item) => (
              <div key={item.emotion} className='space-y-1'>
                <div className='flex justify-between text-sm'>
                  <span className='capitalize text-foreground'>
                    {item.emotion}
                  </span>
                  <span className='text-muted-foreground'>
                    {item.count} ({Math.round((item.count / totalFaces) * 100)}
                    %)
                  </span>
                </div>
                <div className='h-2 w-full bg-white/5 rounded-full overflow-hidden'>
                  <div
                    className={`h-full ${getEmotionColor(
                      item.emotion
                    )} transition-all duration-1000`}
                    style={{ width: `${(item.count / totalFaces) * 100}%` }}
                  />
                </div>
                <div className='text-[10px] text-muted-foreground text-right'>
                  Avg Confidence: {Math.round(item.avg_confidence * 100)}%
                </div>
              </div>
            ))}
            {emotions.length === 0 && (
              <div className='text-center text-muted-foreground py-8'>
                No emotion data available yet.
              </div>
            )}
          </div>
        </div>

        <div className={`${glass.surface} p-6 rounded-xl`}>
          <div className='flex items-center gap-2 mb-6'>
            <Baby className='text-primary w-5 h-5' />
            <h3 className='text-lg font-semibold text-foreground'>
              Age Demographics
            </h3>
            <span className='text-xs text-muted-foreground ml-auto bg-primary/10 px-2 py-1 rounded'>
              AI Estimated
            </span>
          </div>

          <div className='space-y-4'>
            {ages.map((item) => (
              <div key={item.age_group} className='space-y-1'>
                <div className='flex justify-between text-sm'>
                  <span className='text-foreground'>
                    {getAgeLabel(item.age_group)}
                  </span>
                  <span className='text-muted-foreground'>{item.count}</span>
                </div>
                <div className='h-2 w-full bg-white/5 rounded-full overflow-hidden'>
                  <div
                    className='h-full bg-blue-500 transition-all duration-1000'
                    style={{ width: `${(item.count / totalFaces) * 100}%` }}
                  />
                </div>
                <div className='flex justify-between text-[10px] text-muted-foreground'>
                  <span>Avg Age: {item.avg_age}</span>
                  <span>Conf: {Math.round(item.avg_confidence * 100)}%</span>
                </div>
              </div>
            ))}
            {ages.length === 0 && (
              <div className='text-center text-muted-foreground py-8'>
                No age data available yet.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className={`${glass.surface} p-6 rounded-xl`}>
        <div className='flex items-center gap-2 mb-6'>
          <Activity className='text-primary w-5 h-5' />
          <h3 className='text-lg font-semibold text-foreground'>
            Top Connections
          </h3>
          <span className='text-xs text-muted-foreground ml-auto bg-primary/10 px-2 py-1 rounded'>
            Shared Photos
          </span>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {relationships.map((rel) => (
            <div
              key={`${rel.person1}-${rel.person2}`}
              className={`${glass.card} p-3 flex items-center justify-between`}
            >
              <div className='flex items-center gap-3'>
                <div className='flex -space-x-2'>
                  <div className='w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border-2 border-black text-xs font-bold text-primary'>
                    {rel.person1[0]?.toUpperCase()}
                  </div>
                  <div className='w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border-2 border-black text-xs font-bold text-primary'>
                    {rel.person2[0]?.toUpperCase()}
                  </div>
                </div>
                <div className='flex flex-col'>
                  <span className='text-sm font-medium text-foreground'>
                    {rel.person1} &amp; {rel.person2}
                  </span>
                </div>
              </div>
              <div className='text-sm font-bold text-muted-foreground bg-white/5 px-2 py-1 rounded'>
                {rel.shared_count}
              </div>
            </div>
          ))}
          {relationships.length === 0 && (
            <div className='col-span-full text-center text-muted-foreground py-8'>
              No co-occurrence data available yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
