// react-ui/src/App.jsx

import { useState, useEffect, useRef } from 'react';
import './App.css'; // We will create this CSS file next

// Import components
import ChatWindow from './components/ChatWindow.jsx';
import ChatInput from './components/ChatInput.jsx';

// --- Mock Data (as per your screenshot and logs) ---
const mockChartData = {
  data: [
    {
      type: 'bar',
      x: ['Beauty', 'Grocery', 'Health', 'Household', 'Restaurant', 'Utilities'], // From your screenshot
      y: [7257, 7101, 2900, 2500, 2353, 1517], // Values from your mock text
      marker: { color: 'rgb(26, 118, 255)' } // A standard blue color
    }
  ],
  layout: {
    title: 'Total Expense by Category',
    xaxis: { title: 'Category', automargin: true, tickangle: -45 }, // Added tickangle for better label display
    yaxis: { title: 'Total Expense (INR)', automargin: true },
    margin: { l: 70, r: 20, t: 50, b: 120 } // Increased bottom margin for angled labels
  }
};

const mockSqlQuery = "SELECT category, SUM(amount) AS total_expense FROM expenses WHERE user = 'Puspita' GROUP BY category ORDER BY total_expense DESC";
// --- End Mock Data ---

function App() {
  const [messages, setMessages] = useState([
    {
      id: 'greeting-1', // Unique ID
      role: 'assistant',
      text: 'Greetings! How can I help you with your finances today?',
      chartData: null,
      sqlQuery: null
    },
    {
      id: 'user-1',
      role: 'user',
      text: 'Puspitas total expenses divided across categories' // From your screenshot
    },
    {
      id: 'assistant-1',
      role: 'assistant',
      text: "Hi Puspita! Here's a summary of your expenses: Your biggest expense was on Beauty products, totalling INR 7257. Grocery shopping came in a close second at INR 7101. Health expenses were INR 2900, followed by Household expenses at INR 2500. Restaurant meals cost you INR 2353, and Utilities were INR 1517. In short, you spent a significant portion of your budget on beauty and groceries. A chart visualizing this data would clearly show this breakdown.", // Text from your screenshot
      chartData: mockChartData,
      sqlQuery: mockSqlQuery
    }
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null); // To store any potential errors

  // Placeholder for sending a message (will be implemented later)
  const handleSendMessage = async (inputText) => {
    console.log('User wants to send:', inputText);
    // For the mock, let's add the user message and a mock "thinking" then "static response"
    const newUserMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: inputText
    };
    setMessages(prevMessages => [...prevMessages, newUserMessage]);

    setIsLoading(true);

    // Simulate thinking
    setTimeout(() => {
      const mockStaticResponse = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: `I received your message: "${inputText}". I am a mock assistant and cannot process this yet.`,
        chartData: null, // No chart for this mock response
        sqlQuery: null   // No SQL for this mock response
      };
      setMessages(prevMessages => [...prevMessages, mockStaticResponse]);
      setIsLoading(false);
    }, 1500); // Simulate 1.5 seconds delay
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Personal Finance Assistant</h1>
      </header>
      <ChatWindow messages={messages} isLoading={isLoading} />
      <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
      {error && <p className="error-message">Error: {error.message || 'An unexpected error occurred.'}</p>}
    </div>
  );
}

export default App;