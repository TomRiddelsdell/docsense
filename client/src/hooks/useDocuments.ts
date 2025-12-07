import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type {
  DocumentSummary,
  DocumentDetail,
  DocumentListResponse,
  FeedbackListResponse,
  AnalysisSession,
  UploadDocumentRequest,
  AnalyzeDocumentRequest,
  ChatRequest,
  ChatResponse,
  ParametersResponse,
} from '@/types/api';

const STALE_TIME = 5 * 60 * 1000;

export function useDocuments(params?: { page?: number; per_page?: number; status?: string }) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: async () => {
      const { data } = await api.get<DocumentListResponse>('/documents', { params });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useDocument(id: string | undefined) {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const { data } = await api.get<DocumentDetail>(`/documents/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: STALE_TIME,
  });
}

export function useDocumentFeedback(documentId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ['documents', documentId, 'feedback', status],
    queryFn: async () => {
      const { data } = await api.get<FeedbackListResponse>(`/documents/${documentId}/feedback`, {
        params: status ? { status } : undefined,
      });
      return data;
    },
    enabled: !!documentId,
    staleTime: STALE_TIME,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: UploadDocumentRequest) => {
      const formData = new FormData();
      formData.append('file', request.file);
      formData.append('title', request.title);
      if (request.description) formData.append('description', request.description);
      if (request.tags) request.tags.forEach(tag => formData.append('tags', tag));
      if (request.policy_repository_id) formData.append('policy_repository_id', request.policy_repository_id);

      const { data } = await api.post<DocumentSummary>('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useAnalyzeDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ documentId, request }: { documentId: string; request?: AnalyzeDocumentRequest }) => {
      const { data } = await api.post<AnalysisSession>(`/documents/${documentId}/analyze`, request || {});
      return data;
    },
    onSuccess: (_, { documentId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', documentId] });
    },
  });
}

export function useAcceptFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ documentId, feedbackId }: { documentId: string; feedbackId: string }) => {
      const { data } = await api.post(`/documents/${documentId}/feedback/${feedbackId}/accept`);
      return data;
    },
    onSuccess: (_, { documentId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'feedback'] });
      queryClient.invalidateQueries({ queryKey: ['documents', documentId] });
    },
  });
}

export function useRejectFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ documentId, feedbackId, reason }: { documentId: string; feedbackId: string; reason?: string }) => {
      const { data } = await api.post(`/documents/${documentId}/feedback/${feedbackId}/reject`, { reason });
      return data;
    },
    onSuccess: (_, { documentId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'feedback'] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      await api.delete(`/documents/${documentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useChatWithDocument() {
  return useMutation({
    mutationFn: async ({ documentId, request }: { documentId: string; request: ChatRequest }) => {
      const { data } = await api.post<ChatResponse>(`/documents/${documentId}/chat`, request);
      return data;
    },
  });
}

export function useDocumentParameters(documentId: string | undefined) {
  return useQuery({
    queryKey: ['documents', documentId, 'parameters'],
    queryFn: async () => {
      const { data } = await api.get<ParametersResponse>(`/documents/${documentId}/parameters`);
      return data;
    },
    enabled: !!documentId,
    staleTime: STALE_TIME,
  });
}
