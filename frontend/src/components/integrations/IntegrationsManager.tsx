'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function IntegrationsManager() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Integrations Manager</CardTitle>
      </CardHeader>
      <CardContent>
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Integrations manager will be implemented here
        </div>
      </CardContent>
    </Card>
  );
}
