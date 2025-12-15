import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from 'sonner';

interface TestCase {
  id: string;
  name: string;
  category: 'normal' | 'boundary' | 'edge' | 'error';
  inputs: Record<string, any>;
  expected_output?: any;
  precision?: number;
  tolerance?: number;
  description: string;
  metadata: Record<string, any>;
}

interface TestCaseSuite {
  document_id: string;
  formula_id: string;
  total_tests: number;
  test_cases: TestCase[];
}

interface ReferenceCode {
  document_id: string;
  formula_id: string;
  function_name: string;
  code: string;
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
  failed_tests: Array<{
    test_name: string;
    category: string;
    expected: any;
    actual: any;
    discrepancy?: number;
    error: string;
  }>;
}

interface GenerateTestCasesRequest {
  document_id: string;
  formula_ids?: string[];
  count_per_category?: Record<string, number>;
}

interface GenerateReferenceRequest {
  document_id: string;
  formula_id: string;
  precision?: number;
  include_validation?: boolean;
}

interface ValidateImplementationRequest {
  document_id: string;
  formula_id: string;
  implementation_code: string;
  test_case_ids?: string[];
  tolerance?: number;
}

export function useTestingFramework(documentId: string) {
  const [testCases, setTestCases] = useState<TestCaseSuite[]>([]);
  const [reference, setReference] = useState<ReferenceCode | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);

  // Generate test cases mutation
  const generateTestCasesMutation = useMutation({
    mutationFn: async (request: GenerateTestCasesRequest) => {
      const { data } = await api.post<TestCaseSuite[]>('/testing/test-cases', request);
      return data;
    },
    onSuccess: (data: TestCaseSuite[]) => {
      setTestCases(data);
      toast.success(`Generated ${data.reduce((sum: number, suite: TestCaseSuite) => sum + suite.total_tests, 0)} test cases`);
    },
    onError: (error: any) => {
      toast.error('Failed to generate test cases', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });

  // Generate reference implementation mutation
  const generateReferenceMutation = useMutation({
    mutationFn: async (request: GenerateReferenceRequest) => {
      const { data } = await api.post<ReferenceCode>('/testing/reference', request);
      return data;
    },
    onSuccess: (data: ReferenceCode) => {
      setReference(data);
      toast.success('Reference implementation generated');
    },
    onError: (error: any) => {
      toast.error('Failed to generate reference implementation', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });

  // Validate implementation mutation
  const validateImplementationMutation = useMutation({
    mutationFn: async (request: ValidateImplementationRequest) => {
      const { data } = await api.post<ValidationReport>('/testing/validate', request);
      return data;
    },
    onSuccess: (data: ValidationReport) => {
      setValidationReport(data);
      if (data.success) {
        toast.success('Validation passed!', {
          description: `All ${data.total_tests} tests passed`,
        });
      } else {
        toast.error('Validation failed', {
          description: `${data.failed} of ${data.total_tests} tests failed`,
        });
      }
    },
    onError: (error: any) => {
      toast.error('Validation failed', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });

  // Helper functions
  const generateTestCases = async (formulaIds?: string[]) => {
    await generateTestCasesMutation.mutateAsync({
      document_id: documentId,
      formula_ids: formulaIds,
      count_per_category: {
        normal: 10,
        boundary: 5,
        edge: 3,
        error: 2,
      },
    });
  };

  const generateReference = async (
    formulaId: string,
    options?: { precision?: number; includeValidation?: boolean }
  ) => {
    await generateReferenceMutation.mutateAsync({
      document_id: documentId,
      formula_id: formulaId,
      precision: options?.precision,
      include_validation: options?.includeValidation ?? true,
    });
  };

  const validateImplementation = async (formulaId: string, implementationCode: string) => {
    await validateImplementationMutation.mutateAsync({
      document_id: documentId,
      formula_id: formulaId,
      implementation_code: implementationCode,
    });
  };

  return {
    testCases,
    reference,
    validationReport,
    isGeneratingTests: generateTestCasesMutation.isPending,
    isGeneratingReference: generateReferenceMutation.isPending,
    isValidating: validateImplementationMutation.isPending,
    generateTestCases,
    generateReference,
    validateImplementation,
  };
}
