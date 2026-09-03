// GraphPhysicsEngine.swift
// High-performance 2D Temporal & Multi-Hub Physics Engine for Neural Memory Graph

import SwiftUI
import Combine

@MainActor
class GraphPhysicsEngine: ObservableObject {
    @Published var nodes: [GraphNode] = []
    @Published var links: [GraphLink] = []
    @Published var alpha: CGFloat = 1.0
    @Published var isSimulating: Bool = false

    // Layout Mode & Temporal Scrubbing
    @Published var layoutMode: GraphLayoutMode = .cluster
    @Published var timeFilter: TimeFilterRange = .all
    @Published var timeScrubDate: Date? = nil

    private var nodeIndexMap: [String: Int] = [:]
    private var center: CGPoint = CGPoint(x: 500, y: 350)
    private var canvasSize: CGSize = CGSize(width: 1000, height: 700)
    private var topicAnchors: [String: CGPoint] = [:]

    // Physics parameters
    let repulsionConstant: CGFloat = 2800.0
    let springConstant: CGFloat = 0.05
    let restingDistance: CGFloat = 90.0
    let centerGravity: CGFloat = 0.012
    let damping: CGFloat = 0.85
    let minDistance: CGFloat = 25.0

    func setGraph(nodes: [GraphNode], links: [GraphLink], in size: CGSize) {
        self.canvasSize = size
        self.center = CGPoint(x: size.width / 2, y: size.height / 2)
        var initializedNodes = nodes

        // Compute topic regional anchor positions
        let topicNodes = initializedNodes.filter { $0.semanticType == .topic }
        var anchors: [String: CGPoint] = [:]
        let topicCount = max(1, topicNodes.count)
        let clusterRadius: CGFloat = min(size.width, size.height) * 0.32

        for (idx, topic) in topicNodes.enumerated() {
            let angle = (Double(idx) / Double(topicCount)) * 2.0 * Double.pi
            let ax = center.x + clusterRadius * CGFloat(cos(angle))
            let ay = center.y + clusterRadius * CGFloat(sin(angle))
            anchors[topic.id] = CGPoint(x: ax, y: ay)
        }
        self.topicAnchors = anchors

        // Initial layout positioning
        let phi = (1.0 + sqrt(5.0)) / 2.0
        for i in 0..<initializedNodes.count {
            let node = initializedNodes[i]
            if let anchor = anchors[node.id] {
                initializedNodes[i].position = anchor
            } else {
                let theta = Double(i) * 2.0 * Double.pi * phi
                let r = 40.0 * sqrt(Double(i + 1))
                let x = center.x + CGFloat(r * cos(theta))
                let y = center.y + CGFloat(r * sin(theta))
                initializedNodes[i].position = CGPoint(x: x, y: y)
            }
            initializedNodes[i].velocity = .zero
        }

        self.nodes = initializedNodes
        self.links = links
        rebuildIndexMap()
        self.alpha = 1.0
        self.isSimulating = true
    }

    private func rebuildIndexMap() {
        var map: [String: Int] = [:]
        for (idx, node) in nodes.enumerated() {
            map[node.id] = idx
        }
        self.nodeIndexMap = map
    }

    func updateCenter(_ newCenter: CGPoint, size: CGSize) {
        self.center = newCenter
        self.canvasSize = size
    }

    func setLayoutMode(_ mode: GraphLayoutMode) {
        withAnimation(.easeInOut(duration: 0.3)) {
            self.layoutMode = mode
        }
        reheat()
    }

    func reheat() {
        self.alpha = 1.0
        self.isSimulating = true
    }

    func step() {
        guard isSimulating, alpha > 0.005 else {
            if isSimulating { isSimulating = false }
            return
        }

        let n = nodes.count
        guard n > 1 else { return }

        switch layoutMode {
        case .cluster:
            stepClusterMode(n: n)
        case .timeline:
            stepTimelineMode(n: n)
        case .force:
            stepForceMode(n: n)
        }

        // Velocity clamp and position update
        for i in 0..<n {
            if nodes[i].isFixed { continue }
            nodes[i].velocity.x = max(-30, min(30, nodes[i].velocity.x))
            nodes[i].velocity.y = max(-30, min(30, nodes[i].velocity.y))
            nodes[i].position.x += nodes[i].velocity.x
            nodes[i].position.y += nodes[i].velocity.y
        }

        // Alpha cooling
        alpha *= 0.988
    }

    // MARK: - Multi-Hub Regional Clustering

    private func stepClusterMode(n: Int) {
        applyRepulsion(n: n)
        applySpringAttraction()

        // Regional Anchor Gravity instead of single center
        for i in 0..<n {
            if nodes[i].isFixed { continue }
            let node = nodes[i]

            // If node has its own anchor (Topic)
            var targetCenter = center
            if let ownAnchor = topicAnchors[node.id] {
                targetCenter = ownAnchor
            } else {
                // Find connected topic anchor if any
                let connectedTopics = links.compactMap { link -> CGPoint? in
                    if link.sourceId == node.id { return topicAnchors[link.targetId] }
                    if link.targetId == node.id { return topicAnchors[link.sourceId] }
                    return nil
                }
                if let nearestAnchor = connectedTopics.first {
                    targetCenter = nearestAnchor
                }
            }

            let cdx = targetCenter.x - node.position.x
            let cdy = targetCenter.y - node.position.y
            nodes[i].velocity.x = (nodes[i].velocity.x + cdx * 0.025 * alpha) * damping
            nodes[i].velocity.y = (nodes[i].velocity.y + cdy * 0.025 * alpha) * damping
        }
    }

    // MARK: - Chronological Timeline Mode

    private func stepTimelineMode(n: Int) {
        // Collect valid date range
        let dates = nodes.compactMap { $0.timestamp }
        let minDate = dates.min() ?? Date(timeIntervalSinceNow: -86400 * 7)
        let maxDate = dates.max() ?? Date()
        let timeSpan = max(1.0, maxDate.timeIntervalSince(minDate))

        let paddingX: CGFloat = 120
        let availableWidth = max(200, canvasSize.width - paddingX * 2)

        for i in 0..<n {
            if nodes[i].isFixed { continue }
            let node = nodes[i]

            // Target X: chronological position along horizontal timeline
            let targetX: CGFloat
            if let ts = node.timestamp {
                let progress = CGFloat(ts.timeIntervalSince(minDate) / timeSpan)
                targetX = paddingX + progress * availableWidth
            } else {
                targetX = paddingX + availableWidth * 0.5
            }

            // Target Y: semantic lane
            let targetY = node.timelineLaneY

            let dx = targetX - node.position.x
            let dy = targetY - node.position.y

            // Strong spring towards timeline grid
            nodes[i].velocity.x = (nodes[i].velocity.x + dx * 0.08 * alpha) * damping
            nodes[i].velocity.y = (nodes[i].velocity.y + dy * 0.08 * alpha) * damping
        }

        // Gentle link attraction along timeline
        for link in links {
            guard let idx1 = nodeIndexMap[link.sourceId],
                  let idx2 = nodeIndexMap[link.targetId] else { continue }
            let p1 = nodes[idx1].position
            let p2 = nodes[idx2].position
            let dy = p2.y - p1.y
            let fy = dy * 0.01 * alpha
            if !nodes[idx1].isFixed { nodes[idx1].velocity.y += fy }
            if !nodes[idx2].isFixed { nodes[idx2].velocity.y -= fy }
        }
    }

    // MARK: - Free Force Mode

    private func stepForceMode(n: Int) {
        applyRepulsion(n: n)
        applySpringAttraction()

        for i in 0..<n {
            if nodes[i].isFixed { continue }
            let cdx = center.x - nodes[i].position.x
            let cdy = center.y - nodes[i].position.y
            nodes[i].velocity.x = (nodes[i].velocity.x + cdx * centerGravity * alpha) * damping
            nodes[i].velocity.y = (nodes[i].velocity.y + cdy * centerGravity * alpha) * damping
        }
    }

    // MARK: - Shared Physics Primitives

    private func applyRepulsion(n: Int) {
        let maxDist: CGFloat = 280.0
        let maxDistSq: CGFloat = maxDist * maxDist

        for i in 0..<n {
            if nodes[i].isFixed { continue }
            var fx: CGFloat = 0
            var fy: CGFloat = 0
            let p1 = nodes[i].position

            for j in 0..<n {
                if i == j { continue }
                let p2 = nodes[j].position
                var dx = p1.x - p2.x
                var dy = p1.y - p2.y

                if abs(dx) > maxDist || abs(dy) > maxDist { continue }

                var distSq = dx * dx + dy * dy
                if distSq > maxDistSq { continue }

                if distSq < 0.01 {
                    dx = CGFloat.random(in: -1...1)
                    dy = CGFloat.random(in: -1...1)
                    distSq = 1.0
                }

                let dist = max(sqrt(distSq), minDistance)
                let force = (repulsionConstant / (dist * dist)) * alpha
                fx += (dx / dist) * force
                fy += (dy / dist) * force
            }

            nodes[i].velocity.x += fx
            nodes[i].velocity.y += fy
        }
    }

    private func applySpringAttraction() {
        for link in links {
            guard let idx1 = nodeIndexMap[link.sourceId],
                  let idx2 = nodeIndexMap[link.targetId] else { continue }

            let p1 = nodes[idx1].position
            let p2 = nodes[idx2].position

            let dx = p2.x - p1.x
            let dy = p2.y - p1.y
            let dist = max(sqrt(dx * dx + dy * dy), 1.0)
            let displacement = dist - restingDistance
            let force = displacement * springConstant * alpha

            let fx = (dx / dist) * force
            let fy = (dy / dist) * force

            if !nodes[idx1].isFixed {
                nodes[idx1].velocity.x += fx
                nodes[idx1].velocity.y += fy
            }
            if !nodes[idx2].isFixed {
                nodes[idx2].velocity.x -= fx
                nodes[idx2].velocity.y -= fy
            }
        }
    }

    // MARK: - Interaction & Queries

    func dragNode(id: String, to newPosition: CGPoint) {
        guard let idx = nodeIndexMap[id] else { return }
        nodes[idx].position = newPosition
        nodes[idx].velocity = .zero
        nodes[idx].isFixed = true
        alpha = max(alpha, 0.35)
        isSimulating = true
    }

    func releaseNode(id: String) {
        guard let idx = nodeIndexMap[id] else { return }
        nodes[idx].isFixed = false
        alpha = max(alpha, 0.25)
        isSimulating = true
    }

    func findNode(at point: CGPoint, zoom: CGFloat, offset: CGPoint) -> GraphNode? {
        let canvasPoint = CGPoint(
            x: (point.x - offset.x) / zoom,
            y: (point.y - offset.y) / zoom
        )

        for node in nodes.reversed() {
            let r = node.semanticType.baseRadius + 8
            let dx = canvasPoint.x - node.position.x
            let dy = canvasPoint.y - node.position.y
            if dx * dx + dy * dy <= r * r {
                return node
            }
        }
        return nil
    }

    func getNeighbors(for nodeId: String) -> [GraphNode] {
        var neighborIds = Set<String>()
        for link in links {
            if link.sourceId == nodeId { neighborIds.insert(link.targetId) }
            if link.targetId == nodeId { neighborIds.insert(link.sourceId) }
        }
        return nodes.filter { neighborIds.contains($0.id) }
    }

    // Temporal Active Filter
    func getActiveNodes(timeRange: TimeFilterRange, scrubDate: Date?) -> [GraphNode] {
        let now = Date()

        return nodes.filter { node in
            // 1. Time Scrubber Threshold (time-travel)
            if let scrub = scrubDate, let nodeDate = node.timestamp {
                if nodeDate > scrub { return false }
            }

            // 2. Relative Time Window Filter
            if let days = timeRange.days, let nodeDate = node.timestamp {
                let cutoff = now.addingTimeInterval(-days * 86400)
                if nodeDate < cutoff { return false }
            }

            return true
        }
    }
}
