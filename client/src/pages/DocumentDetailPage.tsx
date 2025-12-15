import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  FileText,
  ArrowLeft,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MessageSquare,
  GitBranch,
  Clock,
  AlertCircle,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  Eye,
  FileSearch,
  X,
} from 'lucide-react';
import { useDocument, useDocumentFeedback, useAnalyzeDocument, useAcceptFeedback, useRejectFeedback } from '@/hooks/useDocuments';
import ChatPanel from '@/components/ChatPanel';
import { ValidationDashboard } from '@/components/testing';
import ParameterGraph from '@/components/ParameterGraph';
import AnalysisLogPanel from '@/components/AnalysisLogPanel';
import SemanticIRPanel from '@/components/SemanticIRPanel';
import { ShareDialog } from '@/components/documents/ShareDialog';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import type { FeedbackItem } from '@/types/api';

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  uploaded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  converted: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  analyzing: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  analyzed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  exported: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
};

const severityIcons: Record<string, React.ReactNode> = {
  low: <Lightbulb className="h-4 w-4 text-blue-500" />,
  medium: <AlertCircle className="h-4 w-4 text-yellow-500" />,
  high: <AlertTriangle className="h-4 w-4 text-orange-500" />,
  critical: <XCircle className="h-4 w-4 text-red-500" />,
};

const severityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const feedbackStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-gray-100 text-gray-800',
};

// Wrapper component to handle share dialog with authorization
function ShareDialogWrapper({ documentId, onShareUpdate }: { documentId: string; onShareUpdate: () => void }) {
  const { user, hasPermission } = useAuth();
  
  // Only show share button if user can share documents
  if (!user || !hasPermission('SHARE')) {
    return null;
  }

  // Note: Additional owner check will be done on the backend
  // Frontend just checks if user has the SHARE permission
  return (
    <ShareDialog
      documentId={documentId}
      currentSharedGroups={[]} // Will be populated from document data
      currentVisibility="private" // Will be populated from document data
      onShareUpdate={onShareUpdate}
    />
  );
}

function FeedbackRow({
  item,
  onAccept,
  onReject,
  isAccepting,
  isRejecting,
  isExpanded,
  onToggleExpand,
  onShowInDocument,
}: {
  item: FeedbackItem;
  onAccept: () => void;
  onReject: () => void;
  isAccepting: boolean;
  isRejecting: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onShowInDocument: () => void;
}) {
  // Create a short summary from the description (first 60 chars)
  const shortSummary = item.description && item.description.length > 60
    ? item.description.substring(0, 60) + '...'
    : (item.description || 'No description available');

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={onToggleExpand}
      >
        <TableCell>
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
            {severityIcons[item.severity]}
            <Badge variant="secondary" className={cn('capitalize', severityColors[item.severity])}>
              {item.severity}
            </Badge>
          </div>
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-muted-foreground">{shortSummary}</p>
            </div>
            {item.original_text && (
              <TooltipProvider>
                <Tooltip delayDuration={200}>
                  <TooltipTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 shrink-0"
                    >
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent
                    side="left"
                    className="max-w-md p-4"
                    sideOffset={5}
                  >
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-muted-foreground">Document Excerpt</p>
                      <div className="bg-destructive/10 border border-destructive/20 rounded p-2 max-h-48 overflow-y-auto">
                        <p className="text-sm font-mono whitespace-pre-wrap break-words">
                          {item.original_text}
                        </p>
                      </div>
                      {item.location && (
                        <p className="text-xs text-muted-foreground italic">
                          Location: {item.location}
                        </p>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </TableCell>
        <TableCell className="hidden md:table-cell">
          {item.location || '—'}
        </TableCell>
        <TableCell>
          <Badge variant="secondary" className={cn('capitalize', feedbackStatusColors[item.status])}>
            {item.status}
          </Badge>
        </TableCell>
        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
          <div className="flex justify-end gap-2">
            {item.original_text && (
              <Button
                size="sm"
                variant="outline"
                onClick={onShowInDocument}
              >
                <FileSearch className="h-4 w-4 mr-1" />
                Show in Doc
              </Button>
            )}
            {item.status === 'pending' && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onAccept}
                  disabled={isAccepting || isRejecting}
                >
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Accept
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onReject}
                  disabled={isAccepting || isRejecting}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Reject
                </Button>
              </>
            )}
          </div>
        </TableCell>
      </TableRow>
      {isExpanded && (
        <TableRow>
          <TableCell colSpan={5} className="bg-muted/30">
            <div className="p-4 space-y-4">
              <div>
                <h4 className="text-sm font-semibold mb-2">Full Description</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {item.description || 'No description available'}
                </p>
              </div>

              {item.original_text && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">Original Text</h4>
                  <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3">
                    <p className="text-sm font-mono whitespace-pre-wrap">{item.original_text}</p>
                  </div>
                </div>
              )}

              {item.suggested_text && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">Suggested Text</h4>
                  <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3">
                    <p className="text-sm font-mono whitespace-pre-wrap">{item.suggested_text}</p>
                  </div>
                </div>
              )}

              {item.policy_reference && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">Policy Reference</h4>
                  <Badge variant="outline" className="font-mono">
                    {item.policy_reference}
                  </Badge>
                </div>
              )}

              {item.rejection_reason && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">Rejection Reason</h4>
                  <p className="text-sm text-muted-foreground italic">{item.rejection_reason}</p>
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function DocumentViewer({
  markdown,
  highlightText,
  onClose,
}: {
  markdown: string | null;
  highlightText: string | null;
  onClose: () => void;
}) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  if (!markdown) {
    return (
      <Card className="h-full">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Document Content</CardTitle>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No markdown content available</p>
        </CardContent>
      </Card>
    );
  }

  // Pre-process markdown to add highlight tags
  const processedMarkdown = useMemo(() => {
    if (!highlightText || !markdown) return markdown;

    // Escape special regex characters
    const escapedText = highlightText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // Try exact match first
    const exactRegex = new RegExp(escapedText, 'g');
    if (exactRegex.test(markdown)) {
      console.log('Using exact match for highlighting');
      return markdown.replace(
        exactRegex,
        `<mark id="highlighted-section" class="bg-yellow-300 dark:bg-yellow-700 px-2 py-1 rounded font-bold border-2 border-yellow-500 shadow-md">$&</mark>`
      );
    }

    // Try normalized match (remove extra whitespace, newlines)
    const normalizedHighlight = highlightText.replace(/\s+/g, ' ').trim();
    const normalizedMarkdown = markdown.replace(/\s+/g, ' ');
    const normalizedEscaped = normalizedHighlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const normalizedRegex = new RegExp(normalizedEscaped, 'g');

    if (normalizedRegex.test(normalizedMarkdown)) {
      console.log('Using normalized match for highlighting');
      // Find the original text with its formatting
      const match = normalizedRegex.exec(normalizedMarkdown);
      if (match) {
        const startIndex = match.index;
        // Find corresponding position in original markdown
        let charCount = 0;
        let origIndex = 0;
        for (let i = 0; i < markdown.length && charCount < startIndex; i++) {
          if (!/\s/.test(markdown[i]) || normalizedMarkdown[charCount] === ' ') {
            charCount++;
          }
          origIndex = i;
        }

        // Use a simpler approach: just mark the first occurrence we can find
        const words = normalizedHighlight.split(/\s+/).slice(0, 5).join('\\s+');
        const flexibleRegex = new RegExp(words, 'i');
        return markdown.replace(
          flexibleRegex,
          `<mark id="highlighted-section" class="bg-yellow-300 dark:bg-yellow-700 px-2 py-1 rounded font-bold border-2 border-yellow-500 shadow-md">$&</mark>`
        );
      }
    }

    // Try partial match with first few words
    const firstWords = highlightText.split(/\s+/).slice(0, 5).join('\\s+');
    const partialRegex = new RegExp(firstWords.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');

    console.log('Using partial match (first 5 words) for highlighting');
    return markdown.replace(
      partialRegex,
      `<mark id="highlighted-section" class="bg-yellow-300 dark:bg-yellow-700 px-2 py-1 rounded font-bold border-2 border-yellow-500 shadow-md">$&</mark>`
    );
  }, [markdown, highlightText]);

  // Scroll to highlighted section on mount
  useEffect(() => {
    if (highlightText && scrollContainerRef.current) {
      // Use setTimeout to ensure content is rendered first
      const timer = setTimeout(() => {
        const container = scrollContainerRef.current;
        const element = container?.querySelector('#highlighted-section');

        console.log('DocumentViewer scroll effect:', {
          hasHighlightText: !!highlightText,
          hasContainer: !!container,
          hasElement: !!element,
          highlightTextPreview: highlightText?.substring(0, 50),
        });

        if (element && container) {
          const elementTop = (element as HTMLElement).offsetTop;
          const containerHeight = container.clientHeight;
          const elementHeight = (element as HTMLElement).clientHeight;

          // Calculate the scroll position to center the element
          const scrollPosition = elementTop - (containerHeight / 2) + (elementHeight / 2);

          console.log('Scrolling to position:', scrollPosition, 'elementTop:', elementTop);

          container.scrollTo({
            top: scrollPosition,
            behavior: 'smooth'
          });
        }
      }, 150);

      return () => clearTimeout(timer);
    }
  }, [highlightText, processedMarkdown]);

  return (
    <Card className="flex flex-col h-[calc(100vh-8rem)]">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle>Document Content</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {highlightText && (
          <CardDescription>
            Highlighting: "{highlightText.substring(0, 60)}..."
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="flex-1 min-h-0 p-0">
        <div
          ref={scrollContainerRef}
          className="h-full overflow-y-auto border-t prose prose-sm dark:prose-invert max-w-none p-6"
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeRaw, rehypeKatex]}
          >
            {processedMarkdown}
          </ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DocumentDetailPage() {
  const { id, tab } = useParams<{ id: string; tab?: string }>();
  const navigate = useNavigate();
  const currentTab = tab || 'issues';
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [selectedSemanticItem, setSelectedSemanticItem] = useState<{text: string; type: string} | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const { data: document, isLoading: docLoading, isError: docError, refetch } = useDocument(id);
  const { data: feedbackData, isLoading: feedbackLoading } = useDocumentFeedback(id);
  const analyzeMutation = useAnalyzeDocument();
  const acceptMutation = useAcceptFeedback();
  const rejectMutation = useRejectFeedback();

  // Poll for document status when analyzing
  useEffect(() => {
    if (!isPolling || !id) return;

    const interval = setInterval(async () => {
      const result = await refetch();
      const doc = result.data;

      if (doc?.status === 'analyzed') {
        setIsPolling(false);
        toast.success('Analysis completed successfully!');
      } else if (doc?.status === 'analysis_failed') {
        setIsPolling(false);
        toast.error('Analysis failed. Check the logs for details.');
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [isPolling, id, refetch]);

  const handleTabChange = (value: string) => {
    navigate(`/documents/${id}/${value}`);
  };

  const handleAnalyze = async () => {
    if (!id) return;
    setAnalysisError(null);

    toast.promise(
      analyzeMutation.mutateAsync({ documentId: id }).then(() => {
        refetch();
        setIsPolling(true);
      }),
      {
        loading: 'Starting analysis...',
        success: 'Analysis started successfully. Checking status...',
        error: (err) => {
          const errorMessage = err instanceof Error
            ? err.message
            : 'Analysis failed. Please try again.';
          setAnalysisError(errorMessage);
          return `Analysis failed: ${errorMessage}`;
        },
      }
    );
  };

  const toggleRowExpansion = (itemId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (docLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (docError || !document) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <CardTitle className="text-lg mb-2">Document not found</CardTitle>
            <CardDescription className="mb-4">
              The document you're looking for doesn't exist or has been deleted.
            </CardDescription>
            <Button asChild>
              <Link to="/documents">Back to Documents</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="mb-4">
          <Link to="/documents">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Documents
          </Link>
        </Button>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="h-14 w-14 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <FileText className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{document.title}</h1>
              <div className="flex items-center gap-3 mt-1">
                <Badge variant="secondary" className={cn('capitalize', statusColors[document.status])}>
                  {document.status}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  v{document.version}
                </span>
                <span className="text-sm text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDate(document.updated_at)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <ShareDialogWrapper 
              documentId={document.id}
              onShareUpdate={refetch}
            />
            <Button 
              onClick={handleAnalyze} 
              disabled={analyzeMutation.isPending || document.status === 'analyzing'}
            >
              <Play className="h-4 w-4 mr-2" />
              {analyzeMutation.isPending || document.status === 'analyzing' 
                ? 'Analyzing...' 
                : 'Analyze Document'}
            </Button>
          </div>
        </div>

        {document.description && (
          <p className="text-muted-foreground mt-4">{document.description}</p>
        )}

        {analysisError && (
          <Alert variant="destructive" className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Analysis Failed</AlertTitle>
            <AlertDescription>{analysisError}</AlertDescription>
          </Alert>
        )}

      </div>

      <Separator className="my-6" />

      <Tabs value={currentTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="issues" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            Issues
            {feedbackData && feedbackData.pending_count > 0 && (
              <Badge variant="secondary" className="ml-1">{feedbackData.pending_count}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="chat" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="graph" className="gap-2">
            <GitBranch className="h-4 w-4" />
            Graph
          </TabsTrigger>
          <TabsTrigger value="semantic" className="gap-2">
            <FileSearch className="h-4 w-4" />
            Semantic IR
          </TabsTrigger>
          <TabsTrigger value="testing" className="gap-2">
            <CheckCircle className="h-4 w-4" />
            Testing
          </TabsTrigger>
          <TabsTrigger value="logs" className="gap-2">
            <Clock className="h-4 w-4" />
            AI Logs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="issues" className="mt-6">
          <div className={cn("grid gap-6", selectedFeedback ? "grid-cols-2 items-start" : "grid-cols-1")}>
            <Card className="overflow-visible">
              <CardHeader>
                <CardTitle>Issue Blotter</CardTitle>
                <CardDescription>
                  Review and respond to AI-generated feedback
                  {selectedFeedback && " • Showing document preview"}
                </CardDescription>
              </CardHeader>
              <CardContent>
              {feedbackLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : !feedbackData || feedbackData.items.length === 0 ? (
                <div className="py-12 text-center">
                  <CheckCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <CardTitle className="text-lg mb-2">No issues found</CardTitle>
                  <CardDescription>
                    {document.status === 'converted' || document.status === 'uploaded'
                      ? 'Run analysis to generate feedback.'
                      : 'This document has no outstanding issues.'}
                  </CardDescription>
                </div>
              ) : (
                <>
                  <div className="flex gap-4 mb-4">
                    <div className="text-sm">
                      <span className="font-medium">{feedbackData.pending_count}</span>
                      <span className="text-muted-foreground ml-1">Pending</span>
                    </div>
                    <div className="text-sm">
                      <span className="font-medium text-green-600">{feedbackData.accepted_count}</span>
                      <span className="text-muted-foreground ml-1">Accepted</span>
                    </div>
                    <div className="text-sm">
                      <span className="font-medium text-gray-600">{feedbackData.rejected_count}</span>
                      <span className="text-muted-foreground ml-1">Rejected</span>
                    </div>
                  </div>

                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[100px]">Severity</TableHead>
                        <TableHead>Issue</TableHead>
                        <TableHead className="hidden md:table-cell">Location</TableHead>
                        <TableHead className="w-[100px]">Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {feedbackData.items.map((item) => (
                        <FeedbackRow
                          key={item.id}
                          item={item}
                          onAccept={() => {
                            toast.promise(
                              acceptMutation.mutateAsync({ documentId: id!, feedbackId: item.id }),
                              {
                                loading: 'Accepting feedback...',
                                success: 'Feedback accepted successfully',
                                error: (err) => `Failed to accept: ${err instanceof Error ? err.message : 'Unknown error'}`,
                              }
                            );
                          }}
                          onReject={() => {
                            toast.promise(
                              rejectMutation.mutateAsync({ documentId: id!, feedbackId: item.id }),
                              {
                                loading: 'Rejecting feedback...',
                                success: 'Feedback rejected successfully',
                                error: (err) => `Failed to reject: ${err instanceof Error ? err.message : 'Unknown error'}`,
                              }
                            );
                          }}
                          isAccepting={acceptMutation.isPending}
                          isRejecting={rejectMutation.isPending}
                          isExpanded={expandedRows.has(item.id)}
                          onToggleExpand={() => toggleRowExpansion(item.id)}
                          onShowInDocument={() => setSelectedFeedback(item)}
                        />
                      ))}
                    </TableBody>
                  </Table>
                </>
              )}
            </CardContent>
          </Card>

          {selectedFeedback && (
            <div className="sticky top-6">
              <DocumentViewer
                markdown={document.markdown_content}
                highlightText={selectedFeedback.original_text}
                onClose={() => setSelectedFeedback(null)}
              />
            </div>
          )}
          </div>
        </TabsContent>

        <TabsContent value="chat" className="mt-6">
          <ChatPanel documentId={id!} />
        </TabsContent>

        <TabsContent value="graph" className="mt-6">
          <ParameterGraph documentId={id!} />
        </TabsContent>

        <TabsContent value="semantic" className="mt-6">
          <div className={cn("grid gap-6", selectedSemanticItem ? "grid-cols-2 items-start" : "grid-cols-1")}>
            <div>
              <SemanticIRPanel
                documentId={id!}
                onSelectItem={(text, type) => setSelectedSemanticItem({text, type})}
              />
            </div>
            {selectedSemanticItem && (
              <div className="sticky top-6">
                <DocumentViewer
                  markdown={document?.markdown_content || null}
                  highlightText={selectedSemanticItem.text}
                  onClose={() => setSelectedSemanticItem(null)}
                />
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="testing" className="mt-6">
          <ValidationDashboard documentId={id!} />
        </TabsContent>

        <TabsContent value="logs" className="mt-6">
          <AnalysisLogPanel documentId={id!} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
