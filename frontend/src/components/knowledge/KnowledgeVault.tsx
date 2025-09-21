'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function KnowledgeVault() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Knowledge Vault</CardTitle>
      </CardHeader>
      <CardContent>
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Knowledge vault will be implemented here
        </div>
      </CardContent>
    </Card>
  );
}
