import { cn } from '@/lib/utils';

interface LoadingProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export function Loading({
  className,
  size = 'md',
  text,
  ...props
}: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div
      className={cn('flex items-center justify-center p-8', className)}
      {...props}
    >
      <div className='flex flex-col items-center space-y-4'>
        <div
          className={cn(
            'animate-spin rounded-full border-4 border-gray-300 border-t-blue-600',
            sizeClasses[size]
          )}
          role='status'
          aria-label={text || 'Loading'}
        />
        {text && (
          <p className='text-sm text-gray-600 dark:text-gray-400'>{text}</p>
        )}
      </div>
    </div>
  );
}

export function PageLoading() {
  return (
    <div className='min-h-screen flex items-center justify-center'>
      <Loading size='lg' text='Loading...' />
    </div>
  );
}

export function ComponentLoading() {
  return (
    <div className='flex items-center justify-center p-4'>
      <div
        className='animate-spin rounded-full border-4 border-gray-300 border-t-blue-600 w-8 h-8'
        role='status'
        aria-label='Loading'
      />
    </div>
  );
}

export function InlineLoading() {
  return <Loading size='sm' className='p-2' />;
}
