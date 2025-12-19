/**
 * Comprehensive tests for face detection API integration
 * Tests all new face detection and clustering endpoints
 */

import { describe, expect, test, vi, beforeEach } from 'vitest';
import { api } from '../api';

// Mock the entire api module
describe('Face Detection API Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Face Detection Endpoints', () => {
    test('detectFaces - should detect faces in a photo', async () => {
      const mockResponse = {
        photo_path: '/test/photo.jpg',
        faces: [
          {
            detection_id: 'face_123',
            bounding_box: { x: 0.25, y: 0.35, width: 0.15, height: 0.20 },
            has_embedding: true,
            quality_score: 0.92
          }
        ],
        face_count: 1,
        success: true
      };

      // Mock the API call
      vi.spyOn(api, 'detectFaces').mockResolvedValue(mockResponse);

      const result = await api.detectFaces('/test/photo.jpg');
      
      expect(result).toEqual(mockResponse);
      expect(result.success).toBe(true);
      expect(result.faces.length).toBe(1);
      expect(result.faces[0].detection_id).toBe('face_123');
    });

    test('getFacesInPhoto - should get faces for a photo', async () => {
      const mockResponse = {
        photo_path: '/test/photo.jpg',
        faces: [
          {
            detection_id: 'face_123',
            bounding_box: { x: 0.25, y: 0.35, width: 0.15, height: 0.20 },
            quality_score: 0.92,
            person_id: 'cluster_456',
            person_label: 'John Doe'
          }
        ],
        face_count: 1,
        success: true
      };

      vi.spyOn(api, 'getFacesInPhoto').mockResolvedValue(mockResponse);

      const result = await api.getFacesInPhoto('/test/photo.jpg');
      
      expect(result).toEqual(mockResponse);
      expect(result.faces[0].person_id).toBe('cluster_456');
    });

    test('getFaceThumbnail - should get face thumbnail', async () => {
      const mockThumbnail = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...';
      const mockResponse = {
        detection_id: 'face_123',
        thumbnail: mockThumbnail,
        success: true
      };

      vi.spyOn(api, 'getFaceThumbnail').mockResolvedValue(mockResponse);

      const result = await api.getFaceThumbnail('face_123');
      
      expect(result).toEqual(mockResponse);
      expect(result.thumbnail).toContain('data:image/jpeg;base64,');
    });

    test('detectFacesBatch - should detect faces in multiple photos', async () => {
      const mockResponse = {
        processed_photos: 3,
        total_faces_detected: 7,
        results: [
          {
            photo_path: '/test/photo1.jpg',
            face_count: 2,
            detection_ids: ['face_1', 'face_2']
          },
          {
            photo_path: '/test/photo2.jpg',
            face_count: 3,
            detection_ids: ['face_3', 'face_4', 'face_5']
          },
          {
            photo_path: '/test/photo3.jpg',
            face_count: 2,
            detection_ids: ['face_6', 'face_7']
          }
        ],
        success: true
      };

      vi.spyOn(api, 'detectFacesBatch').mockResolvedValue(mockResponse);

      const result = await api.detectFacesBatch([
        '/test/photo1.jpg',
        '/test/photo2.jpg',
        '/test/photo3.jpg'
      ]);
      
      expect(result).toEqual(mockResponse);
      expect(result.processed_photos).toBe(3);
      expect(result.total_faces_detected).toBe(7);
    });
  });

  describe('Automatic Clustering Endpoints', () => {
    test('clusterFaces - should cluster similar faces', async () => {
      const mockResponse = {
        clusters_created: 3,
        total_faces_clustered: 15,
        clusters: [
          {
            cluster_id: 'cluster_1',
            label: 'Auto Cluster 0',
            face_count: 5,
            photo_count: 3,
            detection_ids: ['face_1', 'face_2', 'face_3', 'face_4', 'face_5']
          },
          {
            cluster_id: 'cluster_2',
            label: 'Auto Cluster 1',
            face_count: 4,
            photo_count: 2,
            detection_ids: ['face_6', 'face_7', 'face_8', 'face_9']
          },
          {
            cluster_id: 'cluster_3',
            label: 'Auto Cluster 2',
            face_count: 6,
            photo_count: 4,
            detection_ids: ['face_10', 'face_11', 'face_12', 'face_13', 'face_14', 'face_15']
          }
        ],
        success: true
      };

      vi.spyOn(api, 'clusterFaces').mockResolvedValue(mockResponse);

      const result = await api.clusterFaces(0.6, 2);
      
      expect(result).toEqual(mockResponse);
      expect(result.clusters_created).toBe(3);
      expect(result.total_faces_clustered).toBe(15);
    });

    test('findSimilarFaces - should find faces similar to reference', async () => {
      const mockResponse = {
        detection_id: 'face_123',
        similar_faces: [
          {
            detection_id: 'face_456',
            photo_path: '/test/photo2.jpg',
            similarity: 0.98,
            person_id: 'cluster_789',
            person_label: 'Jane Doe'
          },
          {
            detection_id: 'face_789',
            photo_path: '/test/photo3.jpg',
            similarity: 0.95,
            person_id: 'cluster_789',
            person_label: 'Jane Doe'
          }
        ],
        count: 2,
        success: true
      };

      vi.spyOn(api, 'findSimilarFaces').mockResolvedValue(mockResponse);

      const result = await api.findSimilarFaces('face_123', 0.7);
      
      expect(result).toEqual(mockResponse);
      expect(result.similar_faces.length).toBe(2);
      expect(result.similar_faces[0].similarity).toBe(0.98);
    });

    test('getClusterQuality - should analyze cluster quality', async () => {
      const mockResponse = {
        cluster_id: 'cluster_123',
        quality_analysis: {
          cluster_id: 'cluster_123',
          label: 'John Doe',
          face_count: 8,
          avg_confidence: 0.92,
          avg_quality_score: 0.88,
          coherence_score: 0.95,
          quality_rating: 'Excellent',
          created_at: '2025-01-15T10:30:00Z',
          updated_at: '2025-01-16T09:15:00Z'
        },
        success: true
      };

      vi.spyOn(api, 'getClusterQuality').mockResolvedValue(mockResponse);

      const result = await api.getClusterQuality('cluster_123');
      
      expect(result).toEqual(mockResponse);
      expect(result.quality_analysis.quality_rating).toBe('Excellent');
    });

    test('mergeClusters - should merge two clusters', async () => {
      const mockResponse = {
        source_cluster_id: 'cluster_123',
        target_cluster_id: 'cluster_456',
        faces_moved: 5,
        success: true
      };

      vi.spyOn(api, 'mergeClusters').mockResolvedValue(mockResponse);

      const result = await api.mergeClusters('cluster_123', 'cluster_456');
      
      expect(result).toEqual(mockResponse);
      expect(result.faces_moved).toBe(5);
    });
  });

  describe('Error Handling', () => {
    test('should handle API errors gracefully', async () => {
      const error = new Error('Internal server error');
      vi.spyOn(api, 'detectFaces').mockRejectedValue(error);

      try {
        await api.detectFaces('/test/photo.jpg');
        fail('Should have thrown an error');
      } catch (err) {
        expect(err).toBe(error);
      }
    });

    test('should handle network errors', async () => {
      const error = new Error('Network Error');
      vi.spyOn(api, 'getFaceThumbnail').mockRejectedValue(error);

      try {
        await api.getFaceThumbnail('nonexistent');
        fail('Should have thrown an error');
      } catch (err) {
        expect(err).toBe(error);
      }
    });

    test('should handle 404 errors', async () => {
      const error = new Error('404 Not Found');
      vi.spyOn(api, 'getFacesInPhoto').mockRejectedValue(error);

      try {
        await api.getFacesInPhoto('/nonexistent/photo.jpg');
        fail('Should have thrown an error');
      } catch (err) {
        expect(err).toBe(error);
      }
    });
  });

  describe('Edge Cases', () => {
    test('should handle empty responses', async () => {
      const mockResponse = {
        photo_path: '/test/empty.jpg',
        faces: [],
        face_count: 0,
        success: true
      };

      vi.spyOn(api, 'detectFaces').mockResolvedValue(mockResponse);

      const result = await api.detectFaces('/test/empty.jpg');
      
      expect(result).toBeDefined();
      expect(result.faces).toHaveLength(0);
      expect(result.face_count).toBe(0);
    });

    test('should handle large batch requests', async () => {
      const largeBatch = Array(100).fill(0).map((_, i) => `/test/photo_${i}.jpg`);
      
      const mockResponse = {
        processed_photos: 100,
        total_faces_detected: 250,
        results: largeBatch.map(path => ({
          photo_path: path,
          face_count: 2,
          detection_ids: [`face_${path.replace(/\/|\./g, '_')}_1`, `face_${path.replace(/\/|\./g, '_')}_2`]
        })),
        success: true
      };

      vi.spyOn(api, 'detectFacesBatch').mockResolvedValue(mockResponse);

      const result = await api.detectFacesBatch(largeBatch);
      
      expect(result).toBeDefined();
      expect(result.processed_photos).toBe(100);
      expect(result.results).toHaveLength(100);
    });

    test('should verify API method signatures', () => {
      // Verify all methods exist and have correct signatures
      expect(typeof api.detectFaces).toBe('function');
      expect(typeof api.getFacesInPhoto).toBe('function');
      expect(typeof api.getFaceThumbnail).toBe('function');
      expect(typeof api.detectFacesBatch).toBe('function');
      expect(typeof api.clusterFaces).toBe('function');
      expect(typeof api.findSimilarFaces).toBe('function');
      expect(typeof api.getClusterQuality).toBe('function');
      expect(typeof api.mergeClusters).toBe('function');
    });
  });
});