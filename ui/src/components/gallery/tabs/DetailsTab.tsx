import React from 'react';
import { Camera, MapPin, HardDrive, Image as ImageIcon, Code } from 'lucide-react';
import { MetadataSection, MetadataRow } from '../MetadataSection';

interface DetailsTabProps {
    metadata: unknown;
    api: unknown; // api module
    photoPath: string;
}

type MetadataShape = {
    file?: { name?: string; extension?: string; mime_type?: string };
    filesystem?: { size_human?: string; created?: string; modified?: string; owner?: string };
    image?: { width?: number; height?: number; format?: string; mode?: string; dpi?: number[]; bits_per_pixel?: number; animation?: boolean };
    exif?: { image?: Record<string, unknown>; exif?: Record<string, unknown> };
    gps?: { latitude?: number; longitude?: number; altitude?: number };
    video?: { format?: { duration?: unknown; format_long_name?: string; bit_rate?: unknown } };
    hashes?: { md5?: string; sha256?: string };
};

export function DetailsTab({ metadata }: DetailsTabProps) {
    if (!metadata) {
        return <div className="p-5 text-white/50 text-center text-sm">No metadata available</div>;
    }

    const { file, filesystem: fs, image: img, exif, gps, hashes, video } = (metadata as MetadataShape);

    // We can also inject 'calc' stats if passed down, or computed

    return (
        <div className="flex flex-col gap-3 p-1 pb-10">

            {/* File Info */}
            {file && (
                <MetadataSection icon={HardDrive} title='File Info' defaultOpen={true}>
                    <MetadataRow label='Name' value={file.name} />
                    <MetadataRow label='Extension' value={file.extension} />
                    <MetadataRow label='MIME Type' value={file.mime_type} />
                </MetadataSection>
            )}

            {/* Image Values */}
            {img?.width && (
                <MetadataSection icon={ImageIcon} title='Image' defaultOpen={true}>
                    <MetadataRow label='Dimensions' value={`${img.width} × ${img.height}`} />
                    <MetadataRow label='Format' value={img.format} />
                    <MetadataRow label='Mode' value={img.mode} />
                    <MetadataRow label='DPI' value={img.dpi?.join(' × ')} />
                    <MetadataRow label='Bits/Pixel' value={img.bits_per_pixel} />
                    <MetadataRow label='Animated' value={img.animation} />
                </MetadataSection>
            )}

            {/* EXIF */}
            {exif?.image && (
                <MetadataSection icon={Camera} title='Camera' defaultOpen>
                    <MetadataRow label='Make' value={exif.image?.Make} />
                    <MetadataRow label='Model' value={exif.image?.Model} />
                    <MetadataRow label='Software' value={exif.image?.Software} />
                </MetadataSection>
            )}

            {exif?.exif && (
                <MetadataSection icon={Camera} title='Exposure'>
                    <MetadataRow label='ISO' value={exif.exif?.ISOSpeedRatings} />
                    <MetadataRow label='Aperture' value={exif.exif?.FNumber} />
                    <MetadataRow label='Shutter' value={exif.exif?.ExposureTime} />
                    <MetadataRow label='Focal Length' value={exif.exif?.FocalLength} />
                    <MetadataRow label='Flash' value={exif.exif?.Flash} />
                </MetadataSection>
            )}

            {/* GPS */}
            {(gps?.latitude || gps?.longitude) && (
                <MetadataSection icon={MapPin} title='Location'>
                    <MetadataRow label='Latitude' value={gps.latitude} />
                    <MetadataRow label='Longitude' value={gps.longitude} />
                    <MetadataRow label='Altitude' value={gps.altitude} />
                </MetadataSection>
            )}

            {/* Storage */}
            {fs && (
                <MetadataSection icon={HardDrive} title='Storage'>
                    <MetadataRow label='Size' value={fs.size_human} />
                    <MetadataRow label='Created' value={fs.created} />
                    <MetadataRow label='Modified' value={fs.modified} />
                    <MetadataRow label='Owner' value={fs.owner} />
                </MetadataSection>
            )}

            {/* Video */}
            {video?.format && (
                <MetadataSection icon={Camera} title='Video'>
                    <MetadataRow label='Duration' value={video.format.duration} />
                    <MetadataRow label='Format' value={video.format.format_long_name} />
                    <MetadataRow label='Bitrate' value={video.format.bit_rate} />
                </MetadataSection>
            )}

            {/* Hashes */}
            {hashes && (
                <MetadataSection icon={Code} title='Hashes'>
                    <MetadataRow label='MD5' value={hashes.md5} />
                    <MetadataRow label='SHA256' value={hashes.sha256} />
                </MetadataSection>
            )}

        </div>
    );
}
