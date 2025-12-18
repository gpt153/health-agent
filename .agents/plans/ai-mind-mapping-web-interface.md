# Feature: AI-Powered Mind Mapping Web Interface

## Feature Description

Build a standalone web-based mind mapping tool for AI-assisted software planning. The tool enables users to brainstorm with AI through natural conversation, visualize project structure as an interactive mind map, and export structured plans for implementation. The interface runs in Chrome browser, is served by the existing Express server at plan.153.se, and features automatic sub-node creation when users describe details.

## User Story

As a non-developer planning software projects
I want to brainstorm with AI and see my ideas as a visual mind map
So that I can understand the big picture, work on one detail at a time, and communicate effectively with AI coding agents

## Problem Statement

Current software planning approaches present several challenges:
- AI generates massive text outputs that are overwhelming and hard to navigate
- Difficult to maintain overview while drilling into specific details
- No visual representation of project structure and relationships
- Manual translation from planning discussions to structured implementation plans
- Communication gap between non-technical stakeholders and AI coding agents

## Solution Statement

Create an AI-powered mind mapping web interface that:
1. Generates initial project structure through conversational brainstorming with AI asking clarifying questions
2. Visualizes software architecture as an interactive, expandable mind map
3. Enables focused conversations by clicking individual nodes
4. Automatically creates sub-nodes when users describe more detail about a feature
5. Exports structured JSON/Markdown compatible with existing `/core_piv_loop:plan-feature` command
6. Serves as a translator/orchestrator between natural language and remote-coding-agent commands (future)

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium-High
**Primary Systems Affected**:
- Express server (new static file route)
- New client-side React application

**Dependencies**:
- React Flow (mind map visualization)
- Vite (build tool for React app)
- Tailwind CSS (styling)
- Zustand (state management)
- Direct Claude API access (temporary hardcoded key)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/index.ts` (lines 250-370) - Why: Express server setup, shows pattern for adding routes and static file serving
- `package.json` (lines 1-65) - Why: Existing dependencies, scripts pattern, Node version requirements
- `tsconfig.json` (all) - Why: TypeScript configuration that client should mirror
- `.prettierrc` (all) - Why: Code formatting standards (single quotes, semicolons, 2-space tabs)
- `eslint.config.mjs` (all) - Why: Linting rules and patterns to follow
- `.agents/reference/new-features.md` (lines 1-50) - Why: Platform adapter patterns (similar interface abstraction approach)

### New Files to Create

**Client Application** (`client/mindmap/`):
- `client/mindmap/package.json` - Vite + React dependencies
- `client/mindmap/vite.config.ts` - Vite configuration
- `client/mindmap/tailwind.config.js` - Tailwind CSS configuration
- `client/mindmap/tsconfig.json` - TypeScript config (based on root tsconfig)
- `client/mindmap/index.html` - Entry HTML file
- `client/mindmap/postcss.config.js` - PostCSS for Tailwind
- `client/mindmap/src/main.tsx` - React entry point
- `client/mindmap/src/App.tsx` - Main application component
- `client/mindmap/src/index.css` - Tailwind imports + global styles
- `client/mindmap/src/types/mindmap.types.ts` - TypeScript interfaces for mind map data
- `client/mindmap/src/store/mindmap.store.ts` - Zustand state management
- `client/mindmap/src/services/chat.service.ts` - AI chat abstraction (ChatService interface + Claude implementation)
- `client/mindmap/src/services/export.service.ts` - Export to JSON/Markdown/plan-feature format
- `client/mindmap/src/components/MindMap.tsx` - React Flow canvas component
- `client/mindmap/src/components/ChatPanel.tsx` - AI conversation sidebar
- `client/mindmap/src/components/ExportButton.tsx` - Export functionality
- `client/mindmap/src/components/NodeEditor.tsx` - Edit node properties
- `client/mindmap/.gitignore` - Ignore node_modules, dist/

**Server Integration**:
- `src/index.ts` - UPDATE: Add static file serving for /mindmap route

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [React Flow - Mind Map Tutorial](https://reactflow.dev/examples/mindmap)
  - Specific section: Complete mind map implementation example
  - Why: Official guide for building mind maps with React Flow, shows node nesting patterns

- [React Flow - API Documentation](https://reactflow.dev/api-reference)
  - Specific sections: useNodesState, useEdgesState, addEdge
  - Why: Core hooks and utilities for managing mind map state

- [Zustand Documentation](https://docs.pmnd.rs/zustand/getting-started/introduction)
  - Specific section: Basic usage, TypeScript
  - Why: Simple state management without Redux complexity

- [Vite - Getting Started](https://vitejs.dev/guide/)
  - Specific section: Creating a Vite project, configuration
  - Why: Build tool setup and dev server configuration

- [Tailwind CSS - Installation](https://tailwindcss.com/docs/installation/using-postcss)
  - Specific section: PostCSS installation
  - Why: CSS framework setup with Vite

- [Claude API - Messages](https://docs.anthropic.com/en/api/messages)
  - Specific section: Creating messages, streaming
  - Why: Direct API calls from browser for AI chat functionality

### Patterns to Follow

**Express Route Pattern** (from `src/index.ts:286-310`):
```typescript
// Health check endpoint pattern
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Static file serving pattern (to be added for /mindmap)
app.use('/mindmap', express.static(path.join(__dirname, '../client/mindmap/dist')));
```

**TypeScript Interface Pattern** (from `src/types/index.ts:59-84`):
```typescript
// Define clean interfaces for abstraction
export interface ChatService {
  sendMessage(message: string, context: MindMapContext): Promise<string>;
  streamResponse(message: string, context: MindMapContext): AsyncGenerator<string>;
}

// Enable easy swapping of implementations
class DirectClaudeChat implements ChatService { }
class RemoteAgentChat implements ChatService { }
```

**Error Handling Pattern** (from `src/index.ts:313-348`):
```typescript
try {
  // Main logic
  const result = await someOperation();
  return res.json({ success: true, data: result });
} catch (error) {
  console.error('[Component] Operation failed:', error);
  return res.status(500).json({ error: 'Internal server error' });
}
```

**Naming Conventions**:
- Files: `kebab-case.ts` for services, `PascalCase.tsx` for React components
- Functions: `camelCase` for all functions
- Types/Interfaces: `PascalCase` with descriptive names
- Constants: `UPPER_SNAKE_CASE` for config values

**Code Style** (from `.prettierrc`):
- Single quotes for strings
- Semicolons required
- 2-space indentation
- 100 character line width
- Arrow function parens: avoid when possible (`x => x` not `(x) => x`)

**Component Structure Pattern**:
```typescript
// React component with proper types
interface MindMapProps {
  initialNodes: MindMapNode[];
  onNodesChange: (nodes: MindMapNode[]) => void;
}

export const MindMap: React.FC<MindMapProps> = ({ initialNodes, onNodesChange }) => {
  // Component logic
  return <div>...</div>;
};
```

---

## IMPLEMENTATION PLAN

### Phase 1: Project Setup & Configuration

Set up the client-side React application structure, build tooling, and development environment.

**Tasks:**
- Create `/client/mindmap/` directory structure
- Initialize new npm project with Vite + React + TypeScript
- Configure Tailwind CSS with PostCSS
- Set up TypeScript configuration matching parent project
- Create base HTML entry point
- Configure Prettier/ESLint for client code

### Phase 2: Core Data Structures & State Management

Define TypeScript interfaces, implement Zustand store, and create data transformation utilities.

**Tasks:**
- Define mind map data structures (nodes, edges, project metadata)
- Implement Zustand store for mind map state
- Create helper functions for node operations (add, update, delete, find parent)
- Design future-proof JSON format with Archon integration fields

### Phase 3: Visual Mind Map Interface

Build the React Flow canvas with drag-and-drop, node creation, and visual editing.

**Tasks:**
- Implement React Flow canvas component
- Create custom node components with expand/collapse
- Add drag-and-drop positioning
- Implement zoom and pan controls
- Style nodes with Tailwind CSS

### Phase 4: AI Chat Integration

Implement ChatService abstraction and direct Claude API integration for conversational planning.

**Tasks:**
- Define ChatService interface for future backend swapping
- Implement DirectClaudeChat with Anthropic API
- Create ChatPanel UI component
- Handle streaming responses from Claude API
- Implement conversation context (send relevant node data with user message)

### Phase 5: Node Expansion & Sub-Node Creation

Implement the critical feature: clicking a node opens focused chat, describing detail creates sub-nodes automatically.

**Tasks:**
- Detect when AI response suggests creating sub-nodes
- Parse AI response for structured node creation (extract labels and descriptions)
- Automatically add child nodes under selected parent
- Update mind map visual hierarchy in real-time
- Handle edge cases (invalid formats, duplicate nodes)

### Phase 6: Export Functionality

Create multiple export formats for different use cases.

**Tasks:**
- Implement JSON export (full mind map with metadata)
- Implement Markdown export (hierarchical structure, human-readable)
- Implement plan-feature format (optimized for `/core_piv_loop:plan-feature`)
- Add download functionality with proper filename generation
- Add import JSON functionality to continue editing

### Phase 7: Server Integration

Integrate the built client application with the existing Express server.

**Tasks:**
- Add static file serving route to `src/index.ts`
- Configure Vite build output to `client/mindmap/dist/`
- Test serving from plan.153.se domain
- Add fallback route for React Router (future-proofing)
- Update root package.json scripts for building client

---

## STEP-BY-STEP TASKS

### CREATE client/mindmap/package.json

- **IMPLEMENT**: Initialize Vite + React + TypeScript project
- **DEPENDENCIES**:
  ```json
  {
    "dependencies": {
      "react": "^18.3.1",
      "react-dom": "^18.3.1",
      "reactflow": "^11.11.0",
      "zustand": "^4.5.0",
      "@anthropic-ai/sdk": "^0.34.0"
    },
    "devDependencies": {
      "@types/react": "^18.3.12",
      "@types/react-dom": "^18.3.1",
      "@vitejs/plugin-react": "^4.3.4",
      "vite": "^6.0.3",
      "typescript": "^5.6.3",
      "tailwindcss": "^3.4.17",
      "postcss": "^8.4.49",
      "autoprefixer": "^10.4.20",
      "prettier": "^3.4.2"
    }
  }
  ```
- **SCRIPTS**:
  ```json
  {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "format": "prettier --write 'src/**/*.{ts,tsx}'",
    "format:check": "prettier --check 'src/**/*.{ts,tsx}'"
  }
  ```
- **GOTCHA**: Use exact React Flow version 11.11.0 for stability
- **VALIDATE**: `cd client/mindmap && npm install`

### CREATE client/mindmap/vite.config.ts

- **IMPLEMENT**: Vite configuration for React + TypeScript
- **PATTERN**: Standard Vite React setup
- **CONTENT**:
  ```typescript
  import { defineConfig } from 'vite';
  import react from '@vitejs/plugin-react';
  import path from 'path';

  export default defineConfig({
    plugins: [react()],
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
    server: {
      port: 5173,
      strictPort: false,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
  });
  ```
- **VALIDATE**: Config syntax is valid

### CREATE client/mindmap/tailwind.config.js

- **IMPLEMENT**: Tailwind CSS configuration
- **CONTENT**:
  ```javascript
  /** @type {import('tailwindcss').Config} */
  export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  };
  ```
- **VALIDATE**: Config is valid

### CREATE client/mindmap/postcss.config.js

- **IMPLEMENT**: PostCSS configuration for Tailwind
- **CONTENT**:
  ```javascript
  export default {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  };
  ```
- **VALIDATE**: Config syntax is correct

### CREATE client/mindmap/tsconfig.json

- **IMPLEMENT**: TypeScript configuration for React
- **MIRROR**: Root `tsconfig.json` settings with React-specific additions
- **CONTENT**:
  ```json
  {
    "compilerOptions": {
      "target": "ES2022",
      "lib": ["ES2022", "DOM", "DOM.Iterable"],
      "module": "ESNext",
      "skipLibCheck": true,
      "strict": true,
      "esModuleInterop": true,
      "moduleResolution": "bundler",
      "resolveJsonModule": true,
      "allowImportingTsExtensions": true,
      "noEmit": true,
      "jsx": "react-jsx",
      "allowSyntheticDefaultImports": true,
      "forceConsistentCasingInFileNames": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "noImplicitReturns": true,
      "noFallthroughCasesInSwitch": true,
      "paths": {
        "@/*": ["./src/*"]
      }
    },
    "include": ["src"],
    "exclude": ["node_modules", "dist"]
  }
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/.prettierrc

- **IMPLEMENT**: Copy root Prettier configuration
- **MIRROR**: `/home/samuel/remote-coding-agent/.prettierrc`
- **CONTENT**:
  ```json
  {
    "semi": true,
    "singleQuote": true,
    "trailingComma": "es5",
    "tabWidth": 2,
    "printWidth": 100,
    "arrowParens": "avoid",
    "endOfLine": "lf"
  }
  ```
- **VALIDATE**: File created

### CREATE client/mindmap/.gitignore

- **IMPLEMENT**: Ignore build artifacts and dependencies
- **CONTENT**:
  ```
  node_modules
  dist
  .DS_Store
  *.local
  .env
  .env.local
  ```
- **VALIDATE**: File created

### CREATE client/mindmap/index.html

- **IMPLEMENT**: Entry HTML file for React app
- **CONTENT**:
  ```html
  <!doctype html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>AI Mind Map - Software Planning</title>
    </head>
    <body>
      <div id="root"></div>
      <script type="module" src="/src/main.tsx"></script>
    </body>
  </html>
  ```
- **VALIDATE**: HTML is valid

### CREATE client/mindmap/src/index.css

- **IMPLEMENT**: Tailwind imports and global styles
- **CONTENT**:
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  #root {
    width: 100vw;
    height: 100vh;
  }
  ```
- **VALIDATE**: CSS syntax is valid

### CREATE client/mindmap/src/types/mindmap.types.ts

- **IMPLEMENT**: TypeScript interfaces for mind map data structures
- **PATTERN**: Future-proof with Archon integration fields
- **CONTENT**:
  ```typescript
  /**
   * Mind map data structures with future Archon integration support
   */

  export interface MindMapProject {
    name: string;
    description: string;
    created_at: string; // ISO-8601
    updated_at?: string; // ISO-8601
  }

  export interface MindMapNode {
    id: string;
    type: 'root' | 'feature' | 'component' | 'detail';
    label: string;
    description: string;
    parent_id: string | null;
    metadata: {
      status: 'planned' | 'doing' | 'review' | 'done';
      archon_project_id: string | null; // Future: link to Archon project
      archon_task_ids: string[]; // Future: link to Archon tasks
      commands: string[]; // Future: track which commands executed
      expanded: boolean; // UI state: is node showing children?
    };
    position: {
      x: number;
      y: number;
    };
  }

  export interface MindMapEdge {
    id: string;
    source: string; // parent node id
    target: string; // child node id
    type: 'parent-child' | 'dependency';
  }

  export interface MindMapData {
    version: string;
    project: MindMapProject;
    nodes: MindMapNode[];
    edges: MindMapEdge[];
  }

  export interface MindMapContext {
    currentNode: MindMapNode | null;
    parentNode: MindMapNode | null;
    childNodes: MindMapNode[];
    siblingNodes: MindMapNode[];
  }

  export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
  }
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/store/mindmap.store.ts

- **IMPLEMENT**: Zustand store for mind map state management
- **PATTERN**: Simple, flat state with computed selectors
- **IMPORTS**:
  ```typescript
  import { create } from 'zustand';
  import type { MindMapData, MindMapNode, MindMapEdge, ChatMessage } from '@/types/mindmap.types';
  ```
- **CONTENT**:
  ```typescript
  interface MindMapStore {
    // State
    data: MindMapData;
    selectedNodeId: string | null;
    chatHistory: ChatMessage[];
    isAIThinking: boolean;

    // Actions - Nodes
    addNode: (node: MindMapNode) => void;
    updateNode: (id: string, updates: Partial<MindMapNode>) => void;
    deleteNode: (id: string) => void;
    setSelectedNode: (id: string | null) => void;

    // Actions - Edges
    addEdge: (edge: MindMapEdge) => void;
    deleteEdge: (id: string) => void;

    // Actions - Chat
    addChatMessage: (message: ChatMessage) => void;
    clearChatHistory: () => void;
    setAIThinking: (thinking: boolean) => void;

    // Actions - Project
    updateProject: (updates: Partial<MindMapData['project']>) => void;
    loadMindMap: (data: MindMapData) => void;
    exportMindMap: () => MindMapData;

    // Selectors
    getNodeById: (id: string) => MindMapNode | undefined;
    getChildNodes: (parentId: string) => MindMapNode[];
    getParentNode: (childId: string) => MindMapNode | undefined;
  }

  export const useMindMapStore = create<MindMapStore>((set, get) => ({
    // Initial state
    data: {
      version: '1.0',
      project: {
        name: 'Untitled Project',
        description: '',
        created_at: new Date().toISOString(),
      },
      nodes: [],
      edges: [],
    },
    selectedNodeId: null,
    chatHistory: [],
    isAIThinking: false,

    // Node actions
    addNode: node =>
      set(state => ({
        data: {
          ...state.data,
          nodes: [...state.data.nodes, node],
        },
      })),

    updateNode: (id, updates) =>
      set(state => ({
        data: {
          ...state.data,
          nodes: state.data.nodes.map(n => (n.id === id ? { ...n, ...updates } : n)),
        },
      })),

    deleteNode: id =>
      set(state => ({
        data: {
          ...state.data,
          nodes: state.data.nodes.filter(n => n.id !== id),
          edges: state.data.edges.filter(e => e.source !== id && e.target !== id),
        },
      })),

    setSelectedNode: id => set({ selectedNodeId: id }),

    // Edge actions
    addEdge: edge =>
      set(state => ({
        data: {
          ...state.data,
          edges: [...state.data.edges, edge],
        },
      })),

    deleteEdge: id =>
      set(state => ({
        data: {
          ...state.data,
          edges: state.data.edges.filter(e => e.id !== id),
        },
      })),

    // Chat actions
    addChatMessage: message =>
      set(state => ({
        chatHistory: [...state.chatHistory, message],
      })),

    clearChatHistory: () => set({ chatHistory: [] }),

    setAIThinking: thinking => set({ isAIThinking: thinking }),

    // Project actions
    updateProject: updates =>
      set(state => ({
        data: {
          ...state.data,
          project: {
            ...state.data.project,
            ...updates,
            updated_at: new Date().toISOString(),
          },
        },
      })),

    loadMindMap: data => set({ data }),

    exportMindMap: () => get().data,

    // Selectors
    getNodeById: id => get().data.nodes.find(n => n.id === id),

    getChildNodes: parentId => get().data.nodes.filter(n => n.parent_id === parentId),

    getParentNode: childId => {
      const child = get().data.nodes.find(n => n.id === childId);
      if (!child || !child.parent_id) return undefined;
      return get().data.nodes.find(n => n.id === child.parent_id);
    },
  }));
  ```
- **GOTCHA**: Use shallow comparisons for performance with large mind maps
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/services/chat.service.ts

- **IMPLEMENT**: ChatService interface + DirectClaudeChat implementation
- **PATTERN**: Interface abstraction for future backend swapping (like IPlatformAdapter)
- **IMPORTS**:
  ```typescript
  import Anthropic from '@anthropic-ai/sdk';
  import type { MindMapContext } from '@/types/mindmap.types';
  ```
- **CONTENT**:
  ```typescript
  /**
   * Chat service abstraction for AI conversations
   * Allows swapping between direct Claude API (MVP) and remote-coding-agent backend (future)
   */

  export interface ChatService {
    sendMessage(message: string, context: MindMapContext): Promise<string>;
    streamResponse(
      message: string,
      context: MindMapContext
    ): AsyncGenerator<string, void, unknown>;
  }

  /**
   * Direct Claude API implementation (MVP)
   * TODO: Move API key to environment variable or backend
   */
  export class DirectClaudeChat implements ChatService {
    private client: Anthropic;
    private systemPrompt: string;

    constructor(apiKey: string) {
      this.client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true });
      this.systemPrompt = `You are an AI assistant helping with software project planning through mind mapping.

When the user describes a feature or provides details:
1. If they describe sub-features or components, respond with a JSON array of child nodes to create
2. If they ask questions, provide helpful guidance
3. If they refine a feature, suggest updates to the current node

For creating child nodes, respond in this exact JSON format:
{
  "action": "create_nodes",
  "nodes": [
    {
      "label": "Node Name",
      "description": "Detailed description of this component or feature"
    }
  ]
}

For other responses, just provide helpful text (no JSON).`;
    }

    async sendMessage(message: string, context: MindMapContext): Promise<string> {
      const contextPrompt = this.buildContextPrompt(context);

      const response = await this.client.messages.create({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        system: this.systemPrompt,
        messages: [
          {
            role: 'user',
            content: `${contextPrompt}\n\nUser: ${message}`,
          },
        ],
      });

      const content = response.content[0];
      if (content.type === 'text') {
        return content.text;
      }

      return 'Sorry, I could not process that request.';
    }

    async *streamResponse(
      message: string,
      context: MindMapContext
    ): AsyncGenerator<string, void, unknown> {
      const contextPrompt = this.buildContextPrompt(context);

      const stream = await this.client.messages.stream({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        system: this.systemPrompt,
        messages: [
          {
            role: 'user',
            content: `${contextPrompt}\n\nUser: ${message}`,
          },
        ],
      });

      for await (const event of stream) {
        if (event.type === 'content_block_delta') {
          if (event.delta.type === 'text_delta') {
            yield event.delta.text;
          }
        }
      }
    }

    private buildContextPrompt(context: MindMapContext): string {
      let prompt = 'Current Context:\n';

      if (context.currentNode) {
        prompt += `\nSelected Node: "${context.currentNode.label}"\n`;
        prompt += `Description: ${context.currentNode.description}\n`;
      }

      if (context.parentNode) {
        prompt += `\nParent Node: "${context.parentNode.label}"\n`;
      }

      if (context.childNodes.length > 0) {
        prompt += `\nExisting Child Nodes:\n`;
        context.childNodes.forEach(child => {
          prompt += `- ${child.label}\n`;
        });
      }

      return prompt;
    }
  }

  /**
   * Future implementation: Remote-coding-agent backend
   * Will call Express server instead of Claude API directly
   */
  export class RemoteAgentChat implements ChatService {
    async sendMessage(message: string, context: MindMapContext): Promise<string> {
      // Future: POST to http://localhost:3000/api/mindmap/chat
      throw new Error('Not implemented - use DirectClaudeChat for MVP');
    }

    async *streamResponse(
      message: string,
      context: MindMapContext
    ): AsyncGenerator<string, void, unknown> {
      // Future: WebSocket connection to remote-coding-agent
      throw new Error('Not implemented - use DirectClaudeChat for MVP');
      yield ''; // Make TypeScript happy
    }
  }

  // TODO: Move to environment variable
  const CLAUDE_API_KEY = 'YOUR_API_KEY_HERE'; // Replace with actual key

  // Export singleton instance
  export const chatService: ChatService = new DirectClaudeChat(CLAUDE_API_KEY);
  ```
- **GOTCHA**: API key is hardcoded for MVP - add TODO comment for moving to env
- **GOTCHA**: `dangerouslyAllowBrowser: true` needed for browser usage (temporary)
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/services/export.service.ts

- **IMPLEMENT**: Export mind map to JSON, Markdown, and plan-feature format
- **IMPORTS**:
  ```typescript
  import type { MindMapData, MindMapNode } from '@/types/mindmap.types';
  ```
- **CONTENT**:
  ```typescript
  /**
   * Export service for mind map data
   * Supports JSON, Markdown, and plan-feature formats
   */

  export class ExportService {
    /**
     * Export as JSON (save/load)
     */
    static exportJSON(data: MindMapData): string {
      return JSON.stringify(data, null, 2);
    }

    /**
     * Export as Markdown (human-readable)
     */
    static exportMarkdown(data: MindMapData): string {
      let markdown = `# ${data.project.name}\n\n`;
      markdown += `${data.project.description}\n\n`;
      markdown += `---\n\n`;

      const rootNodes = data.nodes.filter(n => n.parent_id === null);

      const renderNode = (node: MindMapNode, level: number): string => {
        const indent = '  '.repeat(level);
        let output = `${indent}- **${node.label}**\n`;
        if (node.description) {
          output += `${indent}  ${node.description}\n`;
        }

        const children = data.nodes.filter(n => n.parent_id === node.id);
        children.forEach(child => {
          output += renderNode(child, level + 1);
        });

        return output;
      };

      rootNodes.forEach(root => {
        markdown += renderNode(root, 0);
      });

      return markdown;
    }

    /**
     * Export as plan-feature format (for /core_piv_loop:plan-feature)
     */
    static exportPlanFeature(data: MindMapData, selectedNodeId?: string): string {
      const rootNode = selectedNodeId
        ? data.nodes.find(n => n.id === selectedNodeId)
        : data.nodes.find(n => n.parent_id === null);

      if (!rootNode) {
        return `Feature: ${data.project.name}\n\n${data.project.description}`;
      }

      let output = `Feature: ${rootNode.label}\n\n`;
      output += `Description: ${rootNode.description}\n\n`;

      const children = data.nodes.filter(n => n.parent_id === rootNode.id);
      if (children.length > 0) {
        output += `## Sub-Features\n\n`;
        children.forEach(child => {
          output += `### ${child.label}\n`;
          output += `${child.description}\n\n`;

          const grandchildren = data.nodes.filter(n => n.parent_id === child.id);
          if (grandchildren.length > 0) {
            output += `**Components:**\n`;
            grandchildren.forEach(gc => {
              output += `- ${gc.label}: ${gc.description}\n`;
            });
            output += `\n`;
          }
        });
      }

      const parent = data.nodes.find(n => n.id === rootNode.parent_id);
      if (parent) {
        output += `## Context\n\n`;
        output += `Part of: ${parent.label}\n`;
      }

      return output;
    }

    /**
     * Download file to browser
     */
    static downloadFile(content: string, filename: string, mimeType: string): void {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  }
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/components/MindMap.tsx

- **IMPLEMENT**: React Flow canvas component with drag-and-drop
- **PATTERN**: React Flow mind map tutorial
- **IMPORTS**:
  ```typescript
  import React, { useCallback } from 'react';
  import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    BackgroundVariant,
  } from 'reactflow';
  import 'reactflow/dist/style.css';
  import { useMindMapStore } from '@/store/mindmap.store';
  import type { MindMapNode as MindMapNodeType } from '@/types/mindmap.types';
  ```
- **CONTENT**:
  ```typescript
  export const MindMap: React.FC = () => {
    const { data, selectedNodeId, setSelectedNode, updateNode } = useMindMapStore();

    // Convert MindMapNode to ReactFlow Node
    const initialNodes: Node[] = data.nodes.map(node => ({
      id: node.id,
      type: 'default',
      data: { label: node.label, description: node.description },
      position: node.position,
      selected: node.id === selectedNodeId,
    }));

    const initialEdges: Edge[] = data.edges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
    }));

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // Handle node selection
    const onNodeClick = useCallback(
      (event: React.MouseEvent, node: Node) => {
        setSelectedNode(node.id);
      },
      [setSelectedNode]
    );

    // Handle node position changes
    const onNodeDragStop = useCallback(
      (event: React.MouseEvent, node: Node) => {
        updateNode(node.id, { position: node.position });
      },
      [updateNode]
    );

    // Handle new edge creation
    const onConnect = useCallback(
      (connection: Connection) => {
        setEdges(eds => addEdge(connection, eds));
      },
      [setEdges]
    );

    return (
      <div className="w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onNodeDragStop={onNodeDragStop}
          fitView
        >
          <Controls />
          <MiniMap />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>
    );
  };
  ```
- **GOTCHA**: React Flow CSS must be imported
- **GOTCHA**: Position updates need to sync back to Zustand store
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/components/ChatPanel.tsx

- **IMPLEMENT**: AI conversation sidebar
- **PATTERN**: Chat interface with streaming responses
- **IMPORTS**:
  ```typescript
  import React, { useState, useRef, useEffect } from 'react';
  import { useMindMapStore } from '@/store/mindmap.store';
  import { chatService } from '@/services/chat.service';
  import type { MindMapContext } from '@/types/mindmap.types';
  ```
- **CONTENT**:
  ```typescript
  export const ChatPanel: React.FC = () => {
    const {
      chatHistory,
      addChatMessage,
      selectedNodeId,
      getNodeById,
      getParentNode,
      getChildNodes,
      isAIThinking,
      setAIThinking,
      addNode,
      data,
    } = useMindMapStore();

    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    const buildContext = (): MindMapContext => {
      const currentNode = selectedNodeId ? getNodeById(selectedNodeId) : null;
      const parentNode = currentNode ? getParentNode(currentNode.id) : null;
      const childNodes = currentNode ? getChildNodes(currentNode.id) : [];
      const siblingNodes = parentNode ? getChildNodes(parentNode.id) : [];

      return { currentNode: currentNode || null, parentNode: parentNode || null, childNodes, siblingNodes };
    };

    const handleSend = async () => {
      if (!input.trim()) return;

      const userMessage = { role: 'user' as const, content: input, timestamp: new Date().toISOString() };
      addChatMessage(userMessage);
      setInput('');
      setAIThinking(true);

      const context = buildContext();
      let fullResponse = '';

      try {
        // Stream response
        for await (const chunk of chatService.streamResponse(input, context)) {
          fullResponse += chunk;
        }

        // Check if response contains node creation command
        const nodeCreationMatch = fullResponse.match(/\{[^}]*"action":\s*"create_nodes"[^}]*\}/);
        if (nodeCreationMatch) {
          try {
            const command = JSON.parse(nodeCreationMatch[0]);
            if (command.action === 'create_nodes' && Array.isArray(command.nodes)) {
              // Create child nodes under selected node
              const parentId = selectedNodeId || null;
              command.nodes.forEach((nodeData: { label: string; description: string }) => {
                const newNode: MindMapNodeType = {
                  id: `node-${Date.now()}-${Math.random()}`,
                  type: 'feature',
                  label: nodeData.label,
                  description: nodeData.description,
                  parent_id: parentId,
                  metadata: {
                    status: 'planned',
                    archon_project_id: null,
                    archon_task_ids: [],
                    commands: [],
                    expanded: false,
                  },
                  position: {
                    x: Math.random() * 400,
                    y: Math.random() * 400,
                  },
                };
                addNode(newNode);
              });

              // Clean response (remove JSON command)
              fullResponse = fullResponse.replace(nodeCreationMatch[0], '').trim();
              if (fullResponse) {
                fullResponse = `Created ${command.nodes.length} child nodes.\n\n` + fullResponse;
              } else {
                fullResponse = `Created ${command.nodes.length} child nodes.`;
              }
            }
          } catch (e) {
            console.error('Failed to parse node creation command:', e);
          }
        }

        const aiMessage = {
          role: 'assistant' as const,
          content: fullResponse,
          timestamp: new Date().toISOString(),
        };
        addChatMessage(aiMessage);
      } catch (error) {
        const errorMessage = {
          role: 'system' as const,
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date().toISOString(),
        };
        addChatMessage(errorMessage);
      } finally {
        setAIThinking(false);
      }
    };

    return (
      <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 bg-white">
          <h2 className="text-lg font-semibold">AI Planning Assistant</h2>
          {selectedNodeId && (
            <p className="text-sm text-gray-600">
              Focused on: {getNodeById(selectedNodeId)?.label}
            </p>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatHistory.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : msg.role === 'assistant'
                      ? 'bg-white border border-gray-200'
                      : 'bg-red-100 text-red-800'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isAIThinking && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg p-3">
                <p className="text-sm text-gray-500">AI is thinking...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleSend()}
              placeholder="Describe your feature or ask a question..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isAIThinking}
            />
            <button
              onClick={handleSend}
              disabled={isAIThinking || !input.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    );
  };
  ```
- **GOTCHA**: Parse AI response for JSON commands to create nodes automatically
- **GOTCHA**: Sanitize and validate node creation data
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/components/ExportButton.tsx

- **IMPLEMENT**: Export functionality dropdown
- **IMPORTS**:
  ```typescript
  import React, { useState } from 'react';
  import { useMindMapStore } from '@/store/mindmap.store';
  import { ExportService } from '@/services/export.service';
  ```
- **CONTENT**:
  ```typescript
  export const ExportButton: React.FC = () => {
    const { exportMindMap, data, selectedNodeId } = useMindMapStore();
    const [isOpen, setIsOpen] = useState(false);

    const handleExport = (format: 'json' | 'markdown' | 'plan-feature') => {
      const mindMapData = exportMindMap();
      const timestamp = new Date().toISOString().split('T')[0];
      const projectName = data.project.name.toLowerCase().replace(/\s+/g, '-');

      switch (format) {
        case 'json': {
          const content = ExportService.exportJSON(mindMapData);
          ExportService.downloadFile(
            content,
            `${projectName}-${timestamp}.json`,
            'application/json'
          );
          break;
        }
        case 'markdown': {
          const content = ExportService.exportMarkdown(mindMapData);
          ExportService.downloadFile(content, `${projectName}-${timestamp}.md`, 'text/markdown');
          break;
        }
        case 'plan-feature': {
          const content = ExportService.exportPlanFeature(mindMapData, selectedNodeId || undefined);
          ExportService.downloadFile(
            content,
            `${projectName}-plan-${timestamp}.md`,
            'text/markdown'
          );
          break;
        }
      }

      setIsOpen(false);
    };

    return (
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Export
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
            <button
              onClick={() => handleExport('json')}
              className="w-full text-left px-4 py-2 hover:bg-gray-100 rounded-t-lg"
            >
              Export as JSON
            </button>
            <button
              onClick={() => handleExport('markdown')}
              className="w-full text-left px-4 py-2 hover:bg-gray-100"
            >
              Export as Markdown
            </button>
            <button
              onClick={() => handleExport('plan-feature')}
              className="w-full text-left px-4 py-2 hover:bg-gray-100 rounded-b-lg"
            >
              Export for /plan-feature
            </button>
          </div>
        )}
      </div>
    );
  };
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/App.tsx

- **IMPLEMENT**: Main application layout component
- **IMPORTS**:
  ```typescript
  import React from 'react';
  import { ReactFlowProvider } from 'reactflow';
  import { MindMap } from '@/components/MindMap';
  import { ChatPanel } from '@/components/ChatPanel';
  import { ExportButton } from '@/components/ExportButton';
  import { useMindMapStore } from '@/store/mindmap.store';
  ```
- **CONTENT**:
  ```typescript
  export const App: React.FC = () => {
    const { data, updateProject } = useMindMapStore();

    return (
      <div className="flex flex-col h-screen">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI Mind Map</h1>
              <p className="text-sm text-gray-600">{data.project.name}</p>
            </div>
            <ExportButton />
          </div>
        </header>

        {/* Main Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Mind Map Canvas (70%) */}
          <div className="flex-1">
            <ReactFlowProvider>
              <MindMap />
            </ReactFlowProvider>
          </div>

          {/* Chat Panel (30%) */}
          <div className="w-96">
            <ChatPanel />
          </div>
        </div>
      </div>
    );
  };
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### CREATE client/mindmap/src/main.tsx

- **IMPLEMENT**: React entry point
- **IMPORTS**:
  ```typescript
  import React from 'react';
  import ReactDOM from 'react-dom/client';
  import { App } from './App';
  import './index.css';
  ```
- **CONTENT**:
  ```typescript
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  ```
- **VALIDATE**: `cd client/mindmap && npx tsc --noEmit`

### UPDATE src/index.ts

- **IMPLEMENT**: Add static file serving for /mindmap route
- **PATTERN**: Mirror existing Express route pattern from `src/index.ts:286-310`
- **IMPORTS**: Add at top of file
  ```typescript
  import path from 'path';
  ```
- **ADD**: After line 284 (after `app.use(express.json());`), before health check endpoints:
  ```typescript
  // Serve mind map web app
  app.use('/mindmap', express.static(path.join(__dirname, '../client/mindmap/dist')));

  // Fallback for React Router (future-proofing)
  app.get('/mindmap/*', (_req, res) => {
    res.sendFile(path.join(__dirname, '../client/mindmap/dist/index.html'));
  });

  console.log('[Express] Mind map web app served at /mindmap');
  ```
- **GOTCHA**: Static file serving must come BEFORE catch-all route
- **GOTCHA**: Path is relative to dist/ folder (compiled TypeScript output)
- **VALIDATE**: `npm run type-check` in root directory

### UPDATE package.json (root)

- **IMPLEMENT**: Add scripts for building client
- **ADD**: To scripts section:
  ```json
  "build:client": "cd client/mindmap && npm install && npm run build",
  "build:all": "npm run build && npm run build:client",
  "dev:client": "cd client/mindmap && npm run dev"
  ```
- **VALIDATE**: Scripts syntax is valid JSON

### BUILD AND TEST

- **VALIDATE**: `cd client/mindmap && npm install`
- **VALIDATE**: `cd client/mindmap && npm run type-check`
- **VALIDATE**: `cd client/mindmap && npm run build`
- **VALIDATE**: Check `client/mindmap/dist/` exists with index.html, assets/
- **VALIDATE**: `npm run build` (root - TypeScript compilation)
- **VALIDATE**: `npm run dev` (root - start Express server)
- **VALIDATE**: Open browser to `http://localhost:3000/mindmap` - should see React app
- **VALIDATE**: Test AI chat generates nodes
- **VALIDATE**: Test export functionality
- **VALIDATE**: Test drag-and-drop mind map

---

## TESTING STRATEGY

### Unit Tests (Deferred to Phase 2)

MVP focuses on manual validation. Unit tests can be added for:
- ExportService (JSON, Markdown, plan-feature format generation)
- Zustand store actions (add, update, delete nodes)
- ChatService response parsing

### Integration Tests (Deferred to Phase 2)

- Full workflow: chat → nodes created → export → validate format
- Node hierarchy validation
- Edge creation and deletion

### Manual Testing (MVP Validation)

**Test Case 1: Initial Mind Map Generation**
1. Open http://localhost:3000/mindmap
2. Send message: "I want to build a task management app"
3. AI should ask clarifying questions
4. Respond with feature descriptions
5. Verify nodes appear on canvas

**Test Case 2: Node Expansion**
1. Click a node on the canvas
2. Chat panel should show "Focused on: [Node Name]"
3. Send message: "I need login, signup, and password reset"
4. Verify 3 child nodes created under selected node
5. Verify nodes have parent-child relationship

**Test Case 3: Export Functionality**
1. Click "Export" button
2. Select "Export as JSON"
3. Verify JSON file downloads
4. Open JSON - validate structure matches `MindMapData` interface
5. Repeat for Markdown and plan-feature formats

**Test Case 4: Drag and Drop**
1. Drag a node to new position
2. Verify position persists in store
3. Reload page (future) - position should be saved

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Root project
npm run type-check
npm run lint
npm run format:check

# Client application
cd client/mindmap
npm run type-check
npm run format:check
```

**Expected**: All commands pass with exit code 0

### Level 2: Build Verification

```bash
# Build client
cd client/mindmap
npm run build

# Verify dist/ created
ls -la dist/
# Expected: index.html, assets/ directory with .js and .css files

# Build server
cd ../..
npm run build

# Verify dist/ created
ls -la dist/
# Expected: index.js and other compiled server files
```

**Expected**: Both builds succeed with no errors

### Level 3: Runtime Validation

```bash
# Start Express server (serves both API and mind map UI)
npm run dev

# In browser, navigate to:
http://localhost:3000/mindmap

# Expected:
# - React app loads
# - Mind map canvas visible
# - Chat panel visible
# - No console errors
```

### Level 4: Manual Feature Validation

**Test Checklist:**
- [ ] Mind map canvas renders with React Flow
- [ ] Chat panel accepts input
- [ ] AI responds to messages (verify API key is set)
- [ ] Clicking node opens focused chat
- [ ] Describing details creates child nodes automatically
- [ ] Export button opens dropdown
- [ ] JSON export downloads valid file
- [ ] Markdown export generates readable hierarchy
- [ ] Plan-feature export produces format compatible with `/core_piv_loop:plan-feature`

### Level 5: Production Readiness

```bash
# Build for production
npm run build:all

# Start production server
npm start

# Test via Cloudflare tunnel at plan.153.se/mindmap
# Expected: Same functionality as dev environment
```

---

## ACCEPTANCE CRITERIA

- [ ] React application runs in Chrome browser
- [ ] Served by Express at plan.153.se/mindmap via Cloudflare tunnel
- [ ] AI chat interface generates initial mind map from conversation
- [ ] Clicking a node opens focused chat about that feature
- [ ] Describing details in node chat creates sub-nodes automatically
- [ ] Mind map visualizes project structure with React Flow
- [ ] Drag-and-drop node positioning works
- [ ] Export functionality produces valid JSON, Markdown, and plan-feature formats
- [ ] All validation commands pass with zero errors
- [ ] Code follows project conventions (Prettier, ESLint, TypeScript strict)
- [ ] Future-proof architecture with ChatService abstraction
- [ ] Data format includes fields for Archon integration (unpopulated)

---

## COMPLETION CHECKLIST

- [ ] All files created in correct locations
- [ ] npm install succeeds in client/mindmap/
- [ ] TypeScript compilation succeeds (client and server)
- [ ] Prettier formatting passes
- [ ] Express serves static files at /mindmap
- [ ] React app loads in browser
- [ ] AI chat generates nodes from conversation
- [ ] Node expansion creates child nodes automatically
- [ ] Export functionality works for all formats
- [ ] Manual test cases pass
- [ ] No console errors in browser or server
- [ ] Accessible via plan.153.se/mindmap (after Cloudflare tunnel)

---

## NOTES

### Design Decisions

**1. Hardcoded API Key (MVP Only)**
- **Decision**: Hardcode Claude API key in `chat.service.ts`
- **Rationale**: Simplest for MVP, no backend complexity
- **Future**: Move to environment variable or backend proxy for security
- **TODO Comment**: Added in code for visibility

**2. Direct Claude API from Browser**
- **Decision**: Use `dangerouslyAllowBrowser: true` in Anthropic SDK
- **Rationale**: MVP avoids backend complexity
- **Security Note**: API key exposed in browser (acceptable for single-user tool)
- **Future**: Move to backend proxy when integrating with remote-coding-agent

**3. Zustand Over Redux**
- **Decision**: Zustand for state management
- **Rationale**: Simpler, less boilerplate, perfect for MVP
- **Trade-off**: Less tooling than Redux DevTools
- **Benefit**: Easy to understand, fast to implement

**4. React Flow for Visualization**
- **Decision**: React Flow library for mind map
- **Rationale**: Official mind map tutorial, mature library, well-documented
- **Alternative Considered**: D3.js (too low-level, more complexity)

**5. Future-Proof Data Format**
- **Decision**: Include `archon_project_id`, `archon_task_ids`, `commands` fields in node metadata
- **Rationale**: Easy to add Archon integration later without breaking changes
- **Current**: Fields are null/empty arrays
- **Future**: Populate when Phase 2/3 implemented

### Implementation Trade-offs

**Complexity vs Functionality**:
- Chose simpler streaming approach over complex message queuing
- Single chat thread instead of multiple parallel conversations
- Manual export instead of auto-save (reduces state sync complexity)

**Performance Optimizations (Deferred)**:
- No virtualization for large node lists (acceptable for MVP <100 nodes)
- No debouncing for API calls (acceptable for single-user MVP)
- No memoization for React components (add if performance issues arise)

**Security Considerations**:
- API key exposure acceptable for single-user tool on private domain
- No authentication needed (private VM with Cloudflare tunnel)
- Add authentication layer when multi-user support required

### Success Metrics for MVP

**Primary Goal**: Validate that visual mind mapping improves planning experience over pure text

**Key Metrics**:
1. Can successfully plan the mind map tool itself using the tool (meta-planning)
2. Export produces valid format consumable by `/core_piv_loop:plan-feature`
3. Sub-node creation from natural language works reliably (>80% accuracy)

**User Experience**:
- Faster to understand big picture vs reading long text
- Easier to focus on one detail at a time
- Export format useful for feeding to remote-coding-agent

### Next Steps After MVP

**Phase 2: Remote-Coding-Agent Integration**
- Implement RemoteAgentChat service
- Add WebSocket support to Express
- Execute commands directly from mind map nodes
- Show real-time status updates

**Phase 3: Archon Integration**
- Store mind maps as Archon documents
- Create Archon projects from mind map branches
- Sync node status with Archon task progress
- Use Archon RAG for command orchestration

**Phase 4: Enhanced UX**
- Import JSON to continue editing
- Undo/redo functionality
- Node search and filtering
- Custom node types and styling
- Multi-tab architecture (UX/Frontend/Backend)

---

**Estimated Implementation Time**: 10-15 hours
**Confidence Score for One-Pass Success**: 7/10

**Key Risks**:
1. AI node creation parsing may need refinement (format inconsistencies)
2. React Flow learning curve for custom node styling
3. API key management in browser (security consideration for production)

**Mitigation**:
1. Clear JSON format specification in system prompt
2. Start with default React Flow nodes, customize later
3. Add TODO comments for backend migration path
