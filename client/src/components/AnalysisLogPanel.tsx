import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Terminal, AlertCircle, Info, AlertTriangle, Bug } from 'lucide-react';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  stage: string;
  message: string;
  details?: Record<string, unknown>;
}

interface AnalysisLogResponse {
  document_id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  entries: LogEntry[];
}

const levelIcons: Record<string, React.ReactNode> = {
  debug: <Bug className="h-3 w-3" />,
  info: <Info className="h-3 w-3" />,
  warning: <AlertTriangle className="h-3 w-3" />,
  error: <AlertCircle className="h-3 w-3" />,
};

const levelColors: Record<string, string> = {
  debug: 'text-gray-500',
  info: 'text-blue-500',
  warning: 'text-yellow-500',
  error: 'text-red-500',
};

const statusColors: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function AnalysisLogPanel({ documentId }: { documentId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analysis-logs', documentId],
    queryFn: async () => {
      const { data } = await api.get<AnalysisLogResponse>(`/documents/${documentId}/analysis-logs`);
      return data;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'in_progress' ? 2000 : false;
    },
  });

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <AlertCircle className="h-8 w-8 mx-auto text-destructive mb-2" />
          <p className="text-sm text-muted-foreground">Failed to load analysis logs</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">AI Reasoning Log</CardTitle>
          </div>
          <Badge variant="secondary" className={cn('capitalize', statusColors[data?.status || 'not_started'])}>
            {data?.status?.replace('_', ' ') || 'Not Started'}
          </Badge>
        </div>
        <CardDescription>
          Real-time view of the AI agent's analysis process
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] w-full rounded-md border bg-slate-950 p-4">
          {!data?.entries.length ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              <div className="text-center">
                <Terminal className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No analysis logs yet.</p>
                <p className="text-xs mt-1">Click "Analyze Document" to start analysis.</p>
              </div>
            </div>
          ) : (
            <div className="font-mono text-xs space-y-1">
              {data.entries.map((entry) => (
                <div key={entry.id} className="text-slate-300">
                  <div className="flex gap-2">
                    <span className="text-slate-500 shrink-0">{formatTime(entry.timestamp)}</span>
                    <span className={cn('shrink-0', levelColors[entry.level])}>
                      [{entry.level.toUpperCase().padEnd(7)}]
                    </span>
                    <span className="text-slate-400 shrink-0">[{entry.stage}]</span>
                    <span className="text-slate-200">{entry.message}</span>
                  </div>
                  {entry.details && entry.stage === 'ai_response' && (entry.details as { response?: string }).response && (
                    <div className="ml-8 mt-1 mb-2 p-2 bg-slate-900 rounded border border-slate-700 whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                      <span className="text-emerald-400">{String((entry.details as { response?: string }).response)}</span>
                      {(entry.details as { truncated?: boolean }).truncated && (
                        <div className="text-yellow-400 mt-2 text-[10px]">
                          [Response truncated - showing {String((entry.details as { response?: string }).response).length} of {(entry.details as { total_length?: number }).total_length} characters]
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {data.status === 'in_progress' && (
                <div className="flex gap-2 text-slate-300 animate-pulse">
                  <span className="text-slate-500">...</span>
                  <span className="text-blue-400">Processing...</span>
                </div>
              )}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
