import Cocoa
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var dashboardWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        Task {
            await startServicesIfEnabled()
        }

        Task { @MainActor in
            if CommandLine.arguments.contains("--graph") {
                self.showGraphWindow()
            } else {
                self.showDashboardWindow()
            }
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

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        Task { @MainActor in
            self.showDashboardWindow()
        }
        return true
    }

    @MainActor
    func showDashboardWindow() {
        if dashboardWindow == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 420, height: 520),
                styleMask: [.titled, .closable, .miniaturizable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            window.center()
            window.title = "Neural Memory Agent"
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isMovableByWindowBackground = true
            window.contentView = NSHostingView(
                rootView: PremiumDashboardView().environmentObject(AppState.shared)
            )
            dashboardWindow = window
        }
        dashboardWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private var graphWindow: NSWindow?

    @MainActor
    func showGraphWindow() {
        if graphWindow == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 1050, height: 720),
                styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            window.minSize = NSSize(width: 800, height: 550)
            window.center()
            window.title = "Neural Memory — Knowledge Graph"
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isMovableByWindowBackground = true
            window.contentView = NSHostingView(
                rootView: GraphView().environmentObject(AppState.shared)
            )
            graphWindow = window
        }
        graphWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func startServicesIfEnabled() async {
        await EventCaptureService.shared.start()
        await APIClient.shared.checkConnection()
    }
}
