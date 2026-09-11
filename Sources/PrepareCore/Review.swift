import Foundation
import CoreGraphics

public enum SourcePreview {
    public static let longestEdge = 1600
    /// Downsampled source, EXIF-corrected and laid out like the output. No JPEG re-encoding.
    /// Call off the main actor; at most one source thumbnail is decoded by each call.
    public static func render(page: PreparationPage, settings: PageSettings) throws -> Data {
        try autoreleasepool {
            try settings.validate()
            let image = try ImageInput.thumbnail(page.url, edge: longestEdge)
            let layout = try settings.layout(width: image.width, height: image.height, rotation: page.rotation)
            let data = NSMutableData()
            guard let consumer = CGDataConsumer(data: data as CFMutableData),
                  let pdf = CGContext(consumer: consumer, mediaBox: nil, nil) else {
                throw PrepareError.invalidInput("Could not create a source preview.")
            }
            var box = layout.paper
            pdf.beginPDFPage([kCGPDFContextMediaBox: NSData(bytes: &box, length: MemoryLayout<CGRect>.size)] as CFDictionary)
            pdf.setFillColor(CGColor(gray: 1, alpha: 1)); pdf.fill(box)
            let swaps = page.rotation.rawValue % 2 == 1
            let width = swaps ? layout.content.height : layout.content.width
            let height = swaps ? layout.content.width : layout.content.height
            pdf.translateBy(x: layout.content.midX, y: layout.content.midY)
            pdf.rotate(by: -Double(page.rotation.rawValue) * .pi / 2)
            pdf.draw(image, in: CGRect(x: -width / 2, y: -height / 2, width: width, height: height))
            pdf.endPDFPage(); pdf.closePDF()
            try Task.checkCancellation()
            return data as Data
        }
    }
}

public enum ReviewDocument {
    /// One-page PDF prevents PDFView's own navigation from drifting out of sync.
    /// This copies the actual PDF page drawing commands, not a thumbnail of the output.
    public static func page(data: Data, at index: Int) throws -> Data {
        try Task.checkCancellation()
        guard let provider = CGDataProvider(data: data as CFData), let document = CGPDFDocument(provider),
              index >= 0, index < document.numberOfPages, let page = document.page(at: index + 1) else {
            throw PrepareError.invalidInput("The selected output page is unavailable.")
        }
        let output = NSMutableData()
        var box = page.getBoxRect(.mediaBox)
        guard let consumer = CGDataConsumer(data: output as CFMutableData),
              let pdf = CGContext(consumer: consumer, mediaBox: &box, nil) else {
            throw PrepareError.invalidInput("Could not display the selected output page.")
        }
        pdf.beginPDFPage(nil); pdf.drawPDFPage(page); pdf.endPDFPage(); pdf.closePDF()
        try Task.checkCancellation()
        return output as Data
    }
}
