// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Prepare", platforms: [.macOS(.v14)], products: [
    .executable(name: "Prepare", targets: ["Prepare"]),
    .executable(name: "PrepareChecks", targets: ["PrepareChecks"])
], targets: [
    .target(name: "PrepareCore"),
    .executableTarget(name: "Prepare", dependencies: ["PrepareCore"]),
    .executableTarget(name: "PrepareChecks", dependencies: ["PrepareCore"])
])
