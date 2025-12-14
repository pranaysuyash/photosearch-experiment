import { motion } from 'framer-motion';
import { useState } from 'react';
import { Eye, Heart, Share2, Grid3X3, Sparkles } from 'lucide-react';
import '../modern-gallery.css';
import '../enhanced-animations.css';

interface ModernGalleryDemoProps {
  onUseModern: () => void;
}

export function ModernGalleryDemo({ onUseModern }: ModernGalleryDemoProps) {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);
  const [activeDemo, setActiveDemo] = useState('subgrid');

  const demoCards = [
    {
      id: 1,
      title: 'CSS Subgrid',
      description: 'Nested grid layouts with perfect alignment',
      color: 'bg-gradient-to-br from-purple-500 to-pink-500',
    },
    {
      id: 2,
      title: 'Scroll Transforms',
      description: 'Scroll-driven animations and transforms',
      color: 'bg-gradient-to-br from-blue-500 to-cyan-500',
    },
    {
      id: 3,
      title: 'Custom Easing',
      description: 'Bounce, elastic, and smooth easing functions',
      color: 'bg-gradient-to-br from-green-500 to-emerald-500',
    },
    {
      id: 4,
      title: '3D Transforms',
      description: 'Perspective and 3D rotation effects',
      color: 'bg-gradient-to-br from-orange-500 to-red-500',
    },
    {
      id: 5,
      title: 'Modern Hover',
      description: 'Enhanced hover states with overlays',
      color: 'bg-gradient-to-br from-indigo-500 to-purple-500',
    },
    {
      id: 6,
      title: 'Performance',
      description: 'GPU-accelerated animations',
      color: 'bg-gradient-to-br from-pink-500 to-rose-500',
    },
  ];

  const easingExamples = [
    {
      name: 'Smooth',
      fn: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      usage: 'General transitions',
    },
    {
      name: 'Bounce',
      fn: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      usage: 'Playful interactions',
    },
    {
      name: 'Elastic',
      fn: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
      usage: 'Dynamic feedback',
    },
    {
      name: 'Sharp',
      fn: 'cubic-bezier(0.4, 0, 0.2, 1)',
      usage: 'Quick interactions',
    },
    {
      name: 'Custom',
      fn: 'cubic-bezier(0.23, 1, 0.320, 1)',
      usage: 'Smooth reveals',
    },
  ];

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 py-12 px-4'>
      <div className='max-w-7xl mx-auto'>
        {/* Header */}
        <motion.div
          className='text-center mb-12'
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className='flex items-center justify-center gap-3 mb-4'>
            <Sparkles className='w-8 h-8 text-purple-600' />
            <h1 className='text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent'>
              Modern CSS Gallery Features
            </h1>
            <Sparkles className='w-8 h-8 text-pink-600' />
          </div>
          <p className='text-lg text-muted-foreground max-w-3xl mx-auto'>
            Explore cutting-edge CSS features including subgrid layouts,
            scroll-driven transforms, custom easing functions, and
            performance-optimized animations.
          </p>
        </motion.div>

        {/* Demo Navigation */}
        <div className='flex flex-wrap justify-center gap-2 mb-12'>
          {['subgrid', 'scroll', 'easing', 'transforms'].map((demo) => (
            <button
              key={demo}
              onClick={() => setActiveDemo(demo)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                activeDemo === demo
                  ? 'bg-purple-600 text-white shadow-lg'
                  : 'bg-white/80 text-gray-600 hover:bg-white hover:shadow-md'
              }`}
            >
              {demo.charAt(0).toUpperCase() + demo.slice(1)}
            </button>
          ))}
        </div>

        {/* Demo Showcase */}
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12'>
          {/* CSS Subgrid Demo */}
          {activeDemo === 'subgrid' && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className='bg-white rounded-2xl p-8 shadow-xl'
            >
              <h3 className='text-2xl font-bold mb-4 flex items-center gap-2'>
                <Grid3X3 className='w-6 h-6 text-purple-600' />
                CSS Subgrid Layout
              </h3>
              <div className='space-y-4'>
                <div className='modern-gallery-grid grid-min-200'>
                  {demoCards.slice(0, 4).map((card, i) => (
                    <div
                      key={card.id}
                      className='gallery-item p-6 text-white relative overflow-hidden cursor-pointer'
                      data-item-index={i % 20}
                      onMouseEnter={() => setHoveredCard(card.id)}
                      onMouseLeave={() => setHoveredCard(null)}
                    >
                      <div
                        className={`absolute inset-0 ${card.color} opacity-90`}
                      />
                      <div className='relative z-10'>
                        <h4 className='gallery-title text-lg font-bold mb-2'>
                          {card.title}
                        </h4>
                        <p className='gallery-path text-sm opacity-90'>
                          {card.description}
                        </p>
                        <motion.div
                          className='mt-4 flex gap-2'
                          initial={{ opacity: 0, y: 10 }}
                          animate={{
                            opacity: hoveredCard === card.id ? 1 : 0.7,
                            y: hoveredCard === card.id ? 0 : 10,
                          }}
                        >
                          <button
                            title='Like'
                            aria-label='Like'
                            className='p-2 bg-white/20 rounded-full backdrop-blur-sm'
                          >
                            <Heart size={16} aria-hidden='true' />
                          </button>
                          <button
                            title='Share'
                            aria-label='Share'
                            className='p-2 bg-white/20 rounded-full backdrop-blur-sm'
                          >
                            <Share2 size={16} aria-hidden='true' />
                          </button>
                          <button
                            title='Preview'
                            aria-label='Preview'
                            className='p-2 bg-white/20 rounded-full backdrop-blur-sm'
                          >
                            <Eye size={16} aria-hidden='true' />
                          </button>
                        </motion.div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className='text-sm text-gray-600'>
                  <p>
                    <strong>Features:</strong>
                  </p>
                  <ul className='list-disc list-inside mt-2 space-y-1'>
                    <li>Nested grid alignment</li>
                    <li>Automatic row/column spanning</li>
                    <li>Responsive grid templates</li>
                    <li>Subgrid inheritance</li>
                  </ul>
                </div>
              </div>
            </motion.div>
          )}

          {/* Scroll-Driven Transforms Demo */}
          {activeDemo === 'scroll' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className='bg-white rounded-2xl p-8 shadow-xl'
            >
              <h3 className='text-2xl font-bold mb-4 flex items-center gap-2'>
                <motion.div
                  className='w-6 h-6 bg-blue-600 rounded'
                  animate={{ rotate: 360 }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                />
                Scroll-Driven Animations
              </h3>
              <div className='space-y-6'>
                <div className='space-y-4 max-h-64 overflow-y-auto pr-4'>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <motion.div
                      key={i}
                      className='gallery-item p-4 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-xl border border-blue-200/50'
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      viewport={{ once: true }}
                    >
                      <div className='flex items-center gap-3'>
                        <motion.div
                          className='w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold'
                          whileHover={{ scale: 1.2, rotate: 180 }}
                          transition={{ type: 'spring', stiffness: 300 }}
                        >
                          {i}
                        </motion.div>
                        <div>
                          <p className='font-semibold text-gray-800 dark:text-gray-200'>
                            Scroll Item {i}
                          </p>
                          <p className='text-sm text-gray-600 dark:text-gray-400'>
                            Animates as it enters viewport
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className='text-sm text-gray-600'>
                  <p>
                    <strong>Features:</strong>
                  </p>
                  <ul className='list-disc list-inside mt-2 space-y-1'>
                    <li>Intersection Observer integration</li>
                    <li>Scroll-timeline animations</li>
                    <li>Progressive enhancement</li>
                    <li>Performance optimized</li>
                  </ul>
                </div>
              </div>
            </motion.div>
          )}

          {/* Custom Easing Functions Demo */}
          {activeDemo === 'easing' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className='bg-white rounded-2xl p-8 shadow-xl'
            >
              <h3 className='text-2xl font-bold mb-4 flex items-center gap-2'>
                <motion.div
                  className='w-6 h-6 bg-green-600 rounded'
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                Custom Easing Functions
              </h3>
              <div className='space-y-4'>
                <div className='grid gap-3'>
                  {easingExamples.map((easing, index) => (
                    <motion.div
                      key={easing.name}
                      className='flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg'
                      whileHover={{ scale: 1.02 }}
                    >
                      <div>
                        <p className='font-semibold text-sm'>{easing.name}</p>
                        <p className='text-xs text-gray-600 dark:text-gray-400'>
                          {easing.usage}
                        </p>
                      </div>
                      <motion.button
                        className={`px-3 py-1 bg-green-600 text-white text-xs rounded-full ease-custom-${
                          index + 1
                        } duration-600`}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Test
                      </motion.button>
                    </motion.div>
                  ))}
                </div>
                <div className='text-sm text-gray-600'>
                  <p>
                    <strong>Features:</strong>
                  </p>
                  <ul className='list-disc list-inside mt-2 space-y-1'>
                    <li>Smooth cubic-bezier curves</li>
                    <li>Bounce and elastic effects</li>
                    <li>Context-aware animations</li>
                    <li>Hardware acceleration</li>
                  </ul>
                </div>
              </div>
            </motion.div>
          )}

          {/* 3D Transforms Demo */}
          {activeDemo === 'transforms' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className='bg-white rounded-2xl p-8 shadow-xl'
            >
              <h3 className='text-2xl font-bold mb-4 flex items-center gap-2'>
                <motion.div
                  className='w-6 h-6 bg-orange-600 rounded preserve-3d'
                  animate={{ rotateX: [0, 180, 360] }}
                  transition={{ duration: 3, repeat: Infinity }}
                />
                3D Transforms & Effects
              </h3>
              <div className='space-y-6'>
                <div className='grid grid-cols-2 gap-4'>
                  {[1, 2, 3, 4].map((i) => (
                    <motion.div
                      key={i}
                      className='gallery-item aspect-square bg-gradient-to-br from-orange-400 to-red-500 rounded-xl cursor-pointer overflow-hidden perspective-1000'
                      whileHover={{
                        rotateX: 5,
                        rotateY: 5,
                        scale: 1.05,
                      }}
                      transition={{
                        type: 'spring',
                        stiffness: 300,
                        damping: 20,
                      }}
                    >
                      <div className='w-full h-full flex items-center justify-center text-white font-bold text-lg'>
                        3D {i}
                      </div>
                      <motion.div
                        className='absolute inset-0 bg-gradient-to-t from-black/50 to-transparent'
                        initial={{ opacity: 0 }}
                        whileHover={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                      />
                    </motion.div>
                  ))}
                </div>
                <div className='text-sm text-gray-600'>
                  <p>
                    <strong>Features:</strong>
                  </p>
                  <ul className='list-disc list-inside mt-2 space-y-1'>
                    <li>3D perspective transforms</li>
                    <li>Hardware-accelerated animations</li>
                    <li>Smooth hover transitions</li>
                    <li>Mobile-optimized effects</li>
                  </ul>
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Performance Comparison */}
        <motion.div
          className='bg-white rounded-2xl p-8 shadow-xl mb-12'
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <h3 className='text-2xl font-bold mb-6 flex items-center gap-2'>
            <motion.div
              className='w-6 h-6 bg-purple-600 rounded'
              animate={{
                background: [
                  'linear-gradient(45deg, #8b5cf6, #ec4899)',
                  'linear-gradient(45deg, #ec4899, #8b5cf6)',
                  'linear-gradient(45deg, #8b5cf6, #ec4899)',
                ],
              }}
              transition={{ duration: 3, repeat: Infinity }}
            />
            Performance & Browser Support
          </h3>
          <div className='grid md:grid-cols-3 gap-6'>
            <div className='text-center'>
              <div className='text-3xl font-bold text-green-600 mb-2'>
                60fps
              </div>
              <p className='text-sm text-gray-600'>Smooth animations</p>
            </div>
            <div className='text-center'>
              <div className='text-3xl font-bold text-blue-600 mb-2'>95%</div>
              <p className='text-sm text-gray-600'>Modern browser support</p>
            </div>
            <div className='text-center'>
              <div className='text-3xl font-bold text-purple-600 mb-2'>
                -30%
              </div>
              <p className='text-sm text-gray-600'>Reduced CPU usage</p>
            </div>
          </div>
        </motion.div>

        {/* CTA Section */}
        <motion.div
          className='text-center'
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}
        >
          <motion.button
            onClick={onUseModern}
            className='px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-lg font-semibold rounded-full shadow-xl hover:shadow-2xl transition-all'
            whileHover={{
              scale: 1.05,
              boxShadow: '0 25px 50px rgba(139, 92, 246, 0.3)',
            }}
            whileTap={{ scale: 0.95 }}
          >
            <div className='flex items-center gap-3'>
              <Sparkles className='w-5 h-5' />
              Use Modern Gallery
              <Sparkles className='w-5 h-5' />
            </div>
          </motion.button>
          <p className='text-sm text-muted-foreground mt-4'>
            Experience the future of web layouts and animations
          </p>
        </motion.div>
      </div>
    </div>
  );
}
