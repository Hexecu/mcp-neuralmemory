// UIGraphicalE2ETests.swift
// End-to-end UI & Graphical Contracts Test Suite for SwiftUI Knowledge Graph

import XCTest
import SwiftUI
@testable import NeuralMemoryAgent

final class UIGraphicalE2ETests: XCTestCase {

    func testSemanticColorMappingContract() {
        for type in SemanticNodeType.allCases {
            // Icon verification
            XCTAssertFalse(type.iconName.isEmpty, "Icon name must not be empty for \(type)")
            // Display name verification
            XCTAssertFalse(type.displayName.isEmpty, "Display name must not be empty for \(type)")
            // Base radius positive
            XCTAssertGreaterThanOrEqual(type.baseRadius, 14.0)
            XCTAssertLessThanOrEqual(type.baseRadius, 28.0)
        }

        // Specific color checks
        XCTAssertEqual(SemanticNodeType.decision.iconName, "checkmark.seal.fill")
        XCTAssertEqual(SemanticNodeType.commitment.iconName, "hand.raised.fill")
        XCTAssertEqual(SemanticNodeType.meeting.iconName, "video.fill")
        XCTAssertEqual(SemanticNodeType.reflection.iconName, "sparkles")
        XCTAssertEqual(SemanticNodeType.person.iconName, "person.crop.circle.fill")
        XCTAssertEqual(SemanticNodeType.topic.iconName, "tag.fill")
    }

    func testTimelineLanesVerticalAltitudesContract() {
        let reflection = GraphNode(id: "ref", labels: ["Reflection"])
        let decision = GraphNode(id: "dec", labels: ["Decision"])
        let meeting = GraphNode(id: "meet", labels: ["Meeting"])
        let commitment = GraphNode(id: "com", labels: ["Commitment"])
        let topic = GraphNode(id: "top", labels: ["Topic"])
        let person = GraphNode(id: "per", labels: ["Person"])

        // Altitudes must be ordered monotonically down the canvas
        XCTAssertEqual(reflection.timelineLaneY, 130)
        XCTAssertEqual(decision.timelineLaneY, 240)
        XCTAssertEqual(meeting.timelineLaneY, 350)
        XCTAssertEqual(commitment.timelineLaneY, 460)
        XCTAssertEqual(topic.timelineLaneY, 570)
        XCTAssertEqual(person.timelineLaneY, 570)

        XCTAssertLessThan(reflection.timelineLaneY, decision.timelineLaneY)
        XCTAssertLessThan(decision.timelineLaneY, meeting.timelineLaneY)
        XCTAssertLessThan(meeting.timelineLaneY, commitment.timelineLaneY)
        XCTAssertLessThan(commitment.timelineLaneY, topic.timelineLaneY)
    }

    func testCognitiveInspectorHumanReadableContract() {
        let decisionNode = GraphNode(
            id: "dec-1",
            labels: ["Decision"],
            title: "Migrate to Rust Core",
            verdict: "APPROVED",
            rationale: "Lower memory footprint and predictable tail latency.",
            rawAttributes: ["element_id": "4:neo4j:12345", "project_id": "default"]
        )

        // Title and Subtitle MUST be clean, executive language
        XCTAssertEqual(decisionNode.displayTitle, "Migrate to Rust Core")
        XCTAssertEqual(decisionNode.displaySubtitle, "Verdict: APPROVED")
        // Raw attributes must be preserved in dictionary but isolated
        XCTAssertEqual(decisionNode.rawAttributes["element_id"], "4:neo4j:12345")
        XCTAssertFalse(decisionNode.displayTitle.contains("4:neo4j"))
        XCTAssertFalse(decisionNode.displaySubtitle.contains("4:neo4j"))

        let commitmentNode = GraphNode(
            id: "com-1",
            labels: ["Commitment"],
            task: "Deliver Benchmark Suite",
            dueDate: "15/09/2026"
        )
        XCTAssertEqual(commitmentNode.displayTitle, "Deliver Benchmark Suite")
        XCTAssertEqual(commitmentNode.displaySubtitle, "Due: 15/09/2026")
    }

    func testTimeFilterRangeIntervals() {
        XCTAssertNil(TimeFilterRange.all.days)
        XCTAssertEqual(TimeFilterRange.last30Days.days, 30.0)
        XCTAssertEqual(TimeFilterRange.last7Days.days, 7.0)
        XCTAssertEqual(TimeFilterRange.last3Days.days, 3.0)
        XCTAssertEqual(TimeFilterRange.today.days, 1.0)
    }

    @MainActor
    func testNeighborRelationJumpNavigation() {
        let engine = GraphPhysicsEngine()

        let nodeCenter = GraphNode(id: "center", labels: ["Topic"], name: "Temporal Graphs")
        let nodeNeighbor1 = GraphNode(id: "n1", labels: ["Decision"], title: "Adopt Bi-Temporal Model")
        let nodeNeighbor2 = GraphNode(id: "n2", labels: ["Person"], name: "Francesca")
        let nodeUnrelated = GraphNode(id: "unrelated", labels: ["Topic"], name: "Cooking Recipes")

        let link1 = GraphLink(id: "l1", sourceId: "center", targetId: "n1", relType: "ABOUT_TOPIC")
        let link2 = GraphLink(id: "l2", sourceId: "center", targetId: "n2", relType: "INVOLVES_PERSON")

        engine.setGraph(
            nodes: [nodeCenter, nodeNeighbor1, nodeNeighbor2, nodeUnrelated],
            links: [link1, link2],
            in: CGSize(width: 800, height: 600)
        )

        let neighborsOfCenter = engine.getNeighbors(for: "center")
        XCTAssertEqual(neighborsOfCenter.count, 2)
        XCTAssertTrue(neighborsOfCenter.contains(where: { $0.id == "n1" }))
        XCTAssertTrue(neighborsOfCenter.contains(where: { $0.id == "n2" }))
        XCTAssertFalse(neighborsOfCenter.contains(where: { $0.id == "unrelated" }))

        // Bidirectional query
        let neighborsOfN1 = engine.getNeighbors(for: "n1")
        XCTAssertEqual(neighborsOfN1.count, 1)
        XCTAssertEqual(neighborsOfN1.first?.id, "center")
    }
}
