import Foundation

/// Starting points, not guarantees of acceptance by any particular website.
public enum WorkflowPreset: String, CaseIterable, Sendable {
    case portal500KB, application2MB, photoOriginal

    public var title: String {
        switch self {
        case .portal500KB: "Portal · 500 KB"
        case .application2MB: "Application · 2 MB"
        case .photoOriginal: "Photo · original aspect"
        }
    }
    public var maxBytes: Int {
        switch self {
        case .portal500KB: 500_000
        case .application2MB: 2_000_000
        case .photoOriginal: 10_000_000
        }
    }
    public var profile: CompressionProfile { self == .portal500KB ? .smallFile : .balanced }
    public var settings: PageSettings {
        self == .application2MB ? PageSettings(paper: .a4, margin: 24) : PageSettings()
    }
}
