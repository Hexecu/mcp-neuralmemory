// GraphModels.swift
// Models for the native SwiftUI Memory Graph Visualizer

import SwiftUI

// MARK: - Semantic Node Type

enum SemanticNodeType: String, CaseIterable, Identifiable {
    case decision = "Decision"
    case commitment = "Commitment"
    case meeting = "Meeting"
    case reflection = "Reflection"
    case person = "Person"
    case topic = "Topic"
    case artifact = "Artifact"
    case insight = "Insight"
    case other = "Other"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .decision: return "Decision"
        case .commitment: return "Commitment"
        case .meeting: return "Meeting"
        case .reflection: return "Dream Reflection"
        case .person: return "Person"
        case .topic: return "Topic"
        case .artifact: return "Artifact"
        case .insight: return "Insight"
        case .other: return "Entity"
        }
    }

    var iconName: String {
        switch self {
        case .decision: return "checkmark.seal.fill"
        case .commitment: return "hand.raised.fill"
        case .meeting: return "video.fill"
        case .reflection: return "sparkles"
        case .person: return "person.crop.circle.fill"
        case .topic: return "tag.fill"
        case .artifact: return "doc.text.fill"
        case .insight: return "lightbulb.fill"
        case .other: return "circle.hexagongrid.fill"
        }
    }

    var color: Color {
        switch self {
        case .decision: return Color(red: 0.06, green: 0.73, blue: 0.51) // Emerald
        case .commitment: return Color(red: 0.96, green: 0.62, blue: 0.04) // Amber
        case .meeting: return Color(red: 0.23, green: 0.51, blue: 0.96) // Blue
        case .reflection: return Color(red: 0.93, green: 0.28, blue: 0.60) // Pink/Magenta
        case .person: return Color(red: 0.02, green: 0.71, blue: 0.83) // Cyan
        case .topic: return Color(red: 0.66, green: 0.33, blue: 0.97) // Violet
        case .artifact: return Color(red: 0.45, green: 0.52, blue: 0.60) // Slate
        case .insight: return Color(red: 0.08, green: 0.72, blue: 0.65) // Teal
        case .other: return Color(red: 0.58, green: 0.64, blue: 0.72) // Gray
        }
    }

    var baseRadius: CGFloat {
        switch self {
        case .decision, .reflection: return 24
        case .meeting, .person: return 20
        case .commitment, .insight: return 18
        case .topic: return 16
        case .artifact, .other: return 14
        }
    }

    static func from(labels: [String]) -> SemanticNodeType {
        if labels.contains("Decision") { return .decision }
        if labels.contains("Commitment") || labels.contains("ActionItem") { return .commitment }
        if labels.contains("Meeting") || labels.contains("ActivitySession") { return .meeting }
        if labels.contains("Reflection") || labels.contains("DreamInsight") { return .reflection }
        if labels.contains("Person") { return .person }
        if labels.contains("Topic") || labels.contains("Concept") { return .topic }
        if labels.contains("Artifact") { return .artifact }
        if labels.contains("Insight") || labels.contains("ResearchBrief") { return .insight }
        return .other
    }
}

// MARK: - Graph Node

struct GraphNode: Identifiable, Hashable {
    let id: String
    let labels: [String]
    let name: String?
    let title: String?
    let verdict: String?
    let rationale: String?
    let task: String?
    let dueDate: String?
    let synthesis: String?
    let actionableSuggestion: String?
    let takeaway: String?
    let sourceUrl: String?
    let projectId: String?
    let rawAttributes: [String: String]

    // Simulation Physics State
    var position: CGPoint = .zero
    var velocity: CGPoint = .zero
    var isFixed: Bool = false

    var semanticType: SemanticNodeType {
        SemanticNodeType.from(labels: labels)
    }

    var displayTitle: String {
        if let t = title, !t.isEmpty { return t }
        if let n = name, !n.isEmpty { return n }
        if let tsk = task, !tsk.isEmpty { return tsk }
        if let syn = synthesis, !syn.isEmpty {
            return syn.count > 45 ? String(syn.prefix(42)) + "..." : syn
        }
        return semanticType.displayName + " #" + String(id.suffix(4))
    }

    var displaySubtitle: String {
        switch semanticType {
        case .decision:
            return verdict.map { "Verdict: \($0)" } ?? "Strategic Decision"
        case .commitment:
            return dueDate.map { "Due: \($0)" } ?? "Action Item"
        case .meeting:
            return "Meeting Session"
        case .reflection:
            return "Sleep Cycle Synthesis"
        case .person:
            return "Collaborator"
        case .topic:
            return "Knowledge Domain"
        case .artifact:
            return "Captured Context"
        case .insight:
            return "Research Takeaway"
        case .other:
            return labels.first ?? "Node"
        }
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: GraphNode, rhs: GraphNode) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - Graph Link

struct GraphLink: Identifiable, Hashable {
    let id: String
    let sourceId: String
    let targetId: String
    let relType: String

    var displayLabel: String {
        switch relType.uppercased() {
        case "ABOUT_TOPIC": return "About"
        case "INVOLVES_PERSON": return "Involves"
        case "PROMISED_TO": return "Promised To"
        case "PROMISED_BY": return "Promised By"
        case "TOWARDS_PERSON": return "Towards"
        case "ATTENDED": return "Attended"
        case "ON_ARTIFACT": return "On Document"
        case "ASSOCIATED_WITH": return "Associated"
        case "SUBTOPIC_OF": return "Subtopic"
        case "MENTIONED": return "Mentioned"
        default: return relType.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: GraphLink, rhs: GraphLink) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - API Payloads

struct GraphNodeDTO: Decodable {
    let id: String
    let labels: [String]?
    let name: String?
    let title: String?
    let verdict: String?
    let rationale: String?
    let task: String?
    let task_description: String?
    let due_date: String?
    let due_date_iso: String?
    let synthesis: String?
    let suggestion: String?
    let actionable_suggestion: String?
    let takeaway: String?
    let source_url_or_doc: String?
    let project_id: String?

    func toGraphNode() -> GraphNode {
        var raw: [String: String] = [:]
        if let p = project_id { raw["Project ID"] = p }
        if let l = labels { raw["Labels"] = l.joined(separator: ", ") }
        raw["Element ID"] = id

        return GraphNode(
            id: id,
            labels: labels ?? [],
            name: name,
            title: title,
            verdict: verdict,
            rationale: rationale,
            task: task ?? task_description,
            dueDate: due_date ?? due_date_iso,
            synthesis: synthesis,
            actionableSuggestion: actionable_suggestion ?? suggestion,
            takeaway: takeaway,
            sourceUrl: source_url_or_doc,
            projectId: project_id,
            rawAttributes: raw
        )
    }
}

struct GraphLinkDTO: Decodable {
    let source: String
    let target: String
    let type: String

    func toGraphLink(index: Int) -> GraphLink {
        GraphLink(
            id: "\(source)-\(type)-\(target)-\(index)",
            sourceId: source,
            targetId: target,
            relType: type
        )
    }
}

struct GraphDataResponse: Decodable {
    let nodes: [GraphNodeDTO]
    let links: [GraphLinkDTO]
}
