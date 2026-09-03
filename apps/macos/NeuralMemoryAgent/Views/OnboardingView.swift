// OnboardingView.swift
// Interactive visual onboarding wizard with macOS System Settings guidance

import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var permissionManager: PermissionManager
    @State private var currentStep: Int
    @State private var animateGlow = false

    init(initialStep: Int = 0) {
        _currentStep = State(initialValue: initialStep)
    }

    var body: some View {
        ZStack {
            // Dark glass background
            RadialGradient(
                colors: [
                    Color(red: 0.12, green: 0.13, blue: 0.25),
                    Color(red: 0.05, green: 0.06, blue: 0.12)
                ],
                center: .center,
                startRadius: 50,
                endRadius: 500
            )
            .ignoresSafeArea()

            // Decorative background ambient orbs
            GeometryReader { geo in
                Circle()
                    .fill(Color.purple.opacity(0.18))
                    .frame(width: 320, height: 320)
                    .offset(x: -80, y: -40)
                    .blur(radius: 60)

                Circle()
                    .fill(Color.blue.opacity(0.15))
                    .frame(width: 280, height: 280)
                    .offset(x: geo.size.width - 200, y: geo.size.height - 220)
                    .blur(radius: 50)
            }

            VStack(spacing: 0) {
                // Header
                headerView
                    .padding(.top, 28)
                    .padding(.bottom, 16)

                // Step Body
                ZStack {
                    switch currentStep {
                    case 0:
                        welcomeStepView
                            .transition(.asymmetric(insertion: .opacity.combined(with: .scale(scale: 0.96)), removal: .opacity))
                    case 1:
                        accessibilityStepView
                            .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity), removal: .move(edge: .leading).combined(with: .opacity)))
                    case 2:
                        screenRecordingStepView
                            .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity), removal: .move(edge: .leading).combined(with: .opacity)))
                    case 3:
                        completionStepView
                            .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity), removal: .opacity))
                    default:
                        EmptyView()
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding(.horizontal, 32)

                // Bottom Footer
                VStack(spacing: 16) {
                    progressIndicator
                    bottomControls
                }
                .padding(.horizontal, 36)
                .padding(.bottom, 28)
            }
        }
        .frame(width: 580, height: 680)
        .onAppear {
            withAnimation(.easeInOut(duration: 2.5).repeatForever(autoreverses: true)) {
                animateGlow = true
            }
        }
    }

    // MARK: - Header

    private var headerView: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.purple.opacity(0.3))
                    .frame(width: 36, height: 36)
                    .blur(radius: 4)

                Image(systemName: "brain.head.profile")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(
                        LinearGradient(colors: [.purple, .blue], startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
            }

            VStack(alignment: .leading, spacing: 2) {
                Text("Neural Memory Setup")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                Text("First-time Permissions & Configuration")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white.opacity(0.6))
            }

            Spacer()

            // Step Counter Badge
            Text("Step \(currentStep + 1) of 4")
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(.white.opacity(0.7))
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Color.white.opacity(0.08))
                .clipShape(Capsule())
        }
        .padding(.horizontal, 36)
    }

    // MARK: - Step 0: Welcome

    private var welcomeStepView: some View {
        VStack(spacing: 24) {
            Spacer()

            ZStack {
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.purple.opacity(0.35), Color.blue.opacity(0.1), .clear],
                            center: .center,
                            startRadius: 20,
                            endRadius: 90
                        )
                    )
                    .frame(width: 170, height: 170)

                Image(systemName: "point.3.filled.connected.trianglepath.dotted")
                    .font(.system(size: 64, weight: .light))
                    .foregroundStyle(
                        LinearGradient(colors: [.cyan, .indigo, .purple], startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
                    .shadow(color: .purple.opacity(0.6), radius: 16)
            }

            VStack(spacing: 10) {
                Text("Your Cognitive Second Brain")
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Neural Memory anchors decisions, promises, and discussions directly from your workflow into a private knowledge graph.")
                    .font(.system(size: 13, weight: .regular))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
                    .padding(.horizontal, 20)
            }

            // Value pillars
            VStack(spacing: 10) {
                featureBullet(
                    icon: "lock.shield.fill",
                    color: .green,
                    title: "100% Local & Private",
                    detail: "Zero cloud requirement. In-memory redaction filters passwords and credentials automatically."
                )
                featureBullet(
                    icon: "sparkles",
                    color: .purple,
                    title: "Contextual Micro-Feedback",
                    detail: "Even a brief 'Ok' on an email is anchored to the sender, quote, and terms."
                )
                featureBullet(
                    icon: "chart.line.uptrend.xyaxis",
                    color: .cyan,
                    title: "Temporal Graph & MCP",
                    detail: "Explore knowledge visually and query it directly through Claude, Cursor, and AI agents."
                )
            }
            .padding(14)
            .background(Color.white.opacity(0.04))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            )

            Spacer()
        }
    }

    // MARK: - Step 1: Accessibility Guide

    private var accessibilityStepView: some View {
        VStack(spacing: 18) {
            VStack(spacing: 6) {
                HStack(spacing: 8) {
                    Image(systemName: "hand.raised.fill")
                        .foregroundColor(.blue)
                    Text("1. Accessibility Permission")
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                }

                Text("Enables identifying active window titles and apps (e.g. Mail, Slack, IDE) so context can be anchored accurately.")
                    .font(.system(size: 12))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
            }

            // Visual System Settings Mockup Card
            VStack(spacing: 0) {
                // Window titlebar
                HStack(spacing: 6) {
                    Circle().fill(Color.red.opacity(0.8)).frame(width: 8, height: 8)
                    Circle().fill(Color.yellow.opacity(0.8)).frame(width: 8, height: 8)
                    Circle().fill(Color.green.opacity(0.8)).frame(width: 8, height: 8)
                    Spacer()
                    Text("System Settings — Privacy & Security > Accessibility")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.black.opacity(0.4))

                Divider().background(Color.white.opacity(0.1))

                // Settings Content
                VStack(spacing: 12) {
                    HStack {
                        Image(systemName: "hand.raised.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(.blue)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Accessibility")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.white)
                            Text("Allow the apps below to control your computer.")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }

                    // Mock app row
                    HStack {
                        Image(systemName: "brain.head.profile")
                            .font(.system(size: 14))
                            .foregroundColor(.purple)
                            .frame(width: 24, height: 24)
                            .background(Color.white.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 6))

                        Text("NeuralMemoryAgent")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.white)

                        Spacer()

                        // Toggle indicator
                        ZStack {
                            Capsule()
                                .fill(permissionManager.accessibilityGranted ? Color.green : Color.blue)
                                .frame(width: 44, height: 24)

                            Circle()
                                .fill(Color.white)
                                .frame(width: 20, height: 20)
                                .offset(x: permissionManager.accessibilityGranted ? 10 : 10)
                                .shadow(radius: 2)
                        }
                        .overlay(
                            Capsule()
                                .stroke(Color.white.opacity(animateGlow ? 0.8 : 0.2), lineWidth: 2)
                                .scaleEffect(animateGlow ? 1.12 : 1.0)
                        )
                    }
                    .padding(10)
                    .background(Color.blue.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.blue.opacity(0.4), lineWidth: 1)
                    )
                }
                .padding(16)
                .background(Color(red: 0.15, green: 0.16, blue: 0.22))
            }
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.4), radius: 12, y: 6)

            // Status Indicator & Action
            HStack(spacing: 8) {
                Image(systemName: permissionManager.accessibilityGranted ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundColor(permissionManager.accessibilityGranted ? .green : .orange)
                Text(permissionManager.accessibilityGranted ? "Accessibility Permission Granted!" : "Click below, then turn ON the switch next to NeuralMemoryAgent")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(permissionManager.accessibilityGranted ? .green : .white.opacity(0.85))
            }
            .padding(.vertical, 4)

            Button {
                permissionManager.requestAccessibilityPermission()
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "arrow.up.forward.app")
                    Text("Open System Settings > Accessibility")
                        .font(.system(size: 13, weight: .semibold))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(Color.blue.opacity(0.3))
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.blue.opacity(0.6), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Step 2: Screen Recording Guide

    private var screenRecordingStepView: some View {
        VStack(spacing: 18) {
            VStack(spacing: 6) {
                HStack(spacing: 8) {
                    Image(systemName: "rectangle.dashed.badge.record")
                        .foregroundColor(.purple)
                    Text("2. Visual Context (Screenshots)")
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                }

                Text("Allows taking transient perceptual hashes to understand what you're approving. Pixels are never saved to disk.")
                    .font(.system(size: 12))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
            }

            // Visual Mockup Card
            VStack(spacing: 0) {
                HStack(spacing: 6) {
                    Circle().fill(Color.red.opacity(0.8)).frame(width: 8, height: 8)
                    Circle().fill(Color.yellow.opacity(0.8)).frame(width: 8, height: 8)
                    Circle().fill(Color.green.opacity(0.8)).frame(width: 8, height: 8)
                    Spacer()
                    Text("System Settings — Privacy & Security > Screen Recording")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.black.opacity(0.4))

                Divider().background(Color.white.opacity(0.1))

                VStack(spacing: 12) {
                    HStack {
                        Image(systemName: "camera.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(.purple)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Screen & System Audio Recording")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.white)
                            Text("Allow the apps below to record screen contents.")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }

                    HStack {
                        Image(systemName: "brain.head.profile")
                            .font(.system(size: 14))
                            .foregroundColor(.purple)
                            .frame(width: 24, height: 24)
                            .background(Color.white.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 6))

                        Text("NeuralMemoryAgent")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.white)

                        Spacer()

                        ZStack {
                            Capsule()
                                .fill(permissionManager.screenCaptureGranted ? Color.green : Color.purple)
                                .frame(width: 44, height: 24)

                            Circle()
                                .fill(Color.white)
                                .frame(width: 20, height: 20)
                                .offset(x: 10)
                                .shadow(radius: 2)
                        }
                    }
                    .padding(10)
                    .background(Color.purple.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.purple.opacity(0.4), lineWidth: 1)
                    )
                }
                .padding(16)
                .background(Color(red: 0.15, green: 0.16, blue: 0.22))
            }
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.4), radius: 12, y: 6)

            HStack(spacing: 8) {
                Image(systemName: permissionManager.screenCaptureGranted ? "checkmark.circle.fill" : "info.circle.fill")
                    .foregroundColor(permissionManager.screenCaptureGranted ? .green : .cyan)
                Text(permissionManager.screenCaptureGranted ? "Screen Recording Permission Granted!" : "Optional: You can skip this if you prefer text-only capture.")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(permissionManager.screenCaptureGranted ? .green : .white.opacity(0.85))
            }
            .padding(.vertical, 4)

            Button {
                Task {
                    if #available(macOS 12.3, *) {
                        await permissionManager.requestScreenCapturePermission()
                    }
                }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "arrow.up.forward.app")
                    Text("Open System Settings > Screen Recording")
                        .font(.system(size: 13, weight: .semibold))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(Color.purple.opacity(0.3))
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.purple.opacity(0.6), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Step 3: Completion & Ready

    private var completionStepView: some View {
        VStack(spacing: 20) {
            Spacer()

            ZStack {
                Circle()
                    .fill(Color.green.opacity(0.25))
                    .frame(width: 90, height: 90)

                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 54))
                    .foregroundColor(.green)
                    .shadow(color: .green.opacity(0.6), radius: 16)
            }

            VStack(spacing: 8) {
                Text("Setup Complete!")
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Neural Memory is configured and ready to accompany your workflow.")
                    .font(.system(size: 13))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
            }

            // Summary Status Card
            VStack(spacing: 12) {
                statusRow(
                    icon: "server.rack",
                    title: "Active Storage Mode",
                    badge: AppState.shared.storageMode == "open_local_neo4j" ? "Open Local (Docker/Neo4j)" : "Embedded SQLite (Zero Docker)",
                    color: AppState.shared.storageMode == "open_local_neo4j" ? .blue : .green
                )
                Divider().background(Color.white.opacity(0.1))
                statusRow(
                    icon: "hand.raised.fill",
                    title: "Accessibility",
                    badge: permissionManager.accessibilityGranted ? "Granted" : "Skipped",
                    color: permissionManager.accessibilityGranted ? .green : .secondary
                )
                Divider().background(Color.white.opacity(0.1))
                statusRow(
                    icon: "rectangle.dashed.badge.record",
                    title: "Screen Context",
                    badge: permissionManager.screenCaptureGranted ? "Granted" : "Skipped",
                    color: permissionManager.screenCaptureGranted ? .green : .secondary
                )
            }
            .padding(16)
            .background(Color.white.opacity(0.05))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )

            Spacer()
        }
    }

    // MARK: - Subviews & Helpers

    private func featureBullet(icon: String, color: Color, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(color)
                .frame(width: 24, height: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.white)
                Text(detail)
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.65))
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
        }
    }

    private func statusRow(icon: String, title: String, badge: String, color: Color) -> some View {
        HStack {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundColor(color)
            Text(title)
                .font(.system(size: 12))
                .foregroundColor(.white.opacity(0.8))
            Spacer()
            Text(badge)
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(color)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(color.opacity(0.15))
                .clipShape(Capsule())
        }
    }

    private var progressIndicator: some View {
        HStack(spacing: 8) {
            ForEach(0..<4, id: \.self) { idx in
                Capsule()
                    .fill(idx == currentStep ? Color.white : Color.white.opacity(0.2))
                    .frame(width: idx == currentStep ? 24 : 8, height: 6)
                    .animation(.spring(response: 0.3), value: currentStep)
            }
        }
    }

    private var bottomControls: some View {
        HStack(spacing: 12) {
            if currentStep > 0 && currentStep < 3 {
                Button {
                    withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                        currentStep += 1
                    }
                } label: {
                    Text("Skip Step")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.plain)
            }

            Button {
                handlePrimaryAction()
            } label: {
                HStack(spacing: 8) {
                    Text(primaryButtonTitle)
                        .font(.system(size: 14, weight: .semibold))
                    Image(systemName: currentStep == 3 ? "rocket.fill" : "arrow.right")
                        .font(.system(size: 12, weight: .bold))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    LinearGradient(
                        colors: currentStep == 3
                            ? [Color.green, Color.teal]
                            : [Color(red: 0.35, green: 0.38, blue: 0.95), Color(red: 0.55, green: 0.30, blue: 0.95)],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .shadow(color: (currentStep == 3 ? Color.green : Color.blue).opacity(0.4), radius: 10, y: 4)
            }
            .buttonStyle(.plain)
        }
    }

    private var primaryButtonTitle: String {
        switch currentStep {
        case 0: return "Begin Setup"
        case 1: return permissionManager.accessibilityGranted ? "Continue" : "Next Step"
        case 2: return permissionManager.screenCaptureGranted ? "Continue" : "Next Step"
        case 3: return "Launch Neural Memory"
        default: return "Continue"
        }
    }

    private func handlePrimaryAction() {
        if currentStep < 3 {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.8)) {
                currentStep += 1
            }
        } else {
            UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
            permissionManager.closeOnboardingWindow()
            if let appDelegate = NSApp.delegate as? AppDelegate {
                appDelegate.showGraphWindow()
            }
        }
    }
}
