import { useCallback, useEffect, useRef, useState } from 'react';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { sendChatMessage, fetchChatHistory } from './services/chatApi';
import './index.css';

/* ── Inline SVG Icons ─────────────────────────────────────────── */
const Icon = ({ children, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
    strokeLinejoin="round" aria-hidden="true">{children}</svg>
);
const SearchIcon = () => <Icon><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></Icon>;
const PlusIcon = () => <Icon><path d="M12 5v14M5 12h14"/></Icon>;
const SendIcon = () => <Icon><path d="m21 3-7.2 18-3.6-7.4L3 10.1 21 3Z"/></Icon>;
const ScaleIcon = ({ size = 20 }) => <Icon size={size}><path d="M12 3v18M5 7h14M5 7l-3 6h6L5 7Zm14 0-3 6h6l-3-6ZM7 21h10"/></Icon>;
const BookIcon = () => <Icon><path d="M5 4.5h11a3 3 0 0 1 3 3V20H8a3 3 0 0 0-3 3V4.5Z"/><path d="M5 20h11"/></Icon>;
const VerifyIcon = () => <Icon><path d="m9 12 2 2 4-5"/><path d="M12 3.5 14.3 5l2.7-.1.8 2.5 2.1 1.7-1 2.5.3 2.7-2.4 1.3-1.4 2.3-2.6-.5-2.6.5-1.4-2.3-2.4-1.3.3-2.7-1-2.5 2.1-1.7.8-2.5 2.7.1L12 3.5Z"/></Icon>;
const FolderIcon = () => <Icon><path d="M3 6.5h7l2 2h9v10.5H3z"/></Icon>;
const MenuIcon = () => <Icon><path d="M4 6h16M4 12h16M4 18h16"/></Icon>;
const CloseIcon = () => <Icon><path d="M18 6 6 18M6 6l12 12"/></Icon>;

/* ── Header ───────────────────────────────────────────────────── */
function Header({ onHome, onToggleSidebar, showSidebarToggle }) {
  const { language, toggleLanguage, t } = useLanguage();
  return (
    <header className="site-header">
      <div className="header-inner">
        <div className="header-left">
          {showSidebarToggle && (
            <button className="sidebar-toggle" onClick={onToggleSidebar}
              aria-label="Toggle sidebar" type="button">
              <MenuIcon />
            </button>
          )}
          <button className="brand" onClick={onHome} type="button">
            <span className="brand-seal"><ScaleIcon size={18} /></span>
            <span>
              <strong>{t.brandTitle}</strong>
              <small>{t.brandSubtitle}</small>
            </span>
          </button>
        </div>
        <div className="header-actions">
          <button className={`lang-toggle ${language === 'am' ? 'amharic' : ''}`}
            type="button" onClick={toggleLanguage}
            aria-pressed={language === 'am'}
            title={t.switchLang}>
            <span className={language === 'en' ? 'active' : ''}>EN</span>
            <b>|</b>
            <span className={language === 'am' ? 'active' : ''}>አማ</span>
          </button>
          <button className="profile" aria-label="User profile">●</button>
        </div>
      </div>
    </header>
  );
}

/* ── Home Page ─────────────────────────────────────────────────── */
function Home({ onStart, question, setQuestion, onAsk }) {
  const { t } = useLanguage();
  return (
    <main className="homepage">
      <section className="hero">
        <div className="hero-glow" />
        <div className="hero-content">
          <div className="court-chip">
            <i /><span>{t.courtChip}</span>
          </div>
          <h1>{t.heroTitle}</h1>
          <h2>{t.heroSubtitle}</h2>
          <p>{t.heroDescription}</p>
          <button className="primary-cta" onClick={onStart} type="button">
            {t.startChat}
          </button>
          <div className="credentials">
            <span><BookIcon /> {t.volumes}</span><b>•</b>
            <span><ScaleIcon /> {t.holdings}</span><b>•</b>
            <span><VerifyIcon /> {t.citations}</span>
          </div>
        </div>
      </section>

      <section className="pillars">
        <Pillar number="01" icon="⌁" title={t.pillar1Title}
          text={t.pillar1Text} foot={t.pillar1Foot} />
        <Pillar number="02" icon="⚖" title={t.pillar2Title}
          text={t.pillar2Text} foot={t.pillar2Foot} />
        <Pillar number="03" icon="✓" title={t.pillar3Title}
          text={t.pillar3Text} foot={t.pillar3Foot} />
      </section>

      <div className="disclaimer">{t.disclaimer}</div>
    </main>
  );
}

const Pillar = ({ number, icon, title, text, foot }) => (
  <article className="pillar">
    <div className="pillar-icon">{icon}</div>
    <label>{number} / Pillar</label>
    <h3>{title}</h3>
    <p>{text}</p>
    <small>{foot}</small>
  </article>
);

/* ── Sidebar ──────────────────────────────────────────────────── */
function Sidebar({ history, activeSessionId, onSelectSession, onNew, open, onClose }) {
  const { t } = useLanguage();
  const [search, setSearch] = useState('');

  const grouped = groupHistory(history, t);

  // filter
  const filtered = search.trim()
    ? grouped.map((g) => ({
        ...g,
        items: g.items.filter((item) =>
          item.title.toLowerCase().includes(search.toLowerCase()),
        ),
      })).filter((g) => g.items.length > 0)
    : grouped;

  return (
    <>
      {/* Mobile overlay */}
      {open && <div className="sidebar-overlay" onClick={onClose} />}
      <aside className={`history ${open ? 'open' : ''}`}>
        <button className="sidebar-close-mobile" onClick={onClose} type="button">
          <CloseIcon />
        </button>
        <button className="new-inquiry" type="button" onClick={() => { onNew(); onClose(); }}>
          <PlusIcon /> {t.newInquiry}
        </button>
        <div className="history-search">
          <SearchIcon />
          <input placeholder={t.searchHistory} value={search}
            onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="history-groups">
          {filtered.length === 0 && (
            <p className="no-history">{t.noHistory}</p>
          )}
          {filtered.map((group) => (
            <div className="history-group" key={group.label}>
              <label>{group.label}</label>
              {group.items.map((item) => (
                <button key={item.id}
                  className={activeSessionId === item.id ? 'selected' : ''}
                  onClick={() => { onSelectSession(item.id); onClose(); }}>
                  <strong>{item.title}</strong>
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="chamber">
          <div>
            <span><ScaleIcon /></span>
            <p><b>{t.chamberTitle}</b><small>{t.chamberSub}</small></p>
          </div>
          <footer>
            <a href="#"><FolderIcon /> {t.archivedDockets}</a>
            <a href="#"><BookIcon /> {t.volumeIndex}</a>
          </footer>
        </div>
      </aside>
    </>
  );
}

function groupHistory(sessions, t) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);

  const groups = { today: [], yesterday: [], previous: [] };

  for (const s of sessions) {
    const d = new Date(s.created_at);
    if (d >= todayStart) groups.today.push(s);
    else if (d >= yesterdayStart) groups.yesterday.push(s);
    else groups.previous.push(s);
  }

  const result = [];
  if (groups.today.length) result.push({ label: t.today, items: groups.today });
  if (groups.yesterday.length) result.push({ label: t.yesterday, items: groups.yesterday });
  if (groups.previous.length) result.push({ label: t.previous, items: groups.previous });
  return result;
}

/* ── Chat View ────────────────────────────────────────────────── */
function ChatView({ onNew }) {
  const { language, t } = useLanguage();
  const inputRef = useRef(null);
  const threadRef = useRef(null);

  // Messages: [{role: 'user'|'assistant', content, citations?, loading?, error?}]
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [processStep, setProcessStep] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Cycle process steps while loading
  useEffect(() => {
    if (!loading) {
      setProcessStep(0);
      return;
    }
    setProcessStep(1);
    const timer1 = setTimeout(() => setProcessStep(2), 1200);
    const timer2 = setTimeout(() => setProcessStep(3), 2800);
    const timer3 = setTimeout(() => setProcessStep(4), 4500);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [loading]);

  const getProcessText = (step) => {
    switch (step) {
      case 1: return t.step1;
      case 2: return t.step2;
      case 3: return t.step3;
      case 4: return t.step4;
      default: return t.searching;
    }
  };

  // Load history on mount
  useEffect(() => {
    fetchChatHistory().then(setHistory).catch(() => {});
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, processStep]);

  // Focus input
  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleNewInquiry = useCallback(() => {
    setMessages([]);
    setQuestion('');
    setSessionId(null);
    setActiveSessionId(null);
    setLoading(false);
    inputRef.current?.focus();
  }, []);

  const ask = useCallback(async (e) => {
    e?.preventDefault();
    const text = question.trim();
    if (!text || loading) return;

    setQuestion('');

    // APPEND user message — never overwrite
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const result = await sendChatMessage(text, language, sessionId);

      // Store session ID from the first response
      if (result.session_id) {
        setSessionId(result.session_id);
        setActiveSessionId(result.session_id);
      }

      // APPEND assistant message
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          citations: result.citations || [],
        },
      ]);

      // Refresh history
      fetchChatHistory().then(setHistory).catch(() => {});
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '', error: err.message },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [question, loading, language, sessionId]);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(e); }
  };

  return (
    <main className="chat-workspace">
      <Sidebar history={history} activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId} onNew={handleNewInquiry}
        open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <section className="chat-area">
        <div className="chat-content" ref={threadRef}>
          {/* Integrity banner */}
          <div className="integrity">
            <span><ScaleIcon /></span>
            <div>
              <h2>{t.integrityTitle} <b>{t.integrityTag}</b></h2>
              <p>{t.integrityDesc}</p>
            </div>
          </div>

          {/* Thread */}
          <div className="thread">
            {messages.length === 0 && (
              <p className="new-inquiry-empty">{t.emptyChat}</p>
            )}

            {messages.map((msg, i) =>
              msg.role === 'user' ? (
                <UserMessage key={i} content={msg.content} />
              ) : (
                <AssistantMessage key={i} content={msg.content}
                  citations={msg.citations} error={msg.error} />
              ),
            )}

            {loading && (
              <p className="request-status animated-status">
                <span className="spinner" />
                <span>{getProcessText(processStep)}</span>
              </p>
            )}
          </div>
        </div>

        {/* Dock / Input */}
        <form className="dock" onSubmit={ask}>
          <div className="dock-box">
            <div className="dock-input">
              <SearchIcon />
              <textarea ref={inputRef} value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={t.composerPlaceholder}
                rows="2" onKeyDown={onKeyDown} />
            </div>
            <div className="dock-tools">
              <span><BookIcon /> {t.searchLang}</span>
              <button type="button" className="filter">{t.volumeFilter}</button>
              <button className="search-btn" disabled={loading} type="submit">
                {loading ? t.sendingLabel : <><span className="send-label">{t.send}</span> <SendIcon /></>}
              </button>
            </div>
          </div>
        </form>

        {/* Mobile sidebar toggle floater is handled by the Header */}
      </section>

      {/* Provide sidebar toggle to header */}
      <SidebarToggleBridge onToggle={() => setSidebarOpen((v) => !v)} />
    </main>
  );
}

/* A tiny bridge to allow the header's sidebar toggle to work */
let _sidebarToggleFn = null;
function SidebarToggleBridge({ onToggle }) {
  useEffect(() => { _sidebarToggleFn = onToggle; return () => { _sidebarToggleFn = null; }; }, [onToggle]);
  return null;
}

/* ── Message Components ───────────────────────────────────────── */
function UserMessage({ content }) {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return (
    <div className="user-message">
      <label>Hon. Justice Inquiry • {time} <span>⚖</span></label>
      <p>{content}</p>
    </div>
  );
}

function AssistantMessage({ content, citations, error }) {
  const { t } = useLanguage();
  const [saved, setSaved] = useState(false);
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="assistant-message">
      <label>
        <span><ScaleIcon /></span> {t.assistantLabel} <i>• {time}</i>
      </label>
      <article>
        {error ? (
          <p className="request-status error">{error}</p>
        ) : (
          <>
            <div className="legal-holding">
              <label>{t.retrievedLabel}</label>
              <p>{content || t.noResults}</p>
            </div>
            <Citations citations={citations || []} saved={saved} setSaved={setSaved} />
          </>
        )}
      </article>
    </div>
  );
}

function Citations({ citations, saved, setSaved }) {
  const { t } = useLanguage();
  if (!citations.length) {
    return <p className="request-status">{t.noCitations}</p>;
  }
  return citations.map((c) => (
    <section className="citation-card" key={`${c.file_number}-${c.rank}`}>
      <header>
        <span><VerifyIcon /> {t.rankedPrecedent} #{c.rank} • ውሳኔ መዝገብ</span>
        <b>{c.score ? `${Math.round(c.score * 100)}% ${t.match}` : t.cassationDivision}</b>
      </header>
      <div className="citation-body">
        <div className="case-title">
          <div>
            <label>{t.court}</label>
            <h3>{c.court}</h3>
            <p>{c.date || t.dateNotAvailable}</p>
          </div>
          <div>
            <label>{t.cassFileNo}</label>
            <h3>መ/ቁ {c.file_number}</h3>
            <p>{c.volume}{c.page ? `, p. ${c.page}` : ''}</p>
          </div>
        </div>
        <label>{t.sourceHolding}</label>
        <blockquote>{c.holding}</blockquote>
        <footer>
          <button onClick={() => setSaved(!saved)} type="button">
            {saved ? t.savedDossier : t.saveDossier}
          </button>
          <small><VerifyIcon /> {t.verifyLabel}</small>
        </footer>
      </div>
    </section>
  ));
}

/* ── App Root ─────────────────────────────────────────────────── */
function AppContent() {
  const [view, setView] = useState('home');
  const [question, setQuestion] = useState('');

  const goHome = () => setView('home');
  const startChat = () => { setView('chat'); setQuestion(''); };
  const askFromHome = (e) => {
    e?.preventDefault();
    if (!question.trim()) return;
    setView('chat');
  };

  return (
    <div className="portal">
      <Header onHome={goHome}
        showSidebarToggle={view === 'chat'}
        onToggleSidebar={() => _sidebarToggleFn?.()} />
      {view === 'home' ? (
        <Home onStart={startChat} question={question}
          setQuestion={setQuestion} onAsk={askFromHome} />
      ) : (
        <ChatView onNew={startChat} />
      )}
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}
