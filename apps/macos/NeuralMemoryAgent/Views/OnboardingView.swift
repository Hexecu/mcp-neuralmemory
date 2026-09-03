// OnboardingView.swift
// Premium onboarding experience with animated gradients

import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var permissionManager: PermissionManager
    @State private var currentStep = 0
    @State private var animateGradient = false

    private let steps = [
        PermissionStep(
            icon: "hand.raised.fill",
            title: "Accessibility",
            description: "Track which apps and windows you use to understand your workflow.",
            gradient: [Color(red: 0.4, green: 0.49, blue: 0.92), Color(red: 0.46, green: 0.29, blue: 0.64)]
        ),
        PermissionStep(
            icon: "rectangle.dashed.badge.record",
            title: "Screen Recording",
            description: "Capture screenshots to extract insights from your screen.",
            gradient: [Color(red: 0.66, green: 0.33, blue: 0.97), Color(red: 0.39, green: 0.4, blue: 0.95)]
        )
    ]

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

            // Decorative glow orbs
            GeometryReader { geo in
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.purple.opacity(0.4), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 200
                        )
                    )
                    .frame(width: 400, height: 400)
                    .offset(x: -100, y: -50)
                    .blur(radius: 60)

                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.blue.opacity(0.3), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 150
                        )
                    )
                    .frame(width: 300, height: 300)
                    .offset(x: geo.size.width - 150, y: geo.size.height - 200)
                    .blur(radius: 50)
            }

            VStack(spacing: 0) {
                // Header with logo
                headerView
                    .padding(.top, 40)

                Spacer()

                // Current permission card
                if currentStep < steps.count {
                    permissionCard(steps[currentStep])
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                        .id(currentStep)
                } else {
                    completionView
                        .transition(.scale.combined(with: .opacity))
                }

                Spacer()

                // Progress and button
                VStack(spacing: 20) {
                    progressDots
                    actionButton
                    if currentStep < steps.count && !permissionGranted(for: currentStep) {
                        Button("Skip for now") {
                            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                currentStep += 1
                            }
                        }
                        .buttonStyle(.plain)
                        .foregroundColor(.white.opacity(0.7))
                    }
                }
                .padding(.bottom, 40)
            }
            .padding(.horizontal, 40)
        }
        .frame(width: 520, height: 680)
    }

    // MARK: - Header

    private var headerView: some View {
        VStack(spacing: 16) {
            // App icon with glow
            ZStack {
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.purple.opacity(0.5), .clear],
                            center: .center,
                            startRadius: 20,
                            endRadius: 60
                        )
                    )
                    .frame(width: 120, height: 120)
                    .blur(radius: 20)

                Image(systemName: "brain.head.profile")
                    .font(.system(size: 50, weight: .medium))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 0.66, green: 0.33, blue: 0.97), Color(red: 0.23, green: 0.51, blue: 0.96)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            }

            Text("Neural Memory")
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .foregroundColor(.white)

            Text("Your AI-powered memory assistant")
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(.white.opacity(0.6))
        }
    }

    // MARK: - Permission Card

    private func permissionCard(_ step: PermissionStep) -> some View {
        VStack(spacing: 24) {
            // Icon with gradient background
            ZStack {
                RoundedRectangle(cornerRadius: 24)
                    .fill(
                        LinearGradient(
                            colors: step.gradient,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 80, height: 80)
                    .shadow(color: step.gradient[0].opacity(0.5), radius: 20, y: 10)

                Image(systemName: step.icon)
                    .font(.system(size: 32, weight: .semibold))
                    .foregroundColor(.white)
            }

            VStack(spacing: 12) {
                Text(step.title)
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text(step.description)
                    .font(.system(size: 15, weight: .regular))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }

            // Status badge
            HStack(spacing: 8) {
                Circle()
                    .fill(permissionGranted(for: currentStep) ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)

                Text(permissionGranted(for: currentStep) ? "Authorized" : "Requires permission")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(permissionGranted(for: currentStep) ? .green : .orange)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(
                Capsule()
                    .fill(.white.opacity(0.1))
            )
        }
        .padding(40)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(.ultraThinMaterial.opacity(0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(
                            LinearGradient(
                                colors: [.white.opacity(0.2), .clear],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
        )
    }

    // MARK: - Completion View

    private var completionView: some View {
        VStack(spacing: 24) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color(red: 0.06, green: 0.73, blue: 0.51), Color(red: 0.02, green: 0.59, blue: 0.41)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 80, height: 80)
                    .shadow(color: Color.green.opacity(0.5), radius: 20, y: 10)

                Image(systemName: "checkmark")
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(.white)
            }

            VStack(spacing: 12) {
                Text("All Set!")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Capture stays off until you explicitly enable it from the menu or Settings.")
                    .font(.system(size: 15))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }
        }
        .padding(40)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(.ultraThinMaterial.opacity(0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(.white.opacity(0.1), lineWidth: 1)
                )
        )
    }

    // MARK: - Progress Dots

    private var progressDots: some View {
        HStack(spacing: 8) {
            ForEach(0..<steps.count + 1, id: \.self) { index in
                Circle()
                    .fill(index == currentStep ? Color.white : Color.white.opacity(0.3))
                    .frame(width: index == currentStep ? 10 : 8, height: index == currentStep ? 10 : 8)
                    .animation(.spring(response: 0.3), value: currentStep)
            }
        }
    }

    // MARK: - Action Button

    private var actionButton: some View {
        Button {
            handleAction()
        } label: {
            HStack(spacing: 8) {
                Text(buttonTitle)
                    .font(.system(size: 16, weight: .semibold))

                if currentStep < steps.count && !permissionGranted(for: currentStep) {
                    Image(systemName: "arrow.right")
                        .font(.system(size: 14, weight: .semibold))
                }
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(
                LinearGradient(
                    colors: [Color(red: 0.39, green: 0.4, blue: 0.95), Color(red: 0.55, green: 0.36, blue: 0.96)],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .shadow(color: Color(red: 0.39, green: 0.4, blue: 0.95).opacity(0.4), radius: 16, y: 8)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Logic

    private var buttonTitle: String {
        if currentStep >= steps.count {
            return "Get Started"
        } else if permissionGranted(for: currentStep) {
            return "Continue"
        } else {
            return "Grant Permission"
        }
    }

    private func permissionGranted(for step: Int) -> Bool {
        switch step {
        case 0: return permissionManager.accessibilityGranted
        case 1: return permissionManager.screenCaptureGranted
        default: return false
        }
    }

    private func handleAction() {
        if currentStep >= steps.count {
            permissionManager.closeOnboardingWindow()
            return
        }

        if permissionGranted(for: currentStep) {
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                currentStep += 1
            }
        } else {
            Task {
                switch currentStep {
                case 0:
                    permissionManager.requestAccessibilityPermission()
                case 1:
                    if #available(macOS 12.3, *) {
                        await permissionManager.requestScreenCapturePermission()
                    }
                default:
                    break
                }

                try? await Task.sleep(nanoseconds: 500_000_000)
                await permissionManager.checkAllPermissions()
            }
        }
    }
}

// MARK: - Models

struct PermissionStep {
    let icon: String
    let title: String
    let description: String
    let gradient: [Color]
}
