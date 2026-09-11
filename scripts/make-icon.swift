import AppKit

// Original Prepare artwork: stacked paper and a precise green check.
let arguments = CommandLine.arguments
precondition(arguments.count == 2, "Usage: swift scripts/make-icon.swift <output.iconset>")
let folder = URL(fileURLWithPath: arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let image = NSImage(size: NSSize(width: pixels, height: pixels))
        image.lockFocus()
        let transform = AffineTransform(scale: CGFloat(pixels) / 1024)
        (transform as NSAffineTransform).concat()
        NSColor(calibratedRed: 0.10, green: 0.27, blue: 0.23, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: 48, y: 48, width: 928, height: 928), xRadius: 214, yRadius: 214).fill()
        NSColor(calibratedRed: 0.47, green: 0.64, blue: 0.52, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: 247, y: 243, width: 532, height: 597), xRadius: 37, yRadius: 37).fill()
        NSColor(calibratedRed: 0.96, green: 0.96, blue: 0.90, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: 198, y: 184, width: 532, height: 597), xRadius: 37, yRadius: 37).fill()
        NSColor(calibratedRed: 0.67, green: 0.73, blue: 0.65, alpha: 1).setStroke()
        for y in [656, 594, 532] {
            let line = NSBezierPath()
            line.lineWidth = 18; line.lineCapStyle = .round
            line.move(to: NSPoint(x: 286, y: y)); line.line(to: NSPoint(x: y == 532 ? 475 : 633, y: y)); line.stroke()
        }
        NSColor(calibratedRed: 0.10, green: 0.35, blue: 0.27, alpha: 1).setStroke()
        let check = NSBezierPath(); check.lineWidth = 47; check.lineCapStyle = .round; check.lineJoinStyle = .round
        check.move(to: NSPoint(x: 386, y: 362)); check.line(to: NSPoint(x: 457, y: 291)); check.line(to: NSPoint(x: 590, y: 427)); check.stroke()
        image.unlockFocus()
        guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff),
              let data = bitmap.representation(using: .png, properties: [:]) else { fatalError("Icon rendering failed") }
        let suffix = scale == 2 ? "@2x" : ""
        try data.write(to: folder.appendingPathComponent("icon_\(size)x\(size)\(suffix).png"))
    }
}
print("Generated Prepare icon artwork")
