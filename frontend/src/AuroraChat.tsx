import { useEffect, useRef, useState } from 'react'
import { Bot, ChevronDown, Loader2, Send, Sparkles, X } from 'lucide-react'

type Message = { role: 'user' | 'assistant'; content: string; sources?: string[] }

const QUICK = [
  "What's happening now?",
  'Why is the battery discharging?',
  "Explain today's energy strategy",
  'How much renewable energy are we using?',
  'Is the critical load safe?',
  'What happens during a connectivity loss?',
  'Summarize station status',
]

async function sendChat(message: string, history: Message[]): Promise<{ answer: string; sources?: string[] }> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: history.map((m) => ({ role: m.role, content: m.content })),
    }),
  })
  if (!res.ok) throw new Error(`Chat API ${res.status}`)
  const data = await res.json()
  return { answer: data.answer ?? 'No response.', sources: data.sources }
}

export default function AuroraChat() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 80)
      if (messages.length === 0) {
        setMessages([{
          role: 'assistant',
          content: "Hello! I'm AURORA AI, your Energy Operations Assistant for the Bharati polar research station.\n\nI have access to live station telemetry, forecasts, dispatch decisions, and resilience status. Ask me anything about the current energy state.",
        }])
      }
    }
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const submit = async (text: string) => {
    const msg = text.trim()
    if (!msg || loading) return
    setInput('')
    const next: Message[] = [...messages, { role: 'user', content: msg }]
    setMessages(next)
    setLoading(true)
    try {
      const { answer, sources } = await sendChat(msg, next.slice(0, -1))
      setMessages([...next, { role: 'assistant', content: answer, sources }])
    } catch {
      setMessages([...next, { role: 'assistant', content: '⚠️ Unable to reach the AURORA AI backend. Please check your connection.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        className="aurora-chat-fab"
        onClick={() => setOpen((v) => !v)}
        aria-label="Open AURORA AI assistant"
        title="AURORA AI — Energy Operations Assistant"
      >
        {open ? <ChevronDown size={22} /> : <Sparkles size={22} />}
        {!open && <span className="aurora-chat-fab-label">AURORA AI</span>}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="aurora-chat-panel" role="dialog" aria-label="AURORA AI Energy Operations Assistant">
          {/* Header */}
          <div className="aurora-chat-header">
            <div className="aurora-chat-header-info">
              <Bot size={18} />
              <div>
                <b>AURORA AI</b>
                <small>Energy Operations Assistant</small>
              </div>
            </div>
            <div className="aurora-chat-header-actions">
              <button onClick={() => setMessages([])} title="Clear chat" aria-label="Clear chat history">
                <X size={14} />
                <span>Clear</span>
              </button>
              <button onClick={() => setOpen(false)} aria-label="Close chat">
                <ChevronDown size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="aurora-chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`aurora-chat-msg aurora-chat-msg--${m.role}`}>
                {m.role === 'assistant' && (
                  <span className="aurora-chat-avatar"><Bot size={13} /></span>
                )}
                <div className="aurora-chat-bubble">
                  <MessageContent content={m.content} />
                  {m.sources && m.sources.length > 0 && (
                    <div className="aurora-chat-sources">
                      {m.sources.map((s) => (
                        <span key={s} className="aurora-chat-source-tag">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="aurora-chat-msg aurora-chat-msg--assistant">
                <span className="aurora-chat-avatar"><Bot size={13} /></span>
                <div className="aurora-chat-bubble aurora-chat-typing">
                  <Loader2 size={14} className="aurora-spin" />
                  <span>Analysing station data…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick questions */}
          {messages.length <= 1 && !loading && (
            <div className="aurora-chat-quick">
              {QUICK.map((q) => (
                <button key={q} onClick={() => submit(q)}>{q}</button>
              ))}
            </div>
          )}

          {/* Input */}
          <form
            className="aurora-chat-input-row"
            onSubmit={(e) => { e.preventDefault(); submit(input) }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about station energy, forecasts, dispatch…"
              maxLength={1000}
              disabled={loading}
              aria-label="Chat message input"
            />
            <button type="submit" disabled={loading || !input.trim()} aria-label="Send message">
              <Send size={16} />
            </button>
          </form>
        </div>
      )}
    </>
  )
}

function MessageContent({ content }: { content: string }) {
  // Render newlines as line breaks, bold **text**
  const parts = content.split('\n').map((line, i) => {
    const segments = line.split(/(\*\*[^*]+\*\*)/)
    return (
      <span key={i}>
        {segments.map((seg, j) =>
          seg.startsWith('**') && seg.endsWith('**')
            ? <strong key={j}>{seg.slice(2, -2)}</strong>
            : seg
        )}
        {i < content.split('\n').length - 1 && <br />}
      </span>
    )
  })
  return <>{parts}</>
}
