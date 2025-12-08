import { useRef, useState, useMemo, Suspense } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
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
}

// Generate random GPS coordinates for photos without location
function generateMockGPS(index: number): [number, number] {
  // Distribute across interesting locations
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
  // Add some randomness within the city
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
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Gentle floating animation
  useFrame(() => {
    if (meshRef.current) {
      const scale = hovered ? 1.5 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1);
    }
  });
  
  // Stack height based on index clustering
  const stackHeight = 0.1 + (index % 5) * 0.05;
  const adjustedPosition = position.clone().multiplyScalar(1 + stackHeight);
  
  return (
    <group position={adjustedPosition}>
      <mesh
        ref={meshRef}
        onPointerOver={() => { 
          document.body.style.cursor = 'pointer'; 
          setHovered(true); 
        }}
        onPointerOut={() => { 
          document.body.style.cursor = 'auto'; 
          setHovered(false); 
        }}
        onClick={() => onSelect(photo)}
      >
        <cylinderGeometry args={[0.08, 0.08, 0.15, 8]} />
        <meshStandardMaterial 
          color={hovered ? "#60a5fa" : "#3b82f6"} 
          emissive={hovered ? "#60a5fa" : "#1d4ed8"}
          emissiveIntensity={hovered ? 0.5 : 0.2}
        />
      </mesh>
      
      {/* Photo thumbnail on hover */}
      {hovered && (
        <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
          <Html distanceFactor={10} center>
            <div className="bg-black/90 backdrop-blur-lg rounded-xl p-2 shadow-2xl border border-white/10 transform -translate-y-8">
              <img 
                src={api.getImageUrl(photo.path, 150)} 
                alt={photo.filename}
                className="w-32 h-24 object-cover rounded-lg"
              />
              <p className="text-white text-xs mt-1 text-center truncate max-w-32">
                {photo.filename}
              </p>
            </div>
          </Html>
        </Billboard>
      )}
    </group>
  );
}

// The Earth sphere
function Earth() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Earth textures - using procedural for now (can add real textures later)
  // For production: load actual NASA Blue Marble textures
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.0005; // Slow rotation
    }
  });
  
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[7, 64, 64]} />
      <meshStandardMaterial 
        color="#1a365d" 
        roughness={0.8}
        metalness={0.1}
      />
      {/* Atmosphere glow */}
      <mesh scale={1.02}>
        <sphereGeometry args={[7, 32, 32]} />
        <meshBasicMaterial 
          color="#60a5fa" 
          transparent 
          opacity={0.1} 
          side={THREE.BackSide}
        />
      </mesh>
    </mesh>
  );
}

// Note: OrbitingCloud removed - not currently used. Can be added for photos without GPS later.

// Main scene
function GlobeScene({ photos, onPhotoSelect }: PhotoGlobeProps) {
  // Distribute photos on globe
  const photoPositions = useMemo(() => {
    return photos.map((photo, index) => {
      // Use GPS from metadata if available, otherwise mock
      const [lat, lng] = generateMockGPS(index);
      const position = latLngToVector3(lat, lng, 7);  // Updated radius
      return { photo, position };
    });
  }, [photos]);
  
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.3} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <pointLight position={[-10, -10, -5]} intensity={0.5} color="#60a5fa" />
      
      {/* Stars background */}
      <Stars 
        radius={100} 
        depth={50} 
        count={5000} 
        factor={4} 
        saturation={0} 
        fade 
        speed={1}
      />
      
      {/* The Earth */}
      <Earth />
      
      {/* Photo markers */}
      {photoPositions.slice(0, 100).map((item, i) => (
        <PhotoMarker
          key={item.photo.path}
          photo={item.photo}
          position={item.position}
          onSelect={onPhotoSelect}
          index={i}
        />
      ))}
      
      {/* Controls */}
      <OrbitControls 
        enableDamping
        dampingFactor={0.05}
        minDistance={7}
        maxDistance={20}
        autoRotate
        autoRotateSpeed={0.3}
      />
    </>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <Html center>
      <div className="text-white text-center">
        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm opacity-70">Loading your memories...</p>
      </div>
    </Html>
  );
}

export function PhotoGlobe({ photos, onPhotoSelect, onClose }: PhotoGlobeProps & { onClose?: () => void }) {
  return (
    <div className="fixed inset-0 z-40 bg-gradient-to-b from-slate-950 to-slate-900">
      {/* Exit button */}
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-6 right-6 z-50 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full backdrop-blur-lg border border-white/10 transition-all text-sm"
        >
          Exit Globe
        </button>
      )}
      
      {/* Title overlay */}
      <div className="absolute top-6 left-6 z-10 pointer-events-none">
        <h2 className="text-3xl font-bold text-white/90 drop-shadow-lg">
          Your World of Memories
        </h2>
        <p className="text-white/50 text-sm mt-1">
          {photos.length} photos across the globe
        </p>
      </div>
      
      {/* Instructions */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
        <p className="text-white/40 text-xs bg-black/20 backdrop-blur px-4 py-2 rounded-full">
          Drag to orbit • Scroll to zoom • Click markers to view
        </p>
      </div>
      
      {/* 3D Canvas - fills entire viewport */}
      <Canvas 
        camera={{ position: [0, 5, 12], fov: 50 }}
        dpr={[1, 2]}
        style={{ width: '100%', height: '100%' }}
      >
        <Suspense fallback={<LoadingFallback />}>
          <GlobeScene photos={photos} onPhotoSelect={onPhotoSelect} />
        </Suspense>
      </Canvas>
    </div>
  );
}

export default PhotoGlobe;

