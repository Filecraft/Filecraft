import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import PrepareCore
import PrepareWorkspace

private final class ImageSizes {
    var values: [CGSize] = []
}

/// Inspect the images actually embedded in the PDF, not the pass's edge label.
func embeddedImageSizes(_ data: Data, page index: Int = 1) throws -> [CGSize] {
    guard let provider = CGDataProvider(data: data as CFData), let document = CGPDFDocument(provider),
          let page = document.page(at: index) else {
        throw NSError(domain: "PrepareChecks", code: 5)
    }
    var resources: CGPDFDictionaryRef?, objects: CGPDFDictionaryRef?
    try require(CGPDFDictionaryGetDictionary(page.dictionary!, "Resources", &resources), "PDF has resources")
    try require(CGPDFDictionaryGetDictionary(resources!, "XObject", &objects), "PDF has image objects")
    let sizes = ImageSizes()
    CGPDFDictionaryApplyFunction(objects!, { _, object, info in
        var stream: CGPDFStreamRef?
        guard CGPDFObjectGetValue(object, .stream, &stream), let stream,
              let dict = CGPDFStreamGetDictionary(stream) else { return }
        var subtype: UnsafePointer<CChar>?
        guard CGPDFDictionaryGetName(dict, "Subtype", &subtype), let subtype,
              String(cString: subtype) == "Image" else { return }
        var width: CGPDFInteger = 0, height: CGPDFInteger = 0
        guard CGPDFDictionaryGetInteger(dict, "Width", &width), CGPDFDictionaryGetInteger(dict, "Height", &height) else { return }
        Unmanaged<ImageSizes>.fromOpaque(info!).takeUnretainedValue().values.append(CGSize(width: width, height: height))
    }, Unmanaged.passUnretained(sizes).toOpaque())
    return sizes.values
}

func checkMoveSelectedLast(input: URL) throws {
    let entries = (0..<3).map { _ in PageEntry(url: input) }
    var pages = PageSelection(entries: entries)
    pages.select(entries[1].id)
    try require(pages.moveSelectedLast(), "Move selected last changes order")
    try require(pages.entries.map(\.id) == [entries[0].id, entries[2].id, entries[1].id] && pages.selectedID == entries[1].id,
                "Move selected last preserves identity and relative order")
    try require(!pages.moveSelectedLast(), "Already last is a no-op")
    pages.select(entries[0].id)
    let before = pages.entries
    try require(!pages.moveSelectedLast(isBusy: true) && pages.entries == before, "Busy move is a no-op")
    var empty = PageSelection()
    try require(!empty.moveSelectedLast(), "Empty move is a no-op")
    print("PASS: move selected last preserves identity and order; last/busy/empty no-ops")
}

func checkDuplicateSelected(input: URL) throws {
    var first = PageEntry(url: input)
    first.rotation = .clockwise270
    let second = PageEntry(url: input)
    var pages = PageSelection(entries: [first, second])
    try require(pages.duplicateSelected(), "Duplicate selected changes collection")
    try require(pages.entries.count == 3 && pages.entries[0].id == first.id && pages.entries[2].id == second.id,
                "Duplicate inserts immediately after selected page without changing originals")
    let copy = pages.entries[1]
    try require(copy.id != first.id && copy.id != second.id && copy.page == first.page,
                "Duplicate has fresh identity and exact URL and rotation")
    try require(pages.selectedID == copy.id, "Duplicate selects the new copy")
    pages.rotateSelected()
    try require(pages.entries[0].rotation == .clockwise270 && pages.selected?.rotation == PageRotation.none,
                "Duplicated rotation edits are independent")
    let before = pages.entries
    try require(!pages.duplicateSelected(isBusy: true) && pages.entries == before, "Busy duplication is a no-op")
    var empty = PageSelection()
    try require(!empty.duplicateSelected() && empty.selectedID == nil, "Empty duplication is a no-op")
    var full = PageSelection(entries: (0..<19).map { _ in PageEntry(url: input) })
    try require(full.duplicateSelected() && full.entries.count == 20, "Duplicate accepts twentieth page")
    let fullBefore = full.entries, selected = full.selectedID
    try require(!full.duplicateSelected() && full.entries == fullBefore && full.selectedID == selected,
                "Duplicate cannot exceed twenty pages or disturb selection")
    print("PASS: duplicate selected identity, insertion, independent rotation and 20-page/busy/empty guards")
}

@MainActor
func checkWorkspacePageActions(input: URL) async throws {
    let workspace = Workspace()
    defer { workspace.shutdown() }
    workspace.add([input, input])
    let firstID = workspace.inputs[0].id
    workspace.rotate(firstID)
    workspace.prepare()
    workspace.duplicateSelected(); workspace.moveSelectedLast()
    try require(workspace.inputs.count == 2 && workspace.selection.selectedID == firstID,
                "Workspace blocks selected-page actions during preparation")
    while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
    while workspace.previewLoading { try await Task.sleep(for: .milliseconds(10)) }
    workspace.reviewed = true
    workspace.duplicateSelected()
    try require(workspace.inputs.count == 3 && workspace.selection.selectedIndex == 1 && workspace.selection.selectedID != firstID,
                "Workspace duplicates and selects fresh identity")
    try require(workspace.result == nil && !workspace.reviewed && workspace.preview == nil,
                "Duplicate discards stale comparison and review")
    let copyID = workspace.selection.selectedID
    workspace.prepare()
    while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
    try require(workspace.result?.pageCount == 3, "Duplicate exports a real additional page")
    let pixels = try renderedPage(workspace.result!.data, index: 2)
    try require(pixels.width > pixels.height, "Duplicated page retains rotation in real output")
    workspace.reviewed = true
    workspace.moveSelectedLast()
    try require(workspace.selection.selectedID == copyID && workspace.selection.selectedIndex == 2 && workspace.result == nil && !workspace.reviewed,
                "Move to last preserves identity and invalidates output")
    workspace.prepare()
    while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
    while workspace.previewLoading { try await Task.sleep(for: .milliseconds(10)) }
    workspace.reviewed = true
    workspace.moveSelectedLast()
    try require(workspace.result != nil && workspace.reviewed && workspace.preview?.output != nil,
                "No-op move preserves valid reviewed output")
    for _ in 0..<40 { workspace.duplicateSelected(); workspace.moveSelectedLast() }
    try require(workspace.inputs.count == 20, "Workspace enforces twenty-page duplicate cap")
    while workspace.previewLoading { try await Task.sleep(for: .milliseconds(10)) }
    try require(workspace.preview?.source != nil && workspace.preview?.output == nil, "Rapid selected-page edits settle without stale output")
    print("PASS: workspace duplicate/move output, busy guards, cap, identity and stale-preview invalidation")
}

@MainActor
func checkWorkspaceDPI(input: URL) async throws {
    let workspace = Workspace()
    defer { workspace.shutdown() }
    workspace.add([input])
    workspace.applyPreset(.application2MB)
    let identity = workspace.selection.selectedID
    workspace.dpiCeiling = .dpi150
    try require(workspace.settings?.dpiCeiling == .dpi150 && workspace.activePreset == nil,
                "DPI is captured in settings and customizes preset")
    workspace.prepare()
    while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
    while workspace.previewLoading { try await Task.sleep(for: .milliseconds(10)) }
    try require(workspace.result != nil && workspace.preview?.output != nil, "DPI workspace prepares exact comparison")
    workspace.reviewed = true
    workspace.dpiCeiling = .dpi200
    try require(workspace.result == nil && !workspace.reviewed && workspace.preview?.output == nil,
                "DPI edit clears stale prepared output and review immediately")
    try require(workspace.selection.selectedID == identity, "DPI edit preserves page identity")
    workspace.applyPreset(.application2MB)
    try require(workspace.dpiCeiling == .automatic && workspace.activePreset == .application2MB,
                "Presets restore v0.4 automatic DPI defaults")
    print("PASS: workspace DPI capture, preset reset, identity and stale-output invalidation")
}

func checkDPICeiling(folder: URL) throws {
    let url = folder.appendingPathComponent("dpi-wide.png")
    let canvas = CGContext(data: nil, width: 3000, height: 1500, bitsPerComponent: 8, bytesPerRow: 0,
                           space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    canvas.setFillColor(CGColor(gray: 0.5, alpha: 1)); canvas.fill(CGRect(x: 0, y: 0, width: 3000, height: 1500))
    let writer = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(writer, canvas.makeImage()!, nil)
    try require(CGImageDestinationFinalize(writer), "DPI fixture writes")
    let settings = PageSettings(paper: .usLetter, margin: 72, dpiCeiling: .dpi150)
    let output = try Preparation.run(pages: [PreparationPage(url: url)], settings: settings, maxBytes: 1_000_000)
    let images = try embeddedImageSizes(output.data)
    // Actual image area is 468 × 234 pt, NOT the 468 × 648 available box.
    try require(images == [CGSize(width: 975, height: 487)], "150 DPI uses actual Letter content, rounds down, never the whole paper")
    print("PASS: explicit DPI ceiling limits actual embedded PDF image against content points")
}
