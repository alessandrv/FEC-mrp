// src/hooks/useWebSocket.js

import { useEffect, useRef } from "react";

const useWebSocket = (url, onMessage, onOpen, onClose, onError) => {
    const ws = useRef(null);

    useEffect(() => {
        ws.current = new WebSocket(url);

        ws.current.onopen = (event) => {
            console.log("WebSocket connected");
            if (onOpen) onOpen(event);
        };

        ws.current.onmessage = (event) => {
            if (onMessage) onMessage(event);
        };

        ws.current.onclose = (event) => {
            console.log("WebSocket disconnected");
            if (onClose) onClose(event);
        };

        ws.current.onerror = (event) => {
            console.error("WebSocket error:", event);
            if (onError) onError(event);
        };

        // Cleanup on unmount
        return () => {
            ws.current.close();
        };
    }, [url]);

    return ws.current;
};

export default useWebSocket;
