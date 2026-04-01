import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(
  channel: 'leads' | 'dialogs' | 'pipeline',
  onMessage: (event: unknown) => void
) {
  const ws = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage
  // Track unmount so the reconnect timer does not fire after cleanup
  const unmountedRef = useRef(false)

  const connect = useCallback(() => {
    // Use relative URL so Vite proxy and production reverse-proxy both work correctly
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/${channel}`
    ws.current = new WebSocket(url)
    ws.current.onmessage = (e) => {
      try {
        onMessageRef.current(JSON.parse(e.data))
      } catch {}
    }
    ws.current.onclose = () => {
      // Do not reconnect after the component has unmounted
      if (!unmountedRef.current) setTimeout(connect, 3000)
    }
    ws.current.onerror = () => ws.current?.close()
  }, [channel])

  useEffect(() => {
    unmountedRef.current = false
    connect()
    return () => {
      unmountedRef.current = true
      // Clear onclose before closing to prevent triggering the reconnect timer
      if (ws.current) ws.current.onclose = null
      ws.current?.close()
    }
  }, [connect])
}
