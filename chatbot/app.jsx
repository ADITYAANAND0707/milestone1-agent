(function () {
  'use strict';

  const { useState, useEffect, useRef, useCallback, useMemo } = React;
  const e = React.createElement;

  // ════════════════════════════════════════════════════════════
  // Constants & Helpers
  // ════════════════════════════════════════════════════════════

  const STORAGE_KEY = 'chatbot_conversations';

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function generateTitle(message) {
    const cleaned = message.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
    return cleaned.length > 50 ? cleaned.slice(0, 50) + '\u2026' : cleaned;
  }

  function loadConversations() {
    try { const raw = localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : []; }
    catch { return []; }
  }

  function saveConversations(convs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(convs)); } catch {}
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ── Code Extraction (from dashboard logic) ──
  function extractBestRunnableCodeBlock(text) {
    const re = /```(?:jsx|javascript|js|tsx|typescript|html)?\s*\n([\s\S]*?)```/g;
    const blocks = [];
    let m;
    while ((m = re.exec(text)) !== null) {
      const code = m[1].trim();
      if (code.length < 30) continue;
      const hasRootRender = /root\.render/.test(code);
      const hasComponent = /function\s+[A-Z]|const\s+[A-Z]\w*\s*=/.test(code);
      const hasJSX = /className=|className\s*=|<\/?\w+/.test(code);
      // Score: strongly prefer blocks that look like complete runnable components
      let score = code.length;
      if (hasRootRender) score += 50000;
      if (hasComponent) score += 30000;
      if (hasRootRender && hasComponent) score += 20000;
      if (hasJSX) score += 5000;
      blocks.push({ code, score, hasRootRender, hasComponent });
    }
    if (blocks.length === 0) return null;
    blocks.sort((a, b) => b.score - a.score);
    return blocks[0].code;
  }

  // Extract ALL runnable code blocks (for variants)
  function extractAllRunnableCodeBlocks(text) {
    const re = /```(?:jsx|javascript|js|tsx|typescript|html)?\s*\n([\s\S]*?)```/g;
    const blocks = [];
    let m;
    while ((m = re.exec(text)) !== null) {
      const code = m[1].trim();
      if (code.length < 30) continue;
      const hasRootRender = /root\.render/.test(code);
      const hasComponent = /function\s+[A-Z]|const\s+[A-Z]\w*\s*=/.test(code);
      if (hasRootRender && hasComponent) blocks.push(code);
    }
    return blocks;
  }

  // Extract variant labels from text (## Variant 1: Label)
  function extractVariantLabels(text) {
    const re = /##\s*Variant\s*\d+\s*:?\s*([^\n]*)/gi;
    const labels = [];
    let m;
    while ((m = re.exec(text)) !== null) {
      labels.push(m[1].trim() || `Variant ${labels.length + 1}`);
    }
    return labels;
  }

  // Try to extract component name from code
  function extractComponentName(code) {
    const patterns = [
      /function\s+([A-Z][a-zA-Z0-9]*)\s*\(/,
      /const\s+([A-Z][a-zA-Z0-9]*)\s*=/,
    ];
    for (const p of patterns) {
      const m = code.match(p);
      if (m) return m[1];
    }
    return null;
  }

  function textWithoutAnyCodeBlocks(text) {
    return text.replace(/```[\s\S]*?```/g, '').replace(/\n{3,}/g, '\n\n').trim();
  }

  // ── Markdown rendering ──
  function configureMarked() {
    if (!window.marked) return;
    const renderer = {
      code(args) {
        const text = typeof args === 'string' ? args : (args.text || '');
        const lang = typeof args === 'string' ? '' : (args.lang || '');
        let highlighted = escapeHtml(text);
        try {
          if (window.hljs && lang && hljs.getLanguage(lang)) {
            highlighted = hljs.highlight(text, { language: lang }).value;
          } else if (window.hljs) {
            highlighted = hljs.highlightAuto(text).value;
          }
        } catch {}
        return `<div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-lang-label">${escapeHtml(lang || 'code')}</span>
            <button class="copy-code-btn" onclick="window.__copyCode(this)" title="Copy code">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              Copy
            </button>
          </div>
          <pre><code class="hljs ${lang ? 'language-' + escapeHtml(lang) : ''}">${highlighted}</code></pre>
        </div>`;
      }
    };
    marked.use({ renderer, breaks: true, gfm: true });
  }

  function renderMarkdown(text) {
    if (!window.marked) return escapeHtml(text).replace(/\n/g, '<br>');
    try { return marked.parse(text); }
    catch { return escapeHtml(text).replace(/\n/g, '<br>'); }
  }

  window.__copyCode = function (btn) {
    const wrapper = btn.closest('.code-block-wrapper');
    const code = wrapper ? wrapper.querySelector('code') : null;
    if (code) {
      navigator.clipboard.writeText(code.textContent).then(() => {
        btn.classList.add('copied');
        const orig = btn.innerHTML;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
        setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = orig; }, 2000);
      });
    }
  };

  configureMarked();

  // ── Streaming API (supports status + thinking events from multi-agent system) ──
  async function streamChat(message, history, onChunk, onDone, onError, signal, onStatus, onThinking) {
    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }), signal,
      });
      if (!response.ok) { onError(await response.text() || `HTTP ${response.status}`); return; }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            try {
              const parsed = JSON.parse(line.slice(6));
              if (parsed.type === 'chunk' && parsed.text) onChunk(parsed.text);
              else if (parsed.type === 'thinking' && parsed.text && onThinking) onThinking(parsed.text);
              else if (parsed.type === 'status' && parsed.text && onStatus) onStatus(parsed.text);
              else if (parsed.type === 'done') { onDone(); return; }
              else if (parsed.type === 'error') { onError(parsed.error || 'Unknown error'); return; }
            } catch {}
          }
        }
      }
      onDone();
    } catch (err) {
      if (err.name === 'AbortError') onDone();
      else onError(err.message || 'Network error');
    }
  }

  // ── Agent Pipeline Constants ──
  const AGENT_STEPS = [
    { id: 'classify', label: 'Classify', icon: '\uD83C\uDFAF' },
    { id: 'discovery', label: 'Discovery', icon: '\uD83D\uDD0D' },
    { id: 'generation', label: 'Generate', icon: '\u2699\uFE0F' },
    { id: 'qa', label: 'QA Review', icon: '\u2705' },
    { id: 'respond', label: 'Respond', icon: '\uD83D\uDCAC' },
  ];

  const STATUS_TO_STEP = {
    "Analyzing your request...": "classify",
    "Searching component library...": "discovery",
    "Generating React code...": "generation",
    "Reviewing code quality...": "qa",
    "Fixing issues, regenerating...": "generation",
    "Preparing response...": "respond",
  };

  function getAgentStates(activeStepId) {
    if (!activeStepId) return AGENT_STEPS.map(s => ({ ...s, state: 'pending' }));
    const activeIdx = AGENT_STEPS.findIndex(s => s.id === activeStepId);
    return AGENT_STEPS.map((s, i) => ({
      ...s,
      state: i < activeIdx ? 'complete' : i === activeIdx ? 'active' : 'pending',
    }));
  }

  // ── Agent Pipeline Visualization Component ──
  function AgentPipeline({ activeStep, statusText, visible }) {
    if (!visible) return null;
    const states = getAgentStates(activeStep);

    return e('div', { className: 'agent-pipeline' },
      e('div', { className: 'agent-pipeline-label' },
        e('span', { className: 'pipeline-dot' }),
        'Multi-Agent Pipeline'),
      e('div', { className: 'agent-pipeline-track' },
        states.flatMap((step, i) => {
          const node = e('div', { key: step.id, className: `agent-node ${step.state}` },
            e('div', { className: 'agent-node-circle' },
              step.state === 'complete' ? '\u2713'
                : step.state === 'active' ? step.icon
                : '\u25CB'),
            e('div', { className: 'agent-node-label' }, step.label));
          if (i < states.length - 1) {
            const connState = states[i + 1].state === 'complete' || states[i + 1].state === 'active'
              ? (states[i + 1].state === 'active' ? 'active' : 'complete')
              : '';
            return [node, e('div', { key: `conn-${i}`, className: `agent-connector ${connState}` })];
          }
          return [node];
        })
      ),
      statusText && e('div', { className: 'agent-status-text', key: statusText }, statusText)
    );
  }

  // ════════════════════════════════════════════════════════════
  // SVG Icons
  // ════════════════════════════════════════════════════════════

  const I = {
    plus: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('line', { x1: 12, y1: 5, x2: 12, y2: 19 }), e('line', { x1: 5, y1: 12, x2: 19, y2: 12 })),
    send: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('path', { d: 'M22 2L11 13' }), e('path', { d: 'M22 2L15 22L11 13L2 9L22 2Z' })),
    menu: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('line', { x1: 3, y1: 6, x2: 21, y2: 6 }), e('line', { x1: 3, y1: 12, x2: 21, y2: 12 }), e('line', { x1: 3, y1: 18, x2: 21, y2: 18 })),
    trash: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', width: 14, height: 14 },
      e('polyline', { points: '3 6 5 6 21 6' }), e('path', { d: 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2' })),
    bot: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('rect', { x: 3, y: 11, width: 18, height: 10, rx: 2 }), e('circle', { cx: 12, cy: 5, r: 2 }), e('path', { d: 'M12 7v4' })),
    user: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('path', { d: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2' }), e('circle', { cx: 12, cy: 7, r: 4 })),
    panel: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2 }), e('line', { x1: 15, y1: 3, x2: 15, y2: 21 })),
    code: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', className: 'suggestion-icon' },
      e('polyline', { points: '16 18 22 12 16 6' }), e('polyline', { points: '8 6 2 12 8 18' })),
    layout: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', className: 'suggestion-icon' },
      e('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2 }), e('line', { x1: 3, y1: 9, x2: 21, y2: 9 }), e('line', { x1: 9, y1: 21, x2: 9, y2: 9 })),
    zap: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', className: 'suggestion-icon' },
      e('polygon', { points: '13 2 3 14 12 14 11 22 21 10 12 10 13 2' })),
    book: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', className: 'suggestion-icon' },
      e('path', { d: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20' }), e('path', { d: 'M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z' })),
    file: e('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('path', { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' }), e('polyline', { points: '14 2 14 8 20 8' })),
  };

  // ════════════════════════════════════════════════════════════
  // Components
  // ════════════════════════════════════════════════════════════

  function ToastContainer({ toasts, onDismiss }) {
    if (!toasts.length) return null;
    return e('div', { className: 'toast-container' },
      toasts.map(t => e('div', { key: t.id, className: `toast ${t.type || ''}`, onClick: () => onDismiss(t.id) }, t.message))
    );
  }

  // ── Sidebar ──
  function Sidebar({ conversations, activeId, onSelect, onNewChat, onDelete, isOpen, onClose }) {
    const isMobile = window.innerWidth <= 768;
    const groups = useMemo(() => {
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
      const week = new Date(today); week.setDate(week.getDate() - 7);
      const result = { today: [], yesterday: [], week: [], older: [] };
      for (const c of conversations) {
        const t = c.updatedAt || c.createdAt;
        if (t >= today.getTime()) result.today.push(c);
        else if (t >= yesterday.getTime()) result.yesterday.push(c);
        else if (t >= week.getTime()) result.week.push(c);
        else result.older.push(c);
      }
      return result;
    }, [conversations]);

    const grp = (label, items) => {
      if (!items.length) return null;
      return e(React.Fragment, { key: label },
        e('div', { className: 'conv-group-label' }, label),
        items.map(c => e('button', { key: c.id, className: `conv-item ${c.id === activeId ? 'active' : ''}`,
          onClick: () => { onSelect(c.id); if (isMobile) onClose(); } },
          e('span', { className: 'conv-item-title' }, c.title || 'New conversation'),
          e('button', { className: 'conv-item-delete', title: 'Delete', onClick: (ev) => { ev.stopPropagation(); onDelete(c.id); } }, I.trash)
        ))
      );
    };

    return e(React.Fragment, null,
      isMobile && isOpen && e('div', { className: 'sidebar-overlay', onClick: onClose }),
      e('aside', { className: `sidebar ${isMobile ? (isOpen ? 'open' : '') : (isOpen ? '' : 'hidden-desktop')}` },
        e('div', { className: 'sidebar-header' },
          e('button', { className: 'new-chat-btn', onClick: () => { onNewChat(); if (isMobile) onClose(); } }, I.plus, ' New chat')
        ),
        e('div', { className: 'conversations-list' },
          grp('Today', groups.today), grp('Yesterday', groups.yesterday),
          grp('Previous 7 days', groups.week), grp('Older', groups.older),
          conversations.length === 0 && e('div', { style: { padding: 14, color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' } }, 'No conversations yet')
        ),
        e('div', { className: 'sidebar-footer' },
          e('div', { className: 'sidebar-footer-info' }, 'Powered by ', e('span', null, '4-Agent LangGraph'), ' pipeline'))
      )
    );
  }

  // ── Welcome Screen ──
  function WelcomeScreen({ onSuggestion }) {
    const suggestions = [
      { icon: I.layout, text: 'Explain the project architecture and how all pieces connect' },
      { icon: I.book, text: 'What design tokens and components are available?' },
      { icon: I.code, text: 'Generate a React dashboard card using the design system' },
      { icon: I.zap, text: 'How does the preview system and code extraction work?' },
    ];
    return e('div', { className: 'welcome-screen' },
      e('div', { className: 'welcome-logo' },
        e('svg', { width: 24, height: 24, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
          e('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' }))),
      e('h1', { className: 'welcome-title' }, 'Design System Agent'),
      e('p', { className: 'welcome-subtitle' }, 'Multi-agent system: Orchestrator, Discovery, Generator & QA work together. Ask for UI components and watch the agents collaborate in real time.'),
      e('div', { className: 'suggestions-grid' },
        suggestions.map((s, i) => e('button', { key: i, className: 'suggestion-btn', onClick: () => onSuggestion(s.text) },
          s.icon, e('span', null, s.text))))
    );
  }

  // ── Markdown Content ──
  function MarkdownContent({ content, isStreaming }) {
    const ref = useRef(null);
    useEffect(() => {
      if (ref.current) {
        ref.current.innerHTML = renderMarkdown(content || '');
        ref.current.querySelectorAll('pre code:not(.hljs)').forEach(block => {
          if (window.hljs) try { hljs.highlightElement(block); } catch {}
        });
      }
    }, [content]);
    return e(React.Fragment, null,
      e('div', { ref, className: 'markdown-content' }),
      isStreaming && e('span', { className: 'streaming-cursor' }));
  }

  // ── Fullscreen Preview Modal (supports single or multi-variant) ──
  function PreviewModal({ previewHtml, code, codes, labels, onClose, onCopyCode }) {
    const isMulti = codes && codes.length > 1;
    const [iframeLoaded, setIframeLoaded] = useState(false);
    const [iframesLoaded, setIframesLoaded] = useState(() => isMulti ? codes.map(() => false) : []);
    const [multiHtmls, setMultiHtmls] = useState(() => isMulti ? codes.map(() => null) : []);
    const [viewMode, setViewMode] = useState('desktop');
    const widths = { desktop: '100%', tablet: '768px', mobile: '375px' };

    // Close on Escape
    useEffect(() => {
      const handler = (ev) => { if (ev.key === 'Escape') onClose(); };
      document.addEventListener('keydown', handler);
      return () => document.removeEventListener('keydown', handler);
    }, [onClose]);

    // Prevent body scroll
    useEffect(() => {
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = ''; };
    }, []);

    // Fetch preview HTML for each variant
    useEffect(() => {
      if (!isMulti) return;
      codes.forEach((c, i) => {
        fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: c }) })
          .then(r => r.text())
          .then(html => { setMultiHtmls(prev => { const n = [...prev]; n[i] = html; return n; }); })
          .catch(() => {});
      });
    }, []);

    const markMultiLoaded = (i) => setIframesLoaded(prev => { const n = [...prev]; n[i] = true; return n; });

    // If single mode and no previewHtml provided, fetch it
    const [fetchedHtml, setFetchedHtml] = useState(null);
    useEffect(() => {
      if (!isMulti && !previewHtml && code) {
        fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) })
          .then(r => r.text())
          .then(html => { if (html && html.length > 50) setFetchedHtml(html); })
          .catch(() => {});
      }
    }, []);
    const singleHtml = previewHtml || fetchedHtml;

    const title = isMulti ? `${codes.length} Variants` : 'UI Preview';

    return e('div', { className: 'preview-modal-overlay', onClick: (ev) => { if (ev.target === ev.currentTarget) onClose(); } },
      e('div', { className: `preview-modal ${isMulti ? 'preview-modal--multi' : 'preview-modal--single'}` },
        // Toolbar
        e('div', { className: 'preview-modal-toolbar' },
          e('div', { className: 'preview-modal-title' }, title),
          !isMulti && e('div', { className: 'preview-modal-viewport-btns' },
            ['desktop', 'tablet', 'mobile'].map(mode =>
              e('button', { key: mode, className: `viewport-btn ${viewMode === mode ? 'active' : ''}`,
                onClick: () => setViewMode(mode), title: mode.charAt(0).toUpperCase() + mode.slice(1) },
                mode === 'desktop' ? '\uD83D\uDCBB' : mode === 'tablet' ? '\uD83D\uDCF1' : '\uD83D\uDCF1'))),
          e('div', { className: 'preview-modal-actions' },
            !isMulti && e('button', { onClick: () => onCopyCode && onCopyCode(code) }, 'Copy Code'),
            e('button', { className: 'preview-modal-close', onClick: onClose }, '\u2715'))
        ),
        // Viewport label (single only)
        !isMulti && e('div', { className: 'preview-modal-viewport-label' },
          viewMode === 'desktop' ? 'Desktop' : viewMode === 'tablet' ? 'Tablet (768px)' : 'Mobile (375px)'),
        // Preview area
        isMulti
          ? e('div', { className: 'preview-modal-multi-body' },
              codes.map((c, i) => e('div', { key: i, className: 'preview-modal-variant-pane' },
                e('div', { className: 'preview-modal-variant-label' },
                  e('span', null, (labels && labels[i]) || `Variant ${i + 1}`),
                  e('button', { onClick: () => onCopyCode && onCopyCode(c) }, 'Copy')),
                e('div', { className: 'preview-modal-variant-iframe-area' },
                  !iframesLoaded[i] && e('div', { className: 'preview-modal-loading' }, e('span', { className: 'spinner' }), ' Rendering...'),
                  multiHtmls[i] && e('iframe', {
                    className: 'preview-modal-iframe',
                    title: `Variant ${i + 1}`,
                    srcDoc: multiHtmls[i],
                    style: iframesLoaded[i] ? {} : { opacity: 0 },
                    onLoad: () => markMultiLoaded(i),
                  }))
              )))
          : e('div', { className: 'preview-modal-body' },
              (!singleHtml || !iframeLoaded) && e('div', { className: 'preview-modal-loading' }, e('span', { className: 'spinner' }), !singleHtml ? ' Loading preview...' : ' Rendering...'),
              singleHtml && e('div', { className: 'preview-modal-iframe-wrap', style: { maxWidth: widths[viewMode], margin: viewMode !== 'desktop' ? '0 auto' : undefined } },
                e('iframe', {
                  className: 'preview-modal-iframe',
                  title: 'Expanded preview',
                  srcDoc: singleHtml,
                  style: iframeLoaded ? {} : { opacity: 0 },
                  onLoad: () => setIframeLoaded(true),
                })))
      )
    );
  }

  // ── Inline Preview (for assistant messages with code) ──
  function InlinePreview({ code, onCopyCode }) {
    const [previewHtml, setPreviewHtml] = useState(null);
    const [previewError, setPreviewError] = useState(false);
    const [codeExpanded, setCodeExpanded] = useState(false);
    const [iframeLoaded, setIframeLoaded] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);

    useEffect(() => {
      if (!code) return;
      let cancelled = false;
      setPreviewError(false);
      setPreviewHtml(null);
      setIframeLoaded(false);

      const fetchPreview = async () => {
        try {
          const r = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
          });
          if (cancelled) return;
          if (!r.ok) { setPreviewError(true); return; }
          const html = await r.text();
          if (cancelled) return;
          if (html && html.length > 50) {
            setPreviewHtml(html);
          } else {
            setPreviewError(true);
          }
        } catch {
          if (!cancelled) setPreviewError(true);
        }
      };

      fetchPreview();
      return () => { cancelled = true; };
    }, [code]);

    const retryPreview = () => {
      setPreviewError(false);
      setPreviewHtml(null);
      setIframeLoaded(false);
      fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) })
        .then(r => { if (!r.ok) throw new Error(); return r.text(); })
        .then(html => { if (html && html.length > 50) setPreviewHtml(html); else setPreviewError(true); })
        .catch(() => setPreviewError(true));
    };

    return e('div', { className: 'msg-preview-section' },
      e('div', { className: 'msg-preview-header' },
        e('span', { className: 'msg-preview-label' }, 'Live UI Preview'),
        e('div', { className: 'msg-preview-actions' },
          previewHtml && e('button', { className: 'expand-btn', onClick: () => setModalOpen(true), title: 'Expand to full screen' }, '\u26F6 Expand'),
          e('button', { onClick: () => onCopyCode && onCopyCode(code) }, 'Copy Code'),
          previewError && e('button', { onClick: retryPreview }, 'Retry'),
        )
      ),
      previewError
        ? e('div', { className: 'msg-preview-fallback' }, 'Preview could not render. Click Retry or see code below.')
        : previewHtml
          ? e(React.Fragment, null,
              !iframeLoaded && e('div', { className: 'msg-preview-fallback' }, 'Rendering UI...'),
              e('iframe', {
                className: 'msg-preview-iframe',
                title: 'Live preview',
                srcDoc: previewHtml,
                style: iframeLoaded ? {} : { height: 0, overflow: 'hidden' },
                onLoad: () => setIframeLoaded(true),
              }))
          : e('div', { className: 'msg-preview-fallback' },
              e('span', { className: 'spinner' }), ' Fetching preview...'),
      e('div', { className: 'msg-code-section' },
        e('div', { className: 'msg-code-header', onClick: () => setCodeExpanded(!codeExpanded) },
          e('span', null, 'Code used to generate this UI'),
          e('span', null, codeExpanded ? '\u25B2' : '\u25BC')),
        codeExpanded && e('pre', { className: 'msg-code-pre' }, code)),
      // Fullscreen modal
      modalOpen && previewHtml && e(PreviewModal, {
        previewHtml, code, onCopyCode,
        onClose: () => setModalOpen(false),
      })
    );
  }

  // ── Multi-Preview (side-by-side variants with expand) ──
  function MultiPreview({ codes, labels, onCopyCode }) {
    const [expandAll, setExpandAll] = useState(false);
    const [expandSingle, setExpandSingle] = useState(null); // index

    return e('div', { className: 'multi-preview-section' },
      e('div', { className: 'multi-preview-header' },
        e('span', { className: 'msg-preview-label' }, `${codes.length} Variants`),
        e('div', { className: 'msg-preview-actions' },
          e('button', { className: 'expand-btn', onClick: () => setExpandAll(true), title: 'Expand all side-by-side' }, '\u26F6 Expand All'))),
      e('div', { className: 'multi-preview-grid' },
        codes.map((code, i) => e('div', { key: i, className: 'multi-preview-card' },
          e('div', { className: 'multi-preview-card-label' },
            e('span', null, labels[i] || `Variant ${i + 1}`),
            e('div', { className: 'multi-preview-card-actions' },
              e('button', { onClick: () => setExpandSingle(i), title: 'Expand this variant' }, '\u26F6'),
              e('button', { onClick: () => onCopyCode && onCopyCode(code) }, 'Copy'))),
          e(InlinePreview, { code, onCopyCode, compact: true })
        ))),
      // Expand all modal (multi)
      expandAll && e(PreviewModal, {
        codes, labels, onCopyCode,
        onClose: () => setExpandAll(false),
      }),
      // Expand single variant modal
      expandSingle !== null && e(PreviewModal, {
        previewHtml: null, code: codes[expandSingle], onCopyCode,
        onClose: () => setExpandSingle(null),
      })
    );
  }

  // ── Collapsible Thinking Bar (like Cursor's thinking indicator) ──
  function ThinkingBar({ content, isActive }) {
    const [expanded, setExpanded] = useState(false);
    const ref = useRef(null);
    if (!content) return null;

    // Auto-scroll thinking content to bottom when active
    useEffect(() => {
      if (expanded && ref.current) {
        ref.current.scrollTop = ref.current.scrollHeight;
      }
    }, [content, expanded]);

    const lineCount = (content.match(/\n/g) || []).length + 1;
    const charCount = content.length;
    const summary = isActive ? 'Thinking...' : `Thought for ${lineCount} lines`;

    return e('div', { className: `thinking-bar ${isActive ? 'active' : ''}` },
      e('div', { className: 'thinking-bar-header', onClick: () => setExpanded(!expanded) },
        e('span', { className: `thinking-dot ${isActive ? 'active' : ''}` }),
        e('span', { className: 'thinking-label' }, summary),
        e('span', { className: 'thinking-toggle' }, expanded ? '\u25B2' : '\u25BC')
      ),
      expanded && e('div', { ref, className: 'thinking-bar-content' },
        e(MarkdownContent, { content }))
    );
  }

  // ── Single Message ──
  function Message({ role, content, code, codes, variantLabels, bubbleText, thinkingContent, isStreaming, isThinking, onCopyCode }) {
    const isUser = role === 'user';
    const hasMultiple = !isStreaming && codes && codes.length > 1;
    const hasSingle = !isStreaming && !hasMultiple && code;
    return e('div', { className: `message ${role}` },
      e('div', { className: 'msg-avatar' }, isUser ? I.user : I.bot),
      e('div', { className: 'msg-body' },
        e('div', { className: 'msg-role' }, isUser ? 'You' : 'Project Assistant'),
        isUser
          ? e('div', { className: 'msg-content' }, content)
          : e(React.Fragment, null,
              thinkingContent && e(ThinkingBar, { content: thinkingContent, isActive: isThinking || false }),
              e(MarkdownContent, { content: bubbleText || content, isStreaming }),
              hasMultiple && e(MultiPreview, { codes, labels: variantLabels || [], onCopyCode }),
              hasSingle && e(InlinePreview, { code, onCopyCode }))
      )
    );
  }

  // ── Typing Indicator ──
  function TypingIndicator() {
    return e('div', { className: 'message assistant' },
      e('div', { className: 'msg-avatar' }, I.bot),
      e('div', { className: 'msg-body' },
        e('div', { className: 'msg-role' }, 'Project Assistant'),
        e('div', { className: 'typing-indicator' },
          e('div', { className: 'typing-dot' }), e('div', { className: 'typing-dot' }), e('div', { className: 'typing-dot' })))
    );
  }

  // ── Input Area ──
  function InputArea({ onSend, isStreaming, onStop }) {
    const [input, setInput] = useState('');
    const taRef = useRef(null);
    const adjustH = useCallback(() => {
      const ta = taRef.current;
      if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'; }
    }, []);
    const send = useCallback(() => {
      const msg = input.trim(); if (!msg || isStreaming) return;
      setInput(''); if (taRef.current) taRef.current.style.height = 'auto'; onSend(msg);
    }, [input, isStreaming, onSend]);
    const kd = useCallback((ev) => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); send(); } }, [send]);
    useEffect(() => { adjustH(); }, [input, adjustH]);
    useEffect(() => { if (taRef.current) taRef.current.focus(); }, []);

    return e('div', { className: 'input-area' },
      e('div', { className: 'input-wrapper' },
        e('div', { className: 'input-box' },
          e('textarea', { ref: taRef, value: input, onChange: ev => setInput(ev.target.value), onKeyDown: kd,
            placeholder: 'Ask about the project, generate UI, or get help...', rows: 1, disabled: isStreaming }),
          isStreaming
            ? e('button', { className: 'stop-btn', title: 'Stop', onClick: onStop }, e('div', { className: 'stop-icon' }))
            : e('button', { className: 'send-btn', title: 'Send', disabled: !input.trim(), onClick: send }, I.send)
        ),
        e('div', { className: 'input-hint' }, 'Enter to send, Shift+Enter for new line')
      )
    );
  }

  // ── Code Panel (right top) — with folder grouping, context, delete ──
  function CodePanel({ codeFiles, selectedId, onSelect, onCopy, onDelete, onClearAll }) {
    const selected = codeFiles.find(f => f.id === selectedId);

    // Group files by conversation/folder
    const groups = useMemo(() => {
      const map = {};
      for (const f of codeFiles) {
        const folder = f.folder || 'Unsorted';
        if (!map[folder]) map[folder] = [];
        map[folder].push(f);
      }
      return map;
    }, [codeFiles]);

    const [collapsedFolders, setCollapsedFolders] = useState({});
    const toggleFolder = (folder) => setCollapsedFolders(prev => ({ ...prev, [folder]: !prev[folder] }));

    const folderNames = Object.keys(groups);

    return e('div', { className: 'code-panel' },
      e('div', { className: 'code-panel-header' },
        e('h3', null, 'Code Files'),
        e('div', { className: 'code-panel-header-actions' },
          e('span', { className: 'code-count' }, codeFiles.length),
          codeFiles.length > 0 && e('button', { className: 'code-clear-btn', onClick: onClearAll, title: 'Clear all files' }, 'Clear'))),
      e('div', { className: 'code-panel-body' },
        codeFiles.length === 0 && e('div', { className: 'code-panel-empty' }, 'Code from chat will appear here.'),
        folderNames.map(folder => {
          const files = groups[folder];
          const collapsed = collapsedFolders[folder];
          return e('div', { key: folder, className: 'code-folder' },
            e('div', { className: 'code-folder-header', onClick: () => toggleFolder(folder) },
              e('span', { className: `code-folder-arrow ${collapsed ? 'collapsed' : ''}` }, '\u25BC'),
              e('span', { className: 'code-folder-icon' }, '\uD83D\uDCC1'),
              e('span', { className: 'code-folder-name' }, folder),
              e('span', { className: 'code-folder-count' }, files.length)),
            !collapsed && files.map(f => e('div', { key: f.id, className: `code-file-item ${f.id === selectedId ? 'active' : ''}`, onClick: () => onSelect(f.id) },
              e('div', { className: 'code-file-icon' }, I.file),
              e('div', { className: 'code-file-info' },
                e('div', { className: 'code-file-name' }, f.label),
                e('div', { className: 'code-file-meta' },
                  e('span', null, f.time),
                  f.context && e('span', { className: 'code-file-context' }, f.context))),
              e('button', { className: 'code-file-delete', title: 'Delete', onClick: (ev) => { ev.stopPropagation(); onDelete(f.id); } }, '\u2715')
            ))
          );
        }),
        selected && e('div', { className: 'code-viewer' },
          e('div', { className: 'code-viewer-header' },
            e('span', null, selected.label),
            e('div', { className: 'code-viewer-actions' },
              e('button', { onClick: () => onCopy(selected.code) }, 'Copy'),
              e('button', { onClick: () => onDelete(selected.id), className: 'code-viewer-delete' }, 'Delete'))),
          e('pre', null, selected.code))
      )
    );
  }

  // ── Features Panel (right bottom) — Shortcut Tools (all go through chat) ──
  function FeaturesPanel({ onSendToChat, isStreaming }) {
    const [activeTab, setActiveTab] = useState('actions');
    const [varCount, setVarCount] = useState(2);
    const [varKeywords, setVarKeywords] = useState(['', '', '']);

    // Catalog state
    const [catalog, setCatalog] = useState([]);
    const [catLoading, setCatLoading] = useState(false);

    useEffect(() => {
      if (activeTab === 'catalog' && catalog.length === 0) {
        setCatLoading(true);
        fetch('/api/catalog').then(r => r.json()).then(d => {
          setCatalog(d?.catalog?.components || []);
        }).catch(() => {}).finally(() => setCatLoading(false));
      }
    }, [activeTab]);

    const sendAction = (msg) => { if (!isStreaming && onSendToChat) onSendToChat(msg); };

    // ── Variant shortcut: builds a chat prompt from keywords ──
    const sendVariants = () => {
      const kw = varKeywords.slice(0, varCount).map(k => k.trim()).filter(Boolean);
      const kwDesc = kw.length > 0
        ? kw.map((k, i) => `Variant ${i + 1}: ${k}`).join('. ')
        : `Variant 1: minimal and clean. Variant 2: bold and colorful` + (varCount >= 3 ? `. Variant 3: playful and rounded` : '');
      const msg = `Generate ${varCount} different style variants of the last UI component we discussed. ${kwDesc}. Show each variant as a separate jsx code block with a heading. Each must be a complete standalone React component ending with root.render(React.createElement(ComponentName)).`;
      sendAction(msg);
    };

    // Quick action buttons — each must request runnable code
    const codeRule = ' Output the complete updated React component in a single jsx code block. Must end with root.render(React.createElement(ComponentName)). Keep it compact, under 80 lines. Minimal explanation.';
    const styleActions = [
      { label: 'Minimal', prompt: 'Redesign the last UI component with a minimal, clean style. Less borders, more whitespace, simpler.' + codeRule },
      { label: 'Bold', prompt: 'Redesign the last UI component with a bold, vibrant style. Stronger colors, bigger text, more contrast.' + codeRule },
      { label: 'Playful', prompt: 'Redesign the last UI component with a playful, fun style. Rounded corners, bright colors, friendly feel.' + codeRule },
      { label: 'Elegant', prompt: 'Redesign the last UI component with an elegant, premium style. Subtle shadows, refined typography, muted tones.' + codeRule },
      { label: 'Corporate', prompt: 'Redesign the last UI component with a professional corporate style. Clean lines, blue tones, formal layout.' + codeRule },
    ];

    const modifyActions = [
      { label: 'Add Dark Mode', prompt: 'Add dark mode support to the last UI component. Use dark backgrounds, light text, and adjust all colors.' + codeRule },
      { label: 'Make Responsive', prompt: 'Make the last UI component fully responsive. Add mobile-first breakpoints and stack layout on small screens.' + codeRule },
      { label: 'Add Animation', prompt: 'Add smooth animations and transitions to the last UI component. Hover effects, fade-ins, subtle motion.' + codeRule },
      { label: 'Simplify', prompt: 'Simplify the last UI component. Remove unnecessary elements, reduce complexity, keep it clean and functional.' + codeRule },
      { label: 'Add More Detail', prompt: 'Add more detail and polish to the last UI component. Icons, badges, status indicators, richer layout.' + codeRule },
    ];

    const enhanceActions = [
      { label: 'Loading States', prompt: 'Add loading/skeleton states to the last UI component. Show shimmer placeholders while data loads.' + codeRule },
      { label: 'Error Handling', prompt: 'Add error states and validation to the last UI component. Show error messages, red borders, warnings.' + codeRule },
      { label: 'Hover Effects', prompt: 'Add rich hover effects to the last UI component. Scale, shadow, color changes on interactive elements.' + codeRule },
      { label: 'Better Spacing', prompt: 'Improve the spacing and alignment of the last UI component. Better padding, margins, and visual rhythm.' + codeRule },
      { label: 'Add Icons', prompt: 'Add relevant SVG icons to the last UI component to improve visual communication and usability.' + codeRule },
    ];

    const actionBtn = (item) => e('button', {
      key: item.label,
      className: 'shortcut-btn',
      disabled: isStreaming,
      onClick: () => sendAction(item.prompt),
    }, item.label);

    const tabs = [
      { id: 'actions', label: 'Quick Actions' },
      { id: 'variants', label: 'Variants' },
      { id: 'catalog', label: 'Catalog' },
    ];

    return e('div', { className: 'features-panel' },
      e('div', { className: 'features-tabs' },
        tabs.map(t => e('button', { key: t.id, className: `features-tab ${activeTab === t.id ? 'active' : ''}`,
          onClick: () => setActiveTab(t.id) }, t.label))),
      e('div', { className: 'features-body' },

        // ── Quick Actions Tab ──
        activeTab === 'actions' && e(React.Fragment, null,
          e('div', { className: 'shortcut-hint' }, 'Shortcuts that modify the last UI through chat. Full conversation memory.'),

          e('div', { className: 'shortcut-group' },
            e('div', { className: 'shortcut-group-label' }, 'Style'),
            e('div', { className: 'shortcut-grid' }, styleActions.map(actionBtn))),

          e('div', { className: 'shortcut-group' },
            e('div', { className: 'shortcut-group-label' }, 'Modify'),
            e('div', { className: 'shortcut-grid' }, modifyActions.map(actionBtn))),

          e('div', { className: 'shortcut-group' },
            e('div', { className: 'shortcut-group-label' }, 'Enhance'),
            e('div', { className: 'shortcut-grid' }, enhanceActions.map(actionBtn)))
        ),

        // ── Variants Tab (shortcut — goes through chat) ──
        activeTab === 'variants' && e(React.Fragment, null,
          e('div', { className: 'shortcut-hint' }, 'Generate style variants of the last UI via chat. Uses full conversation context.'),

          e('div', { className: 'feature-section' },
            e('div', { className: 'feature-row', style: { marginBottom: 8 } },
              e('select', { value: varCount, onChange: ev => setVarCount(parseInt(ev.target.value)),
                style: { padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, background: 'var(--bg-input)', color: 'var(--text)', fontSize: 12 } },
                e('option', { value: 2 }, '2 variants'), e('option', { value: 3 }, '3 variants')))),

          e('div', { className: 'feature-section' },
            e('div', { className: 'feature-label' }, 'Style Keywords (optional)'),
            [0, 1].concat(varCount >= 3 ? [2] : []).map(i =>
              e('div', { key: i, className: 'variant-keyword-row' },
                e('label', null, `V${i + 1}:`),
                e('input', { value: varKeywords[i], onChange: ev => { const kw = [...varKeywords]; kw[i] = ev.target.value; setVarKeywords(kw); },
                  placeholder: ['minimal, clean', 'bold, colorful', 'playful, rounded'][i] })))),

          e('button', { className: 'feature-btn feature-btn-primary', style: { width: '100%', marginTop: 10 },
            disabled: isStreaming, onClick: sendVariants },
            isStreaming ? 'Chat is busy...' : 'Generate Variants in Chat'),

          e('div', { className: 'shortcut-hint', style: { marginTop: 10 } },
            'Or try quick variant styles:'),
          e('div', { className: 'shortcut-grid' },
            [
              { label: '2 Variants: Light vs Dark', prompt: 'Generate 2 variants of the last UI: Variant 1 with a light/white theme, Variant 2 with a dark theme. Each as a separate jsx code block, each a complete React component with root.render.' },
              { label: '2 Variants: Compact vs Spacious', prompt: 'Generate 2 variants of the last UI: Variant 1 compact/dense with tight spacing, Variant 2 spacious with generous padding. Each as a separate jsx code block.' },
              { label: '3 Variants: Min/Bold/Fun', prompt: 'Generate 3 variants of the last UI: Variant 1 minimal, Variant 2 bold, Variant 3 playful. Each as a separate jsx code block, each a complete React component with root.render.' },
            ].map(actionBtn))
        ),

        // ── Catalog Tab ──
        activeTab === 'catalog' && e(React.Fragment, null,
          e('div', { className: 'shortcut-hint' }, 'Design system components. Click any to use it in chat.'),
          catLoading && e('div', { style: { padding: 16, textAlign: 'center', color: 'var(--text-muted)' } }, e('span', { className: 'spinner' }), ' Loading...'),
          !catLoading && catalog.length === 0 && e('div', { style: { padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 } }, 'No components found.'),
          e('div', { className: 'catalog-mini-list' },
            catalog.map((c, i) => e('div', { key: i, className: 'catalog-mini-item clickable',
              onClick: () => sendAction(`Generate a UI component using the ${c.name} pattern from our design system. Description: ${c.description || c.name}. Make it look polished with Tailwind CSS.`) },
              e('div', { className: 'catalog-mini-name' }, c.name),
              (c.import || c.path) && e('div', { className: 'catalog-mini-path' }, c.import || c.path),
              c.description && e('div', { className: 'catalog-mini-desc' }, c.description))))
        )
      )
    );
  }

  // ════════════════════════════════════════════════════════════
  // Main App
  // ════════════════════════════════════════════════════════════

  function App() {
    const [conversations, setConversations] = useState(() => loadConversations());
    const [activeId, setActiveId] = useState(null);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    const [showTyping, setShowTyping] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
    const [rightPanelOpen, setRightPanelOpen] = useState(true);
    const [toasts, setToasts] = useState([]);
    const [codeFiles, setCodeFiles] = useState([]);
    const [selectedCodeId, setSelectedCodeId] = useState(null);
    const [agentStep, setAgentStep] = useState(null);
    const [agentStatusText, setAgentStatusText] = useState('');
    const [pipelineVisible, setPipelineVisible] = useState(false);
    const [thinkingContent, setThinkingContent] = useState('');

    const scrollRef = useRef(null);
    const abortRef = useRef(null);
    const conversationsRef = useRef(conversations);
    const [rightPanelWidth, setRightPanelWidth] = useState(380);
    const resizingRef = useRef(false);

    // ── Resize handle drag logic ──
    const startResize = useCallback((ev) => {
      ev.preventDefault();
      resizingRef.current = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      const onMove = (moveEv) => {
        if (!resizingRef.current) return;
        const newWidth = window.innerWidth - moveEv.clientX;
        setRightPanelWidth(Math.max(260, Math.min(700, newWidth)));
      };
      const onUp = () => {
        resizingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    }, []);

    const activeConv = useMemo(() => conversations.find(c => c.id === activeId) || null, [conversations, activeId]);
    const messages = activeConv ? activeConv.messages : [];

    useEffect(() => { conversationsRef.current = conversations; saveConversations(conversations); }, [conversations]);
    useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages, streamingContent, showTyping]);

    const addToast = useCallback((message, type) => {
      const id = generateId();
      setToasts(prev => [...prev, { id, message, type }]);
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
    }, []);
    const dismissToast = useCallback((id) => setToasts(prev => prev.filter(t => t.id !== id)), []);

    const addCodeFile = useCallback((label, code, folder, context) => {
      if (!code || !code.trim()) return;
      const id = generateId();
      setCodeFiles(prev => [{
        id,
        label: label || 'Code ' + (prev.length + 1),
        code: code.trim(),
        time: new Date().toLocaleTimeString(),
        folder: folder || 'Components',
        context: context || null,
      }, ...prev]);
      setSelectedCodeId(id);
    }, []);

    const deleteCodeFile = useCallback((id) => {
      setCodeFiles(prev => prev.filter(f => f.id !== id));
      if (selectedCodeId === id) setSelectedCodeId(null);
    }, [selectedCodeId]);

    const clearAllCodeFiles = useCallback(() => {
      setCodeFiles([]);
      setSelectedCodeId(null);
    }, []);

    const copyCode = useCallback((code) => {
      if (code) navigator.clipboard.writeText(code).then(() => addToast('Copied!', 'success'));
    }, [addToast]);

    // Conversation management
    const createNewChat = useCallback(() => {
      const id = generateId();
      setConversations(prev => [{ id, title: 'New conversation', messages: [], createdAt: Date.now(), updatedAt: Date.now() }, ...prev]);
      setActiveId(id); setIsStreaming(false); setStreamingContent(''); setShowTyping(false);
    }, []);

    const selectConversation = useCallback((id) => {
      setActiveId(id); setIsStreaming(false); setStreamingContent(''); setShowTyping(false);
    }, []);

    const deleteConversation = useCallback((id) => {
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeId === id) setActiveId(null);
    }, [activeId]);

    const updateConversation = useCallback((id, updater) => {
      setConversations(prev => prev.map(c => c.id === id ? { ...c, ...updater(c), updatedAt: Date.now() } : c));
    }, []);

    // Process assistant message: extract code(s), strip from bubble, name files
    const processAssistantMessage = useCallback((fullContent, userMessage) => {
      const allBlocks = extractAllRunnableCodeBlocks(fullContent);
      const bestCode = extractBestRunnableCodeBlock(fullContent);
      let bubbleText = fullContent;
      let code = bestCode;
      let codes = allBlocks.length > 1 ? allBlocks : null;
      let variantLabels = null;

      // Build context snippet from user message
      const contextSnippet = userMessage
        ? (userMessage.length > 40 ? userMessage.slice(0, 40) + '...' : userMessage)
        : null;

      if (allBlocks.length > 1) {
        // Multiple variants detected
        variantLabels = extractVariantLabels(fullContent);
        bubbleText = textWithoutAnyCodeBlocks(fullContent);
        if (!bubbleText.replace(/\s/g, '')) bubbleText = `Here are ${allBlocks.length} variant previews:`;
        // Save each variant as a named code file in a Variants folder
        const folderName = 'Variants';
        allBlocks.forEach((c, i) => {
          const compName = extractComponentName(c);
          const label = variantLabels[i] || `Variant ${i + 1}`;
          const fileName = compName ? `${compName} — ${label}` : label;
          addCodeFile(fileName, c, folderName, contextSnippet);
        });
      } else if (code) {
        bubbleText = textWithoutAnyCodeBlocks(fullContent);
        if (!bubbleText.replace(/\s/g, '')) bubbleText = "Here's a preview of the generated UI:";
        const compName = extractComponentName(code);
        const fileName = compName || 'Component ' + new Date().toLocaleTimeString();
        addCodeFile(fileName, code, 'Components', contextSnippet);
      }
      return { bubbleText, code, codes, variantLabels };
    }, [addCodeFile]);

    // Truncate long assistant messages for history to save tokens
    function trimHistoryContent(content, maxLen) {
      if (!content || content.length <= maxLen) return content;
      const codeBlockRe = /```[\s\S]*?```/g;
      let trimmed = content.replace(codeBlockRe, '\n[code block omitted]\n');
      if (trimmed.length > maxLen) trimmed = trimmed.slice(0, maxLen) + '...';
      return trimmed;
    }

    // Send message
    const sendMessage = useCallback(async (text) => {
      let convId = activeId;
      if (!convId) {
        const id = generateId();
        setConversations(prev => [{ id, title: generateTitle(text), messages: [], createdAt: Date.now(), updatedAt: Date.now() }, ...prev]);
        setActiveId(id); convId = id;
      }

      updateConversation(convId, (c) => ({
        messages: [...c.messages, { role: 'user', content: text }],
        title: c.messages.length === 0 ? generateTitle(text) : c.title,
      }));

      // Use ref for latest state to avoid stale closure
      const latestConvs = conversationsRef.current;
      const currentConv = latestConvs.find(c => c.id === convId);
      const allMsgs = currentConv ? currentConv.messages : [];
      // Include the user message we just added
      // IMPORTANT: Keep the LAST assistant message's full content (with code blocks)
      // so the pipeline's _get_previous_code() can find the original component.
      // Only trim OLDER assistant messages to save tokens.
      const rawHistory = [...allMsgs, { role: 'user', content: text }].slice(-20);
      let lastAssistantIdx = -1;
      for (let i = rawHistory.length - 1; i >= 0; i--) {
        if (rawHistory[i].role === 'assistant') { lastAssistantIdx = i; break; }
      }
      const history = rawHistory.map((m, i) => ({
        role: m.role,
        content: m.role === 'assistant' && i !== lastAssistantIdx
          ? trimHistoryContent(m.content, 500)
          : m.content,
      }));

      setShowTyping(true); setStreamingContent(''); setIsStreaming(true);
      setAgentStep(null); setAgentStatusText(''); setPipelineVisible(true);
      setThinkingContent('');
      const controller = new AbortController();
      abortRef.current = controller;
      let fullContent = '';
      let fullThinking = '';
      let firstChunk = true;

      await streamChat(text, history,
        (chunk) => {
          if (firstChunk) { setShowTyping(false); firstChunk = false; }
          fullContent += chunk;
          setStreamingContent(fullContent);
        },
        () => {
          setIsStreaming(false); setShowTyping(false); setStreamingContent('');
          setPipelineVisible(false); setAgentStep(null); setAgentStatusText('');
          setThinkingContent('');
          if (fullContent) {
            const { bubbleText, code, codes, variantLabels } = processAssistantMessage(fullContent, text);
            updateConversation(convId, (c) => ({
              messages: [...c.messages, {
                role: 'assistant', content: fullContent, bubbleText, code, codes, variantLabels,
                thinkingContent: fullThinking || null,
              }],
            }));
          }
        },
        (error) => {
          setIsStreaming(false); setShowTyping(false); setStreamingContent('');
          setPipelineVisible(false); setAgentStep(null); setAgentStatusText('');
          setThinkingContent('');
          updateConversation(convId, (c) => ({
            messages: [...c.messages, { role: 'assistant', content: `Error: ${error}`, bubbleText: `Sorry, an error occurred: ${error}`, code: null }],
          }));
          addToast(error, 'error');
        },
        controller.signal,
        (statusText) => {
          const stepId = STATUS_TO_STEP[statusText] || null;
          if (stepId) setAgentStep(stepId);
          setAgentStatusText(statusText);
        },
        (thinkingChunk) => {
          fullThinking += thinkingChunk;
          setThinkingContent(fullThinking);
        }
      );
    }, [activeId, conversations, updateConversation, addToast, processAssistantMessage]);

    const stopStreaming = useCallback(() => { if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; } }, []);

    // Streaming message processing (live)
    const streamingCode = isStreaming && streamingContent ? extractBestRunnableCodeBlock(streamingContent) : null;
    const streamingBubble = isStreaming && streamingContent
      ? (() => {
          if (streamingCode) return textWithoutAnyCodeBlocks(streamingContent);
          // Check for incomplete code block (odd number of ``` fences)
          const fenceCount = (streamingContent.match(/```/g) || []).length;
          if (fenceCount > 0 && fenceCount % 2 !== 0) {
            // Last code fence is unclosed — strip it to avoid rendering raw code as text
            const lastFence = streamingContent.lastIndexOf('```');
            const textBefore = streamingContent.substring(0, lastFence).trim();
            return textBefore || 'Generating code...';
          }
          return streamingContent;
        })()
      : '';

    const showWelcome = !activeConv || messages.length === 0;

    return e('div', { className: 'app-layout' },
      // Sidebar
      e(Sidebar, { conversations, activeId, onSelect: selectConversation, onNewChat: createNewChat,
        onDelete: deleteConversation, isOpen: sidebarOpen, onClose: () => setSidebarOpen(false) }),

      // Chat main
      e('div', { className: 'chat-main' },
        // Header
        e('div', { className: 'chat-header' },
          e('button', { className: 'sidebar-toggle-btn', title: 'Toggle sidebar', onClick: () => setSidebarOpen(p => !p) }, I.menu),
          e('div', { className: 'header-title' }, 'Design System Agent'),
          e('span', { className: 'header-model-badge langgraph' }, '4 Agents'),
          e('button', { className: 'right-panel-toggle-btn', title: rightPanelOpen ? 'Hide panel' : 'Show panel',
            onClick: () => setRightPanelOpen(p => !p) }, I.panel)),

        // Agent Pipeline (visible during multi-agent processing)
        e(AgentPipeline, { activeStep: agentStep, statusText: agentStatusText, visible: pipelineVisible && isStreaming }),

        // Messages
        e('div', { className: 'messages-scroll', ref: scrollRef },
          showWelcome && !isStreaming
            ? e(WelcomeScreen, { onSuggestion: sendMessage })
            : e('div', { className: 'messages-container' },
                messages.map((m, i) => e(Message, { key: `${activeId}-${i}`, role: m.role,
                  content: m.content, bubbleText: m.bubbleText, code: m.code,
                  codes: m.codes, variantLabels: m.variantLabels,
                  thinkingContent: m.thinkingContent,
                  onCopyCode: copyCode })),
                isStreaming && !showTyping && (streamingContent || thinkingContent) && e(Message, { key: 'streaming',
                  role: 'assistant', content: streamingContent || '',
                  bubbleText: streamingContent ? streamingBubble : (thinkingContent ? '' : ''),
                  code: null, isStreaming: true, isThinking: !!thinkingContent && !streamingContent,
                  thinkingContent: thinkingContent || null,
                  onCopyCode: copyCode }),
                showTyping && e(TypingIndicator, { key: 'typing' }),
                e('div', { style: { height: 16 } })
              )
        ),

        // Input
        e(InputArea, { onSend: sendMessage, isStreaming, onStop: stopStreaming })
      ),

      // Resize handle (draggable)
      rightPanelOpen && e('div', { className: 'resize-handle', onMouseDown: startResize }),

      // Right Panel
      e('div', { className: `right-panel ${rightPanelOpen ? '' : 'closed'}`,
        style: rightPanelOpen ? { width: rightPanelWidth, minWidth: rightPanelWidth } : undefined },
        e(CodePanel, { codeFiles, selectedId: selectedCodeId, onSelect: setSelectedCodeId, onCopy: copyCode, onDelete: deleteCodeFile, onClearAll: clearAllCodeFiles }),
        e(FeaturesPanel, { onSendToChat: sendMessage, isStreaming })
      ),

      e(ToastContainer, { toasts, onDismiss: dismissToast })
    );
  }

  // Mount
  const rootEl = document.getElementById('root');
  if (rootEl) ReactDOM.createRoot(rootEl).render(e(App));
})();
