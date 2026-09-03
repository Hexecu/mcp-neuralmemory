// MenuBarView.swift
// Menu bar dropdown content with full options

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @ObservedObject private var eventService = EventCaptureService.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Status Header
            VStack(alignment: .leading, spacing: 4) {
                Text("Neural Memory Agent")
                    .font(.headline)
                    .fontWeight(.semibold)

                Text("Last: \(formattedLastSync)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            Divider()

            // Toggle Options
            VStack(alignment: .leading, spacing: 0) {
                Toggle(isOn: $eventService.isTrackingEnabled) {
                    Text("Enable Capture")
                }
                .toggleStyle(.checkbox)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)

                // Pause Capture
                Toggle(isOn: $eventService.isPaused) {
                    Text("Pause Capture")
                }
                .disabled(!eventService.isTrackingEnabled)
                .toggleStyle(.checkbox)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)

                // Private Mode
                Toggle(isOn: $eventService.isPrivateMode) {
                    Text("Private Mode")
                }
                .toggleStyle(.checkbox)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)

                // Track Typing with buffer indicator - uses @Published property directly
                HStack {
                    Toggle(isOn: $eventService.isTrackingKeystrokes) {
                        HStack {
                            Image(systemName: "keyboard")
                                .frame(width: 20)
                            Text("Track Typing")
                        }
                    }
                    .toggleStyle(.checkbox)
                    .disabled(!eventService.isTrackingEnabled)

                    Spacer()

                    // Buffer chars updates automatically via @Published
                    Text("Buffer: \(eventService.keystrokeBuffer.count) chars")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
            }

            Divider()

            // Actions
            VStack(alignment: .leading, spacing: 0) {
                Button {
                    openDashboard()
                } label: {
                    HStack {
                        Image(systemName: "square.grid.2x2")
                            .frame(width: 20)
                        Text("Open Dashboard")
                        Spacer()
                    }
                }
                .buttonStyle(MenuItemButtonStyle())

                Button {
                    openGraphVisualizer()
                } label: {
                    HStack {
                        Image(systemName: "point.3.filled.connected.trianglepath.dotted")
                            .frame(width: 20)
                        Text("View Memory Graph")
                        Spacer()
                    }
                }
                .buttonStyle(MenuItemButtonStyle())

                Button {
                    openSettings()
                } label: {
                    HStack {
                        Image(systemName: "gearshape")
                            .frame(width: 20)
                        Text("Settings & Preferences...")
                        Spacer()
                    }
                }
                .buttonStyle(MenuItemButtonStyle())

                Button {
                    NSApplication.shared.terminate(nil)
                } label: {
                    HStack {
                        Image(systemName: "power")
                            .frame(width: 20)
                        Text("Quit")
                        Spacer()
                    }
                }
                .buttonStyle(MenuItemButtonStyle())
            }
        }
        .frame(width: 260)
    }

    private var formattedLastSync: String {
        if let lastSync = appState.lastSyncTime {
            let formatter = DateFormatter()
            formatter.dateFormat = "dd/MM/yyyy, HH:mm"
            return formatter.string(from: lastSync)
        }
        return "Never"
    }

    private func openDashboard() {
        if let appDelegate = NSApp.delegate as? AppDelegate {
            Task { @MainActor in
                appDelegate.showDashboardWindow()
            }
        }
    }

    private func openGraphVisualizer() {
        if let appDelegate = NSApp.delegate as? AppDelegate {
            Task { @MainActor in
                appDelegate.showGraphWindow()
            }
        }
    }

    private func openSettings() {
        if let appDelegate = NSApp.delegate as? AppDelegate {
            Task { @MainActor in
                appDelegate.showSettingsWindow()
            }
        }
    }
}

// MARK: - Menu Button Styles

struct MenuItemButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(configuration.isPressed ? Color.accentColor.opacity(0.2) : Color.clear)
            .contentShape(Rectangle())
    }
}
