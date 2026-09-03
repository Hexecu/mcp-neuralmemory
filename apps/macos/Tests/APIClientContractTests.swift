import Foundation
import XCTest
@testable import NeuralMemoryAgent

final class APIClientContractTests: XCTestCase {
    func testHealthRequiresExactServiceIdentityAndSuccessStatus() {
        let valid = Data(#"{"status":"ok","service":"neural-memory","version":"0.2.0"}"#.utf8)
        let unrelated = Data(#"{"status":"ok","service":"another-app","version":"1"}"#.utf8)

        XCTAssertTrue(APIClient.isNeuralMemoryHealthResponse(data: valid, statusCode: 200))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: valid, statusCode: 404))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: unrelated, statusCode: 200))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: Data("not json".utf8), statusCode: 200))
    }

    func testAuthorizationRejectsAnEmptyToken() throws {
        XCTAssertThrowsError(try APIClient.authorizationHeader(token: "   "))
        XCTAssertEqual(try APIClient.authorizationHeader(token: " abc "), "Bearer abc")
    }

    func testSemanticNodeTypeMapping() {
        XCTAssertEqual(SemanticNodeType.from(labels: ["Decision"]), .decision)
        XCTAssertEqual(SemanticNodeType.from(labels: ["ActionItem", "Commitment"]), .commitment)
        XCTAssertEqual(SemanticNodeType.from(labels: ["Meeting", "ActivitySession"]), .meeting)
        XCTAssertEqual(SemanticNodeType.from(labels: ["Reflection", "DreamInsight"]), .reflection)
        XCTAssertEqual(SemanticNodeType.from(labels: ["Person"]), .person)
        XCTAssertEqual(SemanticNodeType.from(labels: ["Topic", "Concept"]), .topic)
    }

    func testGraphNodeDTODecodingAndMapping() throws {
        let json = """
        {
            "id": "test-1234",
            "labels": ["Decision"],
            "title": "Rewrite architecture with Neo4j",
            "verdict": "APPROVED",
            "rationale": "High associative graph query throughput"
        }
        """.data(using: .utf8)!

        let dto = try JSONDecoder().decode(GraphNodeDTO.self, from: json)
        let node = dto.toGraphNode()

        XCTAssertEqual(node.id, "test-1234")
        XCTAssertEqual(node.semanticType, .decision)
        XCTAssertEqual(node.displayTitle, "Rewrite architecture with Neo4j")
        XCTAssertEqual(node.verdict, "APPROVED")
        XCTAssertEqual(node.rationale, "High associative graph query throughput")
        XCTAssertEqual(node.displaySubtitle, "Verdict: APPROVED")
    }

    @MainActor
    func testGraphPhysicsEngineNeighborsAndHitTesting() {
        let engine = GraphPhysicsEngine()
        let nodeA = GraphNode(id: "A", labels: ["Person"], name: "Davide", title: nil, verdict: nil, rationale: nil, task: nil, dueDate: nil, synthesis: nil, actionableSuggestion: nil, takeaway: nil, sourceUrl: nil, projectId: nil, rawAttributes: [:], position: CGPoint(x: 100, y: 100))
        let nodeB = GraphNode(id: "B", labels: ["Topic"], name: "Architecture", title: nil, verdict: nil, rationale: nil, task: nil, dueDate: nil, synthesis: nil, actionableSuggestion: nil, takeaway: nil, sourceUrl: nil, projectId: nil, rawAttributes: [:], position: CGPoint(x: 200, y: 200))
        let link = GraphLink(id: "A-B", sourceId: "A", targetId: "B", relType: "ABOUT_TOPIC")

        engine.setGraph(nodes: [nodeA, nodeB], links: [link], in: CGSize(width: 800, height: 600))

        XCTAssertEqual(engine.nodes.count, 2)
        XCTAssertEqual(engine.links.count, 1)

        let neighbors = engine.getNeighbors(for: "A")
        XCTAssertEqual(neighbors.count, 1)
        XCTAssertEqual(neighbors.first?.id, "B")

        // Step simulation
        engine.step()
        XCTAssertGreaterThan(engine.alpha, 0.0)
    }
}
