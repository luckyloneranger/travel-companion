import { useState, useRef, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';
import { Send, Loader2, User, Bot } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  changes?: string[];
}

export function ChatPanel() {
  const { isChatOpen, chatContext, closeChat } = useUIStore();
  const { tripId, updateJourney, updateDayPlans } = useTripStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset messages when chat opens
  useEffect(() => {
    if (isChatOpen) {
      setMessages([{
        role: 'assistant',
        content: chatContext === 'journey'
          ? 'How would you like to modify your journey? You can ask me to change cities, adjust days, swap transport, etc.'
          : 'How would you like to modify your day plans? You can ask me to add activities, change restaurants, adjust timing, etc.',
      }]);
    }
  }, [isChatOpen, chatContext]);

  const handleSend = async () => {
    if (!input.trim() || !tripId || isSending) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsSending(true);

    try {
      const response = await api.editTrip(tripId, userMessage, chatContext === 'day_plans' ? 'day_plans' : '');

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
        updateDayPlans(response.updated_day_plans);
      }
    } catch (err) {
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
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col">
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
                <p className="text-sm">{msg.content}</p>
                {msg.changes && msg.changes.length > 0 && (
                  <ul className="mt-2 text-xs opacity-80 list-disc list-inside">
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
          <Button onClick={handleSend} disabled={isSending || !input.trim()} size="icon" aria-label="Send message">
            {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
