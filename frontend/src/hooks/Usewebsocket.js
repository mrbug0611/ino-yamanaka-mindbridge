//hooks/Usewebsocket.js    const send = useCallback((payload) => {
import {useRef, useCallback} from "react";
const WS_BASE = import.meta.env.VITE_WS_BASE || 
`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

/**
 * @param {function} onSignal        - called with (signal, isDimmed)
 * @param {function} onReactionUpdate - called with (signalId, reactions)
 * @param {function} onPresenceChange - called with (onlineUserIds)
 * @param {function} onTypingChange   - called with (userId, isTyping)
 */
export function useWebSocket({
  onSignal,
  onReactionUpdate,
  onPresenceChange,
  onTypingChange,
}) {
    const wsRef = useRef(null);
    const typingTimeoutRef = useRef(null);

    const connect = useCallBack((sessionId, userId) => {
        if (wsRef.current) {
            wsRef.current.close(); // close html dialogue if already open
        }

        const ws = new WebSocket(`${WS_BASE}/session/${sessionId}/${userId}`);

        ws.onmessage = (evt) => { // handle incoming messages
            const msg = JSON.parse(evt.data);

            if (msg.type === "signal" || msg.type === "shadow_signal") {
                onSignal(msg.signal, msg.type === "shadow_signal");
            } else if (msg.type === "reaction") {
                onReactionUpdate(msg.signal_id, msg.reactions);
            }else if (
                msg.type === "user_joined" ||
                msg.type === "user_left" ||
                msg.type === "connected"
            ) {
                     onPresenceChange(msg.online_users || []);
      }     else if (msg.type === "typing") {
                onTypingChange(msg.user_id, msg.is_typing);
            }
        };

        ws.onclose = () => {}; // handle close if needed
        wsRef.current = ws;

    }, [onSignal, onReactionUpdate, onPresenceChange, onTypingChange]);

    const disconnect = useCallBack(() => {
       wsRef.current?.close();
       wsRef.current = null;
    }, []);

    const send = useCallBack((payload) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(payload));
        }

    }, []);

    const sendTyping = useCallBack((isTyping) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            send({ type: "typing", is_typing: isTyping });
        }

    }, [send]);

    //call this every keystroke - debounces the stopped typing event 
    const notifyTyping = useCallBack(() => {
        sendTyping(true);
        clearTimeout(typingTimeoutRef.current); // reset timer on every keystroke
        typingTimeoutRef.current = setTimeout(() => {
            sendTyping(false); // send stopped typing after 1.5 seconds of inactivity
        }, 1500);
    }, [sendTyping]);

    useEffect(() => {
        return () => {
            clearTimeout(typingTimeoutRef.current);
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, []);

    return { connect, disconnect, send, notifyTyping };
}