// react-ui/src/components/MessageBubble.jsx

import React from 'react';
import Plot from 'react-plotly.js';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'; // Or choose another style
import './MessageBubble.css'; // We'll create this CSS file

function MessageBubble({ message }) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`message-bubble ${message.role}`}>
      <div className="message-text">{message.text}</div>
      {isAssistant && message.chartData && (
        <div className="chart-container">
          <Plot
            data={message.chartData.data}
            layout={message.chartData.layout}
            useResizeHandler={true}
            style={{ width: '100%', minHeight: '300px' }} // Ensure chart has some height
            config={{ responsive: true, displayModeBar: false }} // Make it responsive, hide mode bar
          />
        </div>
      )}
      {isAssistant && message.sqlQuery && (
        <div className="sql-container">
          <details>
            <summary>View Generated SQL</summary>
            <SyntaxHighlighter language="sql" style={atomOneDark} customStyle={{ fontSize: '0.85em', padding: '10px', borderRadius: '4px' }}>
              {message.sqlQuery}
            </SyntaxHighlighter>
          </details>
        </div>
      )}
    </div>
  );
}

export default MessageBubble;