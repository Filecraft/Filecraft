import Foundation

public enum CompressionProfile: String, CaseIterable, Sendable {
    case balanced, smallFile, grayscale

    public var title: String {
        switch self {
        case .balanced: "Balanced"
        case .smallFile: "Small File"
        case .grayscale: "Grayscale"
        }
    }
    // No profile goes below 960 pixels / 0.45 JPEG quality.
    var attempts: [(Int, Double)] {
        switch self {
        case .balanced, .grayscale: [(2400, 0.85), (2000, 0.75), (1600, 0.65), (1200, 0.55), (960, 0.45)]
        case .smallFile: [(1600, 0.65), (1200, 0.55), (960, 0.45)]
        }
    }
    public var maximumPasses: Int { attempts.count }
}
