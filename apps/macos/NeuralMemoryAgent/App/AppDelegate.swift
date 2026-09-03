import Cocoa
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var dashboardWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        if CommandLine.arguments.contains("--export-assets") {
            self.exportAssetsAndExit()
            return
        }

        NSApp.setActivationPolicy(.regular)
        Task {
            await startServicesIfEnabled()
        }

        Task { @MainActor in
            if CommandLine.arguments.contains("--graph") {
                self.showGraphWindow()
            } else if CommandLine.arguments.contains("--settings") {
                self.showSettingsWindow()
            } else if CommandLine.arguments.contains("--onboarding") {
                PermissionManager.shared.showOnboardingWindow()
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
        EmbeddedDaemonManager.shared.stop()
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

    private var settingsWindow: NSWindow?

    @MainActor
    func showSettingsWindow() {
        if settingsWindow == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 580, height: 500),
                styleMask: [.titled, .closable, .miniaturizable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            window.center()
            window.title = "Settings & Management"
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isMovableByWindowBackground = true
            window.contentView = NSHostingView(
                rootView: SettingsView().environmentObject(AppState.shared)
            )
            settingsWindow = window
        }
        settingsWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func startServicesIfEnabled() async {
        await EmbeddedDaemonManager.shared.ensureDaemonRunning()
        await EventCaptureService.shared.start()
        await APIClient.shared.checkConnection()
    }

    @MainActor
    private func exportAssetsAndExit() {
        let fileManager = FileManager.default
        var targetDir = URL(fileURLWithPath: fileManager.currentDirectoryPath).appendingPathComponent("assets/images")
        if !fileManager.fileExists(atPath: targetDir.path) {
            var dir = URL(fileURLWithPath: fileManager.currentDirectoryPath)
            while dir.pathComponents.count > 1 {
                let candidate = dir.appendingPathComponent("assets/images")
                if fileManager.fileExists(atPath: candidate.path) {
                    targetDir = candidate
                    break
                }
                dir.deleteLastPathComponent()
            }
        }
        try? fileManager.createDirectory(at: targetDir, withIntermediateDirectories: true)

        func save<V: View>(_ view: V, size: CGSize, name: String) {
            let container = view
                .frame(width: size.width, height: size.height)
                .background(Color(red: 0.08, green: 0.09, blue: 0.16))
            let hosting = NSHostingView(rootView: container)
            hosting.frame = NSRect(origin: .zero, size: size)

            let win = NSWindow(
                contentRect: NSRect(origin: .zero, size: size),
                styleMask: [.borderless],
                backing: .buffered,
                defer: false
            )
            win.contentView = hosting
            win.layoutIfNeeded()
            hosting.layoutSubtreeIfNeeded()

            if let bitmapRep = hosting.bitmapImageRepForCachingDisplay(in: hosting.bounds) {
                hosting.cacheDisplay(in: hosting.bounds, to: bitmapRep)
                if let png = bitmapRep.representation(using: .png, properties: [:]) {
                    let out = targetDir.appendingPathComponent(name)
                    try? png.write(to: out)
                    print("🖼️ Exported UI Asset: \(name) (\(png.count) bytes) -> \(out.path)")
                }
            }
        }

        let pManager = PermissionManager.shared
        pManager.accessibilityGranted = true
        pManager.screenCaptureGranted = true

        let state = AppState.shared
        state.storageMode = "embedded_sqlite"
        state.isConnected = true

        save(OnboardingView(initialStep: 0).environmentObject(pManager), size: CGSize(width: 580, height: 680), name: "wizard_setup_welcome.png")
        save(OnboardingView(initialStep: 1).environmentObject(pManager), size: CGSize(width: 580, height: 680), name: "wizard_setup_accessibility.png")
        save(OnboardingView(initialStep: 2).environmentObject(pManager), size: CGSize(width: 580, height: 680), name: "wizard_setup_screen_recording.png")
        save(SettingsView().environmentObject(state).environmentObject(pManager), size: CGSize(width: 580, height: 520), name: "settings_storage_mode.png")
        save(GraphView().environmentObject(state), size: CGSize(width: 1050, height: 680), name: "temporal_graph_canvas.png")

        exit(0)
    }
}
