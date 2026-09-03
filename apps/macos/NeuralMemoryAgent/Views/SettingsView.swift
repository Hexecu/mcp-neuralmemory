// SettingsView.swift
// App settings panel

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var permissionManager = PermissionManager.shared

    var body: some View {
        TabView {
            // General Tab
            Form {
                Section("Server Connection") {
                    TextField("Server URL", text: $appState.serverURL)
                    SecureField("API token", text: $appState.apiToken)
                    TextField("Project ID", text: $appState.projectID)

                    HStack {
                        Circle()
                            .fill(appState.isConnected ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                        Text(appState.isConnected ? "Connected" : "Not connected")

                        Spacer()

                        Button("Test Connection") {
                            Task {
                                await APIClient.shared.checkConnection()
                            }
                        }
                    }
                }

            }
            .tabItem {
                Label("General", systemImage: "gear")
            }
            .padding()

            Form {
                Section("Capture") {
                    Toggle("Enable activity capture", isOn: $eventService.isTrackingEnabled)
                    Toggle("Capture screenshots", isOn: $eventService.capturesScreenshots)
                        .disabled(!eventService.isTrackingEnabled)
                    Toggle("Capture typed text", isOn: $eventService.isTrackingKeystrokes)
                        .disabled(!eventService.isTrackingEnabled)
                    Text("All capture is off on a fresh install. Typed text and screenshots require separate opt-in.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .tabItem {
                Label("Capture", systemImage: "record.circle")
            }
            .padding()

            // Permissions Tab
            Form {
                Section("Required Permissions") {
                    permissionRow(
                        title: "Accessibility",
                        granted: permissionManager.accessibilityGranted,
                        description: "For window tracking"
                    ) {
                        permissionManager.requestAccessibilityPermission()
                    }

                    permissionRow(
                        title: "Screen Recording",
                        granted: permissionManager.screenCaptureGranted,
                        description: "For screenshot capture"
                    ) {
                        if #available(macOS 12.3, *) {
                            Task { await permissionManager.requestScreenCapturePermission() }
                        }
                    }
                }

                Section {
                    Button("Refresh Permission Status") {
                        Task { await permissionManager.checkAllPermissions() }
                    }
                }
            }
            .tabItem {
                Label("Permissions", systemImage: "lock.shield")
            }
            .padding()

            // About Tab
            VStack(spacing: 16) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 80))
                    .foregroundStyle(
                        .linearGradient(
                            colors: [.purple, .blue],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                Text("NeuralMemoryAgent")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Version 0.2.0")
                    .foregroundColor(.secondary)

                Text("A local-first memory graph for the work context you choose to capture.")
                    .multilineTextAlignment(.center)
                    .foregroundColor(.secondary)
                    .padding()

                Spacer()
            }
            .tabItem {
                Label("About", systemImage: "info.circle")
            }
            .padding()
        }
        .frame(width: 450, height: 350)
    }

    @ObservedObject private var eventService = EventCaptureService.shared

    @ViewBuilder
    private func permissionRow(
        title: String,
        granted: Bool,
        description: String,
        action: @escaping () -> Void
    ) -> some View {
        HStack {
            VStack(alignment: .leading) {
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
                .buttonStyle(.borderedProminent)
            }
        }
    }
}
