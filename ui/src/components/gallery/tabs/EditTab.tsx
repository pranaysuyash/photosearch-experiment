import React from 'react';
import {
    RotateCw,
    FlipHorizontal,
    FlipVertical,
    Crop as CropIcon,
    Undo,
    Redo,
    RefreshCw,
    Save,
    ArrowLeft
} from 'lucide-react';

export interface EditSettings {
    brightness: number;
    contrast: number;
    saturation: number;
    rotation: number;
    flipH: boolean;
    flipV: boolean;
    crop?: { x: number; y: number; width: number; height: number };
}

interface EditTabProps {
    settings: EditSettings;
    onChange: (settings: EditSettings) => void;
    onSave: () => void;
    onCancel: () => void;
    canUndo: boolean;
    canRedo: boolean;
    onUndo: () => void;
    onRedo: () => void;
    onReset: () => void;
    isSaving: boolean;
}

export function EditTab({
    settings,
    onChange,
    onSave,
    onCancel,
    canUndo,
    canRedo,
    onUndo,
    onRedo,
    onReset,
    isSaving
}: EditTabProps) {

    const updateSetting = (key: keyof EditSettings, value: number | boolean) => {
        onChange({ ...settings, [key]: value });
    };

    return (
        <div className="flex flex-col h-full text-white/90 gap-6 p-2">

            {/* Header Actions */}
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
                <button
                    onClick={onCancel}
                    className="flex items-center gap-2 text-sm text-white/50 hover:text-white transition-colors"
                >
                    <ArrowLeft size={16} />
                    Back
                </button>
                <div className="text-sm font-medium">Edit Mode</div>
            </div>

            {/* Adjustments */}
            <div className="space-y-6">
                <div className="space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-white/50">Adjustments</h3>

                    <SliderControl
                        label="Brightness"
                        value={settings.brightness}
                        min={-100} max={100}
                        onChange={(v) => updateSetting('brightness', v)}
                    />
                    <SliderControl
                        label="Contrast"
                        value={settings.contrast}
                        min={-100} max={100}
                        onChange={(v) => updateSetting('contrast', v)}
                    />
                    <SliderControl
                        label="Saturation"
                        value={settings.saturation}
                        min={-100} max={100}
                        onChange={(v) => updateSetting('saturation', v)}
                    />
                </div>

                <div className="space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-white/50">Transforms</h3>
                    <div className="grid grid-cols-4 gap-2">
                        <ControlButton
                            onClick={() => updateSetting('rotation', (settings.rotation + 90) % 360)}
                            icon={RotateCw}
                            label="Rotate"
                        />
                        <ControlButton
                            onClick={() => updateSetting('flipH', !settings.flipH)}
                            icon={FlipHorizontal}
                            label="Flip H"
                            active={settings.flipH}
                        />
                        <ControlButton
                            onClick={() => updateSetting('flipV', !settings.flipV)}
                            icon={FlipVertical}
                            label="Flip V"
                            active={settings.flipV}
                        />
                        <ControlButton
                            onClick={() => {
                                // Crop functionality not yet implemented
                                console.warn('Crop mode not yet implemented');
                            }}
                            icon={CropIcon}
                            label="Crop"
                            active={false}
                            disabled={true}
                        />
                    </div>
                </div>

            </div>

            <div className="flex-1" />

            {/* History & Save */}
            <div className="space-y-3 pt-4 border-t border-white/10">
                <div className="flex justify-center gap-4 mb-2">
                    <button
                        onClick={onUndo}
                        disabled={!canUndo}
                        className="p-2 hover:bg-white/10 rounded-full disabled:opacity-30 transition-colors"
                        title="Undo"
                    >
                        <Undo size={18} />
                    </button>
                    <button
                        onClick={onReset}
                        className="p-2 hover:bg-white/10 rounded-full text-red-300 hover:text-red-200 transition-colors"
                        title="Reset All"
                    >
                        <RefreshCw size={18} />
                    </button>
                    <button
                        onClick={onRedo}
                        disabled={!canRedo}
                        className="p-2 hover:bg-white/10 rounded-full disabled:opacity-30 transition-colors"
                        title="Redo"
                    >
                        <Redo size={18} />
                    </button>
                </div>

                <button
                    onClick={onSave}
                    disabled={isSaving}
                    className="w-full btn-glass btn-glass--primary py-3 rounded-xl font-semibold flex items-center justify-center gap-2"
                >
                    <Save size={18} />
                    {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>

        </div>
    );
}

function SliderControl({ label, value, min, max, onChange }: { label: string, value: number, min: number, max: number, onChange: (v: number) => void }) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-xs">
                <span className="text-white/70">{label}</span>
                <span className="font-mono text-white/90">{value > 0 ? `+${value}` : value}</span>
            </div>
            <div className="flex items-center gap-3">
                <input
                    type="range"
                    min={min}
                    max={max}
                    value={value}
                    onChange={(e) => onChange(Number(e.target.value))}
                    className="flex-1 accent-white/80 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer"
                />
                <input
                    type="number"
                    value={value}
                    min={min}
                    max={max}
                    onChange={(e) => onChange(Number(e.target.value))}
                    className="w-12 bg-white/10 border border-white/10 rounded px-1 py-0.5 text-xs text-center text-white focus:outline-none focus:border-white/30"
                />
            </div>
        </div>
    );
}

function ControlButton({ onClick, icon: Icon, label, active, disabled }: { onClick?: () => void; icon: React.ComponentType<{ size?: number }>; label: string; active?: boolean; disabled?: boolean }) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-colors ${active ? 'bg-white/20 text-white' : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                } ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
            title={label}
        >
            <Icon size={18} />
            <span className="text-[10px]">{label}</span>
        </button>
    );
}
