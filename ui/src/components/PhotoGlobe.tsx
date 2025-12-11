import { useRef, useState, useMemo, Suspense, useEffect } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { 
  OrbitControls, 
  Stars, 
  Html,
  Billboard
} from "@react-three/drei";
import * as THREE from "three";
import { type Photo, api } from "../api";

interface PhotoGlobeProps {
  photos: Photo[];
  onPhotoSelect: (photo: Photo) => void;
  onClose?: () => void;
}

// Generate random GPS coordinates for photos without location
function generateMockGPS(index: number): [number, number] {
  const locations = [
    [40.7128, -74.0060],   // New York
    [51.5074, -0.1278],    // London
    [35.6762, 139.6503],   // Tokyo
    [48.8566, 2.3522],     // Paris
    [-33.8688, 151.2093],  // Sydney
    [19.0760, 72.8777],    // Mumbai
    [55.7558, 37.6173],    // Moscow
    [-22.9068, -43.1729],  // Rio
    [1.3521, 103.8198],    // Singapore
    [25.2048, 55.2708],    // Dubai
    [37.7749, -122.4194],  // San Francisco
    [52.5200, 13.4050],    // Berlin
    [41.9028, 12.4964],    // Rome
    [31.2304, 121.4737],   // Shanghai
    [34.0522, -118.2437],  // Los Angeles
  ];
  const base = locations[index % locations.length];
  return [
    base[0] + (Math.random() - 0.5) * 5,
    base[1] + (Math.random() - 0.5) * 5
  ];
}

// Convert lat/lng to 3D position on sphere
function latLngToVector3(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  return new THREE.Vector3(x, y, z);
}

// Individual photo marker on globe
function PhotoMarker({ 
  photo, 
  position, 
  onSelect,
  index 
}: { 
  photo: Photo; 
  position: THREE.Vector3; 
  onSelect: (p: Photo) => void;
  index: number;
}) {
  const [hovered, setHovered] = useState(false);
  
  // Floating animation handled by parent rotation mostly, 
  // but we can add local scale pulse
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
        // Constantly face camera
        meshRef.current.lookAt(state.camera.position);
    }
  });
  
  // Calculate stack height to avoid Z-fighting on exact same spots
  const stackHeight = 0.1 + (index % 5) * 0.05;
  const adjustedPosition = position.clone().multiplyScalar(1 + stackHeight/7); // Normalize to radius 7
  
  return (
    <group position={adjustedPosition}>
      <mesh
        ref={meshRef}
        onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer'; setHovered(true); }}
        onPointerOut={(e) => { e.stopPropagation(); document.body.style.cursor = 'auto'; setHovered(false); }}
        onClick={(e) => { e.stopPropagation(); onSelect(photo); }}
      >
        {/* Larger invisible hit target */}
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial transparent opacity={0.0} />
        
        {/* Visible marker */}
        <mesh rotation={[Math.PI/2, 0, 0]}>
            <cylinderGeometry args={[0.08, 0.08, 0.15, 8]} />
            <meshStandardMaterial 
            color={hovered ? "#60a5fa" : "#3b82f6"} 
            emissive={hovered ? "#60a5fa" : "#1d4ed8"}
            emissiveIntensity={hovered ? 0.8 : 0.4}
            />
        </mesh>
      </mesh>
      
      {/* Photo thumbnail on hover */}
      {hovered && (
        <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
          <Html distanceFactor={10} center zIndexRange={[100, 0]}>
            <div className="bg-black/90 backdrop-blur-lg rounded-xl p-2 shadow-2xl border border-white/10 transform -translate-y-8 cursor-pointer pointer-events-none w-max">
              <img 
                src={api.getImageUrl(photo.path, 150)} 
                alt={photo.filename}
                className="w-32 h-24 object-cover rounded-lg"
              />
              <p className="text-white text-xs mt-1 text-center truncate max-w-32 font-medium">
                {photo.filename}
              </p>
            </div>
          </Html>
        </Billboard>
      )}
    </group>
  );
}

// The Rotating Earth Group containing Globe + Markers
function RotatingEarth({ photos, onPhotoSelect, isRotating }: { photos: Photo[], onPhotoSelect: (p: Photo) => void, isRotating: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const colorMap = useLoader(THREE.TextureLoader, '/earth_texture.jpg');
  
  useFrame(() => {
    if (groupRef.current && isRotating) {
      groupRef.current.rotation.y += 0.0005; 
    }
  });

  const photoPositions = useMemo(() => {
    return photos.map((photo, index) => {
      // Use GPS if available, else mock
      const [lat, lng] = (photo.metadata?.gps?.latitude && photo.metadata?.gps?.longitude) 
        ? [photo.metadata.gps.latitude, photo.metadata.gps.longitude] 
        : generateMockGPS(index);
        
      const position = latLngToVector3(lat, lng, 7); 
      return { photo, position };
    });
  }, [photos]);

  return (
    <group ref={groupRef}>
      {/* Earth Sphere */}
      <mesh>
        <sphereGeometry args={[7, 64, 64]} />
        <meshStandardMaterial 
          map={colorMap} 
          roughness={0.6}
          metalness={0.1} 
        />
      </mesh>

      {/* Atmosphere glow */}
      <mesh scale={1.02}>
        <sphereGeometry args={[7, 32, 32]} />
        <meshBasicMaterial 
          color="#60a5fa" 
          transparent 
          opacity={0.15} 
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Markers nested inside the rotating group */}
      {photoPositions.slice(0, 150).map((item, i) => (
        <PhotoMarker
          key={item.photo.path}
          photo={item.photo}
          position={item.position}
          onSelect={onPhotoSelect}
          index={i}
        />
      ))}
    </group>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <Html center>
      <div className="text-white text-center">
        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm opacity-70">Loading Earth...</p>
      </div>
    </Html>
  );
}

export function PhotoGlobe({ photos, onPhotoSelect, onClose }: PhotoGlobeProps) {
  const [isRotating, setIsRotating] = useState(true);
  
  // Space key to toggle rotation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        setIsRotating(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
  
  return (
    <div className="fixed inset-0 z-40 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900 via-[#0a0a0a] to-black">
      {/* Exit + Controls */}
      <div className="absolute top-6 right-6 z-50 flex gap-2">
        <button
          onClick={() => setIsRotating(!isRotating)}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full backdrop-blur-lg border border-white/10 transition-all text-sm font-medium"
        >
          {isRotating ? 'Pause Rotation' : 'Resume Rotation'}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full backdrop-blur-lg border border-white/10 transition-all text-sm font-medium"
          >
            Exit Globe
          </button>
        )}
      </div>
      
      {/* Title overlay */}
      <div className="absolute top-6 left-6 z-10 pointer-events-none">
        <h2 className="text-3xl font-bold text-white/90 drop-shadow-lg tracking-tight">
          Your World
        </h2>
        <p className="text-white/60 text-sm mt-1 font-medium">
          {photos.length} memories mapped
        </p>
      </div>
      
      {/* Instructions */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 pointer-events-none opacity-60">
        <p className="text-white text-xs bg-black/40 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/5">
          Drag to orbit • Scroll to zoom • Click markers to view details
        </p>
      </div>
      
      {/* 3D Canvas - fills entire viewport */}
      <Canvas 
        camera={{ position: [0, 0, 18], fov: 45 }}
        dpr={[1, 2]}
        style={{ width: '100%', height: '100%' }}
      >
        <Suspense fallback={<LoadingFallback />}>
            <ambientLight intensity={0.2} />
            <directionalLight position={[15, 10, 5]} intensity={1.5} color="#ffd4a3" /> {/* Sun */}
            <pointLight position={[-10, -10, -5]} intensity={0.5} color="#60a5fa" /> {/* Ambient bounce */}
            
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={0.5} />
            
            <RotatingEarth photos={photos} onPhotoSelect={onPhotoSelect} isRotating={isRotating} />
            
            <OrbitControls 
                enableDamping
                dampingFactor={0.05}
                minDistance={10}
                maxDistance={30}
                enablePan={false}
            />
        </Suspense>
      </Canvas>
    </div>
  );
}

export default PhotoGlobe;

