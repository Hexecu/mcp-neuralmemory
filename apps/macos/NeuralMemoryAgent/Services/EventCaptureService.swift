// EventCaptureService.swift
// Captures window focus changes, keystrokes, and screenshots

import Foundation
import AppKit
import Carbon.HIToolbox
import ScreenCaptureKit

@MainActor
class EventCaptureService: ObservableObject {
    static let shared = EventCaptureService()

    @Published var keystrokeBuffer: String = ""
    @Published var keystrokeCount: Int = 0
    @Published var isPaused: Bool = false {
        didSet { if isPaused { keystrokeBuffer = "" } }
    }
    @Published var isPrivateMode: Bool = UserDefaults.standard.bool(forKey: "privateMode") {
        didSet {
            UserDefaults.standard.set(isPrivateMode, forKey: "privateMode")
            if isPrivateMode { keystrokeBuffer = "" }
        }
    }
    @Published var isTrackingEnabled: Bool = UserDefaults.standard.bool(forKey: "trackingEnabled") {
        didSet {
            UserDefaults.standard.set(isTrackingEnabled, forKey: "trackingEnabled")
            isTrackingEnabled ? start() : stop()
        }
    }
    @Published var isTrackingKeystrokes: Bool = UserDefaults.standard.bool(forKey: "trackKeystrokes") {
        didSet {
            UserDefaults.standard.set(isTrackingKeystrokes, forKey: "trackKeystrokes")
            if !isTrackingKeystrokes { keystrokeBuffer = "" }
        }
    }
    @Published var capturesScreenshots: Bool = UserDefaults.standard.bool(forKey: "captureScreenshots") {
        didSet { UserDefaults.standard.set(capturesScreenshots, forKey: "captureScreenshots") }
    }

    private var isRunning = false
    private var focusObserver: Any?
    private var timer: Timer?
    private var keystrokeTimer: Timer?
    private var lastActiveApp: String?
    private var lastActiveWindow: String?
    private var lastCaptureTime: Date?
    private var eventMonitor: Any?
    private let maxKeystrokeBufferLength = 500

    private init() {}

    func start() {
        guard isTrackingEnabled, !isRunning else { return }
        isRunning = true

        // Observe app activation
        focusObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor in
                self?.handleAppChange(notification)
            }
        }

        // Periodic capture (every 5 minutes)
        timer = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { [weak self] _ in
            Task {
                await self?.captureCurrentState(reason: "periodic")
            }
        }

        // Start keystroke monitoring
        startKeystrokeMonitoring()

        // Flush keystroke buffer every 60 seconds
        keystrokeTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.flushKeystrokeBuffer()
            }
        }

        print("Event capture started")
    }

    func stop() {
        isRunning = false

        if let observer = focusObserver {
            NSWorkspace.shared.notificationCenter.removeObserver(observer)
            focusObserver = nil
        }

        timer?.invalidate()
        timer = nil

        keystrokeTimer?.invalidate()
        keystrokeTimer = nil

        stopKeystrokeMonitoring()

        keystrokeBuffer = ""
        print("Event capture stopped")
    }

    // MARK: - Keystroke Tracking

    private func startKeystrokeMonitoring() {
        // Global key event monitor (requires Accessibility permission)
        eventMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            guard let self = self,
                  self.isTrackingKeystrokes,
                  !self.isPaused,
                  !self.isPrivateMode else { return }

            if IsSecureEventInputEnabled() {
                return
            }

            let modifiers = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
            if modifiers.contains(.command) || modifiers.contains(.control) {
                return
            }

            DispatchQueue.main.async {
                self.handleKeyEvent(event)
            }
        }
    }

    private func stopKeystrokeMonitoring() {
        if let monitor = eventMonitor {
            NSEvent.removeMonitor(monitor)
            eventMonitor = nil
        }
    }

    private func flushKeystrokeBuffer() {
        flushInteractionBundle(trigger: "idle_pause")
    }

    private func flushInteractionBundle(trigger: String = "idle_pause") {
        guard !keystrokeBuffer.isEmpty, !isPaused, !isPrivateMode else { return }

        let text = keystrokeBuffer
        let app = lastActiveApp ?? "Unknown"
        let window = lastActiveWindow ?? ""

        keystrokeBuffer = ""

        Task { @MainActor in
            var screenshotB64: String? = nil
            if self.capturesScreenshots {
                if #available(macOS 14.0, *) {
                    screenshotB64 = await self.captureScreenshot()
                }
            }

            let appState = AppState.shared
            let payload = InteractionBundlePayload(
                project_id: appState.projectID,
                timestamp: ISO8601DateFormatter().string(from: Date()),
                app: app,
                window_title: window,
                screenshot_base64: screenshotB64,
                keystrokes_typed: text,
                mouse_actions: [trigger],
                trigger_reason: trigger
            )

            do {
                try await APIClient.shared.sendBundle(payload)
                print("Interaction bundle sent (\(trigger)): \(text.count) characters")
            } catch {
                print("Failed to send interaction bundle: \(error.localizedDescription)")
            }
        }
    }

    private func handleKeyEvent(_ event: NSEvent) {
        keystrokeCount += 1

        if event.keyCode == UInt16(kVK_Delete) || event.keyCode == UInt16(kVK_ForwardDelete) {
            if !keystrokeBuffer.isEmpty {
                keystrokeBuffer.removeLast()
            }
            return
        }

        if event.keyCode == UInt16(kVK_Return) {
            flushInteractionBundle(trigger: "enter_pressed")
            return
        }

        guard let chars = event.characters, !chars.isEmpty else { return }
        let sanitized = sanitizeKeystrokes(chars)
        guard !sanitized.isEmpty else { return }

        appendToKeystrokeBuffer(sanitized)
    }

    private func sanitizeKeystrokes(_ text: String) -> String {
        let allowedControls = CharacterSet(charactersIn: "\n\t")
        let filteredScalars = text.unicodeScalars.filter { scalar in
            if allowedControls.contains(scalar) {
                return true
            }
            // Filter private use areas (U+E000–U+F8FF, U+F0000–U+FFFFD, U+100000–U+10FFFD)
            let value = scalar.value
            if (value >= 0xE000 && value <= 0xF8FF) ||
               (value >= 0xF0000 && value <= 0xFFFFD) ||
               (value >= 0x100000 && value <= 0x10FFFD) {
                return false
            }
            if CharacterSet.controlCharacters.contains(scalar) || CharacterSet.illegalCharacters.contains(scalar) {
                return false
            }
            return true
        }
        return String(String.UnicodeScalarView(filteredScalars))
    }

    private func appendToKeystrokeBuffer(_ text: String) {
        guard !text.isEmpty else { return }
        if keystrokeBuffer.count >= maxKeystrokeBufferLength {
            return
        }
        let remaining = maxKeystrokeBufferLength - keystrokeBuffer.count
        if text.count <= remaining {
            keystrokeBuffer.append(contentsOf: text)
        } else {
            keystrokeBuffer.append(contentsOf: text.prefix(remaining))
        }
    }

    // MARK: - Window Focus

    private func handleAppChange(_ notification: Notification) {
        guard !isPaused, !isPrivateMode else { return }

        guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else {
            return
        }

        let appName = app.localizedName ?? "Unknown"
        let windowTitle = getActiveWindowTitle()

        // Only capture if app or window changed
        if appName != lastActiveApp || windowTitle != lastActiveWindow {
            if !keystrokeBuffer.isEmpty {
                flushInteractionBundle(trigger: "window_switch")
            }

            lastActiveApp = appName
            lastActiveWindow = windowTitle

            Task {
                await captureCurrentState(reason: "focus_change")
            }
        }
    }

    private func getActiveWindowTitle() -> String {
        guard let frontApp = NSWorkspace.shared.frontmostApplication else {
            return ""
        }

        // Use Accessibility API to get window title
        let appElement = AXUIElementCreateApplication(frontApp.processIdentifier)
        var focusedWindow: AnyObject?
        AXUIElementCopyAttributeValue(appElement, kAXFocusedWindowAttribute as CFString, &focusedWindow)

        if let windowElement = focusedWindow {
            var title: AnyObject?
            AXUIElementCopyAttributeValue(windowElement as! AXUIElement, kAXTitleAttribute as CFString, &title)
            return title as? String ?? ""
        }

        return ""
    }

    private func captureCurrentState(reason: String) async {
        guard !isPaused, !isPrivateMode else { return }

        // Rate limit: min 30 seconds between captures
        if let lastCapture = lastCaptureTime, Date().timeIntervalSince(lastCapture) < 30 {
            return
        }
        lastCaptureTime = Date()

        let appName = lastActiveApp ?? "Unknown"
        let windowTitle = lastActiveWindow ?? ""

        // Capture screenshot if permission granted
        var screenshotBase64: String? = nil
        let canCapture = capturesScreenshots && PermissionManager.shared.screenCaptureGranted

        if canCapture {
            if #available(macOS 14.0, *) {
                screenshotBase64 = await captureScreenshot()
                if screenshotBase64 != nil {
                    print("Screenshot captured (\(screenshotBase64!.count) encoded bytes)")
                }
            }
        }

        // Create event
        let event = CapturedEvent(
            type: "window_focus",
            timestamp: Date(),
            data: [
                "app": appName,
                "window": windowTitle,
                "reason": reason,
                "has_screenshot": screenshotBase64 != nil ? "true" : "false"
            ],
            textContent: "App: \(appName) | Title: \(windowTitle) | Reason: \(reason)",
            screenshotBase64: screenshotBase64
        )

        // Send to backend
        do {
            try await APIClient.shared.sendEvent(event)
            print("Event sent: \(appName) - \(reason)")
        } catch {
            print("Failed to send event: \(error.localizedDescription)")
        }
    }

    @available(macOS 14.0, *)
    private func captureScreenshot() async -> String? {
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            guard let display = content.displays.first else { return nil }

            let filter = SCContentFilter(display: display, excludingWindows: [])
            let config = SCStreamConfiguration()
            config.width = Int(display.width) / 2  // Half resolution for performance
            config.height = Int(display.height) / 2

            let image = try await SCScreenshotManager.captureImage(
                contentFilter: filter,
                configuration: config
            )

            // Convert to JPEG and base64
            let cgImage = image
            let bitmapRep = NSBitmapImageRep(cgImage: cgImage)
            guard let jpegData = bitmapRep.representation(using: .jpeg, properties: [.compressionFactor: 0.5]) else {
                return nil
            }

            return jpegData.base64EncodedString()
        } catch {
            print("Screenshot capture failed: \(error)")
            return nil
        }
    }
}
