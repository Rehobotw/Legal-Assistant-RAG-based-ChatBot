import { useState } from 'react';
import { sendChatMessage } from '../services/chatApi';

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');

  const send = async (message) => {
    setIsStreaming(true);
    setError('');
    try {
      return await sendChatMessage(message);
    } catch (requestError) {
      setError(requestError.message);
      throw requestError;
    } finally {
      setIsStreaming(false);
    }
  };

  return { isStreaming, error, send };
}
