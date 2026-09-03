// GraphView.swift
// Native SwiftUI interactive Knowledge Graph Visualizer with physics & cognitive inspector

import SwiftUI

struct GraphView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var engine = GraphPhysicsEngine()

    // View state
    @State private var selectedNode: GraphNode?
    @State private var hoveredNode: GraphNode?
    @State private var draggedNodeId: String?

    // Filter & Search
    @State private var currentFilter: SemanticNodeType? = nil
    @State private var searchQuery: String = ""

    // Navigation transform
    @State private var zoomScale: CGFloat = 1.0
    @State private var panOffset: CGPoint = .zero
    @State private var lastDragOffset: CGPoint = .zero

    // Loading & status
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Background theme matching app
                backgroundView

                // Main Force Graph Canvas with 60fps simulation
                TimelineView(.animation(minimumInterval: 1.0 / 60.0)) { timeline in
                    Canvas { context, size in
                        engine.step()
                        drawGraph(context: context, size: size)
                    }
                    .gesture(
                        DragGesture(minimumDistance: 0)
                            .onChanged { value in
                                handleDragChanged(value: value, size: geometry.size)
                            }
                            .onEnded { value in
                                handleDragEnded(value: value)
                            }
                    )
                }

                // Top Floating Controls: Filters, Search, Actions
                VStack {
                    topToolbar
                        .padding(.top, 16)
                        .padding(.horizontal, 20)

                    filterBar
                        .padding(.top, 8)
                        .padding(.horizontal, 20)

                    Spacer()

                    bottomStatusBar
                        .padding(.bottom, 16)
                        .padding(.horizontal, 20)
                }

                // Right Floating Cognitive Inspector Drawer
                if let node = selectedNode {
                    HStack {
                        Spacer()
                        CognitiveInspectorView(
                            node: node,
                            neighbors: engine.getNeighbors(for: node.id),
                            onSelectNeighbor: { neighbor in
                                selectNodeAndCenter(neighbor, size: geometry.size)
                            },
                            onClose: {
                                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                                    selectedNode = nil
                                }
                            }
                        )
                        .transition(.move(edge: .trailing).combined(with: .opacity))
                        .padding(.trailing, 20)
                        .padding(.vertical, 20)
                    }
                }
            }
            .onAppear {
                loadGraph(in: geometry.size)
            }
        }
        .frame(minWidth: 900, minHeight: 650)
    }

    // MARK: - Background

    private var backgroundView: some View {
        ZStack {
            RadialGradient(
                colors: [
                    Color(red: 0.10, green: 0.11, blue: 0.22),
                    Color(red: 0.05, green: 0.05, blue: 0.12),
                    Color(red: 0.03, green: 0.03, blue: 0.08)
                ],
                center: .center,
                startRadius: 100,
                endRadius: 800
            )
            .ignoresSafeArea()

            // Subtle glowing background orbs
            Circle()
                .fill(RadialGradient(colors: [Color.purple.opacity(0.18), .clear], center: .center, startRadius: 0, endRadius: 260))
                .frame(width: 520, height: 520)
                .offset(x: -240, y: -160)
                .blur(radius: 50)

            Circle()
                .fill(RadialGradient(colors: [Color.blue.opacity(0.14), .clear], center: .center, startRadius: 0, endRadius: 220))
                .frame(width: 440, height: 440)
                .offset(x: 280, y: 200)
                .blur(radius: 50)
        }
    }

    // MARK: - Canvas Drawing

    private func drawGraph(context: GraphicsContext, size: CGSize) {
        let activeNodes = getFilteredNodes()
        let activeIds = Set(activeNodes.map { $0.id })

        let selectedId = selectedNode?.id
        let neighborIds = selectedId != nil ? Set(engine.getNeighbors(for: selectedId!).map { $0.id }) : Set<String>()

        // 1. Draw Links
        for link in engine.links {
            guard activeIds.contains(link.sourceId), activeIds.contains(link.targetId) else { continue }
            guard let srcNode = engine.nodes.first(where: { $0.id == link.sourceId }),
                  let tgtNode = engine.nodes.first(where: { $0.id == link.targetId }) else { continue }

            let p1 = toScreenCoords(srcNode.position)
            let p2 = toScreenCoords(tgtNode.position)

            var isHighlighted = false
            var opacity: Double = 0.22

            if let sel = selectedId {
                if link.sourceId == sel || link.targetId == sel {
                    isHighlighted = true
                    opacity = 0.85
                } else {
                    opacity = 0.05
                }
            }

            var path = Path()
            path.move(to: p1)
            path.addLine(to: p2)

            let strokeColor = isHighlighted ? Color(red: 0.66, green: 0.33, blue: 0.97) : Color.white
            context.stroke(
                path,
                with: .color(strokeColor.opacity(opacity)),
                lineWidth: isHighlighted ? 2.2 : 1.0
            )
        }

        // 2. Draw Nodes
        for node in activeNodes {
            let screenPos = toScreenCoords(node.position)
            let r = node.semanticType.baseRadius * zoomScale

            let isSelected = node.id == selectedId
            let isNeighbor = neighborIds.contains(node.id)
            let isSearchMatch = isMatch(node)

            var nodeOpacity: Double = 1.0
            if selectedId != nil && !isSelected && !isNeighbor {
                nodeOpacity = 0.2
            }
            if !searchQuery.isEmpty && !isSearchMatch {
                nodeOpacity = min(nodeOpacity, 0.15)
            }

            // Glow Aura for Selected or Dream nodes
            if isSelected || node.semanticType == .reflection {
                let auraRadius = r + (isSelected ? 14 : 8) * zoomScale
                let auraPath = Path(ellipseIn: CGRect(x: screenPos.x - auraRadius, y: screenPos.y - auraRadius, width: auraRadius * 2, height: auraRadius * 2))
                context.fill(auraPath, with: .color(node.semanticType.color.opacity(0.35 * nodeOpacity)))
            }

            // Solid Node Circle
            let nodePath = Path(ellipseIn: CGRect(x: screenPos.x - r, y: screenPos.y - r, width: r * 2, height: r * 2))
            context.fill(nodePath, with: .color(node.semanticType.color.opacity(nodeOpacity)))

            // Ring stroke
            let strokeWidth: CGFloat = isSelected ? 3.0 : 1.5
            let strokeColor: Color = isSelected ? .white : Color.white.opacity(0.4)
            context.stroke(nodePath, with: .color(strokeColor.opacity(nodeOpacity)), lineWidth: strokeWidth)

            // Dynamic Text Label
            let title = node.displayTitle
            if zoomScale > 0.45 || isSelected || isSearchMatch {
                let text = Text(title)
                    .font(.system(size: max(10, 11 * zoomScale), weight: isSelected ? .bold : .medium, design: .rounded))
                    .foregroundColor(Color.white.opacity(nodeOpacity))

                context.draw(text, at: CGPoint(x: screenPos.x, y: screenPos.y + r + 12 * zoomScale))
            }
        }
    }

    private func toScreenCoords(_ point: CGPoint) -> CGPoint {
        CGPoint(
            x: point.x * zoomScale + panOffset.x,
            y: point.y * zoomScale + panOffset.y
        )
    }

    private func toCanvasCoords(_ point: CGPoint) -> CGPoint {
        CGPoint(
            x: (point.x - panOffset.x) / zoomScale,
            y: (point.y - panOffset.y) / zoomScale
        )
    }

    // MARK: - Drag & Hit Testing

    private func handleDragChanged(value: DragGesture.Value, size: CGSize) {
        if let dragId = draggedNodeId {
            let canvasPos = toCanvasCoords(value.location)
            engine.dragNode(id: dragId, to: canvasPos)
        } else if value.translation.width == 0 && value.translation.height == 0 {
            // Initial press: check if hitting a node
            if let hit = engine.findNode(at: value.startLocation, zoom: zoomScale, offset: panOffset) {
                draggedNodeId = hit.id
                selectedNode = hit
                let canvasPos = toCanvasCoords(value.location)
                engine.dragNode(id: hit.id, to: canvasPos)
            }
        } else {
            // Panning the canvas
            panOffset.x += value.translation.width - lastDragOffset.x
            panOffset.y += value.translation.height - lastDragOffset.y
            lastDragOffset = CGPoint(x: value.translation.width, y: value.translation.height)
        }
    }

    private func handleDragEnded(value: DragGesture.Value) {
        if let dragId = draggedNodeId {
            engine.releaseNode(id: dragId)
            draggedNodeId = nil
        } else if abs(value.translation.width) < 4 && abs(value.translation.height) < 4 {
            // Tap detected
            if let hit = engine.findNode(at: value.startLocation, zoom: zoomScale, offset: panOffset) {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    selectedNode = hit
                }
            } else {
                withAnimation(.easeOut(duration: 0.2)) {
                    selectedNode = nil
                }
            }
        }
        lastDragOffset = .zero
    }

    // MARK: - Filter & Search Helpers

    private func getFilteredNodes() -> [GraphNode] {
        if let filter = currentFilter {
            return engine.nodes.filter { $0.semanticType == filter }
        }
        return engine.nodes
    }

    private func isMatch(_ node: GraphNode) -> Bool {
        guard !searchQuery.isEmpty else { return true }
        let q = searchQuery.lowercased()
        if node.displayTitle.lowercased().contains(q) { return true }
        if let r = node.rationale, r.lowercased().contains(q) { return true }
        if let v = node.verdict, v.lowercased().contains(q) { return true }
        if let s = node.synthesis, s.lowercased().contains(q) { return true }
        return false
    }

    private func selectNodeAndCenter(_ node: GraphNode, size: CGSize) {
        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
            selectedNode = node
            panOffset = CGPoint(
                x: size.width / 2 - node.position.x * zoomScale,
                y: size.height / 2 - node.position.y * zoomScale
            )
        }
    }

    // MARK: - Top Toolbar

    private var topToolbar: some View {
        HStack(spacing: 14) {
            // Brand & Title
            HStack(spacing: 10) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 0.66, green: 0.33, blue: 0.97), Color(red: 0.23, green: 0.51, blue: 0.96)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                VStack(alignment: .leading, spacing: 2) {
                    Text("Memory Knowledge Graph")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("Cognitive semantic relationships")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.5))
                }
            }

            Spacer()

            // Search box
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 13))
                    .foregroundColor(.white.opacity(0.5))

                TextField("Search decisions, people, topics...", text: $searchQuery)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13))
                    .foregroundColor(.white)

                if !searchQuery.isEmpty {
                    Button {
                        searchQuery = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 13))
                            .foregroundColor(.white.opacity(0.5))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .frame(width: 280)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.08))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.12), lineWidth: 1))
            )

            // Zoom Controls
            HStack(spacing: 4) {
                IconButton(icon: "minus.magnifyingglass") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        zoomScale = max(0.3, zoomScale - 0.2)
                    }
                }
                IconButton(icon: "plus.magnifyingglass") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        zoomScale = min(3.0, zoomScale + 0.2)
                    }
                }
                IconButton(icon: "arrow.counterclockwise") {
                    withAnimation(.easeInOut(duration: 0.3)) {
                        zoomScale = 1.0
                        panOffset = .zero
                        engine.reheat()
                    }
                }
            }

            // Refresh from backend
            IconButton(icon: isLoading ? "arrow.triangle.2.circlepath" : "arrow.clockwise") {
                loadGraph(in: CGSize(width: 1000, height: 700))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(red: 0.08, green: 0.09, blue: 0.18).opacity(0.85))
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.12), lineWidth: 1))
        )
    }

    // MARK: - Filter Bar

    private var filterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                FilterChip(
                    title: "All",
                    count: engine.nodes.count,
                    isSelected: currentFilter == nil,
                    color: Color(red: 0.66, green: 0.33, blue: 0.97)
                ) {
                    currentFilter = nil
                }

                ForEach(SemanticNodeType.allCases.filter { $0 != .other }) { type in
                    let count = engine.nodes.filter { $0.semanticType == type }.count
                    if count > 0 {
                        FilterChip(
                            title: type.displayName,
                            count: count,
                            isSelected: currentFilter == type,
                            color: type.color
                        ) {
                            currentFilter = (currentFilter == type) ? nil : type
                        }
                    }
                }
            }
        }
    }

    // MARK: - Bottom Status Bar

    private var bottomStatusBar: some View {
        HStack(spacing: 16) {
            Label("\(engine.nodes.count) Nodes", systemImage: "circle.hexagongrid.fill")
            Label("\(engine.links.count) Relations", systemImage: "point.3.filled.connected.trianglepath.dotted")

            if engine.isSimulating {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.6)
                    Text("Physics Active")
                }
            }

            Spacer()

            Text("Scroll or drag canvas to navigate • Click nodes for details")
                .foregroundColor(.white.opacity(0.4))
        }
        .font(.system(size: 11, weight: .medium))
        .foregroundColor(.white.opacity(0.6))
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(red: 0.08, green: 0.09, blue: 0.18).opacity(0.8))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.white.opacity(0.08), lineWidth: 1))
        )
    }

    // MARK: - Load Graph Data

    private func loadGraph(in size: CGSize) {
        isLoading = true
        Task {
            do {
                let payload = try await APIClient.shared.fetchGraphData()
                let nodes = payload.nodes.map { $0.toGraphNode() }
                let links = payload.links.enumerated().map { $0.element.toGraphLink(index: $0.offset) }

                await MainActor.run {
                    engine.setGraph(nodes: nodes, links: links, in: size)
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Subviews & Controls

struct FilterChip: View {
    let title: String
    let count: Int
    let isSelected: Bool
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Text(title)
                    .font(.system(size: 12, weight: isSelected ? .bold : .medium))

                Text("\(count)")
                    .font(.system(size: 10, weight: .bold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.white.opacity(isSelected ? 0.25 : 0.12))
                    .clipShape(Capsule())
            }
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                Capsule()
                    .fill(isSelected ? color : Color.white.opacity(0.08))
                    .overlay(Capsule().stroke(Color.white.opacity(isSelected ? 0.3 : 0.08), lineWidth: 1))
            )
        }
        .buttonStyle(.plain)
    }
}

struct IconButton: View {
    let icon: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.white.opacity(0.8))
                .frame(width: 32, height: 32)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.white.opacity(0.08))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.white.opacity(0.1), lineWidth: 1))
                )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Cognitive Inspector View

struct CognitiveInspectorView: View {
    let node: GraphNode
    let neighbors: [GraphNode]
    let onSelectNeighbor: (GraphNode) -> Void
    let onClose: () -> Void

    @State private var showRawData = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            HStack(alignment: .top) {
                Image(systemName: node.semanticType.iconName)
                    .font(.system(size: 20))
                    .foregroundColor(node.semanticType.color)
                    .frame(width: 42, height: 42)
                    .background(node.semanticType.color.opacity(0.18))
                    .clipShape(RoundedRectangle(cornerRadius: 12))

                VStack(alignment: .leading, spacing: 4) {
                    Text(node.semanticType.displayName.uppercased())
                        .font(.system(size: 10, weight: .bold, design: .rounded))
                        .foregroundColor(node.semanticType.color)
                        .tracking(0.5)

                    Text(node.displayTitle)
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                        .lineLimit(2)
                }

                Spacer()

                Button(action: onClose) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 18))
                        .foregroundColor(.white.opacity(0.5))
                }
                .buttonStyle(.plain)
            }

            Divider()
                .background(Color.white.opacity(0.1))

            // Scrollable Content
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 14) {
                    // Cognitive Section (Semantic specific)
                    cognitiveSection

                    // Connected Neighbors
                    if !neighbors.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("CONNECTED ENTITIES (\(neighbors.count))")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.white.opacity(0.5))
                                .tracking(0.5)

                            FlowLayout(spacing: 6) {
                                ForEach(neighbors) { neighbor in
                                    Button {
                                        onSelectNeighbor(neighbor)
                                    } label: {
                                        HStack(spacing: 5) {
                                            Circle()
                                                .fill(neighbor.semanticType.color)
                                                .frame(width: 7, height: 7)
                                            Text(neighbor.displayTitle)
                                                .font(.system(size: 11, weight: .medium))
                                                .foregroundColor(.white)
                                        }
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 5)
                                        .background(
                                            Capsule()
                                                .fill(Color.white.opacity(0.08))
                                                .overlay(Capsule().stroke(Color.white.opacity(0.1), lineWidth: 1))
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }

                    // Collapsible Raw Neo4j Attributes
                    DisclosureGroup(isExpanded: $showRawData) {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(node.rawAttributes.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
                                HStack(alignment: .top) {
                                    Text(key)
                                        .font(.system(size: 10, weight: .medium))
                                        .foregroundColor(.white.opacity(0.4))
                                        .frame(width: 80, alignment: .leading)
                                    Text(val)
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(.white.opacity(0.8))
                                }
                            }
                        }
                        .padding(.top, 8)
                    } label: {
                        Text("Technical Graph Attributes")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.white.opacity(0.5))
                    }
                }
            }
        }
        .padding(20)
        .frame(width: 360)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color(red: 0.09, green: 0.10, blue: 0.20).opacity(0.92))
                .overlay(RoundedRectangle(cornerRadius: 20).stroke(Color.white.opacity(0.15), lineWidth: 1))
                .shadow(color: .black.opacity(0.5), radius: 30, x: 0, y: 10)
        )
    }

    @ViewBuilder
    private var cognitiveSection: some View {
        switch node.semanticType {
        case .decision:
            if let verdict = node.verdict {
                InfoBadge(label: "VERDICT", value: verdict, color: .green)
            }
            if let rationale = node.rationale {
                InfoBlock(label: "RATIONALE", value: rationale)
            }

        case .commitment:
            if let task = node.task {
                InfoBlock(label: "TASK / DELIVERABLE", value: task)
            }
            if let due = node.dueDate {
                InfoBadge(label: "DUE DATE", value: due, color: .orange)
            }

        case .reflection:
            if let synthesis = node.synthesis {
                InfoBlock(label: "STRATEGIC SYNTHESIS", value: synthesis)
            }
            if let suggestion = node.actionableSuggestion {
                InfoBlock(label: "ACTIONABLE RECOMMENDATION", value: suggestion, highlight: true)
            }

        case .meeting:
            InfoBlock(label: "ACTIVITY", value: "Meeting session captured from calendar and screen context.")

        case .person:
            InfoBlock(label: "COLLABORATOR", value: "Active collaborator involved in decisions and commitments.")

        case .topic:
            InfoBlock(label: "TOPIC", value: "Knowledge cluster connecting activities, documents, and discussions.")

        default:
            if let takeaway = node.takeaway {
                InfoBlock(label: "TAKEAWAY", value: takeaway)
            }
        }
    }
}

// MARK: - Info Display Components

struct InfoBadge: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(.white.opacity(0.4))
                .tracking(0.5)

            Text(value)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundColor(color)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(color.opacity(0.15))
                .clipShape(Capsule())
        }
    }
}

struct InfoBlock: View {
    let label: String
    let value: String
    var highlight: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(.white.opacity(0.4))
                .tracking(0.5)

            Text(value)
                .font(.system(size: 12, weight: .regular))
                .lineSpacing(3)
                .foregroundColor(.white.opacity(0.9))
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(highlight ? Color.purple.opacity(0.15) : Color.white.opacity(0.04))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(highlight ? Color.purple.opacity(0.3) : Color.white.opacity(0.08), lineWidth: 1))
                )
        }
    }
}

// Simple Flow Layout for tags
struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 300
        var height: CGFloat = 0
        var currentX: CGFloat = 0
        var currentY: CGFloat = 0
        var maxHeightInRow: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX + size.width > width && currentX > 0 {
                currentX = 0
                currentY += maxHeightInRow + spacing
                maxHeightInRow = 0
            }
            maxHeightInRow = max(maxHeightInRow, size.height)
            currentX += size.width + spacing
        }
        height = currentY + maxHeightInRow
        return CGSize(width: width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var currentX = bounds.minX
        var currentY = bounds.minY
        var maxHeightInRow: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX + size.width > bounds.maxX && currentX > bounds.minX {
                currentX = bounds.minX
                currentY += maxHeightInRow + spacing
                maxHeightInRow = 0
            }
            subview.place(at: CGPoint(x: currentX, y: currentY), proposal: .unspecified)
            maxHeightInRow = max(maxHeightInRow, size.height)
            currentX += size.width + spacing
        }
    }
}
