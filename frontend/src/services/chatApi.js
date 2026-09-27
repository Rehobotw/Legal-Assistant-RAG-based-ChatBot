import { apiBaseUrl } from './apiClient';

export async function sendChatMessage(message, language = 'auto') {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail?.detail || 'The precedent service could not process this inquiry.');
  }
  return response.json();
}
