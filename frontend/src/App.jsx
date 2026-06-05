// App.jsx Top Level View Router 
// All logic lives in views/ and /hooks; This file just switches between them 

import {useState} from "react";

export default function App() {

  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [sessionSignals, setSessionSignals] = useState([]);

  function handleLogin(user) {
    setUser(user);
  }

  function handleJoinSession(session, signals) {
    setActiveSession(session);
    setSessionSignals(signals);
  }

  function handleLeaveSession() {
    setActiveSession(null);
    setSessionSignals([]);
  }

  return (
    <div>
      <h1>Hello, React!</h1>
    </div>
  );
}
