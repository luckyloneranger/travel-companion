import { useState, useRef, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';
import { Send, Loader2, User, Bot, RefreshCw } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  changes?: string[];
}

const JOURNEY_SUGGESTIONS = [
  'Add a beach day',
  'Swap two cities',
  'Make it more budget-friendly',
  'Add 2 more days',
];

const DAY_PLAN_SUGGESTIONS = [
  'Replace dinner restaurant',
  'Add a museum in the morning',
  'Make today more relaxed',
  'Move an activity to tomorrow',
];

export function ChatPanel() {
  const { isChatOpen, chatContext, chatPrefill, closeChat } = useUIStore();
  const { tripId, updateJourney, updateDayPlans, dayPlans, setRecentChanges } = useTripStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset messages when chat opens
  useEffect(() => {
    if (isChatOpen) {
      setShowSuggestions(true);
      setMessages([{
        role: 'assistant',
        content: chatContext === 'journey'
          ? 'How would you like to modify your journey? I can add/remove cities, adjust days, change transport, swap activities, and modify budget.'
          : 'How would you like to modify your day plans? I can add activities, change restaurants, adjust timing, move activities between days, and more.',
      }]);
      if (chatPrefill) {
        setInput(chatPrefill);
      }
    }
  }, [isChatOpen, chatContext, chatPrefill]);

  const handleSend = async (messageOverride?: string) => {
    const messageToSend = (messageOverride || input).trim();
    if (!messageToSend || !tripId || isSending) return;

    setInput('');
    setShowSuggestions(false);
    setLastFailedMessage(null);
    setMessages(prev => [...prev, { role: 'user', content: messageToSend }]);
    setIsSending(true);

    try {
      const response = await api.editTrip(tripId, messageToSend, chatContext === 'day_plans' ? 'day_plans' : '');

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.reply,
        changes: response.changes_made,
      }]);

      // Update store with changes
      if (response.updated_journey) {
        updateJourney(response.updated_journey);
      }
      if (response.updated_day_plans) {
        // Compute diff before updating
        const oldIds = new Set(
          (dayPlans ?? []).flatMap(dp => dp.activities.map(a => a.place.place_id))
        );
        const newIds = new Set(
          response.updated_day_plans.flatMap(dp => dp.activities.map(a => a.place.place_id))
        );
        const added = new Set([...newIds].filter(id => !oldIds.has(id)));
        const removed = (dayPlans ?? [])
          .flatMap(dp => dp.activities)
          .filter(a => !newIds.has(a.place.place_id))
          .map(a => a.place.name);
        const modified = new Set<string>();

        if (added.size > 0 || removed.length > 0) {
          setRecentChanges({ added, modified, removed });
          setTimeout(() => setRecentChanges(null), 30000);
        }

        updateDayPlans(response.updated_day_plans);
      }

      // Journey edit cleared day plans — update store so UI reflects it
      if (response.updated_journey && !response.updated_day_plans &&
          response.changes_made?.some((c: string) => c.toLowerCase().includes('day plans cleared'))) {
        useTripStore.getState().updateDayPlans([]);
      }
    } catch (err) {
      setLastFailedMessage(messageToSend);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, something went wrong: ${err instanceof Error ? err.message : 'Unknown error'}`,
      }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Sheet open={isChatOpen} onOpenChange={(open) => !open && closeChat()}>
      <SheetContent className="w-[min(400px,calc(100vw-2rem))] sm:w-[540px] flex flex-col">
        <SheetHeader>
          <SheetTitle>
            {chatContext === 'journey' ? 'Edit Journey' : 'Edit Day Plans'}
          </SheetTitle>
          <SheetDescription className="sr-only">
            Chat to modify your {chatContext === 'journey' ? 'journey plan' : 'day plans'}
          </SheetDescription>
        </SheetHeader>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto space-y-4 py-4" role="log" aria-live="polite" aria-label="Chat messages">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                </div>
              )}
              <div className={`rounded-lg px-4 py-2 max-w-[80%] ${
                msg.role === 'user'
                  ? 'bg-primary-500 text-white'
                  : 'bg-surface-muted text-text-primary'
              }`}>
                <p className="text-sm break-words">{msg.content}</p>
                {msg.changes && msg.changes.length > 0 && (
                  <ul className="mt-2 text-xs opacity-80 list-disc list-inside break-words">
                    {msg.changes.map((c, j) => <li key={j}>{c}</li>)}
                  </ul>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}
          {/* Retry button for failed messages */}
          {lastFailedMessage && !isSending && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => {
                  const msg = lastFailedMessage;
                  setLastFailedMessage(null);
                  handleSend(msg);
                }}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
              >
                <RefreshCw className="h-3 w-3" /> Retry last message
              </button>
            </div>
          )}
          {/* Suggestion chips — always visible */}
          {showSuggestions && (
            <div className="flex gap-2 px-2 overflow-x-auto pb-1 scrollbar-hide">
              {(chatContext === 'journey' ? JOURNEY_SUGGESTIONS : DAY_PLAN_SUGGESTIONS).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => handleSend(suggestion)}
                  disabled={isSending}
                  className="shrink-0 whitespace-nowrap rounded-full border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 px-3 py-1.5 text-xs text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2 pt-4 border-t">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your changes..."
            aria-label="Chat message"
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={isSending}
          />
          <Button onClick={() => handleSend()} disabled={isSending || !input.trim()} size="icon" aria-label="Send message">
            {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
