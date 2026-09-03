// SettingsView.swift
// Unified Settings, Preferences & Management panel for Neural Memory Agent

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var permissionManager = PermissionManager.shared
    @ObservedObject private var eventService = EventCaptureService.shared

    @State private var selectedTab = 0
    @State private var isTestingConnection = false
    @State private var testConnectionResult: String?
    @State private var isRunningDream = false
    @State private var dreamResult: String?

    // Temporal preferences
    @AppStorage("defaultLayoutMode") private var defaultLayoutMode: String = "Cluster"
    @AppStorage("temporalDecayHalflife") private var temporalDecayHalflife: Double = 72.0
    @AppStorage("defaultTimeRange") private var defaultTimeRange: String = "All Time"

    var body: some View {
        VStack(spacing: 0) {
            // Header bar
            HStack(spacing: 12) {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 0.66, green: 0.33, blue: 0.97), Color(red: 0.23, green: 0.51, blue: 0.96)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                VStack(alignment: .leading, spacing: 2) {
                    Text("Settings & Management")
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("Configuration, AI engines, privacy & temporal graph")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.5))
                }

                Spacer()
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            .background(Color(red: 0.08, green: 0.09, blue: 0.18).opacity(0.95))

            Divider()
                .background(Color.white.opacity(0.1))

            // Main Tab View
            TabView(selection: $selectedTab) {
                serverTab
                    .tabItem { Label("Server", systemImage: "server.rack") }
                    .tag(0)

                cognitiveTab
                    .tabItem { Label("Cognitive / LLM", systemImage: "brain.head.profile") }
                    .tag(1)

                captureTab
                    .tabItem { Label("Capture & Privacy", systemImage: "shield.checkered") }
                    .tag(2)

                temporalGraphTab
                    .tabItem { Label("Temporal Graph", systemImage: "chart.line.uptrend.xyaxis") }
                    .tag(3)

                permissionsTab
                    .tabItem { Label("Permissions", systemImage: "lock.shield") }
                    .tag(4)
            }
            .padding(20)
        }
        .frame(width: 580, height: 500)
        .background(
            RadialGradient(
                colors: [
                    Color(red: 0.10, green: 0.11, blue: 0.22),
                    Color(red: 0.05, green: 0.05, blue: 0.12)
                ],
                center: .center,
                startRadius: 50,
                endRadius: 500
            )
            .ignoresSafeArea()
        )
    }

    // MARK: - Server Tab

    private var serverTab: some View {
        Form {
            Section {
                TextField("Server Endpoint", text: $appState.serverURL)
                    .textFieldStyle(.roundedBorder)

                SecureField("Bearer API Token", text: $appState.apiToken)
                    .textFieldStyle(.roundedBorder)

                TextField("Project ID", text: $appState.projectID)
                    .textFieldStyle(.roundedBorder)
            } header: {
                Text("Backend Connection")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Section {
                HStack {
                    Circle()
                        .fill(appState.isConnected ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                    Text(appState.isConnected ? "Connected to local daemon" : "Daemon unreachable")
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.8))

                    Spacer()

                    Button {
                        isTestingConnection = true
                        testConnectionResult = nil
                        Task {
                            await APIClient.shared.checkConnection()
                            await MainActor.run {
                                isTestingConnection = false
                                testConnectionResult = appState.isConnected ? "Connection verified!" : "Check server daemon."
                            }
                        }
                    } label: {
                        HStack(spacing: 5) {
                            if isTestingConnection {
                                ProgressView().scaleEffect(0.6)
                            }
                            Text("Test Connection")
                        }
                    }
                }

                if let res = testConnectionResult {
                    Text(res)
                        .font(.caption)
                        .foregroundColor(appState.isConnected ? .green : .orange)
                }

                HStack {
                    Text("Storage Mode:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    if appState.storageMode == "embedded_sqlite" {
                        HStack(spacing: 4) {
                            Circle().fill(Color.green).frame(width: 7, height: 7)
                            Text("Embedded SQLite (Standalone)")
                                .font(.caption.bold())
                                .foregroundColor(.green)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Color.green.opacity(0.12))
                        .clipShape(Capsule())
                    } else {
                        HStack(spacing: 4) {
                            Circle().fill(Color.blue).frame(width: 7, height: 7)
                            Text("Open Local (Neo4j / Docker)")
                                .font(.caption.bold())
                                .foregroundColor(.blue)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Color.blue.opacity(0.12))
                        .clipShape(Capsule())
                    }
                }

                HStack {
                    Text("Neo4j Database:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Link("Open Neo4j Browser ↗", destination: URL(string: "http://127.0.0.1:8774/browser/")!)
                        .font(.caption)
                }
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Cognitive Tab

    private var cognitiveTab: some View {
        Form {
            Section {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Dream Mode Engine")
                            .font(.system(size: 13, weight: .bold))
                        Text("Runs sleep-cycle replay to generate strategic reflections and latent associative bridges.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button {
                        runDreamCycle()
                    } label: {
                        HStack(spacing: 5) {
                            if isRunningDream {
                                ProgressView().scaleEffect(0.6)
                            }
                            Text("Run Dream Cycle")
                        }
                    }
                    .disabled(isRunningDream || !appState.isConnected)
                }

                if let res = dreamResult {
                    Text(res)
                        .font(.caption)
                        .foregroundColor(.purple)
                        .padding(.top, 4)
                }
            } header: {
                Text("Autonomous Consolidation")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Section {
                HStack {
                    Text("Multimodal LLM:")
                    Spacer()
                    Text("LiteLLM / Gemini 2.5 Flash")
                        .foregroundColor(.secondary)
                }
                HStack {
                    Text("Vision Analyzer:")
                    Spacer()
                    Text("Dynamic Visual Hashing (pHash)")
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Active Inference Stack")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }
        }
        .formStyle(.grouped)
    }

    private func runDreamCycle() {
        isRunningDream = true
        dreamResult = nil
        Task {
            guard let url = URL(string: appState.serverURL + "/api/memory/dream") else { return }
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            if let token = try? APIClient.authorizationHeader(token: appState.apiToken) {
                request.setValue(token, forHTTPHeaderField: "Authorization")
            }
            do {
                let (data, _) = try await URLSession.shared.data(for: request)
                let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                let count = (dict?["reflections_created"] as? Int) ?? 0
                await MainActor.run {
                    dreamResult = "Dream cycle completed: \(count) reflections synthesized!"
                    isRunningDream = false
                }
            } catch {
                await MainActor.run {
                    dreamResult = "Dream cycle error: \(error.localizedDescription)"
                    isRunningDream = false
                }
            }
        }
    }

    // MARK: - Capture & Privacy Tab

    private var captureTab: some View {
        Form {
            Section {
                Toggle("Enable Activity Capture", isOn: $eventService.isTrackingEnabled)
                Toggle("Capture Screen Context (Visual Hashes)", isOn: $eventService.capturesScreenshots)
                    .disabled(!eventService.isTrackingEnabled)
                Toggle("Capture Typed Keystrokes (Buffer)", isOn: $eventService.isTrackingKeystrokes)
                    .disabled(!eventService.isTrackingEnabled)
                Toggle("Private Mode (Zero Persistence)", isOn: $eventService.isPrivateMode)
            } header: {
                Text("Telemetry Opt-In")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Section {
                HStack {
                    Image(systemName: "lock.shield.fill")
                        .foregroundColor(.green)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("PrivacyShield Enabled")
                            .font(.system(size: 12, weight: .bold))
                        Text("Sensitive API keys (sk-..., AIza...), passwords and tokens are redacted before any LLM transmission.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            } header: {
                Text("Safety Guarantee")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Temporal Graph Tab

    private var temporalGraphTab: some View {
        Form {
            Section {
                Picker("Default Layout Mode", selection: $defaultLayoutMode) {
                    Text("Topic Clusters (Multi-Hub)").tag("Cluster")
                    Text("Timeline Stream (Time Axis)").tag("Timeline")
                    Text("Free Force Simulation").tag("Force")
                }

                Picker("Default Time Filter", selection: $defaultTimeRange) {
                    Text("All Time").tag("All Time")
                    Text("Last 30 Days").tag("30 Days")
                    Text("Last 7 Days").tag("7 Days")
                    Text("Last 3 Days").tag("3 Days")
                    Text("Today").tag("Today")
                }
            } header: {
                Text("Graph Topology & Temporal Windows")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Section {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Memory Halflife (Hours):")
                        Spacer()
                        Text("\(Int(temporalDecayHalflife)) h")
                            .font(.system(.body, design: .monospaced))
                    }
                    Slider(value: $temporalDecayHalflife, in: 12...168, step: 6)
                        .tint(Color.purple)
                    Text("Controls Ebbinghaus forgetting decay rate. Nodes inactive for longer than this halflife gradually dim.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Ebbinghaus Memory Decay")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Permissions Tab

    private var permissionsTab: some View {
        Form {
            Section {
                permissionRow(
                    title: "Accessibility Permission",
                    granted: permissionManager.accessibilityGranted,
                    description: "Required for active window title & app context tracking."
                ) {
                    permissionManager.requestAccessibilityPermission()
                }

                permissionRow(
                    title: "Screen Recording Permission",
                    granted: permissionManager.screenCaptureGranted,
                    description: "Required for visual context & hashing."
                ) {
                    if #available(macOS 12.3, *) {
                        Task { await permissionManager.requestScreenCapturePermission() }
                    }
                }
            } header: {
                Text("macOS System Entitlements")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Section {
                Button("Refresh Permission Status") {
                    Task { await permissionManager.checkAllPermissions() }
                }
            }
        }
        .formStyle(.grouped)
    }

    @ViewBuilder
    private func permissionRow(
        title: String,
        granted: Bool,
        description: String,
        action: @escaping () -> Void
    ) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .fontWeight(.medium)
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            if granted {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
            } else {
                Button("Grant") {
                    action()
                }
            }
        }
    }
}
