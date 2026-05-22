import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Sparkles, 
  Database, 
  Plus, 
  Trash2, 
  Send, 
  Upload, 
  X, 
  AlertCircle, 
  Image as ImageIcon,
  Clock,
  ArrowRight,
  Cpu,
  Settings,
  Sliders,
  Key,
  BarChart3,
  Copy,
  Check,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useAppStore } from './state/store';

interface CollapsibleCodeBlockProps {
  language: string;
  code: string;
}

function CollapsibleCodeBlock({ language, code }: CollapsibleCodeBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const lines = code.split('\n');
  const maxInitialLines = 10;
  const isLong = lines.length > maxInitialLines;
  
  const displayedCode = isExpanded || !isLong 
    ? code 
    : lines.slice(0, maxInitialLines).join('\n');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code: ', err);
    }
  };

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <span className="terminal-badge">{language.toUpperCase()}</span>
        <button className="btn-terminal-copy" onClick={handleCopy} title="Copy output">
          {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <div className="terminal-body" style={{ maxHeight: isExpanded ? 'none' : '260px', overflowY: isExpanded ? 'visible' : 'auto' }}>
        <pre className="terminal-pre">
          <code>{displayedCode}</code>
        </pre>
        {!isExpanded && isLong && <div className="terminal-fade-overlay" />}
      </div>
      {isLong && (
        <button 
          className="btn-terminal-toggle" 
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? (
            <>
              <ChevronUp size={16} />
              Collapse Output
            </>
          ) : (
            <>
              <ChevronDown size={16} />
              Show More ({lines.length - maxInitialLines} lines)
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default function App() {
  const {
    sessions,
    currentSession,
    messages,
    isLoading,
    activeDataset,
    error,
    llmConfig,
    fetchSessions,
    createSession,
    selectSession,
    deleteSession,
    uploadFile,
    sendQuery,
    clearError,
    fetchLLMConfig,
    updateLLMConfig
  } = useAppStore();

  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Settings Panel States
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedBackend, setSelectedBackend] = useState('ollama');
  const [selectedModel, setSelectedModel] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [hostUrl, setHostUrl] = useState('http://localhost:11434');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // Load session list and LLM config on start
  useEffect(() => {
    fetchSessions();
    fetchLLMConfig();
  }, [fetchSessions, fetchLLMConfig]);

  // Sync settings inputs when configuration hydrates
  useEffect(() => {
    if (llmConfig) {
      setSelectedBackend(llmConfig.current.backend);
      setSelectedModel(llmConfig.current.model);
      setHostUrl(llmConfig.current.host || 'http://localhost:11434');
      setBaseUrl(llmConfig.current.base_url || 'https://api.openai.com/v1');
      
      const isPredefined = (llmConfig.available_models[llmConfig.current.backend] || []).includes(llmConfig.current.model);
      if (!isPredefined) {
        setSelectedModel('custom');
        setCustomModel(llmConfig.current.model);
      }
    }
  }, [llmConfig]);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = () => {
    if (!inputValue.trim() || isLoading) return;
    sendQuery(inputValue.trim());
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleSaveSettings = () => {
    const finalModel = selectedModel === 'custom' ? customModel : selectedModel;
    updateLLMConfig({
      backend: selectedBackend,
      model: finalModel,
      host: (selectedBackend === 'ollama' || selectedBackend === 'ollama_paid') ? hostUrl : undefined,
      api_key: apiKey ? apiKey : undefined,
      base_url: selectedBackend === 'openai' ? baseUrl : undefined,
    }).then(() => {
      setIsSettingsOpen(false);
      setApiKey('');
    });
  };

  return (
    <div className="app-container">
      {/* Global Error Toast */}
      {error && (
        <div className="alert-toast">
          <AlertCircle size={20} className="text-danger" />
          <span style={{ flex: 1 }}>{error}</span>
          <button className="btn-close-toast" onClick={clearError}>
            <X size={18} />
          </button>
        </div>
      )}

      {/* Hidden File Input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) uploadFile(file);
        }} 
        accept=".csv,.xlsx,.xls,.json,.parquet" 
        style={{ display: 'none' }} 
      />

      {/* Sidebar - Sessions List */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-dot"></span>
            Analytix
          </div>
        </div>

        <button className="btn-new-chat" onClick={createSession} disabled={isLoading}>
          <Plus size={18} />
          New Analysis
        </button>

        {activeDataset && (
          <button className="btn-sidebar-inspector" onClick={() => setIsInspectorOpen(true)}>
            <Database size={16} />
            Dataset Inspector
          </button>
        )}

        <div className="sessions-list-container">
          <h3 className="sessions-list-title">Analysis History</h3>
          {sessions.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#6e6484', fontSize: '0.85rem' }}>
              No history yet. Start a new session.
            </div>
          ) : (
            sessions.map((s) => (
              <div 
                key={s.session_id} 
                className={`session-item ${currentSession?.session_id === s.session_id ? 'active' : ''}`}
                onClick={() => !isLoading && selectSession(s.session_id)}
              >
                <div className="session-item-details">
                  <div className="session-item-title">{s.title || 'Unnamed Session'}</div>
                  <div className="session-item-time">
                    <Clock size={10} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                    {new Date(s.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <button 
                  className="btn-delete-session" 
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!isLoading) deleteSession(s.session_id);
                  }}
                  title="Delete Session"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          {llmConfig && (
            <div className="sidebar-llm-info" onClick={() => setIsSettingsOpen(true)} title="Configure LLM Backend">
              <Cpu size={14} className="neon-icon" />
              <div className="llm-info-text">
                <span className="llm-info-backend">{llmConfig.current.backend.toUpperCase()}</span>
                <span className="llm-info-model">{llmConfig.current.model}</span>
              </div>
              <Settings size={14} className="settings-trigger-icon" />
            </div>
          )}
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="workspace">
        <header className="workspace-header">
          <div className="header-session-info">
            <span className="header-session-title">
              {currentSession ? 'Active Analysis Workspace' : 'Welcome'}
            </span>
            {activeDataset && (
              <div className="badge-dataset">
                <Database size={12} />
                {activeDataset.filename}
              </div>
            )}
          </div>
        </header>

        {/* Chat / Content Window */}
        {!currentSession ? (
          /* Empty Landing State */
          <div className="landing-container" style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center', padding: '40px 20px', background: 'transparent' }}>
            <h1 className="landing-title" style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '1.25rem', letterSpacing: '-0.03em', lineHeight: 1.15 }}>
              Analyze your data<br/>
              <span style={{ color: 'var(--primary)' }}>with intelligence.</span>
            </h1>
            <p className="landing-subtitle" style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '3.5rem', lineHeight: 1.6 }}>
              Upload any dataset to start a conversation with your data.<br/>
              Generate insights, visualizations, and reports in seconds.
            </p>
            
            <div className="landing-steps" style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginBottom: '40px', width: '100%' }}>
              <div className="landing-step-card" style={{ flex: 1, padding: '24px 20px', borderRadius: '12px', border: '1px solid #d6d9e0', background: '#ffffff', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', textAlign: 'center' }}>
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px' }}>
                  <Upload size={24} style={{ color: 'var(--primary)' }} />
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>1. Upload</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>CSV, Excel, or JSON</p>
              </div>
              
              <div className="landing-step-card" style={{ flex: 1, padding: '24px 20px', borderRadius: '12px', border: '1px solid #d6d9e0', background: '#ffffff', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', textAlign: 'center' }}>
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px' }}>
                  <Send size={24} style={{ color: 'var(--primary)' }} />
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>2. Ask</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>Natural language query</p>
              </div>
              
              <div className="landing-step-card" style={{ flex: 1, padding: '24px 20px', borderRadius: '12px', border: '1px solid #d6d9e0', background: '#ffffff', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', textAlign: 'center' }}>
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px' }}>
                  <Database size={24} style={{ color: 'var(--primary)' }} />
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>3. Insight</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>Reports & Visuals</p>
              </div>
            </div>

            <button className="btn-new-chat" style={{ margin: '0 auto' }} onClick={createSession}>
              Create Session to Start
              <ArrowRight size={16} />
            </button>
          </div>
        ) : !activeDataset ? (
          /* File Upload State */
          <div className="upload-container">
            <div className="upload-card" onClick={triggerFileSelect}>
              <div className="upload-icon-wrapper">
                <Upload size={32} />
              </div>
              <h2 className="upload-title">Ingest Your Dataset</h2>
              <p className="upload-subtitle">
                Click here or select a CSV data file to load it into the active AI orchestration environment.
              </p>
              <button className="btn-browse">Browse local files</button>
            </div>
          </div>
        ) : (
          /* Active Chat and Analysis Mode */
          <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              <div className="chat-area">
                {messages.map((msg, index) => (
                  <div key={index} className={`message-bubble ${msg.role}`}>
                    <div className="avatar">
                      {msg.role === 'user' ? 'U' : 'AI'}
                    </div>
                    <div className="message-content">
                      <div className="markdown-body">
                        <ReactMarkdown
                          components={{
                            code({ node, className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '');
                              const isInline = !match && !String(children).includes('\n');
                              if (isInline) {
                                return <code className={className} {...props}>{children}</code>;
                              }
                              return (
                                <CollapsibleCodeBlock 
                                  language={match ? match[1] : 'text'} 
                                  code={String(children).trim()} 
                                />
                              );
                            }
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>

                      {/* Render Visual Blocks attached to this message */}
                      {msg.role === 'assistant' && (msg as any).visualization_urls && (msg as any).visualization_urls.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
                          {(msg as any).visualization_urls.map((url: string, uIdx: number) => (
                            <div key={uIdx} className="visualization-container">
                              <img 
                                src={url} 
                                alt={`Visualization ${uIdx + 1}`} 
                                className="visualization-image"
                                onClick={() => window.open(url, '_blank')}
                              />
                              <div className="visualization-caption">
                                <ImageIcon size={12} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                                Click chart to expand full resolution (PNG)
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Render Table Blocks attached to this message */}
                      {msg.role === 'assistant' && (msg as any).table_data && (msg as any).table_data.length > 0 && (
                        <div className="data-preview-table-container">
                          <table className="data-preview-table">
                            <thead>
                              <tr>
                                {Object.keys((msg as any).table_data[0]).map((col) => (
                                  <th key={col}>{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {(msg as any).table_data.slice(0, 15).map((row: any, rIdx: number) => (
                                <tr key={rIdx}>
                                  {Object.values(row).map((val: any, vIdx) => (
                                    <td key={vIdx}>{val !== null ? String(val) : ''}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {(msg as any).table_data.length > 15 && (
                            <div style={{ padding: '8px 12px', fontSize: '0.75rem', color: '#6e6484', borderTop: '1px solid rgba(255,255,255,0.05)', textAlign: 'center' }}>
                              Showing 15 of {(msg as any).table_data.length} preview rows
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {isLoading && (
                  <div className="thinking-bubble">
                    <div className="thinking-dots">
                      <span className="dot"></span>
                      <span className="dot"></span>
                      <span className="dot"></span>
                    </div>
                    Agent Orchestrator is executing...
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input */}
              <div className="chat-input-container">
                <div className="chat-input-wrapper">
                  <textarea
                    className="chat-input"
                    placeholder="Ask a question about the dataset (e.g., 'visualize correlation matrix', 'calculate average sales')..."
                    rows={1}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                  />
                  <button 
                    className="btn-send" 
                    onClick={handleSend}
                    disabled={!inputValue.trim() || isLoading}
                  >
                    <Send size={18} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* LLM Settings Modal */}
      {isSettingsOpen && llmConfig && (
        <div className="settings-modal-backdrop">
          <div className="settings-modal">
            <div className="settings-modal-header">
              <h2>
                <Sliders size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--primary)' }} />
                LLM Configuration
              </h2>
              <button className="btn-close-modal" onClick={() => setIsSettingsOpen(false)}>
                <X size={20} />
              </button>
            </div>
            
            <div className="settings-modal-body">
              <div className="settings-form-group">
                <label>Provider Backend</label>
                <select 
                  className="settings-select"
                  value={selectedBackend}
                  onChange={(e) => {
                    const nextBackend = e.target.value;
                    setSelectedBackend(nextBackend);
                    const models = llmConfig.available_models[nextBackend] || [];
                    setSelectedModel(models[0] || 'custom');
                  }}
                >
                  {Object.entries(llmConfig.backends).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>

              {(selectedBackend === 'ollama' || selectedBackend === 'ollama_paid') && (
                <div className="settings-form-group">
                  <label>Ollama Host URL</label>
                  <input
                    type="text"
                    className="settings-input"
                    value={hostUrl}
                    onChange={(e) => setHostUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                  />
                </div>
              )}

              <div className="settings-form-group">
                <label>Select Model</label>
                <select 
                  className="settings-select"
                  value={
                    (llmConfig.available_models[selectedBackend] || []).includes(selectedModel) 
                      ? selectedModel 
                      : 'custom'
                  }
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedModel(val);
                    if (val === 'custom') {
                      setCustomModel('');
                    }
                  }}
                >
                  {(llmConfig.available_models[selectedBackend] || []).map((modelName) => (
                    <option key={modelName} value={modelName}>{modelName}</option>
                  ))}
                  <option value="custom">-- Custom Model Name --</option>
                </select>
              </div>

              {selectedModel === 'custom' && (
                <div className="settings-form-group">
                  <label>Custom Model Name</label>
                  <input 
                    type="text" 
                    className="settings-input"
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    placeholder="Enter custom model identifier..."
                  />
                </div>
              )}

              {selectedBackend === 'openai' && (
                <div className="settings-form-group">
                  <label>OpenAI Base URL</label>
                  <input 
                    type="text" 
                    className="settings-input"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://api.openai.com/v1"
                  />
                </div>
              )}

              {selectedBackend !== 'ollama' && (
                <div className="settings-form-group">
                  <label>API Key</label>
                  <input 
                    type="password" 
                    className="settings-input"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={llmConfig.current.has_api_key && selectedBackend === llmConfig.current.backend ? "•••••••••••••••• (Configured)" : "Enter API Key..."}
                  />
                  {llmConfig.current.has_api_key && selectedBackend === llmConfig.current.backend ? (
                    <div className="settings-api-badge success">
                      <Key size={10} />
                      Credentials configured securely on server
                    </div>
                  ) : (
                    <div className="settings-api-badge warning">
                      <Key size={10} />
                      API Key required for this backend
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="settings-modal-footer">
              <button className="settings-btn-secondary" onClick={() => setIsSettingsOpen(false)}>
                Cancel
              </button>
              <button 
                className="settings-btn-primary" 
                onClick={handleSaveSettings}
                disabled={isLoading || (selectedModel === 'custom' && !customModel.trim())}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dataset Inspector Modal Popup */}
      {isInspectorOpen && activeDataset && (
        <div className="settings-modal-backdrop">
          <div className="settings-modal" style={{ maxWidth: '640px' }}>
            <div className="settings-modal-header">
              <h2>
                <Database size={18} style={{ marginRight: '8px', color: 'var(--primary)' }} />
                Dataset Inspector Overview
              </h2>
              <button className="btn-close-modal" onClick={() => setIsInspectorOpen(false)}>
                <X size={20} />
              </button>
            </div>
            
            <div className="settings-modal-body">
              <div className="inspector-section-title" style={{ marginTop: 0 }}>Overview</div>
              <div className="meta-card">
                <div className="meta-row">
                  <span className="meta-label">Filename</span>
                  <span className="meta-value">{activeDataset.filename}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Rows Count</span>
                  <span className="meta-value">{activeDataset.shape[0].toLocaleString()} rows</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Columns Count</span>
                  <span className="meta-value">{activeDataset.shape[1].toLocaleString()} columns</span>
                </div>
              </div>

              <div className="inspector-section-title">Variables List & Columns</div>
              <div className="variables-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px', maxHeight: '300px', overflowY: 'auto', paddingRight: '4px' }}>
                {activeDataset.columns.map((col) => (
                  <div key={col} className="variable-badge">
                    <span className="variable-name" title={col}>{col}</span>
                    <span className="variable-type">col</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="settings-modal-footer">
              <button className="settings-btn-secondary" onClick={() => setIsInspectorOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
