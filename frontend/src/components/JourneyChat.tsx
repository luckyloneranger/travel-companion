/**
 * PlanChat - Chat interface for editing journey plans and day plans
 * 
 * Allows users to make natural language requests to modify their plans.
 * Changes are applied in real-time and reflected in the view.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  MessageCircle, 
  Send, 
  X, 
  Sparkles,
  CheckCircle2,
  Loader2,
  Calendar,
} from 'lucide-react';
import type { V6JourneyPlan, V6DayPlan, ChatMessage } from '@/types';
import { editJourneyViaChat, editDayPlansViaChat } from '@/services/api';
import { headerGradients, shadows } from '@/styles';

type ChatMode = 'journey' | 'dayplan';

interface BaseChatProps {
  context?: {
    origin?: string;
    region?: string;
    interests?: string[];
    pace?: string;
  };
}

interface JourneyChatProps extends BaseChatProps {
  mode: 'journey';
  journey: V6JourneyPlan;
  onJourneyUpdate: (journey: V6JourneyPlan) => void;
  dayPlans?: never;
  onDayPlansUpdate?: never;
}

interface DayPlanChatProps extends BaseChatProps {
  mode: 'dayplan';
  dayPlans: V6DayPlan[];
  onDayPlansUpdate: (dayPlans: V6DayPlan[]) => void;
  journey?: never;
  onJourneyUpdate?: never;
}

type PlanChatProps = JourneyChatProps | DayPlanChatProps;

// Suggested quick actions by mode
const JOURNEY_QUICK_ACTIONS = [
  'Add a day in the current city',
  'Remove the last city',
  'Change transport to train',
];

const DAYPLAN_QUICK_ACTIONS = [
  'Add a coffee break',
  'Remove the last activity',
  'Make day 1 more relaxed',
];

// Use different gradients for different modes
const getModeGradient = (mode: ChatMode) => 
  mode === 'journey' ? headerGradients.journey : headerGradients.dayPlan;

const getModeTitle = (mode: ChatMode) => 
  mode === 'journey' ? 'Edit Your Journey' : 'Edit Day Plans';

const getModeIcon = (mode: ChatMode) => 
  mode === 'journey' ? <Sparkles className="h-5 w-5" /> : <Calendar className="h-5 w-5" />;

const getModeButtonText = (mode: ChatMode) =>
  mode === 'journey' ? 'Edit Journey' : 'Edit Days';

export function JourneyChat(props: PlanChatProps) {
  const { mode, context } = props;
  const gradient = getModeGradient(mode);
  const quickActions = mode === 'journey' ? JOURNEY_QUICK_ACTIONS : DAYPLAN_QUICK_ACTIONS;
  
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Get title for greeting
  const getGreetingTitle = () => {
    if (mode === 'journey' && props.journey) {
      return props.journey.theme;
    }
    if (mode === 'dayplan' && props.dayPlans?.length) {
      return `${props.dayPlans.length}-day itinerary`;
    }
    return 'your plan';
  };
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);
  
  // Add initial greeting when chat is first opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const examples = mode === 'journey' 
        ? '"add Hoi An for 2 days" or "change transport to train"'
        : '"add a coffee break after lunch" or "make day 2 more relaxed"';
      setMessages([{
        id: 'greeting',
        role: 'assistant',
        content: `Hi! I can help you modify your ${getGreetingTitle()}. Try saying things like ${examples}.`,
        timestamp: new Date(),
      }]);
    }
  }, [isOpen, messages.length, mode]);
  
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;
    
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Add loading message
    const loadingId = `loading-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: loadingId,
      role: 'assistant',
      content: 'Thinking...',
      timestamp: new Date(),
      isLoading: true,
    }]);
    
    try {
      if (mode === 'journey' && props.onJourneyUpdate && props.journey) {
        const response = await editJourneyViaChat({
          message: userMessage.content,
          journey: props.journey,
          context,
        });
        
        // Remove loading message and add real response
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== loadingId);
          return [...filtered, {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.message,
            timestamp: new Date(),
            changes: response.changes_made,
          }];
        });
        
        if (response.success && response.updated_journey) {
          props.onJourneyUpdate(response.updated_journey);
        }
      } else if (mode === 'dayplan' && props.onDayPlansUpdate && props.dayPlans) {
        const response = await editDayPlansViaChat({
          message: userMessage.content,
          day_plans: props.dayPlans,
          context: { interests: context?.interests, pace: context?.pace },
        });
        
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== loadingId);
          return [...filtered, {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.message,
            timestamp: new Date(),
            changes: response.changes_made,
          }];
        });
        
        if (response.success && response.updated_day_plans) {
          props.onDayPlansUpdate(response.updated_day_plans);
        }
      }
      
    } catch (error) {
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== loadingId);
        return [...filtered, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: error instanceof Error 
            ? `Sorry, I encountered an error: ${error.message}` 
            : 'Sorry, something went wrong. Please try again.',
          timestamp: new Date(),
        }];
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, mode, props, context]);
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleQuickAction = (action: string) => {
    setInput(action);
    inputRef.current?.focus();
  };
  
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 flex items-center gap-2 px-4 py-3 text-white rounded-full transition-all duration-300 hover:scale-105 z-50"
        style={{ 
          background: `linear-gradient(135deg, ${gradient.from}, ${gradient.to})`,
          boxShadow: shadows.lg,
        }}
      >
        <MessageCircle className="h-5 w-5" />
        <span className="font-medium">{getModeButtonText(mode)}</span>
        {getModeIcon(mode)}
      </button>
    );
  }
  
  return (
    <div 
      className="fixed bottom-6 right-6 w-96 bg-white rounded-2xl overflow-hidden z-50"
      style={{ boxShadow: shadows.xl, maxHeight: 'calc(100vh - 100px)' }}
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 text-white"
        style={{ background: `linear-gradient(135deg, ${gradient.from}, ${gradient.to})` }}
      >
        <div className="flex items-center gap-2">
          {getModeIcon(mode)}
          <span className="font-semibold">{getModeTitle(mode)}</span>
        </div>
        <button 
          onClick={() => setIsOpen(false)}
          className="p-1 rounded-full hover:bg-white/20 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      
      {/* Messages */}
      <div className="h-80 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                msg.role === 'user'
                  ? 'text-white rounded-br-md'
                  : 'bg-white shadow-sm border border-gray-100 rounded-bl-md'
              }`}
              style={msg.role === 'user' ? { 
                background: `linear-gradient(135deg, ${gradient.from}, ${gradient.to})`,
                transition: 'all 0.2s' 
              } : { transition: 'all 0.2s' }}
            >
              {msg.isLoading ? (
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : (
                <>
                  <p className={msg.role === 'user' ? 'text-white' : 'text-gray-700'}>
                    {msg.content}
                  </p>
                  
                  {/* Show changes made */}
                  {msg.changes && msg.changes.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-500 mb-1">Changes made:</p>
                      <ul className="space-y-1">
                        {msg.changes.map((change, idx) => (
                          <li key={idx} className="flex items-start gap-1.5 text-xs text-gray-600">
                            <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                            {change}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Quick actions */}
      {messages.length <= 2 && (
        <div className="px-4 py-2 border-t border-gray-100 bg-white">
          <p className="text-xs text-gray-500 mb-2">Quick suggestions:</p>
          <div className="flex flex-wrap gap-1.5">
            {quickActions.map((action) => (
              <button
                key={action}
                onClick={() => handleQuickAction(action)}
                className="text-xs px-2.5 py-1.5 rounded-full bg-gray-100 text-gray-600 hover:text-white transition-colors"
                style={{ '--tw-bg-opacity': 1 } as React.CSSProperties}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `linear-gradient(135deg, ${gradient.from}, ${gradient.to})`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '';
                }}
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Input */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your edit request..."
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 rounded-full bg-gray-100 border-0 focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all text-sm disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2.5 rounded-full text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95"
            style={{ 
              background: `linear-gradient(135deg, ${gradient.from}, ${gradient.to})`,
            }}
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
