// AppDelegate.swift
// Handles app lifecycle and background tasks

import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Collection is opt-in and remains disabled on a fresh install.
        Task {
            await startServicesIfEnabled()
        }

        // Show onboarding if first launch
        if !UserDefaults.standard.bool(forKey: "hasCompletedOnboarding") {
            Task { @MainActor in
                PermissionManager.shared.showOnboardingWindow()
            }
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
        EventCaptureService.shared.stop()
    }

    private func startServicesIfEnabled() async {
        await EventCaptureService.shared.start()
        await APIClient.shared.checkConnection()
    }
}
