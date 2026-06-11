// App.jsx Top Level View Router 
// All logic lives in views/ and /hooks; This file just switches between them 

import {useState} from "react";
import { LoginView }   from "./views/LoginView";
import { LobbyView }   from "./views/LobbyView";

export default function App() {

  const [view, setView] = useState("login"); // "login" or "session"
  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [sessionSignals, setSessionSignals] = useState([]);

  function handleLogin(user) {
    setUser(user);
    setView("lobby");
  }

  function handleJoinSession(session, signals) {
    setActiveSession(session);
    setSessionSignals(signals);
  }

  function handleLeaveSession() {
    setActiveSession(null);
    setSessionSignals([]);
    setView("lobby");
  }
  function handleLogout() {
    setUser(null);
    setActiveSession(null);
    setSessionSignals([]);
    setView("login");
  }
 
  if (view === "login") {
    return <LoginView onLogin={handleLogin} />;
  }
 
  if (view === "lobby") {
    return <LobbyView user={user} onJoinSession={handleJoinSession} onLogout={handleLogout} />;
  }
 



  return (
    <div>
      <h1>Hello, React!</h1>
    </div>
  );
}
