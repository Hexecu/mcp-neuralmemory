// NeuralMemoryAgentApp.swift
// Main entry point for the NeuralMemoryAgent macOS app

import SwiftUI

@main
struct NeuralMemoryAgentApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        // Main window for Dock click
        WindowGroup {
            PremiumDashboardView()
                .environmentObject(appState)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 420, height: 520)

        // Menu bar icon
        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Image(systemName: appState.isConnected ? "brain.head.profile" : "brain.head.profile.slash")
                .symbolRenderingMode(.hierarchical)
        }

        // Settings window
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }
}

// MARK: - Premium Dashboard View
struct PremiumDashboardView: View {
    @EnvironmentObject var appState: AppState
    @State private var animateGradient = false

    var body: some View {
        ZStack {
            // Animated gradient background
            LinearGradient(
                colors: [
                    Color(red: 0.1, green: 0.1, blue: 0.18),
                    Color(red: 0.09, green: 0.13, blue: 0.24),
                    Color(red: 0.06, green: 0.06, blue: 0.14)
                ],
                startPoint: animateGradient ? .topLeading : .bottomLeading,
                endPoint: animateGradient ? .bottomTrailing : .topTrailing
            )
            .ignoresSafeArea()
            .onAppear {
                withAnimation(.easeInOut(duration: 5).repeatForever(autoreverses: true)) {
                    animateGradient.toggle()
                }
            }

            // Glow orbs
            Circle()
                .fill(RadialGradient(colors: [Color.purple.opacity(0.3), .clear], center: .center, startRadius: 0, endRadius: 150))
                .frame(width: 300, height: 300)
                .offset(x: -120, y: -100)
                .blur(radius: 40)

            Circle()
                .fill(RadialGradient(colors: [Color.blue.opacity(0.2), .clear], center: .center, startRadius: 0, endRadius: 120))
                .frame(width: 250, height: 250)
                .offset(x: 150, y: 200)
                .blur(radius: 40)

            VStack(spacing: 24) {
                // Header
                VStack(spacing: 12) {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 50))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [Color(red: 0.66, green: 0.33, blue: 0.97), Color(red: 0.23, green: 0.51, blue: 0.96)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )

                    Text("NeuralMemoryAgent")
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundColor(.white)

                    Text("Your AI-powered memory assistant")
                        .font(.system(size: 13))
                        .foregroundColor(.white.opacity(0.6))
                }
                .padding(.top, 30)

                // Status cards
                VStack(spacing: 12) {
                    StatusCard(
                        icon: "circle.fill",
                        iconColor: appState.isConnected ? .green : .red,
                        title: "Connection",
                        value: appState.isConnected ? "Connected" : "Disconnected"
                    )

                    StatusCard(
                        icon: "square.stack.3d.up.fill",
                        iconColor: .blue,
                        title: "Events Captured",
                        value: "\(appState.eventCount)"
                    )

                    if let lastSync = appState.lastSyncTime {
                        StatusCard(
                            icon: "arrow.clockwise",
                            iconColor: .purple,
                            title: "Last Sync",
                            value: lastSync.formatted(date: .omitted, time: .shortened)
                        )
                    }
                }
                .padding(.horizontal, 20)

                Spacer()

                // Action buttons
                HStack(spacing: 16) {
                    ActionButton(title: "Sync", icon: "arrow.triangle.2.circlepath", isPrimary: true) {
                        Task { await APIClient.shared.checkConnection() }
                    }

                    ActionButton(title: "Settings", icon: "gear", isPrimary: false) {
                        PermissionManager.shared.showOnboardingWindow()
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 30)
            }
        }
        .frame(minWidth: 380, minHeight: 480)
        .onAppear {
            Task { await APIClient.shared.checkConnection() }
        }
    }
}

// MARK: - Status Card
struct StatusCard: View {
    let icon: String
    let iconColor: Color
    let title: String
    let value: String

    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(iconColor)
                .frame(width: 24)

            Text(title)
                .foregroundColor(.white.opacity(0.7))

            Spacer()

            Text(value)
                .foregroundColor(.white)
                .fontWeight(.medium)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.white.opacity(0.08))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(.white.opacity(0.1), lineWidth: 1)
                )
        )
    }
}

// MARK: - Action Button
struct ActionButton: View {
    let title: String
    let icon: String
    let isPrimary: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                Text(title)
            }
            .font(.system(size: 14, weight: .semibold))
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                Group {
                    if isPrimary {
                        LinearGradient(
                            colors: [Color(red: 0.39, green: 0.4, blue: 0.95), Color(red: 0.55, green: 0.36, blue: 0.96)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    } else {
                        Color.white.opacity(0.15)
                    }
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(.white.opacity(isPrimary ? 0 : 0.2), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}
