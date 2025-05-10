// react-ui/src/components/ChatInput.jsx

import React, { useState } from 'react';
import './ChatInput.css'; // We'll create this CSS file

function ChatInput({ onSendMessage, disabled }) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault(); // Prevent form submission from reloading the page
    if (inputValue.trim() && !disabled) {
      onSendMessage(inputValue.trim());
      setInputValue(''); // Clear input after sending
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Ask me about your expenses..."
        disabled={disabled}
        aria-label="Chat message input"
      />
      <button type="submit" disabled={disabled || !inputValue.trim()}>
        Send
      </button>
    </form>
  );
}

export default ChatInput;