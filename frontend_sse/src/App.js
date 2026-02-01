import React, { useState, useEffect } from 'react';

function App() {
  const [count, setCount] = useState(0);
  const [sseCount, setSseCount] = useState(0);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/count')
      .then(res => res.json())
      .then(data => setCount(data.count))
      .catch(err => console.error('Failed to fetch initial count', err));
  }, []);

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8000/sse');

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received count via SSE:', data.count);
        setSseCount(data.count);
      } catch (err) {
        console.error('Failed to parse SSE message', err);
      }
    };

    eventSource.onerror = (err) => console.error('SSE error', err);

    return () => eventSource.close();
  }, []);

  const handleIncrement = () => {
    fetch('http://localhost:8000/api/v1/count', { method: 'PATCH' })
      .then(res => res.json())
      .then(data => setCount(data.count))
      .catch(err => console.error('Failed to increment', err));
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-4">DB Trigger WS (SSE)</h1>
        <p className="text-lg mb-4">Current Count: <span className="font-semibold">{count}</span></p>
        <p className="text-lg mb-4">Latest Count (SSE): <span className="font-semibold">{sseCount}</span></p>
        <button
          onClick={handleIncrement}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Increment
        </button>
      </div>
    </div>
  );
}

export default App;