# Mafia Platform Design Document

---

This document outlines the microservice architecture, technologies, API and communication patterns for the multiplayer game, "Mafia".

# Service Boundaries & Architecture

---

## Service Responsibilities

- User Management Service: Handles user registration, authentication, profile data (email, username), and manages in-game currency balances. It also tracks device and location information for account security.
- Game Service: Acts as the central game orchestrator. It manages game lobbies, player states (role, status, career), controls the day/night cycle, and broadcasts major game events (e.g., deaths, announcements) to the relevant services.
- Shop Service: Manages the in-game item shop. It allows players to purchase items using their currency and includes an algorithm to balance item availability daily.
- Roleplay Service: Governs the logic for role-specific abilities. It validates and executes player actions (e.g., a Mafia member performing a kill), records these actions, and generates filtered announcements (e.g., "A player was attacked last night") for the Game Service to broadcast.
- Town Service: Manages the game world's locations. It tracks every player's movement between locations and reports these movements for other services to use.
- Character Service: Manages player avatars and inventory. It handles character customization (assets, slots) and keeps track of items purchased from the Shop.
- Rumors Service: Provides an information marketplace. Players can spend currency to buy pieces of information (rumors) about other players, sourced from their actions, appearance, or location.
- Communication Service: Facilitates all in-game chat. It provides a global chat during the voting phase and private, secure chat channels for specific groups (e.g., Mafia members, players in the same location).
- Task Service: Assigns daily tasks to players based on their role and career. It validates task completion and triggers currency rewards. The actions taken during tasks can become fodder for the Rumors Service.
- Voting Service: Manages the daily voting process to exile a player. It collects votes from all players, tallies the results, and reports the outcome to the Game Service.

## Architecture Diagram





# Technologies & Communication Patterns

---

## Technology Stack
| Service(s)              | Developer     | Language | Framework      | Database              |
|--------------------------|--------------|----------|----------------|-----------------------|
| User Management, Game    | Alexandrina G. | Python   | FastAPI        | PostgreSQL            |
| Shop, Roleplay           | Alexander C.   | C#       | ASP.NET Core   | PostgreSQL            |
| Town, Character          | Dmitrii C.     | Kotlin   | Spring Boot    | PostgreSQL, Redis     |
| Rumors, Communication    | Dmitrii B.     | C#       | ASP.NET Core    | PostgreSQL, Websockets |
| Task, Voting             | Irina N.       | Python   | FastAPI         | PostgreSQL            |


## Communication Patterns

- Synchronous (REST APIs)

  Description: For direct, request/response interactions where the client needs an immediate answer. For example, when a user attempts to log in, they must wait for a success or failure response.
  Technology: We use RESTful APIs over HTTPS with JSON as the data serialization format.

  ### Motivation & Trade-offs:
- ✅ Simplicity: REST is a well-understood, stateless, and straightforward pattern, making development and debugging easier.
- ✅ Immediate Feedback: It's perfect for user-facing actions that require instant confirmation.
- ❌ Tight Coupling: The caller is temporarily coupled to the called service. If the downstream service is slow or unavailable, the caller is blocked.

# Communication Contract

This section defines our data management strategy and the specific API endpoints for each service.

## Data Management

- Database per Service: Each microservice (except communication service) owns and manages its own private database. No other service is allowed to access this database directly.
- API-based Access: All communication and data sharing between services must occur through the publicly exposed and well-defined APIs or through the asynchronous messaging system. 

# API Endpoints

---

All request and response bodies are in **JSON** format.


## User Management Service

### POST `/users/register`
Creates a new user account.  
**Request Body:**
```json
{ "username": "string", "email": "string", "password": "string", "identification": "string", "deviceInfo": "object", "location": "string" }
```

**Response (201 Created):**

```json
{ "userId": "uuid", "username": "string" }
```

### POST `/users/login`

Authenticates a user and returns a token.
**Request Body:**

```json
{ "email": "string", "password": "string", "deviceInfo": "object" }
```

**Response (200 OK):**

```json
{ "accessToken": "jwt_string" }
```

### GET `/users/{userId}`

Retrieves a user's profile information, including currency.
**Response (200 OK):**

```json
{ "userId": "uuid", "username": "string", "email": "string", "currency": "integer" }
```

### PUT `/users/{userId}/currency`

Adds, substracts or sets a user's currency balance. *(Internal endpoint)*
**Request Body:**

```json
{ "amount": "integer", "operation": "add|subtract|set" }
```

**Response (200 OK):**

```json
{ "userId": "uuid", "newBalance": "integer", "transactionId": "uuid" }
```

### GET `/users/internal/details`

Used by other services to get user details. *(Internal endpoint)*

**Query Parameters:**
- `userIds`: Comma-separated list of UUIDs

**Response (200 OK):**

```json
{   "users": [ { "userId": "uuid", "username": "string", "isAlive": "boolean" } ] }
```

---

## Game Service

### POST `/games`

Creates a new game lobby.
**Request Body:**

```json
{ "hostId": "uuid", "lobbyName": "string", "maxPlayers": "integer" }
```

**Response (201 Created):**

```json
{ "gameId": "uuid", "lobbyId": "uuid", "hostId": "uuid", "status": "waiting_for_players", "joinCode": "string" }
```

### POST `/games/{gameId}/join`

Allows a user to join a game lobby. *(Requires Auth)*
**Request Body:**
```json
{ "userId": "uuid" }
```

**Response (200 OK):**

```json
{ "message": "Successfully joined game.", "success": "boolean", "playerCount": "number" }
```

### POST `/games/{gameId}/start`

Starts the game. Can only be triggered by the host. *(Requires Auth)*
**Request Body:**
```json
{ "ownerId": "uuid" }
```

**Response (200 OK):**

```json
{ "message": "Game started. Roles have been assigned.", "gameId": "uuid", "players": "array", "initialState": "object" }
```

### GET `/games/{gameId}/state`

Retrieves the current public state of the game. *(Requires Auth)*
**Response (200 OK):**

```json
{ "gameId": "uuid", "phase": "day|night|voting|ended", "cycle": "day", "status": "active", "dayNumber": "number", "alivePlayers": "array", "deadPlayers": "array", "currentTimer": "number", "players": [ { "userId": "uuid", "username": "string", "isAlive": "boolean" } ], "events": "array" }
```

### POST `/games/{gameId}/events`

Processes game events and actions. *(Requires Auth)*
**Request Body:**
```json
{ "eventType": "string", "playerId": "uuid", "data": "object" }
```

**Response (200 OK):**

```json
{ "eventId": "uuid", "processed": "boolean", "nextState": "object" }
```

### WebSocket Events (Server → Client)
The Game Service uses WebSockets to push real-time updates to clients.

**Public Event:**
```json
{ "event": "gameStateUpdate", "data": { "cycle": "night", "message": "Night has begun." } }
```

**Private Event (e.g., for Sheriff):**
```json
{ "event": "privateRoleResult", "data": { "type": "INVESTIGATION_RESULT", "targetId": "uuid-of-player-investigated", "result": "MAFIA" } }
```

---

## Shop Service

### GET `/items`

Lists all items available for purchase today.
**Response (200 OK):**

```json
[
  { "itemId": "uuid", "name": "string", "description": "string", "price": "double", "quantity": "integer" }
]
```

### POST `/purchase`

Allows a user to buy an item.
**Request Body:**

```json
{ "userId": "uuid", "itemId": "uuid", "quantity": "integer" }
```

**Response (200 OK):**

```json
{ "purchaseId": "uuid", "status": "success" }
```

---

## Roleplay Service

### POST `/abilities/use`

A player uses their role-specific ability on a target.
**Request Body:**

```json
{ "userId": "uuid", "ability": "string", "targetUserId": "uuid", "lobbyId": "uuid" }
```

**Response (200 OK):**

```json
{ "actionId": "uuid", "result": "string", "message": "You successfully used your ability." }
```

---

## Town Service

### POST `/move`

Moves a player to a different location in the town.
**Request Body:**

```json
{ "userId": "uuid", "locationId": "uuid", "lobbyId": "uuid" }
```

**Response (200 OK):**

```json
{ "userId": "uuid", "newLocationId": "uuid" }
```

---

## Character Service

### GET `/users/{userId}/inventory`

Retrieves the items in a user's inventory.
**Response (200 OK):**

```json
[
  { "itemId": "uuid", "name": "string", "quantity": "integer" }
]
```

### PUT `/users/{userId}/character`

Updates a user's character customization.
**Request Body:**

```json
{ "assets": [{ "slot": "hair", "assetId": "uuid" }] }
```

**Response (200 OK):**

```json
{ "userId": "uuid", "character": "object" }
```

---

## Rumors Service

### POST `/purchase`

A player buys a random rumor.
**Request Body:**

```json
{ "userId": "uuid", "lobbyId": "uuid" }
```

**Response (200 OK):**

```json
{ "rumorId": "uuid", "text": "string" }
```

---

## Task Service

### GET `/users/{userId}/tasks`

Gets the daily tasks assigned to a user.
**Response (200 OK):**

```json
[
  { "taskId": "uuid", "description": "string", "isComplete": "boolean", "reward": "integer" }
]
```

### POST `/tasks/{taskId}/complete`

Marks a user's task as complete.
**Request Body:**

```json
{ "userId": "uuid" }
```

**Response (200 OK):**

```json
{ "status": "completed", "currencyAwarded": "integer" }
```

---

## Voting Service

### POST `/lobbies/{lobbyId}/vote`

A player casts their vote for who to exile.
**Request Body:**

```json
{ "voterId": "uuid", "candidateId": "uuid" }
```

**Response (200 OK):**

```json
{ "status": "vote_recorded" }
```

### GET `/lobbies/{lobbyId}/results`

Gets the results of the day's vote *(called by Game Service)*.
**Response (200 OK):**

```json
{ "exiledUserId": "uuid", "voteCounts": [{ "userId": "uuid", "votes": "integer" }] }
```

---

## Communication Service

**Technology:** WebSockets

### WS `/ws/global/{lobbyId}`

Connects a user to the global chat for a specific lobby.

### WS `/ws/private/{chatId}`

Connects a user to a private chat (e.g., Mafia channel).

**Message Format (Client → Server):**

```json
{ "type": "message", "content": "string" }
```

**Message Format (Server → Client):**

```json
{ "type": "message", "sender": "string", "content": "string", "timestamp": "datetime" }
```

---

# Repository Structure & Development Workflow

## Repository Organization

- Common Public Repository (CPR): Contains documentation, architecture diagrams, and submodule references
- Individual Private Repositories: Each team member owns 2 microservice repositories
  - Alexandrina G.: user-management-service, game-service
  - Alexander C.: shop-service, roleplay-service
  - Dmitrii C.: town-service, character-service
  - Dmitrii B.: rumors-service, communication-service
  - Irina N.: task-service, voting-service


### Branch Strategy
- main: Production-ready code, protected branch
- development: Integration branch for testing
- feature/*: Individual feature development


### Contribution Rules
- Minimum 3 code reviews required for merge
- All tests must pass before merge
- Follow naming conventions: feature/service-functionality
- Squash commits when merging to main
- Delete feature branches after successful merge

### Code Review Process
1. Create feature branch from development
2. Implement changes with appropriate tests
3. Create PR to development branch
4. Address review feedback
5. Squash and merge after approval

### Testing Requirements
- Unit test coverage minimum: 75 %
