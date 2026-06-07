// VRChat MCP Debugger - WebSocket Client
class MCPDebugger {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.isPaused = false;
        this.messageCount = 0;
        this.filters = { address: '', direction: 'all' };
        this.initElements();
        this.initEventListeners();
        this.connect();
    }
    
    initElements() {
        this.elements = {
            connectionStatus: document.getElementById('connection-status'),
            messageList: document.getElementById('message-list'),
            messageCount: document.getElementById('message-count'),
            bytesIn: document.getElementById('bytes-in'),
            bytesOut: document.getElementById('bytes-out'),
            serverStatus: document.getElementById('server-status'),
            clearButton: document.getElementById('clear-messages'),
            pauseButton: document.getElementById('pause-messages'),
            addressFilter: document.getElementById('address-filter'),
            directionFilter: document.getElementById('direction-filter'),
            applyFilters: document.getElementById('apply-filters'),
            sendAddress: document.getElementById('send-address'),
            sendValue: document.getElementById('send-value'),
            sendButton: document.getElementById('send-message')
        };
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        this.ws = new WebSocket(`${protocol}//${host}/ws`);
        
        this.ws.onopen = () => {
            this.setConnectionStatus(true);
            this.loadInitialData();
        };
        
        this.ws.onclose = () => {
            this.setConnectionStatus(false);
            setTimeout(() => this.connect(), 3000);
        };
        
        this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));
        this.ws.onerror = (e) => console.error('WebSocket error:', e);
    }
    
    setConnectionStatus(connected) {
        this.isConnected = connected;
        const statusEl = this.elements.connectionStatus;
        const statusClass = connected ? 'bg-green-500' : 'bg-red-500';
        const statusText = connected ? 'Connected' : 'Disconnected';
        statusEl.innerHTML = `<span class="h-3 w-3 rounded-full ${statusClass} mr-2"></span><span>${statusText}</span>`;
    }
    
    loadInitialData() {
        if (this.isConnected) {
            this.sendMessage({ type: 'get_messages', limit: 100 });
        }
    }
    
    sendMessage(message) {
        if (this.isConnected) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'messages': this.handleMessages(data.messages); break;
            case 'new_message': !this.isPaused && this.addMessage(data.message); break;
            case 'status':
            case 'status_update': this.updateStatus(data.status); break;
            case 'error': console.error('Server error:', data.message); break;
            default: console.warn('Unhandled message type:', data.type);
        }
    }
    
    handleMessages(messages) {
        this.elements.messageList.innerHTML = '';
        messages.forEach(msg => this.addMessage(msg, false));
    }
    
    addMessage(msg, scroll = true) {
        if (!this.messagePassesFilters(msg)) return;
        
        const time = new Date(msg.timestamp * 1000).toLocaleTimeString();
        const args = Array.isArray(msg.args) ? 
            msg.args.map(a => JSON.stringify(a)).join(', ') : 
            JSON.stringify(msg.args);
        
        const row = document.createElement('tr');
        row.className = `message-row ${msg.direction.toLowerCase()}`;
        row.innerHTML = `
            <td class="px-4 py-1 text-xs text-gray-500">${time}</td>
            <td class="px-4 py-1">
                <span class="px-2 py-1 text-xs rounded-full ${msg.direction === 'INCOMING' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}">
                    ${msg.direction}
                </span>
            </td>
            <td class="px-4 py-1 text-sm font-mono">${msg.address}</td>
            <td class="px-4 py-1 text-sm font-mono">${args}</td>
        `;
        
        this.elements.messageList.prepend(row);
        
        // Keep only the most recent 1000 messages
        const rows = this.elements.messageList.querySelectorAll('tr');
        if (rows.length > 1000) {
            this.elements.messageList.removeChild(rows[rows.length - 1]);
        }
        
        if (scroll && !this.isPaused) {
            this.elements.messageList.parentElement.scrollTop = 0;
        }
    }
    
    messagePassesFilters(msg) {
        return (!this.filters.address || msg.address.includes(this.filters.address)) &&
               (this.filters.direction === 'all' || msg.direction === this.filters.direction);
    }
    
    updateStatus(status) {
        if (status?.osc) {
            this.elements.serverStatus.textContent = `${status.osc.server} → ${status.osc.client}`;
            this.elements.messageCount.textContent = status.osc.total_messages || 0;
            this.elements.bytesIn.textContent = this.formatBytes(status.osc.bytes_received || 0);
            this.elements.bytesOut.textContent = this.formatBytes(status.osc.bytes_sent || 0);
        }
    }
    
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
    }
    
    initEventListeners() {
        // Clear messages
        this.elements.clearButton.addEventListener('click', () => {
            this.elements.messageList.innerHTML = '';
        });
        
        // Toggle pause
        this.elements.pauseButton.addEventListener('click', () => {
            this.isPaused = !this.isPaused;
            const isPaused = this.isPaused;
            this.elements.pauseButton.innerHTML = 
                `<i class="fas fa-${isPaused ? 'play' : 'pause'}"></i> ${isPaused ? 'Resume' : 'Pause'}`;
            this.elements.pauseButton.className = 
                `px-3 py-1 rounded ${isPaused ? 'bg-yellow-200' : 'bg-gray-200'}`;
        });
        
        // Apply filters
        this.elements.applyFilters.addEventListener('click', () => {
            this.filters = {
                address: this.elements.addressFilter.value,
                direction: this.elements.directionFilter.value
            };
            this.loadInitialData();
        });
        
        // Send message
        this.elements.sendButton.addEventListener('click', () => this.sendOscMessage());
        this.elements.sendValue.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendOscMessage();
        });
    }
    
    sendOscMessage() {
        const address = this.elements.sendAddress.value.trim();
        let value = this.elements.sendValue.value.trim();
        
        if (!address) {
            alert('Please enter an OSC address');
            return;
        }
        
        // Try to parse value as number, boolean, or string
        try {
            if (!isNaN(parseFloat(value)) && isFinite(value)) {
                value = parseFloat(value);
            } else if (value.toLowerCase() === 'true') {
                value = true;
            } else if (value.toLowerCase() === 'false') {
                value = false;
            }
        } catch (e) {
            // Keep as string if parsing fails
        }
        
        this.sendMessage({
            type: 'send_message',
            address: address,
            args: [value]
        });
        
        // Clear the input
        this.elements.sendValue.value = '';
    }
}

// Initialize the debugger when the page loads
window.addEventListener('load', () => {
    window.debugger = new MCPDebugger();
});
