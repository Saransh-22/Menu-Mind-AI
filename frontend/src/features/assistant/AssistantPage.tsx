import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../../store';
import {
  listConversations,
  createConversation,
  deleteConversation,
  listMessages,
  sendMessage,
  uploadAttachment,
  extractMenuFromImage,
  generateMenuDesign,
} from '../../api/assistant';
import {
  Conversation,
  ChatMessage,
  MessageAttachment,
  StructuredMenuDraft,
  GeneratedMenuDesign,
} from '../../types';
import { AgentActivityStream } from './components/AgentActivityStream';
import { MenuEditorModal } from './components/MenuEditorModal';
import { MenuDesignStudioModal } from './components/MenuDesignStudioModal';
import { MarkdownRenderer } from '../../components/common/MarkdownRenderer';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import {
  Bot,
  Plus,
  Send,
  Paperclip,
  Trash2,
  Sparkles,
  FileText,
  Palette,
  Image as ImageIcon,
  MessageSquare,
  Search,
  ExternalLink,
} from 'lucide-react';

export const AssistantPage: React.FC = () => {
  const {
    activeRestaurant,
    activeRun,
    assistantPromptContext,
    clearAssistantPromptContext,
  } = useAppStore();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [inputText, setInputText] = useState('');
  const [attachments, setAttachments] = useState<MessageAttachment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Modals state
  const [activeDraft, setActiveDraft] = useState<StructuredMenuDraft | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [activeDesign, setActiveDesign] = useState<GeneratedMenuDesign | null>(null);
  const [isDesignStudioOpen, setIsDesignStudioOpen] = useState(false);
  const [isGeneratingDesign, setIsGeneratingDesign] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const menuImageInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load conversations on mount or restaurant change
  useEffect(() => {
    if (!activeRestaurant) return;
    loadConversations();
  }, [activeRestaurant?.id]);

  const loadConversations = async () => {
    if (!activeRestaurant) return;
    try {
      const convs = await listConversations(activeRestaurant.id);
      setConversations(convs);
      if (convs.length > 0 && !activeConv) {
        selectConversation(convs[0]);
      } else if (convs.length === 0) {
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const selectConversation = async (conv: Conversation) => {
    setActiveConv(conv);
    try {
      const msgs = await listMessages(conv.id);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  const handleNewConversation = async () => {
    if (!activeRestaurant) return;
    try {
      const newConv = await createConversation(
        activeRestaurant.id,
        activeRun?.id,
        `New Discussion ${new Date().toLocaleDateString([], { month: 'short', day: 'numeric' })}`
      );
      setConversations((prev) => [newConv, ...prev]);
      setActiveConv(newConv);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (activeConv?.id === convId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0]);
        } else {
          setActiveConv(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Check if store has incoming context prompt
  useEffect(() => {
    if (assistantPromptContext && activeConv) {
      setInputText(assistantPromptContext);
      clearAssistantPromptContext();
    }
  }, [assistantPromptContext, activeConv]);

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputText;
    if (!textToSend.trim() && attachments.length === 0) return;
    if (!activeConv) return;

    const currentAttachments = [...attachments];
    setInputText('');
    setAttachments([]);
    setIsLoading(true);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: `temp_${Date.now()}`,
      conversation_id: activeConv.id,
      role: 'user',
      content: textToSend,
      attachments: currentAttachments,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const turn = await sendMessage(
        activeConv.id,
        textToSend,
        activeRun?.id,
        currentAttachments
      );
      // Replace optimistic message and append assistant response
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        turn.user_message,
        turn.assistant_message,
      ]);

      // Check if response contains menu draft or design to stage
      if (turn.agent_response.menu_draft) {
        setActiveDraft(turn.agent_response.menu_draft);
      }
      if (turn.agent_response.menu_design) {
        setActiveDesign(turn.agent_response.menu_design);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        conversation_id: activeConv.id,
        role: 'system',
        content: 'Error: Failed to process request. Please verify backend connection and try again.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAttachmentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeConv) return;

    setIsUploading(true);
    try {
      const att = await uploadAttachment(activeConv.id, file);
      setAttachments((prev) => [...prev, att]);
    } catch (err) {
      console.error('Failed to upload attachment:', err);
      alert('Failed to upload file. Please ensure it is under 25MB.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleExtractMenuImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeConv) return;

    setIsLoading(true);
    try {
      const draft = await extractMenuFromImage(activeConv.id, file);
      setActiveDraft(draft);
      setIsEditorOpen(true);

      // Inform user via assistant
      const autoMsg = `I have uploaded an image of our menu. Please inspect the detected items and help me optimize it.`;
      handleSendMessage(autoMsg);
    } catch (err) {
      console.error('Failed to extract menu:', err);
      alert('Failed to parse menu image. Please try a clearer photograph.');
    } finally {
      setIsLoading(false);
      if (menuImageInputRef.current) menuImageInputRef.current.value = '';
    }
  };

  const handleGenerateDesignFromDraft = async (draft: StructuredMenuDraft) => {
    if (!activeConv) return;
    setIsGeneratingDesign(true);
    try {
      const design = await generateMenuDesign(activeConv.id, draft);
      setActiveDesign(design);
      setIsEditorOpen(false);
      setIsDesignStudioOpen(true);

      // Inform chat
      const noticePrompt = `I finalized the menu draft "${draft.title}" with ${draft.total_items} items. Generate customer-facing publication artwork!`;
      handleSendMessage(noticePrompt);
    } catch (err) {
      console.error('Failed to generate design:', err);
      alert('Failed to generate publication design. Please try again.');
    } finally {
      setIsGeneratingDesign(false);
    }
  };

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <ErrorBoundary fallbackTitle="AI Assistant encountered a display issue">
      <div className="flex h-[calc(100vh-6rem)] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        {/* ─── LEFT CONVERSATION DRAWER ────────────────────────────────────── */}
      <div className="w-80 border-r border-gray-200 bg-gray-50/70 flex flex-col">
        {/* Top bar with New Chat */}
        <div className="p-4 border-b border-gray-200 space-y-3">
          <button
            onClick={handleNewConversation}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs placeholder:text-gray-400 focus:outline-none focus:border-emerald-600"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredConversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-400">
              No conversations found.
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv)}
                className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer text-xs transition ${
                  activeConv?.id === conv.id
                    ? 'bg-emerald-50 text-emerald-950 font-semibold border border-emerald-200/80 shadow-xs'
                    : 'text-gray-700 hover:bg-gray-100/80'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <MessageSquare
                    className={`w-4 h-4 flex-shrink-0 ${
                      activeConv?.id === conv.id ? 'text-emerald-700' : 'text-gray-400'
                    }`}
                  />
                  <div className="truncate">
                    <div className="truncate">{conv.title}</div>
                    <div className="text-[10px] text-gray-400 font-normal">
                      {conv.created_at
                        ? new Date(conv.created_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                          })
                        : ''}
                    </div>
                  </div>
                </div>

                <button
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-rose-600 transition"
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ─── MAIN CHAT AREA ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">
        {/* Workspace Top Header */}
        <div className="px-6 py-3.5 border-b border-gray-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-gray-900">
                  {activeConv?.title || 'AI Assistant Workspace'}
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200/60">
                  5 Specialized Agents Active
                </span>
              </div>
              <p className="text-[11px] text-gray-400">
                Menu Consultant • Visual Design • Business Intelligence • Customer Voice • Waste & Ops
              </p>
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => menuImageInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-xs font-semibold text-gray-700 shadow-2xs transition"
              title="Upload photo of paper menu for AI transcription"
            >
              <ImageIcon className="w-3.5 h-3.5 text-emerald-600" />
              Scan Menu Image
            </button>
            <input
              type="file"
              ref={menuImageInputRef}
              accept="image/*"
              className="hidden"
              onChange={handleExtractMenuImage}
            />

            {activeDraft && (
              <button
                onClick={() => setIsEditorOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-xs font-semibold text-emerald-800 border border-emerald-200 transition"
              >
                <FileText className="w-3.5 h-3.5 text-emerald-600" />
                Menu Draft ({activeDraft.total_items})
              </button>
            )}

            {activeDesign && (
              <button
                onClick={() => setIsDesignStudioOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white shadow-2xs transition"
              >
                <Palette className="w-3.5 h-3.5" />
                Visual Studio
              </button>
            )}
          </div>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12">
              <div className="w-14 h-14 rounded-2xl bg-emerald-100/80 text-emerald-700 flex items-center justify-center mb-4">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-base font-bold text-gray-900 mb-1">
                How can the AI Agents assist {activeRestaurant?.name || 'your restaurant'} today?
              </h2>
              <p className="text-xs text-gray-500 mb-6">
                Ask about sales performance, engineer high-margin menu concepts, analyze guest reviews, or scan a printed menu.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full text-left">
                {[
                  'What are my top 3 profit contributors this period?',
                  'Design a 5-item high-margin weekend specials menu.',
                  'Summarize the biggest customer complaints from reviews.',
                  'Which dishes have high spoilage or waste risk?',
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="p-3 rounded-xl border border-gray-200 bg-gray-50/50 hover:bg-emerald-50/40 hover:border-emerald-300 text-xs text-gray-700 font-medium transition text-left"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              const meta = msg.agent_metadata || {};

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-3xl rounded-2xl px-5 py-3.5 shadow-xs ${
                      isUser
                        ? 'bg-emerald-600 text-white rounded-br-none'
                        : 'bg-white border border-gray-200 text-gray-900 rounded-bl-none shadow-xs'
                    }`}
                  >
                    {/* Header info for assistant message */}
                    {!isUser && meta.specialist_agent && (
                      <div className="flex items-center gap-2 pb-2 mb-2 border-b border-gray-100 text-[11px]">
                        <span className="font-bold text-emerald-800">
                          {meta.specialist_agent}
                        </span>
                        {meta.intent && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-mono">
                            {meta.intent}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Agent Activity Trace */}
                    {!isUser && meta.activity_events && (
                      <AgentActivityStream
                        events={meta.activity_events}
                        specialistName={meta.specialist_agent}
                      />
                    )}

                    {/* Markdown Body */}
                    <div className="text-xs leading-relaxed">
                      <MarkdownRenderer content={msg.content} />
                    </div>

                    {/* Attachments preview */}
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {msg.attachments.map((att) => (
                          <div
                            key={att.id}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border ${
                              isUser
                                ? 'bg-emerald-700/60 border-emerald-500 text-white'
                                : 'bg-gray-50 border-gray-200 text-gray-700'
                            }`}
                          >
                            <ImageIcon className="w-3.5 h-3.5" />
                            <span className="truncate max-w-xs">{att.name}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Interactive Structured Menu Draft Card */}
                    {meta.menu_draft && (
                      <div className="mt-4 p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 text-gray-800">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-bold text-xs text-emerald-950 flex items-center gap-1.5">
                            <FileText className="w-4 h-4 text-emerald-700" />
                            {meta.menu_draft.title}
                          </div>
                          <span className="text-[10px] bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full">
                            {meta.menu_draft.total_items} Items
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-600 mb-3">
                          {meta.menu_draft.concept}
                        </p>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              setActiveDraft(meta.menu_draft);
                              setIsEditorOpen(true);
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-2xs transition"
                          >
                            Edit Menu Items
                          </button>
                          <button
                            onClick={() => handleGenerateDesignFromDraft(meta.menu_draft)}
                            disabled={isGeneratingDesign}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-300 bg-white hover:bg-emerald-50 text-emerald-800 text-xs font-semibold transition"
                          >
                            <Palette className="w-3.5 h-3.5" />
                            Generate Visual Artwork
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Interactive Generated Menu Design Card */}
                    {meta.menu_design && (
                      <div className="mt-4 p-4 rounded-xl border border-purple-200 bg-purple-50/40 text-gray-800">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-bold text-xs text-purple-950 flex items-center gap-1.5">
                            <Palette className="w-4 h-4 text-purple-700" />
                            Design Created: {meta.menu_design.title || meta.menu_design.draft_title || 'Visual Menu Design'}
                          </div>
                          <span className="text-[10px] bg-purple-100 text-purple-800 font-semibold px-2 py-0.5 rounded-full">
                            {meta.menu_design.style || meta.menu_design.style_preset || 'Publication Style'}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-600 mb-3">
                          Publication-ready HTML/SVG generated with zero hallucination.
                        </p>
                        <button
                          onClick={() => {
                            setActiveDesign(meta.menu_design);
                            setIsDesignStudioOpen(true);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold shadow-2xs transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Open in Design Studio
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Suggested Followup Chips */}
                  {!isUser && meta.suggested_followups && meta.suggested_followups.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5 pl-2">
                      {meta.suggested_followups.map((sug: string, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(sug)}
                          className="text-[11px] px-2.5 py-1 rounded-full bg-gray-100 hover:bg-emerald-50 hover:text-emerald-700 border border-gray-200 text-gray-700 font-medium transition"
                        >
                          {sug}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex items-center gap-2 p-3 bg-white rounded-xl border border-gray-200 shadow-2xs w-fit text-xs text-gray-500">
              <Sparkles className="w-4 h-4 text-emerald-600 animate-spin" />
              <span>Multi-agent reasoning in progress...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ─── BOTTOM COMPOSER ────────────────────────────────────────────── */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50">
          {/* Staged attachments preview */}
          {attachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div
                  key={att.id}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-900 text-xs border border-emerald-300"
                >
                  <Paperclip className="w-3 h-3 text-emerald-700" />
                  <span className="truncate max-w-xs">{att.name}</span>
                  <button
                    onClick={() =>
                      setAttachments((prev) => prev.filter((a) => a.id !== att.id))
                    }
                    className="ml-1 text-emerald-700 hover:text-rose-600"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2 bg-white rounded-xl border border-gray-300 p-2 shadow-xs focus-within:border-emerald-600 focus-within:ring-1 focus-within:ring-emerald-500/30">
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleAttachmentUpload}
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="p-2 text-gray-400 hover:text-emerald-600 rounded-lg hover:bg-gray-100 transition"
              title="Attach document or reference image"
            >
              <Paperclip className={`w-4 h-4 ${isUploading ? 'animate-pulse' : ''}`} />
            </button>

            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`Ask any question about ${activeRestaurant?.name || 'your restaurant'}...`}
              rows={1}
              className="flex-1 resize-none py-1.5 text-xs text-gray-900 placeholder:text-gray-400 focus:outline-none max-h-32"
            />

            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || (!inputText.trim() && attachments.length === 0)}
              className="p-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 transition shadow-2xs"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 mt-1.5 text-center">
            Shift + Enter for newline. MenuMind AI routes queries dynamically across specialized agents.
          </p>
        </div>
      </div>

      {/* ─── MODALS ─────────────────────────────────────────────────────── */}
      {isEditorOpen && activeDraft && (
        <MenuEditorModal
          isOpen={isEditorOpen}
          onClose={() => setIsEditorOpen(false)}
          initialDraft={activeDraft}
          onGenerateDesign={handleGenerateDesignFromDraft}
          isGenerating={isGeneratingDesign}
        />
      )}

      {isDesignStudioOpen && activeDesign && activeConv && (
        <MenuDesignStudioModal
          isOpen={isDesignStudioOpen}
          onClose={() => setIsDesignStudioOpen(false)}
          design={activeDesign}
          conversationId={activeConv.id}
          onDesignUpdated={(newDesign) => setActiveDesign(newDesign)}
        />
      )}
    </div>
  </ErrorBoundary>
  );
};

export default AssistantPage;
