import React, { useState, useEffect } from 'react';

function App() {
  const [count, setCount] = useState(0);
  const [wsCount, setWsCount] = useState(0);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/count')
      .then(res => res.json())
      .then(data => setCount(data.count))
      .catch(err => console.error('Failed to fetch initial count', err));
  }, []);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => console.log('WebSocket connected');

    ws.onmessage = (event) => {
      console.log('WebSocket event received');
      try {
        const data = JSON.parse(event.data);
        setWsCount(data.count);
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.onclose = () => console.log('WebSocket closed');

    ws.onerror = (err) => console.error('WebSocket error', err);

    return () => ws.close();
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
        <h1 className="text-2xl font-bold mb-4">DB Trigger WS</h1>
        <p className="text-lg mb-4">Current Count: <span className="font-semibold">{count}</span></p>
        <p className="text-lg mb-4">Latest Count (WS): <span className="font-semibold">{wsCount}</span></p>
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