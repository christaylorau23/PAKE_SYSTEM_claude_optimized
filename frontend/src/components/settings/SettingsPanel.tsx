'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function SettingsPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Settings</CardTitle>
      </CardHeader>
      <CardContent>
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Settings panel will be implemented here
        </div>
      </CardContent>
    </Card>
  );
}
