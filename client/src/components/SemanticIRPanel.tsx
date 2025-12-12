import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Download, AlertCircle, CheckCircle, AlertTriangle, Info, Eye } from 'lucide-react';
import { useDocumentSemanticIR } from '@/hooks/useDocuments';
import type { SemanticIR, ValidationIssue } from '@/types/api';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface SemanticIRPanelProps {
  documentId: string;
  onSelectItem?: (text: string, type: string) => void;
}

function ValidationIssueCard({
  issue,
  onSelectItem
}: {
  issue: ValidationIssue;
  onSelectItem?: (text: string, type: string) => void;
}) {
  const severityConfig = {
    error: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
    warning: { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
    info: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  };

  const config = severityConfig[issue.severity];
  const Icon = config.icon;

  // Extract a searchable text from the location or related entities
  const getSearchText = () => {
    // Try to extract entity IDs which might contain terms
    if (issue.related_entity_ids && issue.related_entity_ids.length > 0) {
      return issue.related_entity_ids[0];
    }
    // Otherwise use the location
    return issue.location;
  };

  return (
    <Alert className={`${config.bg} ${config.border} border-l-4 hover:shadow-md transition-shadow`}>
      <Icon className={`h-4 w-4 ${config.color}`} />
      <AlertDescription>
        <div className="space-y-1">
          <div className="font-semibold flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {issue.issue_type.replace(/_/g, ' ')}
            </Badge>
            <span className="flex-1">{issue.message}</span>
            {onSelectItem && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onSelectItem(getSearchText(), 'validation')}
                className="shrink-0 ml-2"
              >
                <Eye className="h-4 w-4 mr-1" />
                View
              </Button>
            )}
          </div>
          <div className="text-sm text-muted-foreground">
            Location: {issue.location}
          </div>
          {issue.suggestion && (
            <div className="text-sm mt-2 p-2 bg-white rounded border">
              <strong>Suggestion:</strong> {issue.suggestion}
            </div>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}

function FormulaRenderer({ latex }: { latex: string }) {
  try {
    const html = katex.renderToString(latex, {
      throwOnError: false,
      displayMode: true,
    });
    return <div dangerouslySetInnerHTML={{ __html: html }} className="overflow-x-auto" />;
  } catch (error) {
    return (
      <div className="bg-muted p-4 rounded-md overflow-x-auto">
        <code className="text-sm">{latex}</code>
      </div>
    );
  }
}

export default function SemanticIRPanel({ documentId, onSelectItem }: SemanticIRPanelProps) {
  const { data: ir, isLoading, isError } = useDocumentSemanticIR(documentId);

  const handleDownload = async (format: 'json' | 'llm-text' | 'markdown') => {
    try {
      const response = await fetch(
        `/api/documents/${documentId}/semantic-ir/download?format=${format}`,
        {
          headers: {
            'Accept': format === 'json' ? 'application/json' : 'text/plain',
          },
        }
      );

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `semantic_ir.${format === 'json' ? 'json' : 'txt'}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Semantic Analysis</CardTitle>
          <CardDescription>Loading semantic representation...</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError || !ir) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Semantic Analysis</CardTitle>
          <CardDescription>Failed to load semantic representation</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Could not extract semantic information from this document.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const stats = {
    sections: ir.sections?.length || 0,
    definitions: ir.definitions?.length || 0,
    formulae: ir.formulae?.length || 0,
    tables: ir.tables?.length || 0,
    issues: ir.validation_issues?.length || 0,
  };

  const errorCount = ir.validation_issues?.filter(i => i.severity === 'error').length || 0;
  const warningCount = ir.validation_issues?.filter(i => i.severity === 'warning').length || 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Semantic Analysis</CardTitle>
            <CardDescription>
              Structured extraction of definitions, formulas, and relationships
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleDownload('json')}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              <Download className="h-4 w-4" />
              Download JSON
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="text-center p-4 bg-muted rounded-lg">
            <div className="text-2xl font-bold">{stats.sections}</div>
            <div className="text-sm text-muted-foreground">Sections</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <div className="text-2xl font-bold">{stats.definitions}</div>
            <div className="text-sm text-muted-foreground">Definitions</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <div className="text-2xl font-bold">{stats.formulae}</div>
            <div className="text-sm text-muted-foreground">Formulas</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <div className="text-2xl font-bold">{stats.tables}</div>
            <div className="text-sm text-muted-foreground">Tables</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <div className="text-2xl font-bold">{stats.issues}</div>
            <div className="text-sm text-muted-foreground">Issues</div>
          </div>
        </div>

        <Tabs defaultValue="definitions" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="definitions">
              Definitions ({stats.definitions})
            </TabsTrigger>
            <TabsTrigger value="formulas">
              Formulas ({stats.formulae})
            </TabsTrigger>
            <TabsTrigger value="tables">
              Tables ({stats.tables})
            </TabsTrigger>
            <TabsTrigger value="validation">
              Validation
              {stats.issues > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {stats.issues}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="definitions" className="space-y-4 mt-4">
            {ir.definitions && ir.definitions.length > 0 ? (
              ir.definitions.map((def) => (
                <Card key={def.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">{def.term}</CardTitle>
                      {onSelectItem && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onSelectItem(def.term, 'definition')}
                          className="shrink-0"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View in Doc
                        </Button>
                      )}
                    </div>
                    {def.aliases && def.aliases.length > 0 && (
                      <div className="flex gap-1 mt-2">
                        {def.aliases.map((alias) => (
                          <Badge key={alias} variant="secondary" className="text-xs">
                            {alias}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">{def.definition}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Section: {def.section_id}
                    </p>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No definitions extracted from this document.
              </div>
            )}
          </TabsContent>

          <TabsContent value="formulas" className="space-y-4 mt-4">
            {ir.formulae && ir.formulae.length > 0 ? (
              ir.formulae.map((formula) => (
                <Card key={formula.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">
                        {formula.name || formula.id}
                      </CardTitle>
                      {onSelectItem && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onSelectItem(formula.latex, 'formula')}
                          className="shrink-0"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View in Doc
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="p-4 bg-white border rounded-md">
                      <FormulaRenderer latex={formula.latex} />
                    </div>
                    <details className="text-sm">
                      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                        Show LaTeX source
                      </summary>
                      <div className="bg-muted p-2 rounded-md mt-2 overflow-x-auto">
                        <code className="text-xs">{formula.latex}</code>
                      </div>
                    </details>
                    {formula.variables && formula.variables.length > 0 && (
                      <div>
                        <div className="text-sm font-medium mb-2">Variables:</div>
                        <div className="flex flex-wrap gap-1">
                          {formula.variables.map((v) => (
                            <Badge key={v} variant="outline" className="text-xs">
                              {v}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {formula.dependencies && formula.dependencies.length > 0 && (
                      <div>
                        <div className="text-sm font-medium mb-2">Dependencies:</div>
                        <div className="flex flex-wrap gap-1">
                          {formula.dependencies.map((d) => (
                            <Badge key={d} variant="secondary" className="text-xs">
                              {d}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Section: {formula.section_id}
                    </p>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No formulas extracted from this document.
              </div>
            )}
          </TabsContent>

          <TabsContent value="tables" className="space-y-4 mt-4">
            {ir.tables && ir.tables.length > 0 ? (
              ir.tables.map((table) => (
                <Card key={table.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">
                        {table.title || table.id}
                      </CardTitle>
                      {onSelectItem && table.title && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onSelectItem(table.title || table.id, 'table')}
                          className="shrink-0"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View in Doc
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm space-y-2">
                      <div>
                        <span className="font-medium">Columns:</span> {table.headers.join(', ')}
                      </div>
                      <div>
                        <span className="font-medium">Rows:</span> {table.rows.length}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Section: {table.section_id}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No tables extracted from this document.
              </div>
            )}
          </TabsContent>

          <TabsContent value="validation" className="space-y-4 mt-4">
            {ir.validation_issues && ir.validation_issues.length > 0 ? (
              <>
                {errorCount > 0 && (
                  <Alert className="bg-red-50 border-red-200">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <AlertDescription>
                      Found {errorCount} error{errorCount !== 1 ? 's' : ''} that should be addressed.
                    </AlertDescription>
                  </Alert>
                )}
                {warningCount > 0 && (
                  <Alert className="bg-yellow-50 border-yellow-200">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    <AlertDescription>
                      Found {warningCount} warning{warningCount !== 1 ? 's' : ''} for review.
                    </AlertDescription>
                  </Alert>
                )}
                <div className="space-y-3">
                  {ir.validation_issues.map((issue) => (
                    <ValidationIssueCard key={issue.id} issue={issue} onSelectItem={onSelectItem} />
                  ))}
                </div>
              </>
            ) : (
              <Alert className="bg-green-50 border-green-200">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription>
                  No validation issues found. The document structure looks good!
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
