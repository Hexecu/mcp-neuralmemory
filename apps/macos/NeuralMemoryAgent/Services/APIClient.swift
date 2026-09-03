// APIClient.swift
// HTTP client for backend communication

import Foundation

actor APIClient {
    static let shared = APIClient()

    private let session = URLSession.shared

    private init() {}

    func checkConnection() async {
        let appState = await AppState.shared
        guard let url = URL(string: await appState.serverURL + "/health") else {
            await appState.updateConnectionStatus(false)
            return
        }

        do {
            let (data, response) = try await session.data(from: url)
            guard let httpResponse = response as? HTTPURLResponse,
                  Self.isNeuralMemoryHealthResponse(data: data, statusCode: httpResponse.statusCode) else {
                await appState.updateConnectionStatus(false)
                return
            }
            await appState.updateConnectionStatus(true)
        } catch {
            await appState.updateConnectionStatus(false)
        }
    }

    func sendEvent(_ event: CapturedEvent) async throws {
        let appState = await AppState.shared
        guard let url = URL(string: await appState.serverURL + "/api/ingest/event") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(
            try Self.authorizationHeader(token: await appState.apiToken),
            forHTTPHeaderField: "Authorization"
        )

        let payload = EventPayload(
            project_id: await appState.projectID,
            event_type: event.type,
            timestamp: ISO8601DateFormatter().string(from: event.timestamp),
            data: event.data,
            text_content: event.textContent,
            screenshot_base64: event.screenshotBase64
        )

        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.serverError(status: httpResponse.statusCode, body: String(data: data, encoding: .utf8))
        }
        await appState.incrementEventCount()
    }

    func sendBundle(_ bundle: InteractionBundlePayload) async throws {
        let appState = await AppState.shared
        guard let url = URL(string: await appState.serverURL + "/api/ingest/bundle") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(
            try Self.authorizationHeader(token: await appState.apiToken),
            forHTTPHeaderField: "Authorization"
        )

        request.httpBody = try JSONEncoder().encode(bundle)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.serverError(status: httpResponse.statusCode, body: String(data: data, encoding: .utf8))
        }
        await appState.incrementEventCount()
    }

    static func isNeuralMemoryHealthResponse(data: Data, statusCode: Int) -> Bool {
        guard statusCode == 200,
              let health = try? JSONDecoder().decode(HealthResponse.self, from: data) else { return false }
        return health.status == "ok" && health.service == "neural-memory"
    }

    static func authorizationHeader(token: String) throws -> String {
        let value = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { throw APIError.missingToken }
        return "Bearer \(value)"
    }
}

struct HealthResponse: Decodable {
    let status: String
    let service: String
    let version: String
}

struct CapturedEvent {
    let type: String
    let timestamp: Date
    let data: [String: String]
    let textContent: String?
    let screenshotBase64: String?
}

struct EventPayload: Encodable {
    let project_id: String
    let event_type: String
    let timestamp: String
    let data: [String: String]
    let text_content: String?
    let screenshot_base64: String?
}

struct InteractionBundlePayload: Encodable {
    let project_id: String
    let timestamp: String
    let app: String
    let window_title: String
    let screenshot_base64: String?
    let keystrokes_typed: String
    let mouse_actions: [String]
    let trigger_reason: String
}

enum APIError: Error, LocalizedError {
    case invalidURL
    case missingToken
    case invalidResponse
    case serverError(status: Int, body: String?)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "The server URL is invalid."
        case .missingToken: return "Add the API token generated during setup."
        case .invalidResponse: return "The server returned an invalid response."
        case .serverError(let status, _): return "The server rejected the event (HTTP \(status))."
        }
    }
}
