// GraphPhysicsEngine.swift
// High-performance 2D force-directed physics engine for Neural Memory Graph

import SwiftUI
import Combine

@MainActor
class GraphPhysicsEngine: ObservableObject {
    @Published var nodes: [GraphNode] = []
    @Published var links: [GraphLink] = []
    @Published var alpha: CGFloat = 1.0
    @Published var isSimulating: Bool = false

    private var nodeIndexMap: [String: Int] = [:]
    private var center: CGPoint = CGPoint(x: 500, y: 350)

    // Physics parameters
    let repulsionConstant: CGFloat = 2400.0
    let springConstant: CGFloat = 0.045
    let restingDistance: CGFloat = 85.0
    let centerGravity: CGFloat = 0.015
    let damping: CGFloat = 0.84
    let minDistance: CGFloat = 20.0

    func setGraph(nodes: [GraphNode], links: [GraphLink], in size: CGSize) {
        self.center = CGPoint(x: size.width / 2, y: size.height / 2)
        var initializedNodes = nodes

        // Position nodes initially in a gentle Fermat spiral around the center
        let phi = (1.0 + sqrt(5.0)) / 2.0 // Golden ratio

        for i in 0..<initializedNodes.count {
            let theta = Double(i) * 2.0 * Double.pi * phi
            let r = 35.0 * sqrt(Double(i + 1))
            let x = center.x + CGFloat(r * cos(theta))
            let y = center.y + CGFloat(r * sin(theta))
            initializedNodes[i].position = CGPoint(x: x, y: y)
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

    func updateCenter(_ newCenter: CGPoint) {
        self.center = newCenter
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

        // 1. Repulsion between all node pairs
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
                var dist = sqrt(dx * dx + dy * dy)

                if dist < 0.1 {
                    dx = CGFloat.random(in: -1...1)
                    dy = CGFloat.random(in: -1...1)
                    dist = 1.0
                }

                if dist < minDistance {
                    dist = minDistance
                }

                let force = (repulsionConstant / (dist * dist)) * alpha
                fx += (dx / dist) * force
                fy += (dy / dist) * force
            }

            // 2. Centering gravity
            let cdx = center.x - p1.x
            let cdy = center.y - p1.y
            fx += cdx * centerGravity * alpha
            fy += cdy * centerGravity * alpha

            nodes[i].velocity.x = (nodes[i].velocity.x + fx) * damping
            nodes[i].velocity.y = (nodes[i].velocity.y + fy) * damping
        }

        // 3. Spring attraction along links
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

        // 4. Update positions
        for i in 0..<n {
            if nodes[i].isFixed { continue }
            // Velocity clamp to prevent explosion
            let vx = max(-25, min(25, nodes[i].velocity.x))
            let vy = max(-25, min(25, nodes[i].velocity.y))

            nodes[i].position.x += vx
            nodes[i].position.y += vy
        }

        // 5. Alpha cooling
        alpha *= 0.985
    }

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
        // Reverse transform point: point in canvas space
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
}
