// PermissionManager.swift
// Handles all macOS permission requests and status checking

import Foundation
import AppKit
import SwiftUI
import ScreenCaptureKit

@MainActor
class PermissionManager: ObservableObject {
    static let shared = PermissionManager()

    @Published var accessibilityGranted = false
    @Published var screenCaptureGranted = false

    private var onboardingWindow: NSWindow?

    private init() {
        Task {
            await checkAllPermissions()
        }
    }

    // MARK: - Permission Checks

    func checkAllPermissions() async {
        checkAccessibilityPermission()
        await checkScreenCapturePermission()
    }

    func checkAccessibilityPermission() {
        accessibilityGranted = AXIsProcessTrusted()
    }

    @available(macOS 12.3, *)
    func checkScreenCapturePermission() async {
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            screenCaptureGranted = !content.displays.isEmpty
            print("🔒 Screen capture permission check: displays=\(content.displays.count), granted=\(screenCaptureGranted)")
        } catch {
            screenCaptureGranted = false
            print("🔒 Screen capture permission DENIED: \(error)")
        }
    }

    // MARK: - Permission Requests

    func requestAccessibilityPermission() {
        // First try the system prompt
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        AXIsProcessTrustedWithOptions(options as CFDictionary)

        // Also open System Preferences directly as fallback
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
                NSWorkspace.shared.open(url)
            }
        }

        // Poll for permission grant
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { timer in
            if AXIsProcessTrusted() {
                Task { @MainActor in
                    PermissionManager.shared.accessibilityGranted = true
                }
                timer.invalidate()
            }
        }
    }

    @available(macOS 12.3, *)
    func requestScreenCapturePermission() async {
        // Open System Preferences directly to Screen Recording
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            _ = await MainActor.run {
                NSWorkspace.shared.open(url)
            }
        }

        // Also try triggering the API (may show additional dialog)
        do {
            _ = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            await checkScreenCapturePermission()
        } catch {
            print("Screen capture permission not granted: \(error)")
        }
    }

    // MARK: - Onboarding Window

    func showOnboardingWindow() {
        let contentView = OnboardingView()
            .environmentObject(self)

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 500, height: 600),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "Welcome to NeuralMemoryAgent"
        window.contentView = NSHostingView(rootView: contentView)
        window.makeKeyAndOrderFront(nil)
        window.level = .floating

        self.onboardingWindow = window
    }

    func closeOnboardingWindow() {
        UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")

        // Delay window close to allow SwiftUI cleanup
        let window = onboardingWindow
        onboardingWindow = nil

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            window?.orderOut(nil)
            window?.close()
        }
    }
}
