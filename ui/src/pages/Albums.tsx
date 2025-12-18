import { useState } from 'react';
import type { Album } from '../api';
import { AlbumGrid } from '../components/albums/AlbumGrid';
import { AlbumDetail } from '../components/albums/AlbumDetail';
import { CreateAlbumDialog } from '../components/albums/CreateAlbumDialog';

export default function AlbumsPage() {
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingAlbum, setEditingAlbum] = useState<Album | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleAlbumClick = (album: Album) => {
    setSelectedAlbum(album);
  };

  const handleBackToGrid = () => {
    setSelectedAlbum(null);
    setRefreshKey((prev) => prev + 1); // Force reload albums
  };

  const handleCreateSuccess = () => {
    setRefreshKey((prev) => prev + 1); // Force reload albums
    setShowCreateDialog(false);
    setEditingAlbum(null);
  };

  const handleEdit = (album: Album) => {
    setEditingAlbum(album);
    setShowCreateDialog(true);
  };

  const handleDelete = () => {
    // After successful delete, go back to grid
    handleBackToGrid();
  };

  return (
    <div className="min-h-screen w-full">
      {selectedAlbum ? (
        <AlbumDetail
          key={selectedAlbum.id}
          albumId={selectedAlbum.id}
          onBack={handleBackToGrid}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      ) : (
        <div className="max-w-screen-2xl mx-auto px-6 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Albums</h1>
            <p className="text-white/60">Organize your photos into collections</p>
          </div>

          <AlbumGrid
            key={refreshKey}
            onAlbumClick={handleAlbumClick}
            onCreateAlbum={() => {
              setEditingAlbum(null);
              setShowCreateDialog(true);
            }}
          />
        </div>
      )}

      {/* Create/Edit Album Dialog */}
      <CreateAlbumDialog
        isOpen={showCreateDialog}
        editAlbum={editingAlbum}
        onClose={() => {
          setShowCreateDialog(false);
          setEditingAlbum(null);
        }}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
}
