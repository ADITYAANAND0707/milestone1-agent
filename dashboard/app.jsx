(function () {
  'use strict';

  const e = React.createElement;

  function escapeHtml(s) {
    if (!s) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function extractFirstCodeBlock(text) {
    const m = text.match(/```(?:jsx|javascript|js|tsx|typescript|html)?\s*\n([\s\S]*?)```/);
    return m ? m[1].trim() : null;
  }

  /** Prefer a code block that looks like runnable React/UI (has root.render, createElement, JSX, or return). */
  function extractBestRunnableCodeBlock(text) {
    const re = /```(?:jsx|javascript|js|tsx|typescript|html)?\s*\n([\s\S]*?)```/g;
    const blocks = [];
    let m;
    while ((m = re.exec(text)) !== null) {
      const code = m[1].trim();
      if (code.length < 10) continue;
      const runnable = /root\.render|createElement|React\.|return\s*\(|<\/?\w+|className=|className\s*=/i.test(code);
      blocks.push({ code, runnable, len: code.length });
    }
    if (blocks.length === 0) return extractFirstCodeBlock(text);
    const best = blocks.filter(b => b.runnable).sort((a, b) => b.len - a.len)[0];
    return (best || blocks.sort((a, b) => b.len - a.len)[0]).code;
  }

  function textWithoutAnyCodeBlocks(text) {
    return text.replace(/```[\s\S]*?```/g, '').replace(/\n{3,}/g, '\n\n').trim();
  }

  // —— Toast (global) ——
  function Toast({ message, isError, show, onHide }) {
    const ref = React.useRef(null);
    React.useEffect(() => {
      if (!show || !message) return;
      const t = setTimeout(() => { onHide && onHide(); }, 2800);
      return () => clearTimeout(t);
    }, [show, message, onHide]);
    if (!message) return null;
    return e('div', {
      ref,
      className: 'toast' + (isError ? ' err' : '') + (show ? ' show' : ''),
      role: 'status'
    }, message);
  }

  // —— Sidebar ——
  function Sidebar({ activePanel, onPanel, cloneLoading, onClone, collapsed, onToggleCollapse }) {
    const panels = [
      { id: 'catalog', label: 'Component catalog' },
      { id: 'chat', label: 'Chat with Claude' },
      { id: 'generate', label: 'Generate & preview' },
      { id: 'agent', label: 'Chat agent' }
    ];
    return e('div', { className: 'sidebar-wrap' },
      e('button', { type: 'button', className: 'sidebar-toggle', onClick: onToggleCollapse, title: collapsed ? 'Expand sidebar' : 'Collapse sidebar' }, collapsed ? '\u2192' : '\u2190'),
      e('aside', { className: 'sidebar' + (collapsed ? ' collapsed' : '') },
        e('div', { className: 'logo' }, e('span', { className: 'logo-short' }, 'M'), e('span', { className: 'logo-expanded' }, 'Milestone '), e('span', { className: 'logo-num' }, '1')),
        panels.map(p => e('button', {
          key: p.id,
          type: 'button',
          className: 'nav-btn' + (activePanel === p.id ? ' active' : ''),
          'data-panel': p.id,
          onClick: () => onPanel(p.id)
        }, e('span', { className: 'nav-label' }, p.label))),
        e('div', { className: 'status-bar' },
          e('p', { style: { margin: '0 0 0.5rem', fontSize: '0.8rem' } }, 'Local catalog + GitHub repo. No MCP server needed.'),
          e('button', {
            type: 'button',
            className: 'btn btn-secondary',
            style: { width: '100%' },
            disabled: cloneLoading,
            onClick: onClone
          }, cloneLoading ? 'Cloning…' : 'Clone component library')
        )
      )
    );
  }

  // —— Catalog ——
  function CatalogPanel({ catalogList, loading, error, onRetry }) {
    if (loading && !catalogList.length) return e('p', { style: { color: 'var(--text2)' } }, 'Loading…');
    if (error) return e('div', null,
      e('p', { style: { color: 'var(--error)' } }, 'Could not load catalog.'),
      e('p', { style: { color: 'var(--text2)', fontSize: '0.85rem', marginTop: '0.5rem' } }, error),
      e('button', { type: 'button', className: 'btn btn-secondary', style: { marginTop: '0.75rem' }, onClick: onRetry }, 'Retry')
    );
    if (!catalogList.length) return e('p', { style: { color: 'var(--text2)' } }, 'No components in catalog. Add design_system/catalog.json.');
    return e('div', { className: 'catalog-grid' },
      catalogList.map((c, i) => e('div', { key: i, className: 'catalog-item' },
        e('div', { className: 'name' }, c.name),
        e('div', { className: 'path' }, c.import || c.path || ''),
        e('div', { className: 'desc' }, c.description || '')
      ))
    );
  }

  // —— Chat (Claude) ——
  function ChatPanel({ messages, onSend, loading }) {
    const [input, setInput] = React.useState('');
    const scrollRef = React.useRef(null);
    React.useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);
    const send = () => {
      const msg = input.trim();
      if (!msg) return;
      setInput('');
      onSend(msg);
    };
    return e('div', { className: 'card' },
      e('div', { className: 'chat-area' },
        e('div', { ref: scrollRef, className: 'chat-messages' },
          messages.map((m, i) => e('div', { key: i, className: 'chat-msg ' + m.role },
            e('div', { className: 'bubble' }, m.content.includes('```') ? e('pre', null, m.content) : m.content)
          ))
        ),
        e('div', { className: 'chat-input-row' },
          e('textarea', {
            value: input,
            onChange: ev => setInput(ev.target.value),
            onKeyDown: ev => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); send(); } },
            placeholder: 'Ask Claude anything…',
            rows: 2
          }),
          e('button', { type: 'button', className: 'btn btn-primary', disabled: loading, onClick: send },
            loading ? e(React.Fragment, null, e('span', { className: 'spinner' }), ' Send') : 'Send')
        )
      )
    );
  }

  // —— Generate & variants ——
  function GeneratePanel({ toast }) {
    const [prompt, setPrompt] = React.useState('');
    const [code, setCode] = React.useState('');
    const [generateLoading, setGenerateLoading] = React.useState(false);
    const [variantsPrompt, setVariantsPrompt] = React.useState('');
    const [variantCount, setVariantCount] = React.useState(2);
    const [keywords, setKeywords] = React.useState(['', '', '']);
    const [variants, setVariants] = React.useState([]);
    const [variantsLoading, setVariantsLoading] = React.useState(false);
    const previewFrameRef = React.useRef(null);

    const doGenerate = async () => {
      setGenerateLoading(true);
      try {
        const r = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt.trim() || 'A login form with email and password.' })
        });
        const d = await r.json();
        if (d.error) toast(d.error, true);
        else { setCode(d.code || ''); toast('Code generated'); }
      } catch (err) { toast(err.message || 'Failed', true); }
      setGenerateLoading(false);
    };

    const updatePreview = () => {
      const c = code.trim();
      if (!c) { toast('Paste or generate code first', true); return; }
      fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: c }) })
        .then(r => r.text())
        .then(html => { if (previewFrameRef.current) previewFrameRef.current.srcdoc = html; toast('Preview updated'); })
        .catch(() => toast('Preview failed', true));
    };

    const doVariants = async () => {
      const p = variantsPrompt.trim() || 'A login form with email and password.';
      const count = parseInt(variantCount, 10);
      const kw = [keywords[0], keywords[1]].concat(count === 3 ? [keywords[2]] : []);
      setVariantsLoading(true);
      setVariants([]);
      try {
        const r = await fetch('/api/generate-variants', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: p, count, keywords: kw.length ? kw : null })
        });
        const text = await r.text();
        let d;
        try { d = JSON.parse(text); } catch (_) {
          toast(text.trimStart().startsWith('<') ? 'Server returned a page instead of JSON. Open http://127.0.0.1:3850.' : 'Invalid response', true);
          setVariantsLoading(false);
          return;
        }
        if (d.error) { toast(d.error, true); setVariants([]); }
        else { setVariants(d.variants || []); toast('Generated ' + (d.variants && d.variants.length) + ' variant(s)'); }
      } catch (err) { toast(err.message || 'Failed', true); }
      setVariantsLoading(false);
    };

    return e(React.Fragment, null,
      e('div', { className: 'card' },
        e('label', { style: { display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' } }, 'Prompt'),
        e('div', { className: 'generate-row' },
          e('textarea', {
            value: prompt,
            onChange: ev => setPrompt(ev.target.value),
            placeholder: 'e.g. A login form with email, password and submit using our design system'
          }),
          e('button', { type: 'button', className: 'btn btn-primary', disabled: generateLoading, onClick: doGenerate },
            generateLoading ? e(React.Fragment, null, e('span', { className: 'spinner' }), ' Generate') : 'Generate')
        ),
        e('div', { className: 'code-preview-grid' },
          e('div', null,
            e('label', { style: { display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' } }, 'Code'),
            e('textarea', { value: code, onChange: ev => setCode(ev.target.value), placeholder: 'Generated code or paste from Claude' }),
            e('div', { style: { marginTop: '0.5rem' } },
              e('button', { type: 'button', className: 'btn btn-secondary', onClick: () => navigator.clipboard.writeText(code).then(() => toast('Copied')) }, 'Copy code'),
              e('button', { type: 'button', className: 'btn btn-primary', style: { marginLeft: '0.5rem' }, onClick: updatePreview }, 'Update preview')
            )
          ),
          e('div', null,
            e('label', { style: { display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' } }, 'Preview'),
            e('div', { className: 'preview-frame-wrap' },
              e('iframe', { ref: previewFrameRef, title: 'Preview' })
            )
          )
        )
      ),
      e('div', { className: 'card variants-section' },
        e('h3', { style: { margin: '0 0 0.5rem', fontSize: '1.05rem' } }, 'Generate 2 or 3 variants'),
        e('p', { style: { color: 'var(--text2)', fontSize: '0.85rem', margin: '0 0 0.75rem' } }, 'Same prompt, multiple styles. Add short description keywords (e.g. minimal, bold, playful).'),
        e('label', { style: { display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' } }, 'Prompt'),
        e('div', { className: 'generate-row' },
          e('textarea', {
            value: variantsPrompt,
            onChange: ev => setVariantsPrompt(ev.target.value),
            placeholder: 'e.g. A signup form with email, password, confirm password'
          }),
          e('div', { style: { display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-start' } },
            e('label', { style: { fontSize: '0.85rem', color: 'var(--text2)' } }, 'Number of variants'),
            e('select', {
              value: variantCount,
              onChange: ev => setVariantCount(ev.target.value),
              style: { padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontSize: '0.9rem' }
            }, e('option', { value: 2 }, '2'), e('option', { value: 3 }, '3')),
            e('button', { type: 'button', className: 'btn btn-primary', disabled: variantsLoading, onClick: doVariants },
              variantsLoading ? e(React.Fragment, null, e('span', { className: 'spinner' }), ' Generating…') : 'Generate variants')
          )
        ),
        e('div', { className: 'variant-keywords-row' },
          e('label', null, 'Variant 1:'),
          e('input', { type: 'text', value: keywords[0], onChange: ev => setKeywords([ev.target.value, keywords[1], keywords[2]]), placeholder: 'e.g. minimal, clean' }),
          e('label', null, 'Variant 2:'),
          e('input', { type: 'text', value: keywords[1], onChange: ev => setKeywords([keywords[0], ev.target.value, keywords[2]]), placeholder: 'e.g. bold, colorful' }),
          variantCount === 3 && e(React.Fragment, { key: 'k3' },
            e('label', null, 'Variant 3:'),
            e('input', { type: 'text', value: keywords[2], onChange: ev => setKeywords([keywords[0], keywords[1], ev.target.value]), placeholder: 'e.g. playful, rounded' })
          )
        ),
        e('div', { className: 'variants-grid' },
          variants.map((v, i) => e(VariantCard, { key: i, variant: v, index: i, toast }))
        )
      )
    );
  }

  function VariantCard({ variant, index, toast }) {
    const [code, setCode] = React.useState(variant.code || '');
    const iframeRef = React.useRef(null);
    React.useEffect(() => setCode(variant.code || ''), [variant.code]);
    const updatePreview = () => {
      const c = code.trim();
      if (!c) { toast('No code for this variant', true); return; }
      fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: c }) })
        .then(r => r.text())
        .then(html => { if (iframeRef.current) iframeRef.current.srcdoc = html; toast('Preview updated'); })
        .catch(() => toast('Preview failed', true));
    };
    const label = variant.keywords || 'Variant ' + (index + 1);
    return e('div', { className: 'variant-card' },
      e('h4', null, label),
      e('div', { className: 'code-preview-grid' },
        e('div', null,
          e('label', { style: { display: 'block', marginBottom: '0.35rem', fontSize: '0.85rem' } }, 'Code'),
          e('textarea', { className: 'variant-code', value: code, onChange: ev => setCode(ev.target.value), style: { minHeight: '160px' } }),
          e('div', { style: { marginTop: '0.5rem' } },
            e('button', { type: 'button', className: 'btn btn-secondary variant-copy', onClick: () => navigator.clipboard.writeText(code).then(() => toast('Copied')) }, 'Copy'),
            e('button', { type: 'button', className: 'btn btn-primary variant-preview', style: { marginLeft: '0.5rem' }, onClick: updatePreview }, 'Update preview')
          )
        ),
        e('div', null,
          e('label', { style: { display: 'block', marginBottom: '0.35rem', fontSize: '0.85rem' } }, 'Preview'),
          e('div', { className: 'preview-frame-wrap' },
            e('iframe', { ref: iframeRef, title: 'Preview ' + (index + 1) })
          )
        )
      )
    );
  }

  // —— Agent panel ——
  function AgentPanel({ toast }) {
    const [messages, setMessages] = React.useState([]);
    const [input, setInput] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const [history, setHistory] = React.useState([]);
    const [versions, setVersions] = React.useState([]);
    const [selectedVersion, setSelectedVersion] = React.useState(null);
    const [rightPanelOpen, setRightPanelOpen] = React.useState(true);
    const scrollRef = React.useRef(null);
    const layoutRef = React.useRef(null);
    const chatColRef = React.useRef(null);
    const resizeRef = React.useRef(null);

    React.useEffect(() => {
      const handle = resizeRef.current;
      const layout = layoutRef.current;
      const chatCol = chatColRef.current;
      if (!handle || !layout || !chatCol) return;
      const onDown = (ev) => {
        ev.preventDefault();
        const startX = ev.clientX;
        const startW = chatCol.offsetWidth;
        const move = (e) => {
          const dx = e.clientX - startX;
          const newW = Math.max(320, Math.min(window.innerWidth - 320, startW + dx));
          layout.style.setProperty('--agent-chat-width', newW + 'px');
        };
        const up = () => {
          document.removeEventListener('mousemove', move);
          document.removeEventListener('mouseup', up);
        };
        document.addEventListener('mousemove', move);
        document.addEventListener('mouseup', up);
      };
      handle.addEventListener('mousedown', onDown);
      return () => handle.removeEventListener('mousedown', onDown);
    }, []);

    React.useEffect(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    const addVersion = (label, code) => {
      if (!code || !code.trim()) return;
      const id = Date.now() + '-' + Math.random().toString(36).slice(2);
      setVersions(prev => [{
        id,
        label: label || 'Version ' + (prev.length + 1),
        code: code.trim(),
        date: new Date().toLocaleString()
      }, ...prev]);
      setSelectedVersion(id);
    };

    const appendAgentMessage = (role, content) => {
      let bubbleContent = content;
      const code = role === 'assistant' ? extractBestRunnableCodeBlock(content) : null;
      if (role === 'assistant' && code) {
        bubbleContent = textWithoutAnyCodeBlocks(content);
        if (!bubbleContent.replace(/\s/g, '')) bubbleContent = "Here's a preview of the code:";
        addVersion('Chat ' + new Date().toLocaleTimeString(), code);
      }
      setMessages(prev => [...prev, { role, content: bubbleContent, code: role === 'assistant' ? code : null }]);
    };

    const sendAgent = async () => {
      const msg = input.trim();
      if (!msg) return;
      setInput('');
      appendAgentMessage('user', msg);
      const newHistory = [...history, { role: 'user', content: msg }];
      setHistory(newHistory);
      setLoading(true);
      try {
        const r = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg, history: history })
        });
        const d = await r.json();
        if (d.error) appendAgentMessage('assistant', 'Error: ' + d.error);
        else {
          appendAgentMessage('assistant', d.content || '');
          setHistory(prev => [...prev, { role: 'assistant', content: d.content || '' }]);
        }
      } catch (e) {
        appendAgentMessage('assistant', 'Request failed: ' + e.message);
      }
      setLoading(false);
    };

    const copyVersionCode = () => {
      const v = selectedVersion ? versions.find(x => x.id === selectedVersion) : null;
      const c = v ? v.code : '';
      if (c) navigator.clipboard.writeText(c).then(() => toast('Copied'));
      else toast('No code to copy', true);
    };

    const sendSvg = e('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' },
      e('path', { d: 'M22 2L11 13' }),
      e('path', { d: 'M22 2L15 22L11 13L2 9L22 2Z' })
    );

    return e('div', { className: 'agent-layout', ref: layoutRef, id: 'agentLayout' },
      e('div', { className: 'agent-chat-column', ref: chatColRef },
        e('div', { className: 'agent-gpt-chat' },
          e('div', { className: 'agent-gpt-messages-scroll', ref: scrollRef },
            e('div', { className: 'agent-gpt-messages' },
              messages.length === 0 && e('div', { className: 'agent-welcome' },
                e('strong', null, 'Chat agent'), e('br'),
                'How can I help you today? Ask for UI, code changes, or ideas. Previews appear in chat; code is saved in the Code file tab.'
              ),
              messages.map((m, i) => e(AgentMessage, {
                key: i,
                role: m.role,
                content: m.content,
                code: m.code,
                onCopyCode: (code) => { if (code) navigator.clipboard.writeText(code).then(() => toast('Copied')); }
              }))
            )
          ),
          e('div', { className: 'agent-gpt-input-wrap' },
            e('div', { className: 'agent-gpt-input-box' },
              e('textarea', {
                value: input,
                onChange: ev => setInput(ev.target.value),
                onKeyDown: ev => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); sendAgent(); } },
                placeholder: 'Message Chat agent…',
                rows: 1
              }),
              e('button', {
                type: 'button',
                className: 'agent-gpt-send',
                title: 'Send',
                disabled: loading,
                onClick: sendAgent
              }, loading ? e('span', { className: 'spinner' }) : sendSvg)
            )
          )
        ),
        e('button', {
          type: 'button',
          className: 'agent-right-panel-toggle',
          title: rightPanelOpen ? 'Close Code file panel' : 'Open Code file panel',
          onClick: () => setRightPanelOpen(prev => !prev)
        }, rightPanelOpen ? '\u203A' : '\u2039')
      ),
      !rightPanelOpen ? null : e('div', { className: 'agent-resize-handle', ref: resizeRef, title: 'Drag to resize' }),
      e('div', { className: 'agent-preview-column' + (rightPanelOpen ? '' : ' closed') },
        e('div', { className: 'agent-code-file-panel' },
          e('h4', { style: { margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600 } }, 'Code file'),
          e('p', { style: { color: 'var(--text2)', fontSize: '0.85rem', margin: '0 0 0.75rem' } }, 'Code from chat is saved here. Click a file to view or copy.'),
          versions.length === 0 && e('p', { style: { color: 'var(--text2)', fontSize: '0.85rem' } }, 'No code yet. Code from chat will appear here.'),
          e('div', { style: { display: 'flex', flexDirection: 'column', gap: '0.5rem' } },
            versions.map(v => e('button', {
              key: v.id,
              type: 'button',
              className: 'agent-version-item',
              onClick: () => setSelectedVersion(v.id)
            }, e('span', { className: 'v-label' }, v.label), e('div', { className: 'v-date' }, v.date)))
          ),
          selectedVersion && (() => {
            const v = versions.find(x => x.id === selectedVersion);
            if (!v) return null;
            return e('div', { style: { marginTop: '1rem', display: 'flex', flexDirection: 'column' } },
              e('label', { style: { fontSize: '0.9rem', marginBottom: '0.35rem', display: 'block' } }, 'Code'),
              e('textarea', {
                readOnly: true,
                value: v.code,
                style: { minHeight: '200px', width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem', resize: 'vertical' }
              }),
              e('button', { type: 'button', className: 'btn btn-primary', style: { marginTop: '0.5rem' }, onClick: copyVersionCode }, 'Copy code')
            );
          })()
        )
      )
    );
  }

  function AgentMessage({ role, content, code, onCopyCode }) {
    const [previewHtml, setPreviewHtml] = React.useState(null);
    const [previewError, setPreviewError] = React.useState(false);
    const [codeExpanded, setCodeExpanded] = React.useState(true);
    const label = role === 'user' ? 'You' : 'A';
    React.useEffect(() => {
      if (role !== 'assistant' || !code) return;
      setPreviewError(false);
      fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) })
        .then(r => r.text())
        .then(html => { setPreviewHtml(html || null); })
        .catch(() => { setPreviewError(true); });
    }, [role, code]);
    if (!code) {
      return e('div', { className: 'agent-msg ' + role },
        e('div', { className: 'agent-avatar', 'aria-hidden': 'true' }, label),
        e('div', { className: 'agent-bubble', style: { maxWidth: '85%' } }, content)
      );
    }
    return e('div', { className: 'agent-msg ' + role },
      e('div', { className: 'agent-avatar', 'aria-hidden': 'true' }, label),
      e('div', { className: 'agent-msg-body' },
        e('div', { className: 'agent-bubble' }, content),
        e('div', { className: 'agent-inline-preview' },
          e('div', { className: 'agent-inline-preview-label' }, 'Live UI preview'),
          previewError
            ? e('div', { className: 'agent-inline-preview-body agent-preview-fallback', style: { padding: '1rem', color: 'var(--text2)', fontSize: '0.85rem' } }, 'Preview could not be rendered (e.g. TSX/imports). See code below.')
            : previewHtml
              ? e('iframe', { className: 'agent-inline-preview-iframe', title: 'Live UI preview', srcDoc: previewHtml })
              : e('div', { className: 'agent-inline-preview-body', style: { padding: '1rem', color: 'var(--text2)', fontSize: '0.85rem' } }, 'Loading preview…'),
          e('div', { className: 'agent-inline-code-wrap' },
            e('div', { className: 'agent-inline-code-header' },
              e('span', { className: 'agent-inline-code-label' }, 'Code used to generate this UI'),
              e('button', { type: 'button', className: 'btn btn-secondary agent-inline-code-toggle', onClick: () => setCodeExpanded(!codeExpanded) }, codeExpanded ? 'Collapse' : 'Show code'),
              e('button', { type: 'button', className: 'btn btn-secondary', style: { marginLeft: '0.35rem' }, onClick: () => { if (code && onCopyCode) onCopyCode(code); } }, 'Copy code')
            ),
            codeExpanded && e('pre', { className: 'agent-inline-code-block' }, code)
          )
        )
      )
    );
  }

  // —— App ——
  function App() {
    const [activePanel, setActivePanel] = React.useState('catalog');
    const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
    const [catalogList, setCatalogList] = React.useState([]);
    const [catalogLoading, setCatalogLoading] = React.useState(true);
    const [catalogError, setCatalogError] = React.useState(null);
    const [chatHistory, setChatHistory] = React.useState([]);
    const [cloneLoading, setCloneLoading] = React.useState(false);
    const [chatLoading, setChatLoading] = React.useState(false);
    const [toastMessage, setToastMessage] = React.useState('');
    const [toastError, setToastError] = React.useState(false);
    const [toastShow, setToastShow] = React.useState(false);

    const showToast = React.useCallback((msg, isErr) => {
      setToastMessage(msg || '');
      setToastError(!!isErr);
      setToastShow(true);
    }, []);

    const loadCatalog = React.useCallback(async () => {
      setCatalogLoading(true);
      setCatalogError(null);
      if (window.__INJECTED_CATALOG__) {
        const d = window.__INJECTED_CATALOG__;
        const catalog = d && d.catalog && typeof d.catalog === 'object' ? d.catalog : {};
        const comps = catalog.components || (Array.isArray(d) ? d : []);
        setCatalogList(Array.isArray(comps) ? comps : []);
        setCatalogLoading(false);
        return;
      }
      try {
        const r = await fetch('/api/catalog');
        if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
        const ct = r.headers.get('content-type') || '';
        const text = await r.text();
        if (!ct.includes('application/json')) throw new Error('Server returned HTML. Open at http://127.0.0.1:3850 after starting the dashboard.');
        const d = JSON.parse(text);
        const catalog = d && d.catalog && typeof d.catalog === 'object' ? d.catalog : {};
        const comps = catalog.components || (Array.isArray(d) ? d : []);
        setCatalogList(Array.isArray(comps) ? comps : []);
      } catch (e) {
        setCatalogError(e.message || String(e));
        setCatalogList([]);
      }
      setCatalogLoading(false);
    }, []);

    React.useEffect(() => { loadCatalog(); }, [loadCatalog]);

    const handlePanel = (id) => {
      setActivePanel(id);
      document.documentElement.classList.toggle('agent-page', id === 'agent');
    };

    const cloneLibrary = async () => {
      setCloneLoading(true);
      try {
        const r = await fetch('/api/clone-library', { method: 'POST' });
        const d = await r.json();
        if (d.error) showToast(d.error, true);
        else showToast(d.message || 'Cloned');
      } catch (e) { showToast(e.message || 'Failed', true); }
      setCloneLoading(false);
    };

    const sendChat = async (msg) => {
      const prev = chatHistory;
      const next = [...prev, { role: 'user', content: msg }];
      setChatHistory(next);
      setChatLoading(true);
      try {
        const r = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg, history: prev })
        });
        const d = await r.json();
        if (d.error) setChatHistory(prev => [...prev, { role: 'assistant', content: 'Error: ' + d.error }]);
        else setChatHistory(prev => [...prev, { role: 'assistant', content: d.content || '' }]);
      } catch (e) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: 'Request failed: ' + e.message }]);
      }
      setChatLoading(false);
    };

    return e('div', { className: 'app' + (sidebarCollapsed ? ' sidebar-collapsed' : '') },
      e(Sidebar, {
        activePanel,
        onPanel: handlePanel,
        cloneLoading,
        onClone: cloneLibrary,
        collapsed: sidebarCollapsed,
        onToggleCollapse: () => setSidebarCollapsed(prev => !prev)
      }),
      e('main', { className: 'main' },
        e('div', { id: 'panel-catalog', className: 'panel' + (activePanel === 'catalog' ? ' active' : '') },
          e('h2', null, 'Component catalog'),
          e('p', { style: { color: 'var(--text2)', fontSize: '0.9rem', margin: '0 0 1rem' } }, 'From design_system/catalog.json – Untitled UI Next.js starter kit. Use these when generating UI.'),
          e(CatalogPanel, { catalogList, loading: catalogLoading, error: catalogError, onRetry: loadCatalog })
        ),
        e('div', { id: 'panel-chat', className: 'panel' + (activePanel === 'chat' ? ' active' : '') },
          e('h2', null, 'Chat with Claude'),
          e('p', { style: { color: 'var(--text2)', fontSize: '0.9rem', margin: '0 0 1rem' } }, 'Talk to Claude here. Set ANTHROPIC_API_KEY to use.'),
          e(ChatPanel, { messages: chatHistory, onSend: sendChat, loading: chatLoading })
        ),
        e('div', { id: 'panel-generate', className: 'panel' + (activePanel === 'generate' ? ' active' : '') },
          e('h2', null, 'Generate & preview'),
          e('p', { style: { color: 'var(--text2)', fontSize: '0.9rem', margin: '0 0 1rem' } }, 'Generate UI from a prompt or paste code. Preview updates below.'),
          e(GeneratePanel, { toast: showToast })
        ),
        e('div', { id: 'panel-agent', className: 'panel panel-agent' + (activePanel === 'agent' ? ' active' : '') },
          e(AgentPanel, { toast: showToast })
        )
      ),
      e(Toast, {
        message: toastMessage,
        isError: toastError,
        show: toastShow,
        onHide: () => setToastShow(false)
      })
    );
  }

  const root = document.getElementById('root');
  if (root) {
    const reactRoot = ReactDOM.createRoot(root);
    reactRoot.render(e(App));
  }
})();
