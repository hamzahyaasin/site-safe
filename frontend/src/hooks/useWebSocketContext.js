import { useContext } from 'react'
import { WebSocketContext } from '../context/WebSocketContext.jsx'

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext)
  if (!ctx) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return ctx
}
