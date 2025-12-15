import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Copy, Download, FileCode, Info } from 'lucide-react';
import { toast } from 'sonner';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ReferenceCode {
  document_id: string;
  formula_id: string;
  function_name: string;
  code: string;
}

interface ReferenceCodeViewerProps {
  reference: ReferenceCode | null;
  onGenerateReference: (formulaId: string) => void;
  isLoading: boolean;
}

export function ReferenceCodeViewer({
  reference,
  onGenerateReference,
  isLoading,
}: ReferenceCodeViewerProps) {
  const [selectedFormulaId, setSelectedFormulaId] = useState<string>('');

  const handleCopyCode = () => {
    if (reference) {
      navigator.clipboard.writeText(reference.code);
      toast.success('Code copied to clipboard');
    }
  };

  const handleDownloadCode = () => {
    if (reference) {
      const blob = new Blob([reference.code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reference.function_name}_reference.py`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Reference code downloaded');
    }
  };

  const handleGenerate = () => {
    if (selectedFormulaId) {
      onGenerateReference(selectedFormulaId);
    }
  };

  if (!reference) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Reference Implementation</CardTitle>
          <CardDescription>
            Generate executable Python code from formula specifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Reference implementations are automatically generated from your formula
              specifications. They include parameter validation, precision handling, and
              edge case support.
            </AlertDescription>
          </Alert>

          <div className="flex gap-2">
            <Select value={selectedFormulaId} onValueChange={setSelectedFormulaId}>
              <SelectTrigger className="w-[300px]">
                <SelectValue placeholder="Select a formula" />
              </SelectTrigger>
              <SelectContent>
                {/* Formula options would be populated from test cases */}
                <SelectItem value="formula-1">Formula 1</SelectItem>
                <SelectItem value="formula-2">Formula 2</SelectItem>
              </SelectContent>
            </Select>

            <Button
              onClick={handleGenerate}
              disabled={!selectedFormulaId || isLoading}
              className="gap-2"
            >
              <FileCode className="h-4 w-4" />
              {isLoading ? 'Generating...' : 'Generate Reference'}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Reference Implementation</h3>
          <p className="text-sm text-muted-foreground">
            <code className="text-xs font-mono">{reference.function_name}</code> for formula{' '}
            <code className="text-xs font-mono">{reference.formula_id}</code>
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleCopyCode} variant="outline" size="sm" className="gap-2">
            <Copy className="h-4 w-4" />
            Copy
          </Button>
          <Button onClick={handleDownloadCode} variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            Download
          </Button>
        </div>
      </div>

      {/* Code Display */}
      <Card>
        <CardContent className="p-0">
          <div className="relative">
            <div className="absolute top-2 right-2 z-10">
              <Badge>Python</Badge>
            </div>
            <SyntaxHighlighter
              language="python"
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
              }}
              showLineNumbers
            >
              {reference.code}
            </SyntaxHighlighter>
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          This reference implementation was automatically generated from the specification.
          It includes parameter validation, precision handling with Decimal arithmetic,
          and proper error handling.
        </AlertDescription>
      </Alert>
    </div>
  );
}
