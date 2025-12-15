import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  AlertCircle,
  CheckCircle,
  XCircle,

  FileCode,
  TestTube,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { TestCaseList } from './TestCaseList';
import { ReferenceCodeViewer } from './ReferenceCodeViewer';
import { ValidationResults } from './ValidationResults';
import { useTestingFramework } from '@/hooks/useTestingFramework';

interface ValidationDashboardProps {
  documentId: string;
  formulaIds?: string[];
}

export function ValidationDashboard({ documentId, formulaIds }: ValidationDashboardProps) {
  const [activeTab, setActiveTab] = useState('test-cases');
  const {
    testCases,
    reference,
    validationReport,
    isGeneratingTests,
    isGeneratingReference,
    isValidating,
    generateTestCases,
    generateReference,
    validateImplementation,
  } = useTestingFramework(documentId);

  const handleGenerateTests = async () => {
    await generateTestCases(formulaIds);
  };

  const handleGenerateReference = async (formulaId: string) => {
    await generateReference(formulaId, { precision: 4, includeValidation: true });
  };

  const handleValidate = async (formulaId: string, implementationCode: string) => {
    await validateImplementation(formulaId, implementationCode);
  };

  // Calculate overall statistics
  const totalTests = testCases.reduce((sum, suite) => sum + suite.total_tests, 0);
  const overallPassRate = validationReport?.pass_rate ?? 0;
  const isSuccess = validationReport?.success ?? false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Testing & Validation</h2>
          <p className="text-muted-foreground">
            Generate test cases, reference implementations, and validate your code
          </p>
        </div>
        <Button
          onClick={handleGenerateTests}
          disabled={isGeneratingTests}
          className="gap-2"
        >
          {isGeneratingTests ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <TestTube className="h-4 w-4" />
              Generate Tests
            </>
          )}
        </Button>
      </div>

      {/* Statistics Overview */}
      {(testCases.length > 0 || validationReport) && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tests</CardTitle>
              <TestTube className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalTests}</div>
              <p className="text-xs text-muted-foreground">
                Across {testCases.length} formula{testCases.length !== 1 ? 's' : ''}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overallPassRate.toFixed(1)}%</div>
              <Progress value={overallPassRate} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              {isSuccess ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {validationReport ? (isSuccess ? 'Passed' : 'Failed') : 'Not Run'}
              </div>
              <p className="text-xs text-muted-foreground">
                {validationReport
                  ? `${validationReport.passed}/${validationReport.total_tests} tests`
                  : 'Run validation to see results'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Validation Alert */}
      {validationReport && !isSuccess && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Validation Failed</AlertTitle>
          <AlertDescription>
            {validationReport.failed} test{validationReport.failed !== 1 ? 's' : ''} failed.
            Review the discrepancies below and update your implementation.
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="test-cases" className="gap-2">
            <TestTube className="h-4 w-4" />
            Test Cases
            {totalTests > 0 && (
              <Badge variant="secondary" className="ml-2">
                {totalTests}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="reference" className="gap-2">
            <FileCode className="h-4 w-4" />
            Reference
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Results
            {validationReport && (
              <Badge
                variant={isSuccess ? 'default' : 'destructive'}
                className="ml-2"
              >
                {validationReport.passed}/{validationReport.total_tests}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="test-cases" className="space-y-4">
          <TestCaseList
            testCases={testCases}
            onGenerateTests={handleGenerateTests}
            isLoading={isGeneratingTests}
          />
        </TabsContent>

        <TabsContent value="reference" className="space-y-4">
          <ReferenceCodeViewer
            reference={reference}
            onGenerateReference={handleGenerateReference}
            isLoading={isGeneratingReference}
          />
        </TabsContent>

        <TabsContent value="results" className="space-y-4">
          <ValidationResults
            validationReport={validationReport}
            onValidate={handleValidate}
            isLoading={isValidating}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
