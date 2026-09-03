// AppState.swift
// Global application state

import SwiftUI
import Combine

@MainActor
class AppState: ObservableObject {
    static let shared = AppState()

    // Connection status
    @Published var isConnected = false
    @Published var lastSyncTime: Date?
    @Published var eventCount = 0

    // Permissions
    @Published var permissionsGranted = false

    // Settings
    @AppStorage("serverURL") var serverURL = "http://127.0.0.1:8765"
    @Published var apiToken: String {
        didSet { KeychainStore.saveToken(apiToken) }
    }
    @AppStorage("projectID") var projectID = "default"
    @Published var storageMode: String = "detecting"

    private init() {
        let localTokenURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/NeuralMemory/token.txt")
        if let fileToken = try? String(contentsOf: localTokenURL, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines), !fileToken.isEmpty {
            apiToken = fileToken
        } else if let legacyToken = UserDefaults.standard.string(forKey: "apiToken"), !legacyToken.isEmpty {
            apiToken = legacyToken
        } else if let storedToken = KeychainStore.loadToken(), !storedToken.isEmpty {
            apiToken = storedToken
        } else {
            apiToken = ""
        }
    }

    func updateConnectionStatus(_ connected: Bool) {
        isConnected = connected
        if connected {
            lastSyncTime = Date()
        }
    }

    func incrementEventCount() {
        eventCount += 1
    }
}
