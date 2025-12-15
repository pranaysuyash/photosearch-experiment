import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, MapPin, FileText, Settings, Hash } from 'lucide-react';

interface MetadataField {
  category: string;
  icon: React.ComponentType<{ size?: number }>;
  fields: Array<{
    name: string;
    type: 'string' | 'number' | 'date' | 'boolean';
    examples: string[];
    description: string;
  }>;
}

const METADATA_FIELDS: MetadataField[] = [
  {
    category: 'Camera & Lens',
    icon: Camera,
    fields: [
      {
        name: 'camera.make',
        type: 'string',
        examples: ['"Canon"', '"Sony"', '"Nikon"'],
        description: 'Camera manufacturer'
      },
      {
        name: 'camera.model',
        type: 'string',
        examples: ['"EOS R5"', '"A7III"', '"D850"'],
        description: 'Camera model name'
      },
      {
        name: 'lens.focal_length',
        type: 'number',
        examples: ['50', '85', '24-70'],
        description: 'Focal length in mm'
      },
      {
        name: 'lens.aperture',
        type: 'number',
        examples: ['1.4', '2.8', '4.0'],
        description: 'Maximum aperture (f-stop)'
      }
    ]
  },
  {
    category: 'Time & Location',
    icon: MapPin,
    fields: [
      {
        name: 'date.taken',
        type: 'date',
        examples: ['"2023-01-01"', '"2024-06-01"'],
        description: 'Date photo was taken'
      },
      {
        name: 'gps.city',
        type: 'string',
        examples: ['"San Francisco"', '"Paris"', '"Tokyo"'],
        description: 'City where photo was taken'
      },
      {
        name: 'gps.latitude',
        type: 'number',
        examples: ['37.7749', '48.8566', '35.6762'],
        description: 'GPS latitude'
      },
      {
        name: 'gps.longitude',
        type: 'number',
        examples: ['-122.4194', '2.3522', '139.6503'],
        description: 'GPS longitude'
      }
    ]
  },
  {
    category: 'File Properties',
    icon: FileText,
    fields: [
      {
        name: 'file.size',
        type: 'number',
        examples: ['5000000', '10000000'],
        description: 'File size in bytes'
      },
      {
        name: 'file.extension',
        type: 'string',
        examples: ['".jpg"', '".png"', '".raw"'],
        description: 'File extension'
      },
      {
        name: 'image.width',
        type: 'number',
        examples: ['1920', '3840', '4000'],
        description: 'Image width in pixels'
      },
      {
        name: 'image.height',
        type: 'number',
        examples: ['1080', '2160', '3000'],
        description: 'Image height in pixels'
      }
    ]
  },
  {
    category: 'Technical Settings',
    icon: Settings,
    fields: [
      {
        name: 'exif.iso',
        type: 'number',
        examples: ['100', '800', '3200'],
        description: 'ISO sensitivity'
      },
      {
        name: 'exif.shutter_speed',
        type: 'string',
        examples: ['"1/1000"', '"1/60"', '"2s"'],
        description: 'Shutter speed'
      },
      {
        name: 'exif.exposure_bias',
        type: 'number',
        examples: ['-1.0', '0', '+2.0'],
        description: 'Exposure compensation'
      },
      {
        name: 'exif.flash',
        type: 'string',
        examples: ['"No Flash"', '"Flash"', '"Auto"'],
        description: 'Flash setting'
      }
    ]
  }
];

interface MetadataFieldAutocompleteProps {
  query: string;
  onFieldSelected: (field: string) => void;
  isVisible: boolean;
}

export const MetadataFieldAutocomplete = ({
  query,
  onFieldSelected,
  isVisible
}: MetadataFieldAutocompleteProps) => {
  const [suggestions, setSuggestions] = useState<Array<{
    field: any;
    category: string;
    icon: React.ComponentType<{ size?: number }>;
  }>>([]);


  useEffect(() => {
    if (!isVisible || !query) {
      setSuggestions([]);
      return;
    }

    // Detect if user is typing a field name
    const lastWord = query.split(' ').pop() || '';
    
    if (lastWord.length < 2) {
      setSuggestions([]);
      return;
    }

    let matches: Array<{
      field: any;
      category: string;
      icon: React.ComponentType<{ size?: number }>;
    }> = [];

    if (lastWord.includes('.')) {
      // User is typing a field path like "camera."
      matches = METADATA_FIELDS.flatMap(cat =>
        cat.fields
          .filter(field =>
            field.name.toLowerCase().startsWith(lastWord.toLowerCase())
          )
          .map(field => ({ field, category: cat.category, icon: cat.icon }))
      );
    } else {
      // Fuzzy search across all field names and descriptions
      matches = METADATA_FIELDS.flatMap(cat =>
        cat.fields
          .filter(field =>
            field.name.toLowerCase().includes(lastWord.toLowerCase()) ||
            field.description.toLowerCase().includes(lastWord.toLowerCase()) ||
            cat.category.toLowerCase().includes(lastWord.toLowerCase())
          )
          .map(field => ({ field, category: cat.category, icon: cat.icon }))
      );
    }

    // Limit to top 8 suggestions
    setSuggestions(matches.slice(0, 8));
  }, [query, isVisible]);

  const handleFieldClick = (fieldName: string) => {
    // Replace the last word in the query with the selected field
    const words = query.split(' ');
    words[words.length - 1] = fieldName;
    const newQuery = words.join(' ');
    onFieldSelected(newQuery);
  };

  if (!isVisible || suggestions.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        className="absolute top-full mt-2 w-full bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto"
      >
        <div className="p-3 border-b border-gray-100">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Hash size={14} />
            Available Metadata Fields
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Click to insert field into your query
          </p>
        </div>

        <div className="p-2">
          {suggestions.map((suggestion, idx) => {
            const Icon = suggestion.icon;
            return (
              <motion.button
                key={`${suggestion.field.name}-${idx}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                onClick={() => handleFieldClick(suggestion.field.name)}
                className="w-full text-left p-3 rounded-lg hover:bg-blue-50 transition-colors group border border-transparent hover:border-blue-200"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 p-1.5 rounded-md bg-gray-100 group-hover:bg-blue-100 transition-colors">
                    <Icon size={14} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <code className="text-sm font-mono font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                        {suggestion.field.name}
                      </code>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                        {suggestion.field.type}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2">
                      {suggestion.field.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-1">
                      <span className="text-xs text-gray-500">Examples:</span>
                      {suggestion.field.examples.map((example: string, exIdx: number) => (
                        <code
                          key={exIdx}
                          className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded"
                        >
                          {example}
                        </code>
                      ))}
                    </div>
                    
                    <div className="text-xs text-gray-400 mt-1">
                      {suggestion.category}
                    </div>
                  </div>
                </div>
              </motion.button>
            );
          })}
        </div>

        <div className="p-3 border-t border-gray-100 bg-gray-50/50">
          <div className="text-xs text-gray-500">
            <strong>Pro tip:</strong> Use operators like <code>=</code>, <code>&gt;</code>, <code>LIKE</code>, <code>AND</code>, <code>OR</code> to build powerful queries
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};