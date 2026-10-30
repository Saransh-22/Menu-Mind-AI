import { apiClient } from './client';
import {
  Conversation,
  ChatMessage,
  ChatTurnResponse,
  MessageAttachment,
  StructuredMenuDraft,
  DesignSpecification,
  GeneratedMenuDesign,
} from '../types';

export const listConversations = async (restaurantId: number, search?: string): Promise<Conversation[]> => {
  const params: Record<string, any> = { restaurant_id: restaurantId };
  if (search) params.search = search;
  const res = await apiClient.get<Conversation[]>('/api/chat/conversations', { params });
  return res.data;
};

export const createConversation = async (
  restaurantId: number,
  runId?: number,
  title: string = 'New Conversation'
): Promise<Conversation> => {
  const res = await apiClient.post<Conversation>('/api/chat/conversations', {
    restaurant_id: restaurantId,
    run_id: runId,
    title,
  });
  return res.data;
};

export const getConversation = async (conversationId: string): Promise<Conversation> => {
  const res = await apiClient.get<Conversation>(`/api/chat/conversations/${conversationId}`);
  return res.data;
};

export const updateConversation = async (conversationId: string, title: string): Promise<Conversation> => {
  const res = await apiClient.patch<Conversation>(`/api/chat/conversations/${conversationId}`, { title });
  return res.data;
};

export const deleteConversation = async (conversationId: string): Promise<void> => {
  await apiClient.delete(`/api/chat/conversations/${conversationId}`);
};

export const listMessages = async (conversationId: string): Promise<ChatMessage[]> => {
  const res = await apiClient.get<ChatMessage[]>(`/api/chat/conversations/${conversationId}/messages`);
  return res.data;
};

export const sendMessage = async (
  conversationId: string,
  content: string,
  runId?: number,
  attachments: MessageAttachment[] = []
): Promise<ChatTurnResponse> => {
  const res = await apiClient.post<ChatTurnResponse>(`/api/chat/conversations/${conversationId}/messages`, {
    content,
    run_id: runId,
    attachments,
  });
  return res.data;
};

export const uploadAttachment = async (
  conversationId: string,
  file: File
): Promise<MessageAttachment> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<MessageAttachment>(
    `/api/chat/conversations/${conversationId}/attachments`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return res.data;
};

export const extractMenuFromImage = async (
  conversationId: string,
  file: File
): Promise<StructuredMenuDraft> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<StructuredMenuDraft>(
    `/api/chat/conversations/${conversationId}/extract-menu`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return res.data;
};

export const generateMenuDesign = async (
  conversationId: string,
  menuDraft: StructuredMenuDraft,
  spec: Partial<DesignSpecification> = {}
): Promise<GeneratedMenuDesign> => {
  const res = await apiClient.post<GeneratedMenuDesign>(
    `/api/chat/conversations/${conversationId}/menu-designs`,
    {
      menu_draft: menuDraft,
      spec,
    }
  );
  return res.data;
};

export const listMenuDesigns = async (conversationId: string): Promise<GeneratedMenuDesign[]> => {
  const res = await apiClient.get<GeneratedMenuDesign[]>(
    `/api/chat/conversations/${conversationId}/menu-designs`
  );
  return res.data;
};

export const regenerateMenuDesign = async (
  conversationId: string,
  designId: string,
  params: { style: string; palette?: string[]; layout?: string }
): Promise<GeneratedMenuDesign> => {
  const res = await apiClient.post<GeneratedMenuDesign>(
    `/api/chat/conversations/${conversationId}/menu-designs/${designId}/regenerate`,
    params
  );
  return res.data;
};

export const exportMenuDesignUrl = (
  conversationId: string,
  designId: string,
  format: 'html' | 'svg' | 'png' = 'html'
): string => {
  const base = import.meta.env.VITE_API_BASE_URL || '';
  return `${base}/api/chat/conversations/${conversationId}/menu-designs/${designId}/export?format=${format}`;
};
