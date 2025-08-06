/**
 * WebSocket service for real-time dashboard updates
 */

class WebSocketService {
  constructor() {
    this.socket = null
    this.reconnectInterval = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000 // Start with 1 second
    this.maxReconnectDelay = 30000 // Max 30 seconds
    this.listeners = new Map()
    this.isConnected = false
    this.isConnecting = false
  }

  connect(url, protocols = []) {
    if (this.isConnecting || this.isConnected) {
      console.log('WebSocket already connecting or connected')
      return Promise.resolve()
    }

    this.isConnecting = true
    console.log(`Connecting to WebSocket: ${url}`)

    return new Promise((resolve, reject) => {
      try {
        // Determine WebSocket URL
        const wsUrl = this.getWebSocketUrl(url)
        this.socket = new WebSocket(wsUrl, protocols)

        this.socket.onopen = (event) => {
          console.log('✅ WebSocket connected successfully to:', wsUrl)
          this.isConnected = true
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.reconnectDelay = 1000

          // Clear any existing reconnect timer
          if (this.reconnectInterval) {
            clearTimeout(this.reconnectInterval)
            this.reconnectInterval = null
          }

          // Send initial subscription message
          this.send({
            type: 'subscribe_all'
          })

          this.emit('connected', event)
          resolve()
        }

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('📨 WebSocket message received:', data)
            this.emit('message', data)
            
            // Emit specific event types
            if (data.type) {
              this.emit(data.type, data)
            }
          } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error)
          }
        }

        this.socket.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason)
          this.isConnected = false
          this.isConnecting = false
          this.socket = null

          this.emit('disconnected', event)

          // Attempt to reconnect if not a clean close
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(url, protocols)
          }
        }

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          this.emit('error', error)
          reject(error)
        }

      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  getWebSocketUrl(path) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const fullPath = path.startsWith('/') ? path : `/${path}`
    return `${protocol}//${host}${fullPath}`
  }

  scheduleReconnect(url, protocols) {
    if (this.reconnectInterval) {
      clearTimeout(this.reconnectInterval)
    }

    console.log(`Attempting to reconnect in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`)

    this.reconnectInterval = setTimeout(() => {
      this.reconnectAttempts++
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay)
      
      this.connect(url, protocols).catch(error => {
        console.error('Reconnection failed:', error)
      })
    }, this.reconnectDelay)
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      this.socket.send(message)
      console.log('WebSocket message sent:', data)
    } else {
      console.warn('WebSocket not connected, cannot send message:', data)
    }
  }

  disconnect() {
    if (this.reconnectInterval) {
      clearTimeout(this.reconnectInterval)
      this.reconnectInterval = null
    }

    if (this.socket) {
      console.log('Disconnecting WebSocket')
      this.socket.close(1000, 'Client disconnecting')
      this.socket = null
    }

    this.isConnected = false
    this.isConnecting = false
    this.reconnectAttempts = 0
  }

  // Event listener management
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in WebSocket event handler for ${event}:`, error)
        }
      })
    }
  }

  // Utility methods
  isSocketConnected() {
    return this.isConnected && this.socket && this.socket.readyState === WebSocket.OPEN
  }

  getConnectionState() {
    if (!this.socket) return 'disconnected'
    
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  }

  // Ping-pong for connection health
  startHeartbeat(interval = 30000) {
    this.stopHeartbeat()
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isSocketConnected()) {
        this.send({
          type: 'ping',
          timestamp: Date.now()
        })
      }
    }, interval)
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
}

// Create singleton instances for different connection types
export const dashboardWebSocket = new WebSocketService()
export const systemDetailWebSocket = new WebSocketService()

// Helper function to connect to dashboard WebSocket
export const connectToDashboard = () => {
  return dashboardWebSocket.connect('/ws/dashboard/')
}

// Helper function to connect to system detail WebSocket
export const connectToSystemDetail = (hostname) => {
  return systemDetailWebSocket.connect(`/ws/system/${hostname}/`)
}

export default WebSocketService