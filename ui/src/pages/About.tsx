/**
 * About Page
 * 
 * Information about the application
 */

const About = () => {
  return (
    <div className='mx-auto w-full max-w-3xl'>
      <div className='mb-6'>
        <h1 className='text-2xl font-semibold tracking-tight text-foreground'>
          About Living Museum
        </h1>
        <p className='text-sm text-muted-foreground'>
          Your intelligent photo workstation.
        </p>
      </div>

      <div className='glass-surface rounded-2xl p-5 sm:p-7 space-y-6'>
        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>
            What is Living Museum?
          </h2>
          <p className='text-sm text-muted-foreground leading-relaxed'>
            Living Museum helps you search and rediscover your photo library using
            metadata, semantics, OCR, and faces — across local folders and connected cloud sources.
          </p>
        </section>

        <section className='space-y-3'>
          <h2 className='text-sm font-semibold text-foreground'>Key features</h2>
          <ul className='grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-muted-foreground'>
            <li className='glass-surface rounded-xl px-3 py-2'>Search + intent</li>
            <li className='glass-surface rounded-xl px-3 py-2'>Face clustering</li>
            <li className='glass-surface rounded-xl px-3 py-2'>OCR text search</li>
            <li className='glass-surface rounded-xl px-3 py-2'>Saved searches</li>
          </ul>
        </section>

        <section className='space-y-3'>
          <h2 className='text-sm font-semibold text-foreground'>Tech</h2>
          <div className='grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-muted-foreground'>
            <div className='glass-surface rounded-xl px-3 py-2'>
              <span className='font-semibold text-foreground'>Frontend:</span>{' '}
              React, TypeScript, Vite
            </div>
            <div className='glass-surface rounded-xl px-3 py-2'>
              <span className='font-semibold text-foreground'>Backend:</span>{' '}
              Python, FastAPI
            </div>
            <div className='glass-surface rounded-xl px-3 py-2'>
              <span className='font-semibold text-foreground'>DB:</span> SQLite
              + LanceDB
            </div>
            <div className='glass-surface rounded-xl px-3 py-2'>
              <span className='font-semibold text-foreground'>UI:</span> Tailwind
              + glass surfaces
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default About;
