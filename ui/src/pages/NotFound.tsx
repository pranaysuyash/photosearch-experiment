/**
 * Not Found Page
 * 
 * 404 Error page
 */

import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <div className='flex items-center justify-center min-h-[70vh] px-4'>
      <div className='text-center max-w-md'>
        <div className='text-6xl font-bold text-destructive mb-2'>404</div>
        <div className='text-lg font-semibold text-foreground mb-2'>
          Page not found
        </div>
        <div className='text-sm text-muted-foreground mb-6'>
          The page you’re looking for doesn’t exist or has been moved.
        </div>
        <Link to='/' className='btn-glass btn-glass--primary text-sm px-5 py-2'>
          Return to Library
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
