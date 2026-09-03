// swift-tools-version: 5.9
// NeuralMemoryAgent Swift Package
// Note: For full app build with Info.plist, use Xcode

import PackageDescription

let package = Package(
    name: "NeuralMemoryAgent",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "NeuralMemoryAgent",
            targets: ["NeuralMemoryAgent"]
        )
    ],
    targets: [
        .executableTarget(
            name: "NeuralMemoryAgent",
            path: "NeuralMemoryAgent",
            exclude: ["Info.plist", "NeuralMemoryAgent.entitlements"],
            resources: [
                .process("Assets.xcassets")
            ]
        ),
        .testTarget(
            name: "NeuralMemoryAgentTests",
            dependencies: ["NeuralMemoryAgent"],
            path: "Tests"
        )
    ]
)
