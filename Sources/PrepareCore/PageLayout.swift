import Foundation
import CoreGraphics

public enum PageRotation: Int, CaseIterable, Sendable {
    case none = 0, clockwise90 = 1, clockwise180 = 2, clockwise270 = 3
    public var next: PageRotation { PageRotation(rawValue: (rawValue + 1) % 4)! }
}

public enum PaperFormat: String, CaseIterable, Sendable {
    case original, a4, usLetter
}
public struct PageSettings: Sendable, Equatable {
    public var paper: PaperFormat
    public var margin: Double
    public init(paper: PaperFormat = .original, margin: Double = 0) {
        self.paper = paper; self.margin = margin
    }

    /// Original means image aspect ratio with a 720-point longest page edge,
    /// matching Prepare's legacy output; it does not infer physical scan DPI.
    public func layout(width: Int, height: Int, rotation: PageRotation) throws -> PageLayout {
        try validate()
        guard width > 0, height > 0, width <= 20_000, height <= 20_000 else {
            throw PrepareError.invalidInput("Invalid image dimensions for page layout.")
        }
        let swapped = rotation.rawValue % 2 == 1
        let w = Double(swapped ? height : width), h = Double(swapped ? width : height)
        let size: CGSize
        switch paper {
        case .original: size = CGSize(width: w * 720 / max(w, h), height: h * 720 / max(w, h))
        case .a4: size = CGSize(width: 210 * 72 / 25.4, height: 297 * 72 / 25.4)
        case .usLetter: size = CGSize(width: 612, height: 792)
        }
        guard margin * 2 < min(size.width, size.height) else {
            throw PrepareError.invalidInput("The margin leaves no image area. Reduce it or choose A4 or US Letter.")
        }
        let available = CGRect(origin: .zero, size: size).insetBy(dx: margin, dy: margin)
        let scale = min(available.width / w, available.height / h)
        let content = CGRect(x: (size.width - w * scale) / 2, y: (size.height - h * scale) / 2,
                             width: w * scale, height: h * scale)
        return PageLayout(paper: CGRect(origin: .zero, size: size), content: content)
    }
    public func validate() throws {
        guard margin.isFinite, (0...360).contains(margin) else {
            throw PrepareError.invalidInput("Enter a margin from 0 to 360 points (72 points = 1 inch).")
        }
    }
}
public struct PageLayout: Sendable {
    public let paper: CGRect
    public let content: CGRect
}

public struct PreparationPage: Sendable, Equatable {
    public let url: URL
    public var rotation: PageRotation
    public init(url: URL, rotation: PageRotation = .none) {
        self.url = url; self.rotation = rotation
    }
}
