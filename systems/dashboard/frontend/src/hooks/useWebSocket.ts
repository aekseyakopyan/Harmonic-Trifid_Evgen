import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(
  channel: 'leads' | 'dialogs' | 'pipeline',
  onMessage: (event: unknown) => void
) {
  const ws = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    const url = `ws://${window.location.hostname}:8001/ws/${channel}`
    ws.current = new WebSocket(url)
    ws.current.onmessage = (e) => {
      try {
        onMessageRef.current(JSON.parse(e.data))
      } catch {}
    }
    ws.current.onclose = () => setTimeout(connect, 3000)
    ws.current.onerror = () => ws.current?.close()
  }, [channel])

  useEffect(() => {
    connect()
    return () => {
      ws.current?.close()
    }
  }, [connect])
}
