"use client";
import React, { useState, useEffect, useRef } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || (API_URL.replace(/^http/, "ws") + "/ws");

export default function App() {
  const [sender, setSender] = useState("user1");
  const [receiver, setReceiver] = useState("user2");
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/messages?sender=${sender}&receiver=${receiver}`)
      .then((r) => r.json())
      .then((data) => setMessages(data))
      .catch((e) => console.log(e));

    const socket = new WebSocket(WS_URL);
    socket.onmessage = () => {
      fetch(`${API_URL}/messages?sender=${sender}&receiver=${receiver}`)
        .then((r) => r.json())
        .then((data) => setMessages(data));
    };
    ws.current = socket;

    return () => socket.close();
  }, [sender, receiver]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text) return;
    await fetch(`${API_URL}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender, receiver, text }),
    });
    if (ws.current) {
      ws.current.send("update");
    }
    setText("");
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h2>Chat Application</h2>
      <div className="box">
        <div>
          <label>Your Name: </label>
          <input value={sender} onChange={(e) => setSender(e.target.value)} />
        </div>
        <div>
          <label>Chat With: </label>
          <input value={receiver} onChange={(e) => setReceiver(e.target.value)} />
        </div>
      </div>

      <div className="box" style={{ height: '300px', overflowY: 'scroll' }}>
        <h4>Messages</h4>
        {messages.length === 0 ? (
          <p>No messages yet.</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} style={{ borderBottom: '1px solid #eee', padding: '5px' }}>
              <b>{m.sender}:</b> {m.text}
            </div>
          ))
        )}
      </div>

      <form onSubmit={send} className="box">
        <input
          style={{ width: '70%' }}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type message here..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
