import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, XCircle, AlertCircle, Play } from 'lucide-react';


interface FailedTest {
  test_name: string;
  category: string;
  expected: any;
  actual: any;
  discrepancy?: number;
  error: string;
}

interface ValidationReport {
  report_id: string;
  document_id: string;
  formula_id: string;
  success: boolean;
  pass_rate: number;
  total_tests: number;
  passed: number;
  failed: number;
  discrepancy_summary: {
    numeric_tests: number;
    max_discrepancy?: number;
    mean_discrepancy?: number;
    median_discrepancy?: number;
    tests_with_discrepancy?: number;
  };
  failed_tests: FailedTest[];
}

interface ValidationResultsProps {
  validationReport: ValidationReport | null;
  onValidate: (formulaId: string, code: string) => void;
  isLoading: boolean;
}

export function ValidationResults({
  validationReport,
  onValidate,
  isLoading,
}: ValidationResultsProps) {
  const [implementationCode, setImplementationCode] = useState('');
  const [selectedFormulaId, setSelectedFormulaId] = useState('');

  const handleValidate = () => {
    if (selectedFormulaId && implementationCode.trim()) {
      onValidate(selectedFormulaId, implementationCode);
    }
  };

  if (!validationReport) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Validation Results</CardTitle>
          <CardDescription>
            Validate your implementation against the reference
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">
              Your Implementation Code
            </label>
            <Textarea
              placeholder="def calculate_nav(total_assets, total_liabilities, shares_outstanding):
    return (total_assets - total_liabilities) / shares_outstanding"
              value={implementationCode}
              onChange={(e) => setImplementationCode(e.target.value)}
              className="font-mono text-sm"
              rows={10}
            />
          </div>

          <Button
            onClick={handleValidate}
            disabled={!implementationCode.trim() || isLoading}
            className="gap-2"
          >
            <Play className="h-4 w-4" />
            {isLoading ? 'Validating...' : 'Run Validation'}
          </Button>

          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Paste your Python implementation above and click "Run Validation" to compare
              it against the reference implementation.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const { success, pass_rate, passed, failed, total_tests, discrepancy_summary, failed_tests } =
    validationReport;

  return (
    <div className="space-y-4">
      {/* Status Alert */}
      <Alert variant={success ? 'default' : 'destructive'}>
        {success ? (
          <CheckCircle className="h-4 w-4" />
        ) : (
          <XCircle className="h-4 w-4" />
        )}
        <AlertTitle>
          {success ? 'Validation Passed!' : 'Validation Failed'}
        </AlertTitle>
        <AlertDescription>
          {success
            ? `All ${total_tests} tests passed successfully. Your implementation matches the specification.`
            : `${failed} of ${total_tests} tests failed. Review the discrepancies below.`}
        </AlertDescription>
      </Alert>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pass_rate.toFixed(1)}%</div>
            <Progress value={pass_rate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tests Passed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{passed}</div>
            <p className="text-xs text-muted-foreground">of {total_tests} total</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tests Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{failed}</div>
            <p className="text-xs text-muted-foreground">
              {((failed / total_tests) * 100).toFixed(1)}% of total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Max Discrepancy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {discrepancy_summary.max_discrepancy?.toExponential(2) ?? 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              Mean: {discrepancy_summary.mean_discrepancy?.toExponential(2) ?? 'N/A'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Discrepancy Summary */}
      {discrepancy_summary.numeric_tests > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Discrepancy Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm font-medium">Numeric Tests</p>
                <p className="text-2xl font-bold">{discrepancy_summary.numeric_tests}</p>
              </div>
              <div>
                <p className="text-sm font-medium">With Discrepancy</p>
                <p className="text-2xl font-bold">
                  {discrepancy_summary.tests_with_discrepancy ?? 0}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">Median Discrepancy</p>
                <p className="text-2xl font-bold">
                  {discrepancy_summary.median_discrepancy?.toExponential(2) ?? 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Failed Tests */}
      {failed > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Failed Tests ({failed})</CardTitle>
            <CardDescription>
              Review these failures to identify implementation issues
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              {failed_tests.map((test, index) => (
                <AccordionItem key={index} value={`test-${index}`}>
                  <AccordionTrigger>
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      <code className="text-sm font-mono">{test.test_name}</code>
                      <Badge variant="outline">{test.category}</Badge>
                      {test.discrepancy !== undefined && (
                        <Badge variant="secondary">
                          Δ {test.discrepancy.toExponential(2)}
                        </Badge>
                      )}
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pl-6">
                      <div className="grid gap-2">
                        <div>
                          <span className="text-sm font-medium">Expected:</span>
                          <code className="ml-2 text-sm">{JSON.stringify(test.expected)}</code>
                        </div>
                        <div>
                          <span className="text-sm font-medium">Actual:</span>
                          <code className="ml-2 text-sm">{JSON.stringify(test.actual)}</code>
                        </div>
                        {test.discrepancy !== undefined && (
                          <div>
                            <span className="text-sm font-medium">Discrepancy:</span>
                            <code className="ml-2 text-sm">{test.discrepancy}</code>
                          </div>
                        )}
                        {test.error && (
                          <div>
                            <span className="text-sm font-medium">Error:</span>
                            <p className="ml-2 text-sm text-muted-foreground">{test.error}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Run Again */}
      <Card>
        <CardContent className="pt-6">
          <Button onClick={handleValidate} disabled={isLoading} className="gap-2">
            <Play className="h-4 w-4" />
            Run Validation Again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
