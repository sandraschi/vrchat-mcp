# VRChat MCP - Claude Code Worktrees Implementation Guide

> **Advanced Development Pattern**: Parallel specialized development for VRChat's complex 3D social platform integration

## 🎯 **VRChat MCP Complexity Challenges**

VRChat MCP development involves multiple complex domains that benefit tremendously from parallel specialized development:

- **Avatar Management**: 3D model handling, VRM validation, API integration
- **World Discovery**: Instance management, metadata extraction, search functionality  
- **Social Features**: Friend system, presence tracking, status management
- **Real-time Events**: WebSocket handling, notifications, activity streams
- **Authentication**: VRChat API auth, token management, rate limiting

## 🚀 **VRChat-Specific Worktree Setup**

### **1. Domain-Based Worktree Strategy**
```bash
cd vrchat-mcp

# Core VRChat domains - each requires specialized expertise
git worktree add ../vrchat-avatar-mgmt -b feature/avatar-management
git worktree add ../vrchat-world-api -b feature/world-discovery
git worktree add ../vrchat-social -b feature/social-features
git worktree add ../vrchat-realtime -b feature/realtime-events
git worktree add ../vrchat-auth -b feature/authentication
git worktree add ../vrchat-testing -b improve/comprehensive-testing
```

### **2. Specialized Claude Sessions**

#### **Terminal 1: Avatar Management**
```bash
cd ../vrchat-avatar-mgmt
claude
```

**Specialized Prompt**:
```
You are building VRChat avatar management tools for an MCP server. Focus on:

CORE RESPONSIBILITIES:
- VRChat avatar API integration (/api/1/avatars endpoints)
- 3D model file validation (VRM, FBX formats)
- Avatar thumbnail handling and caching
- Avatar favorite/unfavorite functionality
- Avatar switching and selection tools

KEY CHALLENGES:
- VRChat API rate limiting (200 requests/hour)
- VRM model validation and compatibility checks
- Avatar thumbnail expiration (24h cache invalidation)
- Cross-platform avatar compatibility
- Large 3D model file handling and memory management

VRCHAT API CONTEXT:
- GET /api/1/avatars - List user avatars with pagination
- PUT /api/1/avatars/{id}/select - Switch to specific avatar
- GET /api/1/avatars/{id} - Get detailed avatar information
- POST /api/1/avatars/{id}/favorite - Add avatar to favorites

TECHNICAL REQUIREMENTS:
- Robust error handling for VRChat API failures
- Efficient caching strategy for avatar metadata
- 3D model validation pipeline
- Integration with Claude Desktop tool schemas

Build professional avatar management that makes VRChat avatar handling effortless through natural language commands in Claude Desktop.
```

#### **Terminal 2: World Discovery & Management**
```bash
cd ../vrchat-world-api
claude
```

**Specialized Prompt**:
```
You are building VRChat world discovery and management tools for an MCP server. Focus on:

CORE RESPONSIBILITIES:
- VRChat world search and discovery functionality
- World instance management (joining, creating, listing)
- World metadata extraction and intelligent caching
- Favorite worlds management and organization
- World capacity and availability tracking

KEY CHALLENGES:
- VRChat world API complexity and rate limiting
- Instance availability and capacity real-time tracking
- World thumbnail and preview image handling
- Public vs private world access permissions
- Large-scale world metadata management

VRCHAT API CONTEXT:
- GET /api/1/worlds - Search and list worlds with filters
- GET /api/1/worlds/{id} - Get detailed world information
- GET /api/1/worlds/{id}/instances - List world instances
- POST /api/1/worlds/{id}/instances - Create new instance
- PUT /api/1/worlds/{id}/favorite - Favorite/unfavorite world

TECHNICAL REQUIREMENTS:
- Intelligent caching for world metadata
- Real-time instance availability tracking
- Search optimization for large world databases
- Integration with VRChat's world categories and tags

Build comprehensive world management that makes VRChat world navigation and discovery seamless through Claude Desktop.
```

#### **Terminal 3: Social Features**
```bash
cd ../vrchat-social
claude
```

**Specialized Prompt**:
```
You are building VRChat social features for an MCP server. Focus on:

CORE RESPONSIBILITIES:
- Friend system management (add, remove, block, unblock)
- User presence tracking and status monitoring
- Friend location and activity tracking
- Social interaction tools and utilities
- User profile and status management

KEY CHALLENGES:
- Real-time presence updates and synchronization
- Friend status change notifications
- Privacy settings and visibility controls
- Large friend list performance optimization
- Cross-instance friend tracking

VRCHAT API CONTEXT:
- GET /api/1/auth/user/friends - List user friends
- POST /api/1/user/{id}/friendRequest - Send friend request
- DELETE /api/1/auth/user/friends/{id} - Remove friend
- GET /api/1/users/{id} - Get user profile information
- PUT /api/1/users/{id}/block - Block/unblock user

TECHNICAL REQUIREMENTS:
- Efficient friend list caching and updates
- Real-time status change handling
- Privacy-aware information display
- Integration with VRChat's trust system

Build robust social features that enhance VRChat's social experience through intelligent friend and user management via Claude Desktop.
```

#### **Terminal 4: Real-time Events**
```bash
cd ../vrchat-realtime
claude
```

**Specialized Prompt**:
```
You are building VRChat real-time event handling for an MCP server. Focus on:

CORE RESPONSIBILITIES:
- WebSocket connection management for VRChat notifications
- Real-time friend status and presence updates
- Activity and event stream processing
- Notification filtering and prioritization
- Event persistence and history management

KEY CHALLENGES:
- VRChat WebSocket protocol implementation
- Connection stability and reconnection logic
- High-frequency event processing and filtering
- Memory-efficient event stream handling
- Cross-instance event correlation

VRCHAT WEBSOCKET CONTEXT:
- Connection endpoint: wss://pipeline.vrchat.cloud
- Event types: friend-online, friend-offline, friend-update, friend-location
- Authentication via auth cookies from REST API
- Heartbeat and connection keep-alive requirements

TECHNICAL REQUIREMENTS:
- Robust WebSocket connection management
- Event deduplication and ordering
- Efficient notification delivery to Claude Desktop
- Integration with other VRChat MCP components

Build reliable real-time event handling that keeps users connected to their VRChat social network through live updates in Claude Desktop.
```

#### **Terminal 5: Authentication**
```bash
cd ../vrchat-auth
claude
```

**Specialized Prompt**:
```
You are building VRChat authentication and API management for an MCP server. Focus on:

CORE RESPONSIBILITIES:
- VRChat login and session management
- API token handling and refresh logic
- Rate limiting and request throttling
- Multi-factor authentication (TOTP, Email)
- Secure credential storage and management

KEY CHALLENGES:
- VRChat's complex authentication flow
- 2FA/MFA handling for automated systems
- API rate limit compliance (200 requests/hour)
- Session expiration and renewal
- Secure credential storage in OS keychain

VRCHAT AUTH CONTEXT:
- POST /api/1/auth/user - Login with credentials
- GET /api/1/auth/user - Verify current session
- POST /api/1/auth/twofactorauth/totp/verify - TOTP verification
- POST /api/1/logout - Logout and invalidate session
- Rate limiting headers: X-RateLimit-Remaining, X-RateLimit-Reset

TECHNICAL REQUIREMENTS:
- Secure credential management
- Automated 2FA handling where possible
- Intelligent rate limiting and backoff
- Session persistence across MCP restarts

Build robust authentication that handles VRChat's security requirements while providing seamless API access for other MCP components.
```

#### **Terminal 6: Comprehensive Testing**
```bash
cd ../vrchat-testing
claude
```

**Specialized Prompt**:
```
You are building comprehensive testing for VRChat MCP server. Focus on:

CORE RESPONSIBILITIES:
- Unit tests for all VRChat API integrations
- Mock VRChat API responses for testing
- Integration tests between MCP components
- Performance testing for real-time features
- Error handling and edge case validation

KEY TESTING SCENARIOS:
- VRChat API rate limiting and backoff
- WebSocket connection failures and recovery
- Large friend list performance
- Avatar file validation edge cases
- Authentication failure and recovery

TESTING REQUIREMENTS:
- Mock VRChat API server for offline testing
- Comprehensive error scenario coverage
- Performance benchmarks for real-time features
- Integration testing between all worktree components

Build a testing framework that ensures VRChat MCP reliability and performance across all usage scenarios.
```

## 🔧 **VRChat-Specific Workflow Patterns**

### **1. Multi-Approach Authentication Testing**
```bash
# Test different 2FA handling approaches
git worktree add ../vrchat-auth-manual -b approach/manual-2fa
git worktree add ../vrchat-auth-automated -b approach/automated-2fa
git worktree add ../vrchat-auth-hybrid -b approach/hybrid-2fa
```

### **2. Performance Optimization Parallel Tracks**
```bash
# Optimize different performance aspects simultaneously
git worktree add ../vrchat-perf-caching -b optimize/intelligent-caching
git worktree add ../vrchat-perf-batching -b optimize/request-batching
git worktree add ../vrchat-perf-streaming -b optimize/realtime-streaming
```

### **3. Integration Testing Strategy**
```bash
# Final integration worktree
git worktree add ../vrchat-integration -b integration/full-vrchat-stack

cd ../vrchat-integration
git merge feature/avatar-management
git merge feature/world-discovery
git merge feature/social-features
git merge feature/realtime-events
git merge feature/authentication

claude
# Prompt: "Test complete VRChat MCP integration, ensure all components work together seamlessly"
```

## 📋 **VRChat-Specific Context Files**

### **vrchat-avatar-mgmt/CLAUDE.md**
```markdown
# VRChat Avatar Management Context

## Key APIs
- GET /api/1/avatars - List user avatars (paginated)
- PUT /api/1/avatars/{id}/select - Switch active avatar
- GET /api/1/avatars/{id} - Get avatar details
- POST /api/1/avatars/{id}/favorite - Toggle favorite status

## Rate Limits & Constraints
- 200 requests per hour per IP
- Avatar thumbnails expire after 24 hours
- VRM model validation required for custom avatars
- Maximum file size limits for avatar uploads

## Common Issues & Solutions
- Rate limiting: Implement exponential backoff
- Thumbnail caching: Store with expiration timestamps
- VRM validation: Use proper VRM specification checks
- Memory management: Stream large avatar files

## Testing Data
- Sample avatar IDs for testing
- Mock VRChat API responses
- VRM test files for validation
```

### **vrchat-realtime/CLAUDE.md**
```markdown
# VRChat Real-time Events Context

## WebSocket Connection
- Endpoint: wss://pipeline.vrchat.cloud
- Authentication: Use auth cookies from REST API login
- Heartbeat: Send ping every 30 seconds

## Event Types
- friend-online: Friend comes online
- friend-offline: Friend goes offline  
- friend-update: Friend status/location change
- friend-location: Friend joins/leaves world

## Connection Management
- Auto-reconnect on disconnect
- Event deduplication by timestamp
- Connection state monitoring
- Graceful shutdown handling

## Performance Considerations
- Buffer high-frequency events
- Implement event filtering
- Memory-efficient event storage
- Connection pooling for multiple users
```

## 🚀 **VRChat MCP Development Results**

### **Before Worktrees** (Traditional Development):
- **Single Claude overwhelmed** by VRChat's complexity
- **Sequential development** bottlenecks
- **Context switching** between 3D, social, real-time domains
- **Development time**: Weeks for basic functionality

### **After Worktrees** (Parallel Specialized Development):
- **6 specialized Claude instances** working simultaneously
- **Parallel progress** on all VRChat domains
- **Domain expertise** in each area (3D, social, real-time, auth)
- **Development time**: Days for comprehensive functionality
- **Better architecture** through separation of concerns
- **Comprehensive testing** via dedicated testing worktree

## 🏆 **Success Metrics**

### **Development Velocity**
- **5-10x faster** VRChat feature development
- **Parallel progress** on avatar, world, social, real-time features
- **Specialized solutions** for each VRChat domain
- **Professional-grade** VRChat integration

### **Code Quality**
- **Domain expertise** in each specialized area
- **Better error handling** for VRChat API complexities
- **Comprehensive testing** of real-time features
- **Robust authentication** handling

### **User Experience**
- **Rich VRChat integration** in Claude Desktop
- **Natural language** VRChat commands
- **Real-time social** updates and notifications
- **Seamless avatar and world** management

---

**VRChat MCP with Claude Code worktrees transforms overwhelming 3D social platform complexity into manageable, specialized, high-velocity development streams.**

This pattern enables building production-quality VRChat integration that would be nearly impossible with traditional single-threaded development approaches.
