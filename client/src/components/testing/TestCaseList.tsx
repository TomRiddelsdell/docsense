import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { TestTube } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TestCase {
  id: string;
  name: string;
  category: 'normal' | 'boundary' | 'edge' | 'error';
  inputs: Record<string, any>;
  expected_output?: any;
  precision?: number;
  tolerance?: number;
  description: string;
}

interface TestCaseSuite {
  document_id: string;
  formula_id: string;
  total_tests: number;
  test_cases: TestCase[];
}

interface TestCaseListProps {
  testCases: TestCaseSuite[];
  onGenerateTests: () => void;
  isLoading: boolean;
}

const categoryColors = {
  normal: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  boundary: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  edge: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

export function TestCaseList({ testCases, onGenerateTests, isLoading }: TestCaseListProps) {
  const [expandedFormulas, setExpandedFormulas] = useState<Set<string>>(new Set());

  const toggleFormula = (formulaId: string) => {
    setExpandedFormulas((prev) => {
      const next = new Set(prev);
      if (next.has(formulaId)) {
        next.delete(formulaId);
      } else {
        next.add(formulaId);
      }
      return next;
    });
  };

  if (testCases.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Test Cases Generated</CardTitle>
          <CardDescription>
            Generate test cases from your document specifications to begin validation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={onGenerateTests} disabled={isLoading} className="gap-2">
            <TestTube className="h-4 w-4" />
            {isLoading ? 'Generating...' : 'Generate Test Cases'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Generated Test Cases</h3>
          <p className="text-sm text-muted-foreground">
            {testCases.reduce((sum, suite) => sum + suite.total_tests, 0)} tests across{' '}
            {testCases.length} formula{testCases.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={onGenerateTests} disabled={isLoading} variant="outline" size="sm">
          Regenerate
        </Button>
      </div>

      <Accordion type="multiple" className="w-full">
        {testCases.map((suite) => (
          <AccordionItem key={suite.formula_id} value={suite.formula_id}>
            <AccordionTrigger>
              <div className="flex items-center gap-3">
                <code className="text-sm font-mono">{suite.formula_id}</code>
                <Badge variant="secondary">{suite.total_tests} tests</Badge>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4">
                {/* Category Breakdown */}
                <div className="flex gap-2">
                  {Object.entries(
                    suite.test_cases.reduce((acc, tc) => {
                      acc[tc.category] = (acc[tc.category] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>)
                  ).map(([category, count]) => (
                    <Badge key={category} className={cn(categoryColors[category as keyof typeof categoryColors])}>
                      {category}: {count}
                    </Badge>
                  ))}
                </div>

                {/* Test Cases Table */}
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Inputs</TableHead>
                        <TableHead>Expected</TableHead>
                        <TableHead>Description</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {suite.test_cases.slice(0, 10).map((testCase) => (
                        <TableRow key={testCase.id}>
                          <TableCell className="font-mono text-xs">
                            {testCase.name}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(categoryColors[testCase.category])}
                            >
                              {testCase.category}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-xs">
                            <code className="text-xs">
                              {JSON.stringify(testCase.inputs, null, 0).slice(0, 50)}
                              {JSON.stringify(testCase.inputs).length > 50 ? '...' : ''}
                            </code>
                          </TableCell>
                          <TableCell>
                            {testCase.expected_output !== undefined && testCase.expected_output !== null ? (
                              <code className="text-xs">
                                {String(testCase.expected_output)}
                              </code>
                            ) : (
                              <span className="text-muted-foreground text-xs">
                                To be computed
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="max-w-sm text-xs text-muted-foreground">
                            {testCase.description}
                          </TableCell>
                        </TableRow>
                      ))}
                      {suite.test_cases.length > 10 && (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                            ... and {suite.test_cases.length - 10} more tests
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
