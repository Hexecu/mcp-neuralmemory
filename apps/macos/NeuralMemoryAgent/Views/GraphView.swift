// GraphView.swift
// Native SwiftUI Temporal Knowledge Graph Visualizer with timeline stream, multi-hub clusters & cognitive inspector

import SwiftUI

struct GraphView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var engine = GraphPhysicsEngine()

    // Sample data configuration
    private let initialSampleNodes: [GraphNode]?
    private let initialSampleLinks: [GraphLink]?
    private let initialLayoutMode: GraphLayoutMode
    private let initialSelectedId: String?

    // Selection & Hit Testing
    @State private var selectedNode: GraphNode?
    @State private var draggedNodeId: String?

    // Filter & Search
    @State private var currentFilter: SemanticNodeType? = nil
    @State private var searchQuery: String = ""

    // Temporal Scrubbing
    @State private var isPlayingTime: Bool = false
    @State private var scrubProgress: Double = 1.0 // 0.0 to 1.0
    @State private var timeTimer: Timer? = nil

    // Navigation transform
    @State private var zoomScale: CGFloat = 1.0
    @State private var panOffset: CGPoint = .zero
    @State private var lastDragOffset: CGPoint = .zero

    // Loading & status
    @State private var isLoading = false
    @State private var errorMessage: String?

    init(
        sampleNodes: [GraphNode]? = nil,
        sampleLinks: [GraphLink]? = nil,
        layoutMode: GraphLayoutMode = .cluster,
        selectedNodeId: String? = nil
    ) {
        self.initialSampleNodes = sampleNodes
        self.initialSampleLinks = sampleLinks
        self.initialLayoutMode = layoutMode
        self.initialSelectedId = selectedNodeId
        _selectedNode = State(initialValue: sampleNodes?.first(where: { $0.id == selectedNodeId }))
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Cosmic dark-glass background
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

                // Top Floating Toolbar: Brand, Layout Modes, Search, Settings
                VStack {
                    topToolbar
                        .padding(.top, 16)
                        .padding(.horizontal, 20)

                    filterBar
                        .padding(.top, 8)
                        .padding(.horizontal, 20)

                    Spacer()

                    // Bottom Temporal Scrubber & Controls
                    temporalScrubberBar
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
        .frame(minWidth: 960, minHeight: 680)
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
        let activeNodes = getActiveAndFilteredNodes()
        let activeIds = Set(activeNodes.map { $0.id })

        let selectedId = selectedNode?.id
        let neighborIds = selectedId != nil ? Set(engine.getNeighbors(for: selectedId!).map { $0.id }) : Set<String>()

        // 1. Draw Timeline Lanes (if Timeline mode)
        if engine.layoutMode == .timeline {
            drawTimelineLanes(context: context, size: size)
        }

        // 2. Draw Links
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
                    opacity = 0.04
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

        // 3. Draw Nodes with Temporal Glow
        for node in activeNodes {
            let screenPos = toScreenCoords(node.position)
            let r = node.semanticType.baseRadius * zoomScale

            let isSelected = node.id == selectedId
            let isNeighbor = neighborIds.contains(node.id)
            let isSearchMatch = isMatch(node)
            let recency = node.recencyScore()

            var nodeOpacity: Double = max(0.4, recency)
            if selectedId != nil && !isSelected && !isNeighbor {
                nodeOpacity = 0.15
            }
            if !searchQuery.isEmpty && !isSearchMatch {
                nodeOpacity = min(nodeOpacity, 0.12)
            }

            // Glow Aura for Selected, Reflection, or High Recency
            if isSelected || node.semanticType == .reflection || recency > 0.8 {
                let auraRadius = r + (isSelected ? 14 : 6) * zoomScale
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

    private func drawTimelineLanes(context: GraphicsContext, size: CGSize) {
        let lanes: [(title: String, y: CGFloat, color: Color)] = [
            ("DREAM REFLECTIONS", 130, Color(red: 0.93, green: 0.28, blue: 0.60)),
            ("DECISIONS", 240, Color(red: 0.06, green: 0.73, blue: 0.51)),
            ("MEETINGS", 350, Color(red: 0.23, green: 0.51, blue: 0.96)),
            ("COMMITMENTS", 460, Color(red: 0.96, green: 0.62, blue: 0.04)),
            ("TOPICS & COLLABORATORS", 570, Color(red: 0.66, green: 0.33, blue: 0.97))
        ]

        for lane in lanes {
            let screenY = lane.y * zoomScale + panOffset.y
            var linePath = Path()
            linePath.move(to: CGPoint(x: 20, y: screenY))
            linePath.addLine(to: CGPoint(x: size.width - 20, y: screenY))
            context.stroke(linePath, with: .color(Color.white.opacity(0.06)), lineWidth: 1)

            let label = Text(lane.title)
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundColor(lane.color.opacity(0.45))
            context.draw(label, at: CGPoint(x: 100, y: screenY - 10))
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
            if let hit = engine.findNode(at: value.startLocation, zoom: zoomScale, offset: panOffset) {
                draggedNodeId = hit.id
                selectedNode = hit
                let canvasPos = toCanvasCoords(value.location)
                engine.dragNode(id: hit.id, to: canvasPos)
            }
        } else {
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

    private func getActiveAndFilteredNodes() -> [GraphNode] {
        let scrubDate = computeScrubDate()
        var nodes = engine.getActiveNodes(timeRange: engine.timeFilter, scrubDate: scrubDate)

        if let filter = currentFilter {
            nodes = nodes.filter { $0.semanticType == filter }
        }
        return nodes
    }

    private func computeScrubDate() -> Date? {
        guard scrubProgress < 0.99 else { return nil }
        let dates = engine.nodes.compactMap { $0.timestamp }
        guard let minDate = dates.min(), let maxDate = dates.max(), minDate < maxDate else { return nil }
        let span = maxDate.timeIntervalSince(minDate)
        return minDate.addingTimeInterval(span * scrubProgress)
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
                    Text("Temporal Knowledge Graph")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("Multi-hub cognitive architecture")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.5))
                }
            }

            Spacer()

            // Layout Mode Switcher (Cluster / Timeline / Force)
            HStack(spacing: 2) {
                ForEach(GraphLayoutMode.allCases) { mode in
                    Button {
                        engine.setLayoutMode(mode)
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: mode.iconName)
                                .font(.system(size: 11))
                            Text(mode.displayName)
                                .font(.system(size: 11, weight: engine.layoutMode == mode ? .bold : .medium))
                        }
                        .foregroundColor(engine.layoutMode == mode ? .white : .white.opacity(0.6))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(engine.layoutMode == mode ? Color.purple.opacity(0.4) : Color.clear)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(3)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.white.opacity(0.06))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.white.opacity(0.1), lineWidth: 1))
            )

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
            .frame(width: 220)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.08))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.12), lineWidth: 1))
            )

            // Zoom & View Controls
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

            // Settings Window Button (Opens unified configuration)
            IconButton(icon: "gear") {
                if let appDelegate = NSApp.delegate as? AppDelegate {
                    Task { @MainActor in
                        appDelegate.showSettingsWindow()
                    }
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(red: 0.08, green: 0.09, blue: 0.18).opacity(0.88))
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

    // MARK: - Bottom Temporal Scrubber Bar

    private var temporalScrubberBar: some View {
        HStack(spacing: 16) {
            // Time Range Presets
            HStack(spacing: 4) {
                ForEach(TimeFilterRange.allCases) { range in
                    Button {
                        engine.timeFilter = range
                        scrubProgress = 1.0
                    } label: {
                        Text(range.rawValue)
                            .font(.system(size: 10, weight: engine.timeFilter == range ? .bold : .medium))
                            .foregroundColor(engine.timeFilter == range ? .white : .white.opacity(0.6))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(
                                Capsule()
                                    .fill(engine.timeFilter == range ? Color.purple.opacity(0.4) : Color.clear)
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(3)
            .background(Capsule().fill(Color.white.opacity(0.06)))

            Divider()
                .frame(height: 18)
                .background(Color.white.opacity(0.15))

            // Play/Pause button for time-travel replay
            Button {
                toggleTimePlay()
            } label: {
                Image(systemName: isPlayingTime ? "pause.fill" : "play.fill")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.white)
                    .frame(width: 24, height: 24)
                    .background(Circle().fill(Color.purple.opacity(0.5)))
            }
            .buttonStyle(.plain)

            // Continuous Time Slider
            HStack(spacing: 8) {
                Image(systemName: "clock.arrow.circlepath")
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.5))

                Slider(value: $scrubProgress, in: 0.05...1.0)
                    .tint(Color.purple)

                Text(scrubDateLabel)
                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                    .foregroundColor(.white.opacity(0.8))
                    .frame(width: 140, alignment: .leading)
            }

            Spacer()

            // Active count indicator
            HStack(spacing: 6) {
                Circle()
                    .fill(Color.green)
                    .frame(width: 6, height: 6)
                Text("\(getActiveAndFilteredNodes().count)/\(engine.nodes.count) Nodes")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white.opacity(0.7))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(red: 0.08, green: 0.09, blue: 0.18).opacity(0.9))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.white.opacity(0.1), lineWidth: 1))
        )
    }

    private var scrubDateLabel: String {
        if scrubProgress >= 0.99 {
            return "Now (Latest)"
        }
        if let d = computeScrubDate() {
            let formatter = DateFormatter()
            formatter.dateFormat = "dd/MM HH:mm"
            return formatter.string(from: d)
        }
        return "Time Horizon"
    }

    private func toggleTimePlay() {
        if isPlayingTime {
            isPlayingTime = false
            timeTimer?.invalidate()
            timeTimer = nil
        } else {
            if scrubProgress >= 0.98 { scrubProgress = 0.05 }
            isPlayingTime = true
            timeTimer = Timer.scheduledTimer(withTimeInterval: 0.08, repeats: true) { _ in
                if scrubProgress < 1.0 {
                    scrubProgress += 0.02
                } else {
                    isPlayingTime = false
                    timeTimer?.invalidate()
                    timeTimer = nil
                }
            }
        }
    }

    // MARK: - Load Graph Data

    private func loadGraph(in size: CGSize) {
        if let sampleNodes = initialSampleNodes, let sampleLinks = initialSampleLinks, !sampleNodes.isEmpty {
            engine.layoutMode = initialLayoutMode
            engine.setGraph(nodes: sampleNodes, links: sampleLinks, in: size)
            for _ in 0..<60 {
                engine.step()
            }
            if let selId = initialSelectedId {
                selectedNode = engine.nodes.first(where: { $0.id == selId })
            }
            return
        }

        isLoading = true
        Task {
            do {
                let payload = try await APIClient.shared.fetchGraphData()
                var nodes = payload.nodes.map { $0.toGraphNode() }
                var links = payload.links.enumerated().map { $0.element.toGraphLink(index: $0.offset) }

                if nodes.isEmpty {
                    let showcase = Self.showcaseData()
                    nodes = showcase.nodes
                    links = showcase.links
                }

                await MainActor.run {
                    engine.setGraph(nodes: nodes, links: links, in: size)
                    for _ in 0..<30 {
                        engine.step()
                    }
                    if let firstDecision = nodes.first(where: { $0.semanticType == .decision }) {
                        selectedNode = firstDecision
                    }
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    let showcase = Self.showcaseData()
                    engine.setGraph(nodes: showcase.nodes, links: showcase.links, in: size)
                    for _ in 0..<30 {
                        engine.step()
                    }
                    selectedNode = showcase.nodes.first(where: { $0.semanticType == .decision })
                    isLoading = false
                }
            }
        }
    }

    // MARK: - Showcase Mock Data
    static func showcaseData() -> (nodes: [GraphNode], links: [GraphLink]) {
        let now = Date()
        let hour: TimeInterval = 3600
        let day: TimeInterval = 86400

        let nodes: [GraphNode] = [
            // Topics
            GraphNode(id: "t-cloud", labels: ["Topic"], name: "Cloud Infrastructure Q4", timestamp: now - 3 * day),
            GraphNode(id: "t-agent", labels: ["Topic"], name: "Autonomous Desktop Agent", timestamp: now - 2 * day),
            GraphNode(id: "t-privacy", labels: ["Topic"], name: "Security & PrivacyShield", timestamp: now - 1 * day),
            GraphNode(id: "t-product", labels: ["Topic"], name: "Product Roadmap 2026", timestamp: now - 4 * day),

            // Decisions
            GraphNode(
                id: "d-cloud",
                labels: ["Decision"],
                title: "Approved Cloud Q4 Proposal 5,000€",
                verdict: "APPROVED",
                rationale: "Approved dedicated GPU inference servers based on latency benchmarks from Marco Rossi.",
                timestamp: now - 2 * hour
            ),
            GraphNode(
                id: "d-storage",
                labels: ["Decision"],
                title: "Adopt SQLite WAL Property Engine",
                verdict: "APPROVED",
                rationale: "Selected embedded zero-docker SQLite for standalone MacBook distribution.",
                timestamp: now - 5 * hour
            ),
            GraphNode(
                id: "d-privacy",
                labels: ["Decision"],
                title: "Enforce Luhn CC & IBAN Redaction",
                verdict: "APPROVED",
                rationale: "Zero plaintext persistence of sensitive financial credentials.",
                timestamp: now - 1 * day
            ),

            // Commitments
            GraphNode(
                id: "c-slides",
                labels: ["Commitment"],
                task: "Send updated slide deck to Marco Rossi",
                dueDate: "Tomorrow, 18:00",
                timestamp: now - 3 * hour
            ),
            GraphNode(
                id: "c-review",
                labels: ["Commitment"],
                task: "Review PR for Temporal Physics Engine",
                dueDate: "Friday, 15:00",
                timestamp: now - 6 * hour
            ),
            GraphNode(
                id: "c-demo",
                labels: ["Commitment"],
                task: "Prepare executive briefing demo for team",
                dueDate: "Monday, 10:00",
                timestamp: now - 2 * day
            ),

            // Meetings
            GraphNode(
                id: "m-arch",
                labels: ["Meeting"],
                title: "Architecture Sync w/ Marco & Sara",
                takeaway: "Agreed on Dual-Track packaging and standalone SQLite store.",
                timestamp: now - 4 * hour
            ),
            GraphNode(
                id: "m-sec",
                labels: ["Meeting"],
                title: "Security Review & PrivacyShield",
                takeaway: "Validated regex patterns and deny-list for password vaults.",
                timestamp: now - 1 * day
            ),

            // Reflections
            GraphNode(
                id: "r-synthesis",
                labels: ["Reflection"],
                title: "Weekly Milestone Synthesis",
                synthesis: "Synthesized 3 major architectural decisions: local privacy shield, standalone DMG, and orbital temporal graph.",
                actionableSuggestion: "Publish standalone release and documentation site.",
                timestamp: now - 1 * hour
            ),
            GraphNode(
                id: "r-workflow",
                labels: ["Reflection"],
                title: "Workflow Optimization Insight",
                synthesis: "Micro-feedback assent capture saves an average of 45 minutes daily in manual note-taking.",
                actionableSuggestion: "Expand multimodal bundle triggers to Slack and terminal.",
                timestamp: now - 12 * hour
            ),

            // People
            GraphNode(id: "p-marco", labels: ["Person"], name: "Marco Rossi", timestamp: now - 3 * day),
            GraphNode(id: "p-sara", labels: ["Person"], name: "Sara Bianchi", timestamp: now - 2 * day),

            // Artifacts
            GraphNode(id: "a-proposal", labels: ["Artifact"], title: "Cloud_Proposal_v2.pdf", timestamp: now - 2 * hour),
            GraphNode(id: "a-spec", labels: ["Artifact"], title: "architecture_spec.md", timestamp: now - 5 * hour)
        ]

        let links: [GraphLink] = [
            GraphLink(id: "l1", sourceId: "d-cloud", targetId: "t-cloud", relType: "ABOUT_TOPIC"),
            GraphLink(id: "l2", sourceId: "d-cloud", targetId: "p-marco", relType: "TOWARDS_PERSON"),
            GraphLink(id: "l3", sourceId: "d-cloud", targetId: "a-proposal", relType: "ON_ARTIFACT"),
            GraphLink(id: "l4", sourceId: "d-storage", targetId: "t-agent", relType: "ABOUT_TOPIC"),
            GraphLink(id: "l5", sourceId: "d-privacy", targetId: "t-privacy", relType: "ABOUT_TOPIC"),
            GraphLink(id: "l6", sourceId: "c-slides", targetId: "p-marco", relType: "PROMISED_TO"),
            GraphLink(id: "l7", sourceId: "c-slides", targetId: "t-cloud", relType: "ABOUT_TOPIC"),
            GraphLink(id: "l8", sourceId: "c-review", targetId: "t-agent", relType: "ABOUT_TOPIC"),
            GraphLink(id: "l9", sourceId: "m-arch", targetId: "p-marco", relType: "ATTENDED"),
            GraphLink(id: "l10", sourceId: "m-arch", targetId: "p-sara", relType: "ATTENDED"),
            GraphLink(id: "l11", sourceId: "m-arch", targetId: "t-agent", relType: "DISCUSSED"),
            GraphLink(id: "l12", sourceId: "m-sec", targetId: "p-sara", relType: "ATTENDED"),
            GraphLink(id: "l13", sourceId: "m-sec", targetId: "t-privacy", relType: "DISCUSSED"),
            GraphLink(id: "l14", sourceId: "r-synthesis", targetId: "t-agent", relType: "DERIVED_FROM"),
            GraphLink(id: "l15", sourceId: "r-synthesis", targetId: "t-cloud", relType: "DERIVED_FROM"),
            GraphLink(id: "l16", sourceId: "r-workflow", targetId: "t-agent", relType: "DERIVED_FROM"),
            GraphLink(id: "l17", sourceId: "d-storage", targetId: "a-spec", relType: "ON_ARTIFACT")
        ]

        return (nodes, links)
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

                    // Temporal Timestamp Banner
                    if let ts = node.timestamp {
                        HStack(spacing: 8) {
                            Image(systemName: "calendar.badge.clock")
                                .font(.system(size: 12))
                                .foregroundColor(.purple)
                            Text("Observed: \(formattedDate(ts))")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundColor(.white.opacity(0.8))
                        }
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 8).fill(Color.purple.opacity(0.12)))
                    }

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

    private func formattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd/MM/yyyy HH:mm"
        return formatter.string(from: date)
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
