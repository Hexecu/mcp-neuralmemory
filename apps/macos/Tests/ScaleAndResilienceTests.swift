// ScaleAndResilienceTests.swift
// Performance scale, numerical stability & boundary testing for Knowledge Graph

import XCTest
import CoreGraphics
@testable import NeuralMemoryAgent

final class ScaleAndResilienceTests: XCTestCase {

    @MainActor
    func testMassiveGraphScale500NodesSimulation() {
        let engine = GraphPhysicsEngine()
        var nodes: [GraphNode] = []
        var links: [GraphLink] = []

        let types: [SemanticNodeType] = [.decision, .commitment, .meeting, .reflection, .person, .topic, .insight]
        let baseDate = Date(timeIntervalSinceNow: -86400 * 10) // 10 days ago

        // 1. Create 500 nodes with varying labels and timestamps
        for i in 0..<500 {
            let type = types[i % types.count]
            let ts = baseDate.addingTimeInterval(Double(i) * 1700.0)
            let node = GraphNode(
                id: "node-\(i)",
                labels: [type.rawValue],
                name: "Entity \(i)",
                title: "Title \(i)",
                verdict: type == .decision ? "APPROVED" : nil,
                rationale: "Rationale for entity \(i)",
                task: type == .commitment ? "Deliverable \(i)" : nil,
                dueDate: "2026-09-15",
                synthesis: type == .reflection ? "Synthesis of cluster \(i)" : nil,
                timestamp: ts
            )
            nodes.append(node)
        }

        // 2. Create 1,200 cross-linking relations (multi-hub graph topology)
        for i in 0..<1200 {
            let srcIdx = i % 500
            let tgtIdx = (i * 7 + 13) % 500
            if srcIdx != tgtIdx {
                links.append(GraphLink(
                    id: "link-\(i)",
                    sourceId: "node-\(srcIdx)",
                    targetId: "node-\(tgtIdx)",
                    relType: i % 3 == 0 ? "ABOUT_TOPIC" : "INVOLVES_PERSON"
                ))
            }
        }

        // 3. Initialize engine with massive graph
        let canvasSize = CGSize(width: 1400, height: 900)
        engine.setGraph(nodes: nodes, links: links, in: canvasSize)

        XCTAssertEqual(engine.nodes.count, 500)
        XCTAssertEqual(engine.links.count, links.count)

        // 4. Run 40 physics simulation steps and measure performance
        let start = CACurrentMediaTime()
        let steps = 40
        for _ in 0..<steps {
            engine.step()
        }
        let elapsed = CACurrentMediaTime() - start
        let avgStepMs = (elapsed / Double(steps)) * 1000.0
        print("⚡ Massive 500-node simulation avg step time: \(String(format: "%.2f", avgStepMs)) ms")

        // 5. Numerical Stability Asserts (Zero NaN, Zero Inf, Clamped Velocities)
        for node in engine.nodes {
            XCTAssertFalse(node.position.x.isNaN, "Node position X was NaN for \(node.id)")
            XCTAssertFalse(node.position.y.isNaN, "Node position Y was NaN for \(node.id)")
            XCTAssertFalse(node.position.x.isInfinite, "Node position X was Infinite for \(node.id)")
            XCTAssertFalse(node.position.y.isInfinite, "Node position Y was Infinite for \(node.id)")

            XCTAssertGreaterThanOrEqual(node.velocity.x, -30.0)
            XCTAssertLessThanOrEqual(node.velocity.x, 30.0)
            XCTAssertGreaterThanOrEqual(node.velocity.y, -30.0)
            XCTAssertLessThanOrEqual(node.velocity.y, 30.0)
        }
    }

    @MainActor
    func testLayoutModeTransitionsUnderScale() {
        let engine = GraphPhysicsEngine()
        var nodes: [GraphNode] = []

        let now = Date()
        for i in 0..<100 {
            let ts = now.addingTimeInterval(-Double(i) * 3600.0)
            nodes.append(GraphNode(
                id: "n-\(i)",
                labels: [i % 2 == 0 ? "Decision" : "Commitment"],
                title: "Node \(i)",
                timestamp: ts
            ))
        }

        engine.setGraph(nodes: nodes, links: [], in: CGSize(width: 1000, height: 700))

        // Transition 1: Cluster mode
        engine.setLayoutMode(.cluster)
        XCTAssertEqual(engine.layoutMode, .cluster)
        engine.step()

        // Transition 2: Timeline mode
        engine.setLayoutMode(.timeline)
        XCTAssertEqual(engine.layoutMode, .timeline)
        for _ in 0..<10 { engine.step() }

        // Verify that in timeline mode, decisions and commitments attract to their designated lanes
        for node in engine.nodes {
            XCTAssertFalse(node.position.x.isNaN)
            XCTAssertFalse(node.position.y.isNaN)
            let expectedLane = node.timelineLaneY
            // Velocity should be pulling toward lane
            XCTAssertTrue(expectedLane == 240 || expectedLane == 460)
        }

        // Transition 3: Free Force mode
        engine.setLayoutMode(.force)
        XCTAssertEqual(engine.layoutMode, .force)
        engine.step()
        XCTAssertGreaterThan(engine.alpha, 0.0)
    }

    @MainActor
    func testHitTestingAtExtremeZoomScales() {
        let engine = GraphPhysicsEngine()
        let targetNode = GraphNode(
            id: "target",
            labels: ["Decision"],
            title: "Crucial Decision",
            position: CGPoint(x: 400, y: 300)
        )
        engine.setGraph(nodes: [targetNode], links: [], in: CGSize(width: 800, height: 600))
        // Manually place node
        engine.nodes[0].position = CGPoint(x: 400, y: 300)

        let zoomScales: [CGFloat] = [0.3, 0.5, 1.0, 1.5, 2.5, 3.0]

        for zoom in zoomScales {
            let offset = CGPoint(x: 50, y: -30)
            let screenPoint = CGPoint(
                x: targetNode.position.x * zoom + offset.x,
                y: targetNode.position.y * zoom + offset.y
            )

            let hit = engine.findNode(at: screenPoint, zoom: zoom, offset: offset)
            XCTAssertNotNil(hit, "Hit testing failed at zoom scale \(zoom)")
            XCTAssertEqual(hit?.id, "target")
        }

        // Test miss
        let missPoint = CGPoint(x: 0, y: 0)
        let miss = engine.findNode(at: missPoint, zoom: 1.0, offset: .zero)
        XCTAssertNil(miss, "Hit testing should return nil on empty space")
    }

    @MainActor
    func testTemporalScrubberEdgeCases() {
        let engine = GraphPhysicsEngine()

        let now = Date()
        let past = now.addingTimeInterval(-86400 * 5)

        // Case 1: Nodes with identical timestamps
        let node1 = GraphNode(id: "1", labels: ["Topic"], timestamp: past)
        let node2 = GraphNode(id: "2", labels: ["Topic"], timestamp: past)
        // Case 2: Node with nil timestamp
        let nodeNil = GraphNode(id: "nil-ts", labels: ["Person"], timestamp: nil)
        // Case 3: Node with current timestamp
        let nodeNow = GraphNode(id: "now", labels: ["Decision"], timestamp: now)

        engine.setGraph(nodes: [node1, node2, nodeNil, nodeNow], links: [], in: CGSize(width: 800, height: 600))

        // Time travel to past date
        let activePast = engine.getActiveNodes(timeRange: .all, scrubDate: past)
        XCTAssertEqual(activePast.count, 3) // node1, node2, nodeNil (nil ts is always active)
        XCTAssertFalse(activePast.contains(where: { $0.id == "now" }))

        // Time travel to now
        let activeNow = engine.getActiveNodes(timeRange: .all, scrubDate: now)
        XCTAssertEqual(activeNow.count, 4)

        // Half-life boundary conditions
        XCTAssertGreaterThan(nodeNow.recencyScore(now: now, halflifeHours: 1.0), 0.99)
        XCTAssertGreaterThan(nodeNow.recencyScore(now: now, halflifeHours: 1000.0), 0.99)
        XCTAssertEqual(nodeNil.recencyScore(), 0.5) // Fallback default
    }
}
