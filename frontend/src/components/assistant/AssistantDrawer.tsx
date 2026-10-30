import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../store';
import {
  listConversations,
  createConversation,
  listMessages,
  sendMessage,
} from '../../api/assistant';
import { Conversation, ChatMessage } from '../../types';
import {
  X,
  Send,
  Bot,
  Maximize2,
  Sparkles,
} from 'lucide-react';
import { MarkdownRenderer } from '../common/MarkdownRenderer';

export const AssistantDrawer: React.FC = () => {
  const {
    activeRestaurant,
    activeRun,
    isAssistantDrawerOpen,
    setAssistantDrawerOpen,
    assistantPromptContext,
    clearAssistantPromptContext,
  } = useAppStore();

  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAssistantDrawerOpen && activeRestaurant) {
      initDrawer();
    }
  }, [isAssistantDrawerOpen, activeRestaurant?.id]);

  const initDrawer = async () => {
    if (!activeRestaurant) return;
    try {
      const convs = await listConversations(activeRestaurant.id);
      setConversations(convs);
      if (convs.length > 0) {
        setActiveConv(convs[0]);
        const msgs = await listMessages(convs[0].id);
        setMessages(msgs);
      } else {
        const newConv = await createConversation(
          activeRestaurant.id,
          activeRun?.id,
          'Drawer Chat'
        );
        setConversations([newConv]);
        setActiveConv(newConv);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to init drawer conversation:', err);
    }
  };

  useEffect(() => {
    if (assistantPromptContext && activeConv && isAssistantDrawerOpen) {
      setInputText(assistantPromptContext);
      clearAssistantPromptContext();
    }
  }, [assistantPromptContext, activeConv, isAssistantDrawerOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isAssistantDrawerOpen) return null;

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputText;
    if (!textToSend.trim() || !activeConv) return;

    setInputText('');
    setIsLoading(true);

    const tempUserMsg: ChatMessage = {
      id: `temp_${Date.now()}`,
      conversation_id: activeConv.id,
      role: 'user',
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const turn = await sendMessage(activeConv.id, textToSend, activeRun?.id);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        turn.user_message,
        turn.assistant_message,
      ]);
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExpandToFull = () => {
    setAssistantDrawerOpen(false);
    navigate('/assistant');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md sm:max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-200 bg-gray-50/90">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-gray-900">
                MenuMind Assistant
              </h3>
              <p className="text-[10px] text-gray-500">
                {activeRestaurant?.name || 'Restaurant Intelligence'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleExpandToFull}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-200 hover:text-gray-700 transition"
              title="Expand to Full Workspace"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setAssistantDrawerOpen(false)}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-200 hover:text-gray-700 transition"
              title="Close Drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/30 text-xs">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-400">
              <Sparkles className="w-8 h-8 text-emerald-500 mb-2" />
              <p className="font-semibold text-gray-700 mb-1">How can I help right now?</p>
              <p className="text-[11px] mb-4">Ask about the current data on your screen or request optimization tips.</p>
              <div className="space-y-2 w-full text-left">
                <button
                  onClick={() => handleSendMessage('Give me a quick 3-bullet summary of my current performance.')}
                  className="w-full p-2.5 rounded-lg border border-gray-200 bg-white hover:bg-emerald-50 hover:border-emerald-300 text-xs text-gray-700 transition"
                >
                  "Give me a quick 3-bullet summary of my current performance."
                </button>
                <button
                  onClick={() => handleSendMessage('Which items have the highest profit margins?')}
                  className="w-full p-2.5 rounded-lg border border-gray-200 bg-white hover:bg-emerald-50 hover:border-emerald-300 text-xs text-gray-700 transition"
                >
                  "Which items have the highest profit margins?"
                </button>
              </div>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === 'user';
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 shadow-xs ${
                      isUser
                        ? 'bg-emerald-600 text-white rounded-br-none'
                        : 'bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-xs'
                    }`}
                  >
                    {!isUser && m.agent_metadata?.specialist_agent && (
                      <div className="text-[10px] font-bold text-emerald-700 mb-1">
                        {m.agent_metadata.specialist_agent}
                      </div>
                    )}
                    <div className="text-xs leading-relaxed">
                      <MarkdownRenderer content={m.content} />
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex items-center gap-2 p-2.5 bg-white rounded-xl border border-gray-200 text-xs text-gray-500 w-fit">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600 animate-spin" />
              <span>Analyzing...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input */}
        <div className="p-3 border-t border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSendMessage();
              }}
              placeholder="Type your question..."
              className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-600"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || !inputText.trim()}
              className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 transition shadow-2xs"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
