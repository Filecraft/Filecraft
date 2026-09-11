import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

public struct PreparationProgress: Sendable {
    public let pass: Int
    public let page: Int
    public let totalPages: Int
}
public struct Prepared: Sendable {
    public let profile: CompressionProfile
    public let originalBytes: Int

    public let data: Data
    public let pageCount: Int
    public let longestEdge: Int
    public let quality: Double
}
public enum PrepareError: LocalizedError {
    case invalidInput(String)
    case cannotFit
    public var errorDescription: String? {
        switch self {
        case .invalidInput(let reason): reason
        case .cannotFit: "Cannot meet this limit within the quality floor. Try fewer pages or a larger limit."
        }
    }
}
public enum Preparation {
    public static func save(_ result: Prepared, to url: URL) throws {
        // Exclusive creation: reject an existing path, including an original input.
        try result.data.write(to: url, options: .withoutOverwriting)
    }
    // Bounded attempts and input limits, not a promise of visual fidelity.
    public static func run(inputs: [URL], profile: CompressionProfile = .balanced, maxBytes: Int, progress: @Sendable (PreparationProgress) -> Void = { _ in }) throws -> Prepared {
        try run(pages: inputs.map { PreparationPage(url: $0) }, profile: profile, maxBytes: maxBytes, progress: progress)
    }
    public static func run(pages: [PreparationPage], settings: PageSettings = PageSettings(), profile: CompressionProfile = .balanced, maxBytes: Int, progress: @Sendable (PreparationProgress) -> Void = { _ in }) throws -> Prepared {
        try settings.validate()
        let inputs = pages.map(\.url)
        guard !inputs.isEmpty, inputs.count <= 20, (1...100_000_000).contains(maxBytes) else {
            throw PrepareError.invalidInput("Choose 1–20 still images and a limit up to 100 MB.")
        }
        var originalBytes = 0
        for url in inputs {
            let (_, size) = try ImageInput.validatedSource(url)
            originalBytes += size
        }
        let attempts = profile.attempts
        for (index, attempt) in attempts.enumerated() {
            let (edge, quality) = attempt
            try Task.checkCancellation()
            let data = try autoreleasepool { try render(pages: pages, settings: settings, profile: profile, edge: edge, quality: quality, pass: index + 1, progress: progress) }
            try Task.checkCancellation()
            if data.count <= maxBytes {
                return Prepared(profile: profile, originalBytes: originalBytes, data: data, pageCount: inputs.count, longestEdge: edge, quality: quality)
            }
        }
        throw PrepareError.cannotFit
    }
    private static func render(pages: [PreparationPage], settings: PageSettings, profile: CompressionProfile, edge: Int, quality: Double, pass: Int, progress: @Sendable (PreparationProgress) -> Void) throws -> Data {
        let output = NSMutableData()
        guard let consumer = CGDataConsumer(data: output as CFMutableData),
              let pdf = CGContext(consumer: consumer, mediaBox: nil, nil) else {
            throw PrepareError.invalidInput("Could not create a PDF document.")
        }
        var closed = false
        defer { if !closed { pdf.closePDF() } }
        for (index, page) in pages.enumerated() {
            let url = page.url
            try Task.checkCancellation()
            try autoreleasepool {
                let image = try ImageInput.thumbnail(url, edge: edge)
                // Flatten transparency over white and omit source metadata.
                // A single-component gray buffer produces a genuinely grayscale JPEG,
                // not an RGB image merely decorated with a display-only filter.
                let gray = profile == .grayscale
                guard let canvas = CGContext(data: nil, width: image.width, height: image.height,
                     bitsPerComponent: 8, bytesPerRow: 0, space: gray ? CGColorSpaceCreateDeviceGray() : CGColorSpaceCreateDeviceRGB(),
                     bitmapInfo: gray ? CGImageAlphaInfo.none.rawValue : CGImageAlphaInfo.noneSkipLast.rawValue) else {
                    throw PrepareError.invalidInput("Could not allocate an image buffer.")
                }
                let imageRect = CGRect(x: 0, y: 0, width: image.width, height: image.height)
                canvas.setFillColor(CGColor(gray: 1, alpha: 1)); canvas.fill(imageRect)
                canvas.draw(image, in: imageRect)
                let compressed = NSMutableData()
                guard let flattened = canvas.makeImage(),
                      let destination = CGImageDestinationCreateWithData(compressed, UTType.jpeg.identifier as CFString, 1, nil) else {
                    throw PrepareError.invalidInput("Could not encode an image.")
                }
                CGImageDestinationAddImage(destination, flattened, [kCGImageDestinationLossyCompressionQuality: quality] as CFDictionary)
                guard CGImageDestinationFinalize(destination),
                      let provider = CGDataProvider(data: compressed as CFData),
                      let jpeg = CGImage(jpegDataProviderSource: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else {
                    throw PrepareError.invalidInput("Image encoding failed.")
                }
                let layout = try settings.layout(width: jpeg.width, height: jpeg.height, rotation: page.rotation)
                let swaps = page.rotation.rawValue % 2 == 1
                let width = swaps ? layout.content.height : layout.content.width
                let height = swaps ? layout.content.width : layout.content.height
                var rect = layout.paper
                let rectData = NSData(bytes: &rect, length: MemoryLayout<CGRect>.size)
                pdf.beginPDFPage([kCGPDFContextMediaBox: rectData] as CFDictionary)
                pdf.setFillColor(CGColor(gray: 1, alpha: 1)); pdf.fill(rect)
                pdf.saveGState()
                pdf.translateBy(x: layout.content.midX, y: layout.content.midY)
                pdf.rotate(by: -Double(page.rotation.rawValue) * .pi / 2)
                pdf.draw(jpeg, in: CGRect(x: -width / 2, y: -height / 2, width: width, height: height))
                pdf.restoreGState()
                pdf.endPDFPage()
            }
            progress(PreparationProgress(pass: pass, page: index + 1, totalPages: pages.count))
        }
        pdf.closePDF()
        closed = true
        return output as Data
    }
}
