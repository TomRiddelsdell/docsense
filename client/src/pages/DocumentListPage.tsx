import { useState } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FileText, Upload, Search, ChevronLeft, ChevronRight, FolderOpen, RefreshCw, Download, Eye } from 'lucide-react';
import { useDocuments, useDocument } from '@/hooks/useDocuments';
import { cn } from '@/lib/utils';
import api from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import type { DocumentSummary } from '@/types/api';

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  uploaded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  converted: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  analyzing: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  analyzed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  exported: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

export default function DocumentListPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  
  const { data, isLoading, isError, error } = useDocuments({
    page,
    per_page: 10,
    status: status !== 'all' ? status : undefined,
  });

  const { data: previewDoc } = useDocument(previewDocId || undefined);

  const filteredDocuments = data?.documents.filter(doc =>
    !search || doc.title.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFileType = (format: string): string => {
    return format.replace('application/', '').replace('text/', '').toUpperCase();
  };

  const handleRetry = async (docId: string) => {
    setRetryingId(docId);
    try {
      await api.post(`/documents/${docId}/reset`);
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err) {
      console.error('Failed to reset document:', err);
    } finally {
      setRetryingId(null);
    }
  };

  const handleDownload = (docId: string, title: string) => {
    const link = document.createElement('a');
    link.href = `${api.defaults.baseURL}/documents/${docId}/download`;
    link.download = title;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalPages = data ? Math.ceil(data.total / 10) : 1;

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-destructive mb-4">
              {error instanceof Error ? error.message : 'Failed to load documents'}
            </p>
            <Button onClick={() => window.location.reload()}>Try Again</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground">
            Manage and analyze your trading algorithm documents
          </p>
        </div>
        <Button asChild>
          <Link to="/documents/upload" className="gap-2">
            <Upload className="h-4 w-4" />
            Upload Document
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="analyzed">Analyzed</SelectItem>
                <SelectItem value="exported">Exported</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-1/3" />
                    <Skeleton className="h-3 w-1/4" />
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="py-12 text-center">
              <FolderOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <CardTitle className="text-lg mb-2">No documents found</CardTitle>
              <CardDescription className="mb-4">
                {search 
                  ? 'No documents match your search criteria.'
                  : 'Upload your first document to get started.'}
              </CardDescription>
              <Button asChild>
                <Link to="/documents/upload" className="gap-2">
                  <Upload className="h-4 w-4" />
                  Upload Document
                </Link>
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden md:table-cell">Type</TableHead>
                    <TableHead className="hidden sm:table-cell">Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDocuments.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <Link 
                          to={`/documents/${doc.id}`}
                          className="flex items-center gap-3 hover:underline"
                        >
                          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                            <FileText className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium">{doc.title}</p>
                          </div>
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="secondary"
                          className={cn('capitalize', statusColors[doc.status])}
                        >
                          {doc.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-sm">
                        {formatFileType(doc.original_format)}
                      </TableCell>
                      <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                        {formatDate(doc.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {(doc.status === 'analyzing' || doc.status === 'failed') && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRetry(doc.id)}
                              disabled={retryingId === doc.id}
                              className="gap-1"
                            >
                              <RefreshCw className={cn("h-3 w-3", retryingId === doc.id && "animate-spin")} />
                              {retryingId === doc.id ? 'Resetting...' : 'Retry'}
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(doc.id, doc.title)}
                            className="gap-1"
                            title="Download original file"
                          >
                            <Download className="h-3 w-3" />
                            Download
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPreviewDocId(doc.id)}
                            className="gap-1"
                            title="Preview markdown"
                          >
                            <Eye className="h-3 w-3" />
                            Preview
                          </Button>
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/documents/${doc.id}`}>View</Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {data && totalPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {totalPages} ({data.total} documents)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Markdown Preview Dialog */}
      <Dialog open={previewDocId !== null} onOpenChange={() => setPreviewDocId(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>{previewDoc?.title || 'Document Preview'}</DialogTitle>
            <DialogDescription>
              Rendered markdown content
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto prose prose-sm dark:prose-invert max-w-none p-6 border rounded-md">
            {previewDoc?.markdown_content ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeRaw, rehypeKatex]}
              >
                {previewDoc.markdown_content}
              </ReactMarkdown>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <p>Loading markdown content...</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
