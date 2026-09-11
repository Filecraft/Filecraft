import Foundation

/// Source-level wiring contract complements exercised Workspace behavior checks.
/// Not a substitute for native accessibility / layout inspection on macOS.
func checkUIContract() throws {
    let sources = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
    let ui = try String(contentsOf: sources.appendingPathComponent("Prepare/main.swift"), encoding: .utf8)
    for token in [
        "Workflow preset", "Compression profile", "Advanced layout", "Review workbench",
        "Sort by filename", "Reverse order", "Rotate all", "Clear pages…", "Clear all pages?",
        "Source · original color", "Exact output ·", "Save a copy…",
        "model.applyPreset", "selection: $model.profile", "model.batch(.sortByFilename)",
        "model.batch(.reverse)", "model.batch(.rotateAll)", "model.batch(.clear)",
        ".confirmationDialog", "private var actionToolbar", "private var sidebar"
    ] {
        try require(ui.contains(token), "UI contract missing label or action wiring: \(token)")
    }
    print("PASS: UI source wiring contract for sidebar, profiles, presets, actions and review labels")
}
