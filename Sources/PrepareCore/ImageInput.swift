import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

/// Shared validation for output and preview. Never decode a full-resolution source.
enum ImageInput {
    static func validatedSource(_ url: URL) throws -> (CGImageSource, Int) {
        try Task.checkCancellation()
        guard url.isFileURL else { throw PrepareError.invalidInput("Only local image files are supported. Nothing is downloaded.") }
        let values = try url.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
        let allowed = [UTType.jpeg.identifier, UTType.png.identifier, UTType.heic.identifier]
        guard values.isRegularFile == true, let size = values.fileSize, size <= 40_000_000,
              let source = CGImageSourceCreateWithURL(url as CFURL, [kCGImageSourceShouldCache: false] as CFDictionary),
              let type = CGImageSourceGetType(source), allowed.contains(type as String), CGImageSourceGetCount(source) == 1 else {
            throw PrepareError.invalidInput("\(url.lastPathComponent): unreadable or unsupported image. Choose a single-frame JPEG, PNG or HEIC up to 40 MB. PDFs are not accepted.")
        }
        let props = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
        guard let width = props?[kCGImagePropertyPixelWidth] as? Int,
              let height = props?[kCGImagePropertyPixelHeight] as? Int,
              width > 0, height > 0, width <= 20_000, height <= 20_000,
              Int64(width) * Int64(height) <= 80_000_000 else {
            throw PrepareError.invalidInput("\(url.lastPathComponent): image exceeds the 80-megapixel input limit.")
        }
        return (source, size)
    }
    static func orientedSize(_ url: URL) throws -> (width: Int, height: Int) {
        let (source, _) = try validatedSource(url)
        let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as! [CFString: Any]
        let width = properties[kCGImagePropertyPixelWidth] as! Int
        let height = properties[kCGImagePropertyPixelHeight] as! Int
        let orientation = properties[kCGImagePropertyOrientation] as? Int ?? 1
        return (5...8).contains(orientation) ? (height, width) : (width, height)
    }
    static func thumbnail(_ url: URL, edge: Int) throws -> CGImage {
        let (source, _) = try validatedSource(url)
        guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: edge
        ] as CFDictionary) else {
            throw PrepareError.invalidInput("\(url.lastPathComponent): image pixels could not be decoded. Try exporting a fresh copy in Preview.")
        }
        try Task.checkCancellation()
        return image
    }
}
