// react-ui/src/components/ChatWindow.jsx

import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble.jsx';
import './ChatWindow.css'; // We'll create this CSS file

function ChatWindow({ messages, isLoading }) {
  const messagesEndRef = useRef(null); // Ref for auto-scrolling

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]); // Scroll whenever messages change

  return (
    <div className="chat-window">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isLoading && (
        <div className="message-bubble assistant typing-indicator">
          <span>Thinking</span><span>.</span><span>.</span><span>.</span>
        </div>
      )}
      <div ref={messagesEndRef} /> {/* Invisible element to scroll to */}
    </div>
  );
}

export default ChatWindow;