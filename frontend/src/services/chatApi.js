import { apiBaseUrl } from './apiClient';

export async function sendChatMessage(message, language = 'auto', sessionId = null) {
  const body = { message, language };
  if (sessionId) body.session_id = sessionId;

  let response;
  try {
    response = await fetch(`${apiBaseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      'Cannot reach the precedent service. Start the backend on port 8000 and try again.',
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    if (typeof detail?.detail === 'string') throw new Error(detail.detail);
    if (response.status === 404) {
      throw new Error(
        'The precedent API route was not found. Check the frontend API proxy configuration.',
      );
    }
    throw new Error(
      `The precedent service could not process this inquiry (HTTP ${response.status}).`,
    );
  }
  return response.json();
}

export async function fetchChatHistory() {
  let response;
  try {
    response = await fetch(`${apiBaseUrl}/chat/history`);
  } catch {
    return [];
  }
  if (!response.ok) return [];
  return response.json();
}
