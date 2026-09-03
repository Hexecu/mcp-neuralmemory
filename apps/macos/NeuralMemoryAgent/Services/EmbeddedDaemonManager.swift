// EmbeddedDaemonManager.swift
// Manages the embedded standalone neural-memory-daemon child process

import Foundation
import os.log

@MainActor
final class EmbeddedDaemonManager {
    static let shared = EmbeddedDaemonManager()

    private let logger = Logger(subsystem: "com.neuralcode.neuralmemoryagent", category: "EmbeddedDaemonManager")
    private var daemonProcess: Process?
    private(set) var isManagedByApp = false

    private init() {}

    func ensureDaemonRunning() async {
        let appState = AppState.shared
        let healthURLString = appState.serverURL + "/health"

        // 1. Check if daemon or Open Local is already running
        if await isServerReachable(urlString: healthURLString) {
            logger.info("Neural Memory daemon or Open Local container already running on port 8765")
            return
        }

        // 2. Locate embedded standalone daemon binary
        guard let daemonExecutableURL = findDaemonExecutable() else {
            logger.warning("No embedded neural-memory-daemon binary found. Relying on external setup.")
            return
        }

        logger.info("Starting embedded neural-memory-daemon from: \(daemonExecutableURL.path)")

        // 3. Prepare log directory
        let logDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/NeuralMemoryAgent")
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
        let logFile = logDir.appendingPathComponent("daemon.log")

        // 4. Launch Process
        let process = Process()
        process.executableURL = daemonExecutableURL
        process.arguments = ["--port", "8765"]

        // Redirect stdout and stderr to log file
        if let outputHandle = try? FileHandle(forWritingTo: logFile) {
            outputHandle.seekToEndOfFile()
            process.standardOutput = outputHandle
            process.standardError = outputHandle
        } else if FileManager.default.createFile(atPath: logFile.path, contents: nil) {
            if let outputHandle = try? FileHandle(forWritingTo: logFile) {
                process.standardOutput = outputHandle
                process.standardError = outputHandle
            }
        }

        do {
            try process.run()
            self.daemonProcess = process
            self.isManagedByApp = true
            logger.info("Embedded daemon process launched with PID: \(process.processIdentifier)")

            // 5. Poll until healthy (up to 3 seconds)
            for _ in 0..<15 {
                try? await Task.sleep(nanoseconds: 200_000_000)
                if await isServerReachable(urlString: healthURLString) {
                    logger.info("Embedded daemon healthy and ready.")
                    break
                }
            }
        } catch {
            logger.error("Failed to run embedded daemon process: \(error.localizedDescription)")
        }
    }

    func stop() {
        if let process = daemonProcess, process.isRunning {
            logger.info("Terminating embedded daemon PID \(process.processIdentifier)...")
            process.terminate()
            daemonProcess = nil
            isManagedByApp = false
        }
    }

    private func findDaemonExecutable() -> URL? {
        // Look inside .app bundle Contents/MacOS/
        if let bundleExecURL = Bundle.main.executableURL?.deletingLastPathComponent()
            .appendingPathComponent("neural-memory-daemon"),
           FileManager.default.isExecutableFile(atPath: bundleExecURL.path) {
            return bundleExecURL
        }

        // Look inside Contents/Resources/
        if let resURL = Bundle.main.resourceURL?.appendingPathComponent("neural-memory-daemon"),
           FileManager.default.isExecutableFile(atPath: resURL.path) {
            return resURL
        }

        // Look in local project dist_daemon (for development testing)
        let localPath = FileManager.default.currentDirectoryPath + "/dist_daemon/neural-memory-daemon/neural-memory-daemon"
        if FileManager.default.isExecutableFile(atPath: localPath) {
            return URL(fileURLWithPath: localPath)
        }

        return nil
    }

    private func isServerReachable(urlString: String) async -> Bool {
        guard let url = URL(string: urlString) else { return false }
        var request = URLRequest(url: url)
        request.timeoutInterval = 1.0
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else { return false }
            return APIClient.isNeuralMemoryHealthResponse(data: data, statusCode: httpResponse.statusCode)
        } catch {
            return false
        }
    }
}
