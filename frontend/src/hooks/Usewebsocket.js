// hooks/useWebSocket.js
// Manages the WebSocket lifecycle for a session.
//
// Key design: callbacks are stored in refs so the ws.onmessage handler
// always calls the latest version without needing to reconnect.

import { useRef, useCallback, useEffect } from "react";

const WS_BASE = import.meta.env.VITE_WS_BASE || 
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws`;
export function useWebSocket({
  onSignal,
  onReactionUpdate,
  onPresenceChange,
  onTypingChange,
  onSessionEnded,
}) {
  const wsRef           = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Store callbacks in refs so ws.onmessage always calls the latest version
  // without needing to close and reopen the connection on every render
  const onSignalRef         = useRef(onSignal);
  const onReactionUpdateRef = useRef(onReactionUpdate);
  const onPresenceChangeRef = useRef(onPresenceChange);
  const onTypingChangeRef   = useRef(onTypingChange);
  const onSessionEndedRef   = useRef(onSessionEnded);

  // Keep refs in sync with latest prop values on every render
  useEffect(() => { onSignalRef.current         = onSignal;        });
  useEffect(() => { onReactionUpdateRef.current  = onReactionUpdate; });
  useEffect(() => { onPresenceChangeRef.current  = onPresenceChange; });
  useEffect(() => { onTypingChangeRef.current    = onTypingChange;   });
  useEffect(() => { onSessionEndedRef.current    = onSessionEnded;   });

  const connect = useCallback((sessionId, userId) => {
    if (wsRef.current) wsRef.current.close();

    const ws = new WebSocket(`${WS_BASE}/session/${sessionId}/${userId}`);

    ws.onmessage = (evt) => {
    let msg;
    try {
        msg = JSON.parse(evt.data);
    } catch {
        console.warn("Invalid WS message:", evt.data);
        return;
    }

    if (msg.type === "signal" || msg.type === "signal_shadow") {
        onSignalRef.current?.(msg.signal, msg.type === "signal_shadow");
      } else if (msg.type === "reaction") {
        onReactionUpdateRef.current?.(msg.signal_id, msg.reactions);
      } else if (
        msg.type === "user_joined" ||
        msg.type === "user_left"   ||
        msg.type === "connected"
      ) {
        onPresenceChangeRef.current?.(msg.online_users || []);
      } else if (msg.type === "typing") {
        onTypingChangeRef.current?.(msg.user_id, msg.is_typing);
      } else if (msg.type === "session_ended") {
        onSessionEndedRef.current?.();
      }
    };

    ws.onopen = () => {
    };

    ws.onerror = (e) => {
      console.error("WebSocket error:", e);
    };

    ws.onclose = (e) => {
    };

    wsRef.current = ws;
  }, []); // no deps — refs handle the latest callbacks

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    clearTimeout(typingTimeoutRef.current);
  }, []);

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const sendTyping = useCallback((isTyping) => {
    send({ type: "typing", is_typing: isTyping });
  }, [send]);

  const notifyTyping = useCallback((isTyping) => {
      // Change ws.current to wsRef.current
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ 
              type: "typing", 
              is_typing: isTyping 
          }));
      }
  }, []);

  return { connect, disconnect, send, notifyTyping };
}