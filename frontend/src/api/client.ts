export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface SessionResponse {
  session_id: string;
  created_at: string;
  dataset_name?: string;
  dataset_shape?: number[];
  dataset_columns?: string[];
}

export interface SessionInfo {
  session_id: string;
  title: string;
  updated_at: string;
}

export interface UploadResponse {
  filename: string;
  shape: [number, number];
  columns: string[];
  preview: Record<string, any>[];
}

export interface QueryResponse {
  answer: string;
  table_data: Record<string, any>[] | null;
  visualization_urls: string[];
  messages: Message[];
}

export interface LLMConfigResponse {
  current: {
    backend: string;
    model: string;
    host: string;
    has_api_key: boolean;
    base_url?: string;
  };
  available_models: Record<string, string[]>;
  backends: Record<string, string>;
}

export interface LLMConfigRequest {
  backend: string;
  model: string;
  host?: string;
  api_key?: string;
  base_url?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = {
  /**
   * Create a new analysis session.
   */
  async createSession(): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE_URL}/sessions`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
  },

  /**
   * List all persisted sessions on disk.
   */
  async listSessions(): Promise<SessionInfo[]> {
    const res = await fetch(`${API_BASE_URL}/sessions`);
    if (!res.ok) throw new Error('Failed to list sessions');
    return res.json();
  },

  /**
   * Load and hydrate a session from disk into memory.
   */
  async loadSession(sessionId: string): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(`Failed to load session ${sessionId}`);
    return res.json();
  },

  /**
   * Delete a session from memory and disk.
   */
  async deleteSession(sessionId: string): Promise<{ status: string; session_id: string }> {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`Failed to delete session ${sessionId}`);
    return res.json();
  },

  /**
   * Upload a dataset and load it into the active session.
   */
  async uploadData(sessionId: string, file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload dataset');
    return res.json();
  },

  /**
   * Process a natural language query for the active session.
   */
  async querySession(sessionId: string, text: string): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error('Failed to process query');
    return res.json();
  },

  /**
   * Retrieve the chat history for a session.
   */
  async getMessages(sessionId: string): Promise<Message[]> {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error(`Failed to fetch messages for session ${sessionId}`);
    return res.json();
  },

  /**
   * Retrieve the active LLM configuration and choices.
   */
  async getLLMConfig(): Promise<LLMConfigResponse> {
    const res = await fetch(`${API_BASE_URL}/llm/config`);
    if (!res.ok) throw new Error('Failed to fetch LLM config');
    return res.json();
  },

  /**
   * Update the active LLM configuration.
   */
  async updateLLMConfig(data: LLMConfigRequest): Promise<{ status: string; config: any }> {
    const res = await fetch(`${API_BASE_URL}/llm/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update LLM config');
    return res.json();
  },
};
