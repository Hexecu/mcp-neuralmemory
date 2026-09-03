# Temporal Knowledge Graph & Visualizer

Neural Memory includes a specialized **Temporal Property Graph Visualizer** built natively in SwiftUI, accompanied by an interactive D3.js/SVG fallback viewer. It is engineered specifically to represent chronological progression, semantic relationships, and memory retention dynamics over time.

<p align="center">
  <img src="assets/images/temporal_graph_canvas.png" width="940" alt="Temporal Knowledge Graph Canvas" style="border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.5);">
</p>

---

## 1. Visual Layout Modes

In the top toolbar of the Graph window, users can toggle between two primary visual layout paradigms:

```
[ 🌌 Topic Clusters | ⏳ Timeline Stream | ⚡ Free Force ]
```

### 1.1 Regional Topic Clusters (Default)
Traditional force-directed graphs suffer from the **"central collapse ball"** problem: all nodes are pulled toward a single central coordinate $(X_c, Y_c)$, resulting in an unreadable tangle of overlapping circles.

Neural Memory solves this using **Orbital Regional Gravitational Centers**:
1. Every `Topic` node or primary project acts as an independent orbital center placed dynamically around the canvas.
2. Nodal entities (`Decision`, `Commitment`, `Person`, `Meeting`, `Artifact`) experience:
   - Strong Coulombic repulsion against all neighboring nodes ($F_{rep} \propto 1/d^2$).
   - Targeted magnetic attraction toward their dominant topic center ($F_{orbit} = k \cdot (X_{topic} - X_{node})$).
3. Result: Distinct, beautiful "galaxies" of related ideas that separate naturally in space.

### 1.2 Temporal Timeline Stream
Inspired by state-of-the-art temporal graph memory architectures (*Graphiti by Zep*, *Mem0*, *ChronoKG*):
- **Horizontal X-Axis**: Mapped to the continuous chronological timeline from earliest memory to the present.
- **Vertical Y-Axis (Semantic Altitude Lanes)**:
  Nodes are distributed along dedicated horizontal altitude tracks based on their semantic cognitive function:
  - **Lane 1 (Top, $Y = 90$)**: *Dream Reflections & Higher-Order Insights* (purple glow)
  - **Lane 2 ($Y = 175$)**: *Strategic Decisions* (emerald green)
  - **Lane 3 ($Y = 260$)**: *Meeting Sessions & Collaborative Calls* (amber orange)
  - **Lane 4 ($Y = 345$)**: *Commitments, Promises & Open Loops* (crimson red)
  - **Lane 5 (Bottom, $Y = 430$)**: *Topics, Concepts & People* (cyan blue)

---

## 2. Interactive Time-Travel & Scrubber

At the bottom of the Graph window, the **Time Scrubber** enables navigating through personal memory history:

### 2.1 Range Presets
Quickly filter the visible memory window:
- **`All Time`**: Displays the entire accumulated graph history.
- **`30 Days`**: Shows work and insights from the last month.
- **`7 Days`**: Focuses on the current week.
- **`3 Days`**: Recent context for active sprints.
- **`Today`**: Real-time snapshot of the current day.

### 2.2 Continuous Time-Travel Slider
- Dragging the slider dynamically filters graph nodes by timestamp: nodes only appear once the playhead crosses their observation time.
- **Play / Pause (Animation)**: Automatically plays back the chronological evolution of your knowledge graph, visualizing how thoughts, meetings, and decisions connected over time.

---

## 3. Hermann Ebbinghaus Memory Decay

Human memory retention diminishes over time unless reinforced. Neural Memory models this mathematically via the **Ebbinghaus Forgetting Curve**:

$$R = e^{-\frac{\Delta t}{S}}$$

Where:
- $R \in (0, 1]$ is the **retrievability** (visual prominence) of the memory node.
- $\Delta t$ is the elapsed time since the node was created or last referenced.
- $S$ is the **memory strength** (configurable in Settings under *Temporal Graph* from 12 hours to 168 hours).

### Visual Rendering
- **Recent & Active Nodes**: Render with 100% opacity, intense neon drop shadows, and subtle orbital pulse animations.
- **Historical Dormant Nodes**: Opacity smoothly attenuates to 35% with reduced edge thickness, keeping the screen clean while retaining background awareness.
- **Memory Reactivation**: If an old topic or decision is referenced in a new interaction bundle, its memory strength $S$ is reinforced, instantly restoring full visual brilliance.

---

## 4. Node Types & Color Hierarchy

| Node Type | Color | Hex Code | Icon | Cognitive Function |
| :--- | :--- | :--- | :--- | :--- |
| **`Decision`** | Emerald Green | `#2ecc71` | `checkmark.seal.fill` | Approved proposals, rejected options, strategic choices |
| **`Commitment`** | Crimson Coral | `#e74c3c` | `clock.badge.exclamationmark` | Promises made/received, deadlines, action items |
| **`Meeting`** | Warm Amber | `#f39c12` | `video.bubble.fill` | Zoom, Google Meet, Teams call syncs and participants |
| **`Reflection`** | Electric Purple | `#9b59b6` | `sparkles` | Consolidated insights generated during Dream Mode |
| **`Topic`** | Ocean Cyan | `#1abc9c` | `folder.fill` | Core domains, workstreams, technical topics |
| **`Person`** | Royal Blue | `#3498db` | `person.crop.circle.fill` | Colleagues, clients, and collaborators |
| **`Artifact`** | Steel Slate | `#95a5a6` | `doc.text.fill` | Documents, code repositories, URLs, PRs |

---

## 5. Embedded HTML5 / D3.js Visualizer

For headless environments or external browser access, the backend serves an embedded D3.js visualizer:

- **Local URL**: `http://127.0.0.1:8765/graph`
- **Data Endpoint**: `GET /api/graph/data?project_id=default&since=...&until=...`
- **Features**: Drag-to-pan, scroll-to-zoom, node click detail inspector, SVG vector rendering.
