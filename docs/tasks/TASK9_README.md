# Task 9: 3D Explore Mode

## Overview
**3D Explore Mode** (The "Memory Museum") transforms the photo browsing experience into an immersive 3D gallery. Users can navigate a spatial environment where their photos are displayed as framed artworks.

## Features
- **Immersive Environment**: 3D canvas using `@react-three/fiber`.
- **Procedural Gallery**: Dynamic placement of photos in 3D space.
- **Interactive Frames**: Hover effects and click interactions to view details.
- **Seamless Integration**: Smooth transition from the 2D "Story Mode" or "Grid View".
- **Performance Optimized**: Uses low-resolution thumbnails for textures and instance rendering where possible.

## Architecture

### Frontend (`ui/src/components/MemoryMuseum.tsx`)
- **Engine**: Three.js via React Three Fiber (R3F).
- **Controls**: `FirstPersonControls` or `OrbitControls` for navigation.
- **State**: Syncs with the main `usePhotoSearch` hook to display current search results in 3D.
- **Assets**: Dynamically loads textures from the `/image/thumbnail` backend endpoint.

### Backend Support
- **Thumbnail API**: Optimized `GET /image/thumbnail` endpoint to ensure fast texture loading.
- **CORS**: Configured to allow 3D canvas texture requests.

## Usage
1.  Navigate to **Story Mode**.
2.  Click the **"Enter 3D"** button (cube icon).
3.  **Controls**:
    *   **Mouse**: Look around / Drag to rotate.
    *   **Scroll**: Zoom in/out.
    *   **Click**: Open photo detail.

## Future Improvements
- [ ] procedural infinite hallways.
- [ ] VR support.
- [ ] Spatial audio based on photo locations.
